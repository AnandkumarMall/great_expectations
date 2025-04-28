from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, cast

from great_expectations._docs_decorators import public_api
from great_expectations.analytics.client import submit as submit_event
from great_expectations.analytics.events import (
    ValidationDefinitionCreatedEvent,
    ValidationDefinitionDeletedEvent,
)
from great_expectations.compatibility.typing_extensions import override
from great_expectations.core.factory.factory import Factory
from great_expectations.core.validation_definition import ValidationDefinition
from great_expectations.data_context.data_context.context_factory import project_manager
from great_expectations.exceptions.exceptions import DataContextError

if TYPE_CHECKING:
    from great_expectations.data_context.store.validation_definition_store import (
        ValidationDefinitionStore,
    )


@public_api
class ValidationDefinitionFactory(Factory[ValidationDefinition]):
    """
    Responsible for basic CRUD operations on a Data Context's ValidationDefinitions.
    """

    def __init__(self, store: ValidationDefinitionStore) -> None:
        super().__init__()
        self._store = store

    @public_api
    @override
    def add(self, validation: ValidationDefinition) -> ValidationDefinition:
        """Add a ValidationDefinition to the collection.

        Args:
            validation: ValidationDefinition to add

        Raises:
            DataContextError: if ValidationDefinition already exists
        """
        return super().add(validation)

    @public_api
    @override
    def delete(self, name: str) -> None:
        """Delete a ValidationDefinition from the collection.

        Args:
            name: The name of the ValidationDefinition to delete

        Raises:
            DataContextError: if ValidationDefinition doesn't exist
        """
        super().delete(name)

    @public_api
    @override
    def get(self, name: str) -> ValidationDefinition:
        """Get a ValidationDefinition from the collection by name.

        Args:
            name: Name of ValidationDefinition to get

        Raises:
            DataContextError: when ValidationDefinition is not found.
        """
        return super().get(name)

    @public_api
    @override
    def all(self) -> Iterable[ValidationDefinition]:
        """Get all ValidationDefinitions."""
        return super().all()

    @public_api
    @override
    def add_or_update(self, validation: ValidationDefinition) -> ValidationDefinition:
        """Add or update a ValidationDefinition by name.

        If a ValidationDefinition with the same name exists, overwrite it, otherwise
        create a new ValidationDefinition.

        Args:
            validation: ValidationDefinition to add or update
        """
        return super().add_or_update(validation)

    @override
    def _add(self, validation: ValidationDefinition) -> ValidationDefinition:
        key = self._store.get_key(name=validation.name, id=None)
        if self._store.has_key(key=key):
            raise DataContextError(  # noqa: TRY003 # FIXME CoP
                f"Cannot add ValidationDefinition with name {validation.name} because it already exists."  # noqa: E501 # FIXME CoP
            )
        self._store.add(key=key, value=validation)

        submit_event(
            event=ValidationDefinitionCreatedEvent(
                validation_definition_id=validation.id,
            )
        )

        return validation

    @override
    def _delete(self, name: str) -> None:
        try:
            validation_definition = self._get(name=name)
        except DataContextError as e:
            raise DataContextError(  # noqa: TRY003 # FIXME CoP
                f"Cannot delete ValidationDefinition with name {name} because it cannot be found."
            ) from e

        key = self._store.get_key(name=validation_definition.name, id=validation_definition.id)
        self._store.remove_key(key=key)

        submit_event(
            event=ValidationDefinitionDeletedEvent(
                validation_definition_id=validation_definition.id,
            )
        )

    @override
    def _get(self, name: str) -> ValidationDefinition:
        key = self._store.get_key(name=name, id=None)

        try:
            return cast(ValidationDefinition, self._store.get(key=key))
        except Exception:
            raise DataContextError(f"ValidationDefinition with name {name} was not found.")  # noqa: TRY003 # FIXME CoP

    @override
    def _all(self) -> Iterable[ValidationDefinition]:
        return self._store.get_all()

    @override
    def _add_or_update(self, validation: ValidationDefinition) -> ValidationDefinition:
        # Always add or update underlying suite to avoid freshness issues
        suite_factory = project_manager.get_suite_factory()
        validation.suite = suite_factory.add_or_update(suite=validation.suite)
        validation.data.save()

        try:
            existing_validation = self._get(name=validation.name)
        except DataContextError:
            return self._add(validation=validation)
        validation.id = existing_validation.id
        validation.save()

        return validation
