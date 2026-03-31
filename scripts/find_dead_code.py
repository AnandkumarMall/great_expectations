#!/usr/bin/env python3
"""Dead code detection for the GX codebase.

Identifies code not reachable from @public_api roots by building a dependency
graph through AST-based static analysis.

Layers:
  1. Module-level reachability (high confidence)
  2. Symbol-level reachability (medium confidence)
  3. Dynamic import awareness (patches Layers 1 & 2)
  4. Test suite analysis

Usage:
  python scripts/find_dead_code.py --verbose
  python scripts/find_dead_code.py --layer 1 --verbose
  python scripts/find_dead_code.py --json-output dead_code_report.json
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any

# ============================================================
# Layer identifiers
# ============================================================

_LAYER_MODULE = 1
_LAYER_SYMBOL = 2
_LAYER_DYNAMIC = 3
_LAYER_TEST = 4

# Which layers to run for each --layer value
_LAYER_SETS: dict[str, set[int]] = {
    "1": {_LAYER_MODULE, _LAYER_DYNAMIC},
    "2": {_LAYER_MODULE, _LAYER_SYMBOL, _LAYER_DYNAMIC},
    "3": {_LAYER_MODULE, _LAYER_DYNAMIC},
    "4": {_LAYER_MODULE, _LAYER_DYNAMIC, _LAYER_TEST},
    "all": {_LAYER_MODULE, _LAYER_SYMBOL, _LAYER_DYNAMIC, _LAYER_TEST},
}

# config_defaults is the 3rd positional arg (index 2) of instantiate_class_from_config
_CONFIG_DEFAULTS_ARG_INDEX = 2

# ============================================================
# Data classes
# ============================================================


@dataclass
class ModuleInfo:
    filepath: pathlib.Path
    module_name: str
    is_init: bool
    imports: set[str] = field(default_factory=set)
    imported_names: dict[str, tuple[str, str]] = field(
        default_factory=dict
    )  # local_name -> (source_module, original_name)
    star_imports: list[str] = field(default_factory=list)  # modules we star-import from
    defined_symbols: dict[str, int] = field(default_factory=dict)  # name -> line_number
    public_api_symbols: set[str] = field(default_factory=set)
    all_exports: list[str] | None = None


@dataclass
class DeadCodeCandidate:
    filepath: str
    module_name: str
    symbol_name: str | None = None
    line_number: int | None = None
    confidence: str = "high"
    reason: str = ""


@dataclass
class DeadCodeReport:
    dead_modules: list[DeadCodeCandidate] = field(default_factory=list)
    dead_symbols: list[DeadCodeCandidate] = field(default_factory=list)
    dead_tests: list[DeadCodeCandidate] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    known_exceptions_applied: list[str] = field(default_factory=list)


# ============================================================
# Layer 1: Module Graph Builder
# ============================================================


class ModuleGraphBuilder:
    """Discovers modules, parses imports, and builds the module dependency graph."""

    def __init__(self, package_root: pathlib.Path):
        self.package_root = package_root
        self.repo_root = package_root.parent
        self.package_name = package_root.name  # "great_expectations"
        self.modules: dict[str, ModuleInfo] = {}

    def discover_and_parse(self) -> None:
        """Discover all .py files and parse them."""
        for filepath in sorted(self.package_root.rglob("*.py")):
            module_name = self._filepath_to_module_name(filepath)
            if module_name:
                info = self._parse_module(filepath, module_name)
                self.modules[module_name] = info

    def _filepath_to_module_name(self, filepath: pathlib.Path) -> str | None:
        try:
            relative = filepath.relative_to(self.repo_root)
        except ValueError:
            return None
        parts = list(relative.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].removesuffix(".py")
        return ".".join(parts)

    def _parse_module(self, filepath: pathlib.Path, module_name: str) -> ModuleInfo:
        is_init = filepath.name == "__init__.py"
        info = ModuleInfo(filepath=filepath, module_name=module_name, is_init=is_init)

        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError):
            return info

        self._process_imports(_extract_runtime_imports(tree), module_name, is_init, info)
        self._extract_definitions(tree, info)
        self._extract_public_api_symbols(tree, info)
        self._extract_all_exports(tree, info)

        return info

    def _process_imports(
        self,
        runtime_imports: list[ast.Import | ast.ImportFrom],
        module_name: str,
        is_init: bool,
        info: ModuleInfo,
    ) -> None:
        for node in runtime_imports:
            if isinstance(node, ast.Import):
                self._process_import_node(node, info)
            elif isinstance(node, ast.ImportFrom):
                self._process_import_from_node(node, module_name, is_init, info)

    def _process_import_node(self, node: ast.Import, info: ModuleInfo) -> None:
        for alias in node.names:
            if alias.name.startswith(self.package_name):
                info.imports.add(alias.name)

    def _process_import_from_node(
        self, node: ast.ImportFrom, module_name: str, is_init: bool, info: ModuleInfo
    ) -> None:
        resolved = self._resolve_import_from(node, module_name, is_init)
        if not (resolved and resolved.startswith(self.package_name)):
            return

        info.imports.add(resolved)

        for alias in node.names:
            if alias.name == "*":
                info.star_imports.append(resolved)
            else:
                local_name = alias.asname or alias.name
                info.imported_names[local_name] = (resolved, alias.name)

        self._add_speculative_submodules(node, module_name, is_init, info)

    def _add_speculative_submodules(
        self, node: ast.ImportFrom, module_name: str, is_init: bool, info: ModuleInfo
    ) -> None:
        # "from . import X" — X might be a submodule, add it speculatively
        if node.module is not None or node.level <= 0:
            return
        base = self._resolve_relative_base(module_name, is_init, node.level)
        if not base:
            return
        for alias in node.names:
            if alias.name != "*":
                candidate = f"{base}.{alias.name}"
                if candidate.startswith(self.package_name):
                    info.imports.add(candidate)

    def _resolve_import_from(
        self, node: ast.ImportFrom, current_module: str, is_init: bool
    ) -> str | None:
        if node.level == 0:
            return node.module
        base = self._resolve_relative_base(current_module, is_init, node.level)
        if base is None:
            return None
        if node.module:
            return f"{base}.{node.module}"
        return base

    def _resolve_relative_base(
        self, current_module: str, is_init: bool, level: int
    ) -> str | None:
        package = current_module if is_init else current_module.rsplit(".", 1)[0]
        steps_up = level - 1
        pkg_parts = package.split(".")
        if steps_up >= len(pkg_parts):
            return None
        if steps_up > 0:
            pkg_parts = pkg_parts[:-steps_up]
        return ".".join(pkg_parts)

    @staticmethod
    def _extract_definitions(tree: ast.Module, info: ModuleInfo) -> None:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                info.defined_symbols[node.name] = node.lineno
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        info.defined_symbols[target.id] = node.lineno

    @staticmethod
    def _extract_public_api_symbols(tree: ast.Module, info: ModuleInfo) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == "public_api":
                    info.public_api_symbols.add(node.name)
                    break

    @staticmethod
    def _extract_all_exports(tree: ast.Module, info: ModuleInfo) -> None:
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        info.all_exports = [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]

    def build_module_edges(self) -> dict[str, set[str]]:
        """Build the module-level dependency graph, resolving to known modules."""
        edges: dict[str, set[str]] = defaultdict(set)

        for module_name, info in self.modules.items():
            for imported in info.imports:
                resolved = self._resolve_to_known_module(imported)
                if resolved:
                    edges[module_name].add(resolved)

            # Check if imported names are actually submodules
            for _local_name, (source_mod, original_name) in info.imported_names.items():
                candidate = f"{source_mod}.{original_name}"
                if candidate in self.modules:
                    edges[module_name].add(candidate)

        return edges

    def _resolve_to_known_module(self, module_name: str) -> str | None:
        if module_name in self.modules:
            return module_name
        # Maybe it refers to a name within a parent module
        parent, sep, _ = module_name.rpartition(".")
        if sep and parent in self.modules:
            return parent
        return None

    def find_root_modules(self) -> set[str]:
        roots = set()
        for module_name, info in self.modules.items():
            if info.public_api_symbols:
                roots.add(module_name)
        if self.package_name in self.modules:
            roots.add(self.package_name)
        return roots

    def bfs_reachable(self, roots: set[str], edges: dict[str, set[str]]) -> set[str]:
        visited: set[str] = set()
        queue = deque(roots)

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            # Python loads all parent __init__.py when importing a submodule.
            # Add ancestor packages so their edges are followed too.
            parts = node.split(".")
            for i in range(1, len(parts)):
                ancestor = ".".join(parts[:i])
                if ancestor in self.modules and ancestor not in visited:
                    queue.append(ancestor)

            for neighbor in edges.get(node, set()):
                if neighbor not in visited:
                    queue.append(neighbor)

        return visited


# ============================================================
# Layer 3: Dynamic Import Detector
# ============================================================


class DynamicImportDetector:
    """Detects dynamic import patterns that static import analysis misses."""

    def __init__(self, graph_builder: ModuleGraphBuilder):
        self.graph = graph_builder

    def detect_all(self) -> tuple[set[str], dict[str, set[str]], set[str]]:
        """Returns (extra_root_modules, extra_edges, extra_symbol_roots)."""
        extra_roots: set[str] = set()
        extra_edges: dict[str, set[str]] = defaultdict(set)
        extra_symbol_roots: set[str] = set()

        self._detect_instantiate_class_from_config(extra_roots, extra_edges)
        self._detect_config_class_names(extra_edges, extra_symbol_roots)

        return extra_roots, extra_edges, extra_symbol_roots

    @staticmethod
    def _is_instantiate_call(node: ast.Call) -> bool:
        func = node.func
        return (
            isinstance(func, ast.Name) and func.id == "instantiate_class_from_config"
        ) or (
            isinstance(func, ast.Attribute) and func.attr == "instantiate_class_from_config"
        )

    def _detect_instantiate_class_from_config(
        self, extra_roots: set[str], extra_edges: dict[str, set[str]]
    ) -> None:
        for module_name, info in self.graph.modules.items():
            try:
                source = info.filepath.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not self._is_instantiate_call(node):
                    continue
                self._extract_config_defaults(node, module_name, extra_roots, extra_edges)

    def _extract_config_defaults(
        self,
        node: ast.Call,
        module_name: str,
        extra_roots: set[str],
        extra_edges: dict[str, set[str]],
    ) -> None:
        for kw in node.keywords:
            if kw.arg == "config_defaults" and isinstance(kw.value, ast.Dict):
                self._extract_module_from_dict(kw.value, module_name, extra_roots, extra_edges)

        if (
            len(node.args) > _CONFIG_DEFAULTS_ARG_INDEX
            and isinstance(node.args[_CONFIG_DEFAULTS_ARG_INDEX], ast.Dict)
        ):
            self._extract_module_from_dict(
                node.args[_CONFIG_DEFAULTS_ARG_INDEX], module_name, extra_roots, extra_edges
            )

    def _extract_module_from_dict(
        self,
        dict_node: ast.Dict,
        source_module: str,
        extra_roots: set[str],
        extra_edges: dict[str, set[str]],
    ) -> None:
        for key, value in zip(dict_node.keys, dict_node.values, strict=False):
            if not (isinstance(key, ast.Constant) and key.value == "module_name"):
                continue
            if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
                continue
            target = value.value
            if not target.startswith("great_expectations"):
                continue

            resolved = self.graph._resolve_to_known_module(target)
            if resolved:
                extra_edges[source_module].add(resolved)
            else:
                # Treat as a package prefix — mark all submodules reachable
                for mod in self.graph.modules:
                    if mod == target or mod.startswith(target + "."):
                        extra_roots.add(mod)

    def _build_class_to_modules_lookup(self) -> dict[str, list[str]]:
        class_to_modules: dict[str, list[str]] = defaultdict(list)
        for mod_name, info in self.graph.modules.items():
            for sym_name in info.defined_symbols:
                if sym_name[0:1].isupper():
                    class_to_modules[sym_name].append(mod_name)
        return class_to_modules

    def _detect_config_class_names(
        self, extra_edges: dict[str, set[str]], extra_symbol_roots: set[str]
    ) -> None:
        """Find class_name string values in config dicts."""
        class_to_modules = self._build_class_to_modules_lookup()

        # Scan files known to contain config dicts with class_name references
        target_modules = [
            m
            for m in self.graph.modules
            if "types.base" in m or "store" in m or "abstract_data_context" in m
        ]

        for mod_name in target_modules:
            self._scan_module_for_class_names(
                mod_name, class_to_modules, extra_edges, extra_symbol_roots
            )

    def _scan_module_for_class_names(
        self,
        mod_name: str,
        class_to_modules: dict[str, list[str]],
        extra_edges: dict[str, set[str]],
        extra_symbol_roots: set[str],
    ) -> None:
        info = self.graph.modules[mod_name]
        try:
            source = info.filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return

        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values, strict=False):
                if not (isinstance(key, ast.Constant) and key.value == "class_name"):
                    continue
                if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
                    continue
                class_name = value.value
                for target_mod in class_to_modules.get(class_name, []):
                    extra_edges[mod_name].add(target_mod)
                    extra_symbol_roots.add(f"{target_mod}.{class_name}")

    def load_exceptions(self, path: pathlib.Path) -> tuple[set[str], set[str], list[str]]:
        """Load known exceptions. Returns (extra_roots, ignore_patterns, notes)."""
        extra_roots: set[str] = set()
        ignore_patterns: set[str] = set()
        notes: list[str] = []

        if not path.exists():
            return extra_roots, ignore_patterns, notes

        with open(path) as f:
            data = json.load(f)

        for pattern in data.get("always_reachable_modules", []):
            matched = False
            for mod in self.graph.modules:
                if fnmatch(mod, pattern):
                    extra_roots.add(mod)
                    matched = True
            if matched:
                notes.append(f"Pattern '{pattern}' matched modules")

        ignore_patterns = set(data.get("ignore_patterns", []))
        return extra_roots, ignore_patterns, notes


# ============================================================
# Layer 2: Symbol Graph Builder
# ============================================================


class SymbolGraphBuilder:
    """Builds symbol-level reference edges within reachable modules."""

    # Synthetic symbol for module-level code (always treated as a root)
    MODULE_BODY = "<module_body>"

    def __init__(self, graph_builder: ModuleGraphBuilder, reachable_modules: set[str]):
        self.graph = graph_builder
        self.reachable_modules = reachable_modules
        self._symbol_edges: dict[str, set[str]] = defaultdict(set)

    def build(self) -> None:
        for mod_name in self.reachable_modules:
            info = self.graph.modules.get(mod_name)
            if info:
                self._process_module_symbols(mod_name, info)

    def _process_module_symbols(self, mod_name: str, info: ModuleInfo) -> None:
        try:
            source = info.filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return

        import_map = self._build_import_map(info)
        top_level_defs: set[int] = set()

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                top_level_defs.add(id(node))
                sym_fqn = f"{mod_name}.{node.name}"
                self._symbol_edges[sym_fqn] = self._extract_references(
                    node, import_map, mod_name, info
                )

        self._process_module_body(mod_name, info, tree, import_map, top_level_defs)

    def _process_module_body(
        self,
        mod_name: str,
        info: ModuleInfo,
        tree: ast.Module,
        import_map: dict[str, str],
        top_level_defs: set[int],
    ) -> None:
        """Track module-level (non-def) code as always-reachable references."""
        module_body_fqn = f"{mod_name}.{self.MODULE_BODY}"
        module_refs: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if id(node) in top_level_defs:
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    name = child.id
                    if name in import_map:
                        module_refs.add(import_map[name])
                    elif name in info.defined_symbols:
                        module_refs.add(f"{mod_name}.{name}")
        if module_refs:
            self._symbol_edges[module_body_fqn] = module_refs

    def _build_import_map(self, info: ModuleInfo) -> dict[str, str]:
        """Build local_name → fqn mapping from imports."""
        import_map: dict[str, str] = {}

        for local_name, (source_mod, original_name) in info.imported_names.items():
            target_info = self.graph.modules.get(source_mod)
            if target_info and original_name in target_info.defined_symbols:
                import_map[local_name] = f"{source_mod}.{original_name}"

        # Expand star imports
        for star_mod in info.star_imports:
            target_info = self.graph.modules.get(star_mod)
            if not target_info:
                continue
            names = (
                target_info.all_exports
                if target_info.all_exports is not None
                else [n for n in target_info.defined_symbols if not n.startswith("_")]
            )
            for name in names:
                if name in target_info.defined_symbols:
                    import_map.setdefault(name, f"{star_mod}.{name}")

        return import_map

    @staticmethod
    def _extract_references(
        node: ast.AST,
        import_map: dict[str, str],
        current_module: str,
        module_info: ModuleInfo,
    ) -> set[str]:
        refs: set[str] = set()
        node_name = getattr(node, "name", None)

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                name = child.id
                if name in import_map:
                    refs.add(import_map[name])
                elif name in module_info.defined_symbols and name != node_name:
                    refs.add(f"{current_module}.{name}")

            # Base classes of the top-level class
            if isinstance(child, ast.ClassDef) and child is node:
                _add_base_class_refs(child, import_map, current_module, module_info, refs)

        return refs

    def find_root_symbols(self) -> set[str]:
        roots: set[str] = set()
        for mod_name in self.reachable_modules:
            info = self.graph.modules.get(mod_name)
            if not info:
                continue
            for sym_name in info.public_api_symbols:
                roots.add(f"{mod_name}.{sym_name}")
            if info.is_init and info.all_exports:
                self._add_init_export_roots(mod_name, info, roots)
            # Module-level code is always reachable (runs at import time)
            body_fqn = f"{mod_name}.{self.MODULE_BODY}"
            if body_fqn in self._symbol_edges:
                roots.add(body_fqn)
        return roots

    def _add_init_export_roots(
        self, mod_name: str, info: ModuleInfo, roots: set[str]
    ) -> None:
        for name in info.all_exports or []:
            if name in info.defined_symbols:
                roots.add(f"{mod_name}.{name}")
            elif name in info.imported_names:
                source_mod, original_name = info.imported_names[name]
                target_info = self.graph.modules.get(source_mod)
                if target_info and original_name in target_info.defined_symbols:
                    roots.add(f"{source_mod}.{original_name}")

    def bfs_reachable(self, roots: set[str]) -> set[str]:
        visited: set[str] = set()
        queue = deque(roots)
        while queue:
            sym = queue.popleft()
            if sym in visited:
                continue
            visited.add(sym)
            for neighbor in self._symbol_edges.get(sym, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        return visited

    def all_symbols(self) -> set[str]:
        all_syms: set[str] = set()
        for mod_name in self.reachable_modules:
            info = self.graph.modules.get(mod_name)
            if not info:
                continue
            for sym_name in info.defined_symbols:
                all_syms.add(f"{mod_name}.{sym_name}")
        return all_syms


def _add_base_class_refs(
    node: ast.ClassDef,
    import_map: dict[str, str],
    current_module: str,
    module_info: ModuleInfo,
    refs: set[str],
) -> None:
    for base in node.bases:
        if isinstance(base, ast.Name):
            if base.id in import_map:
                refs.add(import_map[base.id])
            elif base.id in module_info.defined_symbols:
                refs.add(f"{current_module}.{base.id}")


# ============================================================
# Layer 4: Test Analyzer
# ============================================================


class TestAnalyzer:
    """Identifies test files that import dead production code."""

    def __init__(
        self,
        tests_root: pathlib.Path,
        repo_root: pathlib.Path,
        reachable_modules: set[str],
        all_modules: set[str],
    ):
        self.tests_root = tests_root
        self.repo_root = repo_root
        self.reachable_modules = reachable_modules
        self.all_modules = all_modules
        self.dead_modules = all_modules - reachable_modules

    def analyze(self) -> list[DeadCodeCandidate]:
        candidates: list[DeadCodeCandidate] = []

        for filepath in sorted(self.tests_root.rglob("*.py")):
            if filepath.name in ("conftest.py", "__init__.py"):
                continue
            if not filepath.name.startswith("test_"):
                continue
            candidate = self._analyze_file(filepath)
            if candidate:
                candidates.append(candidate)

        return candidates

    def _analyze_file(self, filepath: pathlib.Path) -> DeadCodeCandidate | None:
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return None

        gx_imports = self._collect_gx_imports(tree)
        if not gx_imports:
            return None

        resolved = self._resolve_to_known(gx_imports)
        dead_imports = resolved & self.dead_modules
        if not dead_imports:
            return None

        rel_path = filepath.relative_to(self.repo_root)
        if dead_imports == resolved:
            return DeadCodeCandidate(
                filepath=str(rel_path),
                module_name="",
                confidence="high",
                reason=f"All production imports are dead: {sorted(dead_imports)}",
            )
        return DeadCodeCandidate(
            filepath=str(rel_path),
            module_name="",
            confidence="medium",
            reason=f"Some imports are dead: {sorted(dead_imports)}",
        )

    @staticmethod
    def _collect_gx_imports(tree: ast.Module) -> set[str]:
        gx_imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("great_expectations"):
                    gx_imports.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("great_expectations"):
                        gx_imports.add(alias.name)
        return gx_imports

    def _resolve_to_known(self, gx_imports: set[str]) -> set[str]:
        resolved: set[str] = set()
        for imp in gx_imports:
            if imp in self.all_modules:
                resolved.add(imp)
            else:
                parent = imp.rsplit(".", 1)[0]
                if parent in self.all_modules:
                    resolved.add(parent)
        return resolved


# ============================================================
# Helpers
# ============================================================


def _extract_runtime_imports(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    """Extract imports that execute at runtime (skip TYPE_CHECKING blocks)."""
    type_checking_ids: set[int] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.If) and _is_type_checking_guard(node.test):
            for child in ast.walk(node):
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    type_checking_ids.add(id(child))

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) not in type_checking_ids
    ]


def _is_type_checking_guard(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


# ============================================================
# Orchestrator
# ============================================================


class ReachabilityAnalyzer:
    def __init__(
        self,
        package_root: pathlib.Path,
        tests_root: pathlib.Path,
        exceptions_path: pathlib.Path | None = None,
        layers: str = "all",
        verbose: bool = False,
    ):
        self.package_root = package_root
        self.tests_root = tests_root
        self.exceptions_path = exceptions_path
        self.active_layers = _LAYER_SETS.get(layers, _LAYER_SETS["all"])
        self.verbose = verbose
        self.repo_root = package_root.parent

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  {msg}", file=sys.stderr)

    def run(self) -> DeadCodeReport:
        report = DeadCodeReport()

        # --- Layer 1: Module graph ---
        self._log("Building module graph...")
        builder = ModuleGraphBuilder(self.package_root)
        builder.discover_and_parse()
        self._log(f"Discovered {len(builder.modules)} modules")

        edges = builder.build_module_edges()
        roots = builder.find_root_modules()
        self._log(f"Found {len(roots)} root modules (with @public_api)")

        # --- Layer 3: Dynamic imports ---
        extra_roots, ignore_patterns, extra_symbol_roots = self._run_layer3(
            builder, edges, report
        )

        # --- BFS module reachability ---
        all_roots = roots | extra_roots
        reachable = builder.bfs_reachable(all_roots, edges)
        self._log(f"Reachable: {len(reachable)}/{len(builder.modules)} modules")

        all_module_names = set(builder.modules.keys())
        self._build_dead_modules(builder, reachable, all_module_names, ignore_patterns, report)

        # --- Layer 2: Symbol-level ---
        total_symbols, reachable_symbols_count = self._run_layer2(
            builder, reachable, extra_symbol_roots, report
        )

        # --- Layer 4: Test analysis ---
        if _LAYER_TEST in self.active_layers and self.tests_root.exists():
            self._log("Analyzing test files...")
            test_analyzer = TestAnalyzer(
                self.tests_root, self.repo_root, reachable, all_module_names
            )
            report.dead_tests = test_analyzer.analyze()
            self._log(f"Found {len(report.dead_tests)} test files with dead imports")

        report.statistics = self._build_stats(
            builder, all_roots, reachable, (total_symbols, reachable_symbols_count), report
        )
        return report

    def _run_layer3(
        self,
        builder: ModuleGraphBuilder,
        edges: dict[str, set[str]],
        report: DeadCodeReport,
    ) -> tuple[set[str], set[str], set[str]]:
        extra_roots: set[str] = set()
        ignore_patterns: set[str] = set()
        extra_symbol_roots: set[str] = set()

        if _LAYER_DYNAMIC not in self.active_layers:
            return extra_roots, ignore_patterns, extra_symbol_roots

        self._log("Detecting dynamic imports...")
        detector = DynamicImportDetector(builder)
        dyn_roots, dyn_edges, dyn_sym_roots = detector.detect_all()
        extra_roots |= dyn_roots
        extra_symbol_roots |= dyn_sym_roots
        for src, targets in dyn_edges.items():
            edges[src] |= targets
        self._log(
            f"Dynamic: {len(dyn_roots)} extra roots, "
            f"{sum(len(v) for v in dyn_edges.values())} extra edges, "
            f"{len(dyn_sym_roots)} extra symbol roots"
        )

        if self.exceptions_path and self.exceptions_path.exists():
            exc_roots, ignore_patterns, notes = detector.load_exceptions(self.exceptions_path)
            extra_roots |= exc_roots
            report.known_exceptions_applied = notes
            self._log(f"Loaded {len(notes)} exception patterns")

        return extra_roots, ignore_patterns, extra_symbol_roots

    def _build_dead_modules(
        self,
        builder: ModuleGraphBuilder,
        reachable: set[str],
        all_module_names: set[str],
        ignore_patterns: set[str],
        report: DeadCodeReport,
    ) -> None:
        dead_module_names = all_module_names - reachable
        if ignore_patterns:
            dead_module_names = {
                m for m in dead_module_names if not any(fnmatch(m, pat) for pat in ignore_patterns)
            }
        for mod_name in sorted(dead_module_names):
            info = builder.modules[mod_name]
            rel_path = info.filepath.relative_to(self.repo_root)
            report.dead_modules.append(
                DeadCodeCandidate(
                    filepath=str(rel_path),
                    module_name=mod_name,
                    confidence="high",
                    reason="Module not reachable from any @public_api root",
                )
            )

    def _run_layer2(
        self,
        builder: ModuleGraphBuilder,
        reachable: set[str],
        extra_symbol_roots: set[str],
        report: DeadCodeReport,
    ) -> tuple[int, int]:
        if _LAYER_SYMBOL not in self.active_layers:
            return 0, 0

        self._log("Building symbol graph...")
        sym_builder = SymbolGraphBuilder(builder, reachable)
        sym_builder.build()

        sym_roots = sym_builder.find_root_symbols() | extra_symbol_roots
        self._log(f"Found {len(sym_roots)} root symbols")

        reachable_symbols = sym_builder.bfs_reachable(sym_roots)
        all_symbols = sym_builder.all_symbols()
        self._log(f"Symbols: {len(reachable_symbols)}/{len(all_symbols)} reachable")

        self._build_dead_symbols(builder, all_symbols - reachable_symbols, report)
        return len(all_symbols), len(reachable_symbols)

    # Names too noisy / not actionable to surface as dead symbols
    _SKIP_SYMBOL_NAMES = {"logger", "log", "T", "P", "F", "__all__", "__version__", "__author__"}

    def _build_dead_symbols(
        self,
        builder: ModuleGraphBuilder,
        dead_symbols: set[str],
        report: DeadCodeReport,
    ) -> None:
        for sym_fqn in sorted(dead_symbols):
            mod_name, sep, sym_name = sym_fqn.rpartition(".")
            if not sep or not mod_name:
                continue
            if sym_name.startswith("_") or sym_name in self._SKIP_SYMBOL_NAMES:
                continue
            info = builder.modules.get(mod_name)
            if not info:
                continue
            line = info.defined_symbols.get(sym_name)
            rel_path = info.filepath.relative_to(self.repo_root)
            report.dead_symbols.append(
                DeadCodeCandidate(
                    filepath=str(rel_path),
                    module_name=mod_name,
                    symbol_name=sym_name,
                    line_number=line,
                    confidence="medium",
                    reason="Symbol not referenced by any reachable code",
                )
            )

    def _build_stats(
        self,
        builder: ModuleGraphBuilder,
        all_roots: set[str],
        reachable: set[str],
        symbol_counts: tuple[int, int],
        report: DeadCodeReport,
    ) -> dict[str, Any]:
        total_symbols, reachable_symbols_count = symbol_counts
        stats: dict[str, Any] = {
            "total_modules": len(builder.modules),
            "reachable_modules": len(reachable),
            "dead_modules": len(report.dead_modules),
            "root_modules": len(all_roots),
        }
        if _LAYER_SYMBOL in self.active_layers:
            stats["total_symbols"] = total_symbols
            stats["reachable_symbols"] = reachable_symbols_count
            stats["dead_symbols"] = len(report.dead_symbols)
        if _LAYER_TEST in self.active_layers:
            stats["dead_test_files"] = len(report.dead_tests)
        return stats


# ============================================================
# Report Generator
# ============================================================


class ReportGenerator:
    def __init__(self, report: DeadCodeReport):
        self.report = report

    def to_json(self, filepath: pathlib.Path) -> None:
        data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "statistics": self.report.statistics,
            "dead_modules": [self._to_dict(c) for c in self.report.dead_modules],
            "dead_symbols": [self._to_dict(c) for c in self.report.dead_symbols],
            "dead_tests": [self._to_dict(c) for c in self.report.dead_tests],
            "known_exceptions_applied": self.report.known_exceptions_applied,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _to_dict(c: DeadCodeCandidate) -> dict[str, Any]:
        d: dict[str, Any] = {
            "filepath": c.filepath,
            "module_name": c.module_name,
            "confidence": c.confidence,
            "reason": c.reason,
        }
        if c.symbol_name:
            d["symbol_name"] = c.symbol_name
        if c.line_number is not None:
            d["line_number"] = c.line_number
        return d

    def print_summary(self) -> None:
        stats = self.report.statistics
        total_mod = stats.get("total_modules", 0)
        reach_mod = stats.get("reachable_modules", 0)
        dead_mod = stats.get("dead_modules", 0)

        print("\n=== GX Dead Code Analysis ===")
        pct = f"{dead_mod / total_mod * 100:.1f}%" if total_mod else "N/A"
        print(f"Modules:  {reach_mod}/{total_mod} reachable ({dead_mod} dead, {pct})")
        self._print_symbol_line(stats)
        self._print_test_line(stats)
        self._print_dead_modules()
        self._print_dead_symbols()
        self._print_test_sections()

        if self.report.known_exceptions_applied:
            print(f"\nKnown exceptions applied: {len(self.report.known_exceptions_applied)}")

    def _print_symbol_line(self, stats: dict[str, Any]) -> None:
        if "total_symbols" not in stats:
            return
        ts = stats["total_symbols"]
        rs = stats["reachable_symbols"]
        ds = stats["dead_symbols"]
        sp = f"{ds / ts * 100:.1f}%" if ts else "N/A"
        print(f"Symbols:  {rs}/{ts} reachable ({ds} dead, {sp})")

    @staticmethod
    def _print_test_line(stats: dict[str, Any]) -> None:
        if "dead_test_files" in stats:
            print(f"Tests:    {stats['dead_test_files']} files with dead imports")

    def _print_dead_modules(self) -> None:
        if not self.report.dead_modules:
            return
        print(f"\n--- HIGH CONFIDENCE: Dead Modules ({len(self.report.dead_modules)}) ---")
        _print_list([c.filepath for c in self.report.dead_modules], limit=80)

    def _print_dead_symbols(self) -> None:
        if not self.report.dead_symbols:
            return
        print(f"\n--- MEDIUM CONFIDENCE: Dead Symbols ({len(self.report.dead_symbols)}) ---")
        lines = [
            f"{c.filepath}:{c.line_number} :: {c.symbol_name}"
            if c.line_number
            else f"{c.filepath} :: {c.symbol_name}"
            for c in self.report.dead_symbols
        ]
        _print_list(lines, limit=80)

    def _print_test_sections(self) -> None:
        if not self.report.dead_tests:
            return
        high = [c for c in self.report.dead_tests if c.confidence == "high"]
        med = [c for c in self.report.dead_tests if c.confidence == "medium"]
        if high:
            print(f"\n--- DEAD TESTS (all imports dead) ({len(high)}) ---")
            _print_list([c.filepath for c in high], limit=40)
        if med:
            print(f"\n--- TESTS WITH SOME DEAD IMPORTS ({len(med)}) ---")
            _print_list([c.filepath for c in med], limit=40)


def _print_list(items: list[str], limit: int) -> None:
    for item in items[:limit]:
        print(f"  {item}")
    remaining = len(items) - limit
    if remaining > 0:
        print(f"  ... and {remaining} more")


# ============================================================
# CLI
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Find dead code in the GX codebase")
    parser.add_argument("--json-output", default=None, help="Path for JSON report")
    parser.add_argument("--exceptions", default=None, help="Path to known exceptions JSON")
    parser.add_argument(
        "--layer",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Which analysis layers to run (default: all)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    parser.add_argument("--package-root", default=None, help="Path to great_expectations/ package")
    parser.add_argument("--tests-root", default=None, help="Path to tests/ directory")
    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).parent
    repo_root = script_dir.parent

    package_root = (
        pathlib.Path(args.package_root) if args.package_root else repo_root / "great_expectations"
    )
    tests_root = pathlib.Path(args.tests_root) if args.tests_root else repo_root / "tests"
    exceptions_path = (
        pathlib.Path(args.exceptions)
        if args.exceptions
        else script_dir / "dead_code_exceptions.json"
    )

    if not package_root.exists():
        print(f"Error: Package root not found: {package_root}", file=sys.stderr)
        sys.exit(1)

    analyzer = ReachabilityAnalyzer(
        package_root=package_root,
        tests_root=tests_root,
        exceptions_path=exceptions_path if exceptions_path.exists() else None,
        layers=args.layer,
        verbose=args.verbose,
    )

    report = analyzer.run()

    gen = ReportGenerator(report)
    gen.print_summary()

    if args.json_output:
        output_path = pathlib.Path(args.json_output)
        gen.to_json(output_path)
        print(f"\nFull report written to: {output_path}")


if __name__ == "__main__":
    main()
