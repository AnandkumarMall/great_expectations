from abc import ABC, abstractmethod
from typing import Dict, Generic, Iterable, TypeVar

T = TypeVar("T")


class Factory(ABC, Generic[T]):
    """
    Responsible for basic CRUD operations on collections of GX domain objects.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, T] = {}

    def add(self, obj: T) -> T:
        """Add an object to the collection.

        Args:
            obj: Object to add

        Returns:
            The added object
        """
        result = self._add(obj)
        self._cache[obj.name] = result
        return result

    def delete(self, name: str) -> None:
        """Delete an object from the collection.

        Args:
            name: Name of object to delete
        """
        self._delete(name)
        self._cache.pop(name, None)

    def get(self, name: str) -> T:
        """Get an object from the collection by name.

        Args:
            name: Name of object to get

        Returns:
            The requested object
        """
        if name in self._cache:
            return self._cache[name]
        result = self._get(name)
        self._cache[name] = result
        return result

    def all(self) -> Iterable[T]:
        """Get all objects in the collection.

        Returns:
            Iterable of all objects
        """
        results = self._all()
        self._cache.clear()
        for obj in results:
            self._cache[obj.name] = obj
        return results

    def add_or_update(self, obj: T) -> T:
        """Add or update an object in the collection.

        Args:
            obj: Object to add or update

        Returns:
            The added or updated object
        """
        result = self._add_or_update(obj)
        self._cache[obj.name] = result
        return result

    @abstractmethod
    def _add(self, obj: T) -> T:
        pass

    @abstractmethod
    def _delete(self, name: str) -> None:
        pass

    @abstractmethod
    def _get(self, name: str) -> T:
        pass

    @abstractmethod
    def _all(self) -> Iterable[T]:
        pass

    @abstractmethod
    def _add_or_update(self, obj: T) -> T:
        pass
