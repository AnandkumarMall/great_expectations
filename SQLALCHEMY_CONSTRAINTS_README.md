# SQLAlchemy Version Constraints System

This document explains the SQLAlchemy version constraints system implemented to handle compatibility issues between different database packages and SQLAlchemy versions.

## Problem Background

Great Expectations supports multiple database backends with varying SQLAlchemy compatibility:

- **pyathena** requires SQLAlchemy 1.4.x (does not support SQLAlchemy 2.0+)
- **Most other databases** (PostgreSQL, MySQL, MSSQL, Snowflake, BigQuery) work with SQLAlchemy 2.0+
- **Type checking and development** should use SQLAlchemy 2.0+ for modern features

## Solution: Constraint Files

We've implemented three constraint files to handle different scenarios:

### 1. `constraints-dev-sqlalchemy1.txt`
**Use for**: Athena tests, pyathena compatibility
- SQLAlchemy 1.4.x series
- Compatible with pyathena requirements
- Older pandas/greenlet versions

### 2. `constraints-dev-sqlalchemy2.txt`
**Use for**: Modern databases, type checking, general development
- SQLAlchemy 2.0+ series
- Modern pandas (2.0+)
- Updated greenlet (3.0+)
- Database packages that support SQLAlchemy 2.0

### 3. `constraints-dev.txt` (unchanged)
**Use for**: Default/legacy installations
- Original constraint file (currently empty)

## Usage

### With invoke deps (Recommended)

```bash
# Auto-detect based on markers (athena → SQLAlchemy 1.4, others → SQLAlchemy 2.0)
invoke deps --gx-install -m athena -r test --sqlalchemy-version auto

# Force SQLAlchemy 1.4 (for athena compatibility)
invoke deps --gx-install -m postgresql -r test --sqlalchemy-version 1

# Force SQLAlchemy 2.0 (for modern databases)
invoke deps --gx-install -m snowflake -r test --sqlalchemy-version 2

# Use default constraints-dev.txt
invoke deps --gx-install -m bigquery -r test
```

### Direct pip installation

```bash
# For athena/pyathena compatibility
pip install -c constraints-dev-sqlalchemy1.txt -r requirements.txt -r reqs/requirements-dev-athena.txt

# For modern databases
pip install -c constraints-dev-sqlalchemy2.txt -r requirements.txt -r reqs/requirements-dev-snowflake.txt

# For type checking
pip install -c constraints-dev-sqlalchemy2.txt -r requirements-types.txt
```

## Auto-Detection Logic

When using `--sqlalchemy-version auto`, the system automatically selects:

- **SQLAlchemy 1.4** if any marker contains "athena"
- **SQLAlchemy 2.0** for all other cases

## CI/CD Integration

The CI/CD pipeline automatically uses the appropriate constraints:

- **Athena tests**: Use SQLAlchemy 1.4 constraints
- **All other database tests**: Use SQLAlchemy 2.0 constraints
- **Type checking**: Uses SQLAlchemy 2.0 constraints
- **Integration tests**: Auto-detect based on markers

## Database Compatibility Matrix

| Database | SQLAlchemy 1.4 | SQLAlchemy 2.0 | Recommended |
|----------|---------------|---------------|-------------|
| Athena (pyathena) | ✅ | ❌ | 1.4 |
| PostgreSQL | ✅ | ✅ | 2.0 |
| MySQL | ✅ | ✅ | 2.0 |
| MSSQL | ✅ | ✅ | 2.0 |
| Snowflake | ✅ | ✅ | 2.0 |
| BigQuery | ✅ | ✅ | 2.0 |
| SQLite | ✅ | ✅ | 2.0 |
| Trino | ✅ | ✅ | 2.0 |

## Local Development

For local development, choose the appropriate constraint file based on your needs:

```bash
# If working with athena features
invoke deps --gx-install --sqlalchemy-version 1

# For general development (recommended)
invoke deps --gx-install --sqlalchemy-version 2

# For type checking
pip install -c constraints-dev-sqlalchemy2.txt -r requirements-types.txt
```

## Troubleshooting

### Dependency Conflicts
If you encounter dependency conflicts:

1. Clear your environment: `pip freeze | xargs pip uninstall -y`
2. Reinstall with appropriate constraints
3. Check that pyathena and SQLAlchemy 2.0 aren't being installed together

### Test Failures
If tests fail due to SQLAlchemy version issues:

1. Check which constraint file was used in the logs
2. Verify the test marker matches the expected SQLAlchemy version
3. For athena tests, ensure SQLAlchemy 1.4 constraints were used

### CI Issues
If CI fails with dependency conflicts:

1. Check the `invoke deps` command includes `--sqlalchemy-version auto`
2. Verify athena tests use SQLAlchemy 1.4 constraints
3. Confirm other database tests use SQLAlchemy 2.0 constraints

## Future Migration

When pyathena adds SQLAlchemy 2.0 support:

1. Update `constraints-dev-sqlalchemy1.txt` to allow newer versions
2. Eventually deprecate SQLAlchemy 1.4 constraints
3. Migrate all tests to SQLAlchemy 2.0
4. Simplify constraint system
