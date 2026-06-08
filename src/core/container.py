"""Dependency Injection Container implementation."""
from typing import Any, Callable, Type, TypeVar

T = TypeVar("T")

class Container:
    """Lightweight Dependency Injection Container for managing service lifecycles."""
    
    _instance: "Container | None" = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "Container":
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._services = {}
            cls._instance._factories = {}
        return cls._instance

    def register_singleton(self, service_type: Type[Any], instance: Any) -> None:
        """Registers a concrete singleton instance for a given interface or service class."""
        self._services[service_type] = instance

    def register_factory(self, service_type: Type[Any], factory: Callable[[], Any]) -> None:
        """Registers a lazy factory function to generate an instance when resolved."""
        self._factories[service_type] = factory

    def resolve(self, service_type: Type[T]) -> T:
        """Resolves and returns the registered instance for a given service type.

        Args:
            service_type: The type or interface class to resolve.

        Returns:
            The resolved instance matching the requested type.

        Raises:
            ValueError: If the requested type has not been registered.
        """
        if service_type in self._services:
            return self._services[service_type]
        
        if service_type in self._factories:
            # Instantiate using registered factory, store as singleton
            instance = self._factories[service_type]()
            self._services[service_type] = instance
            return instance
            
        raise ValueError(
            f"Service of type '{service_type.__name__}' is not registered in the DI container."
        )

    def reset(self) -> None:
        """Resets the registered service maps (primarily used for unit testing)."""
        self._services.clear()
        self._factories.clear()
