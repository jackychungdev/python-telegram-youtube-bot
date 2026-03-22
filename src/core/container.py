"""
Container Module

Simple dependency injection container for managing service lifecycles.
"""
from typing import Any, Dict, Type, Optional, Callable
from enum import Enum


class Scope(Enum):
    """Service lifecycle scope."""
    SINGLETON = 'singleton'  # Single instance for application lifetime
    TRANSIENT = 'transient'  # New instance each time
    SCOPED = 'scoped'        # Instance per request/session


class Container:
    """Dependency injection container.
    
    Provides simple IoC container with support for:
    - Singleton, Transient, and Scoped lifecycles
    - Interface-based registration
    - Automatic dependency resolution
    - Service factories
    
    Example:
        ```python
        container = Container()
        container.register(IUserService, UserService, scope=Scope.SINGLETON)
        container.register(IDatabase, SQLiteDatabase)
        
        user_service = container.resolve(IUserService)
        ```
    """
    
    def __init__(self):
        """Initialize empty container."""
        self._services: Dict[Type, Dict[str, Any]] = {}
        self._instances: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
    
    def register(
        self,
        interface: Type,
        implementation: Type = None,
        scope: Scope = Scope.TRANSIENT,
        factory: Callable = None,
        **kwargs
    ):
        """Register a service.
        
        Args:
            interface: Interface/base class to register
            implementation: Implementation class (optional if factory provided)
            scope: Lifecycle scope (default: transient)
            factory: Factory function to create instance (optional)
            **kwargs: Additional arguments to pass to constructor/factory
            
        Raises:
            ValueError: If neither implementation nor factory provided
        """
        if implementation is None and factory is None:
            raise ValueError("Either implementation or factory must be provided")
        
        self._services[interface] = {
            'implementation': implementation,
            'scope': scope,
            'factory': factory,
            'kwargs': kwargs
        }
        
        # Clear singleton cache if re-registering
        if interface in self._instances:
            del self._instances[interface]
    
    def register_singleton(self, interface: Type, implementation: Type = None, 
                          factory: Callable = None, **kwargs):
        """Register a singleton service.
        
        Convenience method for registering with SINGLETON scope.
        
        Args:
            interface: Interface to register
            implementation: Implementation class
            factory: Factory function
            **kwargs: Constructor arguments
        """
        self.register(interface, implementation, Scope.SINGLETON, factory, **kwargs)
    
    def register_transient(self, interface: Type, implementation: Type = None,
                          factory: Callable = None, **kwargs):
        """Register a transient service.
        
        Convenience method for registering with TRANSIENT scope.
        
        Args:
            interface: Interface to register
            implementation: Implementation class
            factory: Factory function
            **kwargs: Constructor arguments
        """
        self.register(interface, implementation, Scope.TRANSIENT, factory, **kwargs)
    
    def register_scoped(self, interface: Type, implementation: Type = None,
                       factory: Callable = None, **kwargs):
        """Register a scoped service.
        
        Convenience method for registering with SCOPED scope.
        
        Args:
            interface: Interface to register
            implementation: Implementation class
            factory: Factory function
            **kwargs: Constructor arguments
        """
        self.register(interface, implementation, Scope.SCOPED, factory, **kwargs)
    
    def resolve(self, interface: Type, scope_id: str = None):
        """Resolve a service instance.
        
        Args:
            interface: Interface to resolve
            scope_id: Scope identifier (for SCOPED services)
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If interface not registered
        """
        if interface not in self._services:
            raise KeyError(f"Service {interface.__name__} is not registered")
        
        service_info = self._services[interface]
        scope = service_info['scope']
        
        # Check cache based on scope
        if scope == Scope.SINGLETON:
            if interface not in self._instances:
                self._instances[interface] = self._create_instance(service_info)
            return self._instances[interface]
        
        elif scope == Scope.SCOPED:
            if scope_id is None:
                scope_id = 'default'
            
            if scope_id not in self._scoped_instances:
                self._scoped_instances[scope_id] = {}
            
            if interface not in self._scoped_instances[scope_id]:
                self._scoped_instances[scope_id][interface] = self._create_instance(service_info)
            
            return self._scoped_instances[scope_id][interface]
        
        else:  # TRANSIENT
            return self._create_instance(service_info)
    
    def _create_instance(self, service_info: Dict[str, Any]):
        """Create service instance.
        
        Args:
            service_info: Service registration information
            
        Returns:
            New service instance
        """
        implementation = service_info['implementation']
        factory = service_info['factory']
        kwargs = service_info.get('kwargs', {})
        
        # Resolve dependencies from container
        resolved_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, type):
                # It's a type, try to resolve from container
                try:
                    resolved_kwargs[key] = self.resolve(value)
                except KeyError:
                    resolved_kwargs[key] = value
            else:
                resolved_kwargs[key] = value
        
        # Use factory if provided
        if factory:
            return factory(self, **resolved_kwargs)
        
        # Otherwise use constructor
        return implementation(**resolved_kwargs)
    
    def unregister(self, interface: Type):
        """Unregister a service.
        
        Args:
            interface: Interface to unregister
        """
        if interface in self._services:
            del self._services[interface]
        if interface in self._instances:
            del self._instances[interface]
        # Remove from all scoped instances
        for scope_dict in self._scoped_instances.values():
            if interface in scope_dict:
                del scope_dict[interface]
    
    def clear(self):
        """Clear all registrations and instances."""
        self._services.clear()
        self._instances.clear()
        self._scoped_instances.clear()
    
    def is_registered(self, interface: Type) -> bool:
        """Check if a service is registered.
        
        Args:
            interface: Interface to check
            
        Returns:
            True if registered, False otherwise
        """
        return interface in self._services
    
    def get_registrations(self) -> Dict[Type, Dict[str, Any]]:
        """Get all service registrations.
        
        Returns:
            Dictionary of all registered services
        """
        return self._services.copy()
    
    def create_scope(self, scope_id: str):
        """Create a new scope context.
        
        Args:
            scope_id: Scope identifier
            
        Returns:
            ScopeContext manager
        """
        return ScopeContext(self, scope_id)
    
    def dispose(self):
        """Dispose all instances and clear container."""
        self.clear()


class ScopeContext:
    """Context manager for scoped services."""
    
    def __init__(self, container: Container, scope_id: str):
        """Initialize scope context.
        
        Args:
            container: Parent container
            scope_id: Scope identifier
        """
        self.container = container
        self.scope_id = scope_id
    
    def __enter__(self):
        """Enter scope context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit scope context and clean up scoped instances."""
        if self.scope_id in self.container._scoped_instances:
            del self.container._scoped_instances[self.scope_id]


# Global default container instance
_default_container: Optional[Container] = None


def get_container() -> Container:
    """Get the default global container.
    
    Returns:
        Default container instance
    """
    global _default_container
    if _default_container is None:
        _default_container = Container()
    return _default_container


def set_container(container: Container):
    """Set the default global container.
    
    Args:
        container: Container to use as default
    """
    global _default_container
    _default_container = container


def register(interface: Type, implementation: Type = None, **kwargs):
    """Register service in default container.
    
    Args:
        interface: Interface to register
        implementation: Implementation class
        **kwargs: Registration options
        
    Returns:
        Default container
    """
    container = get_container()
    container.register(interface, implementation, **kwargs)
    return container


def resolve(interface: Type):
    """Resolve service from default container.
    
    Args:
        interface: Interface to resolve
        
    Returns:
        Service instance
    """
    return get_container().resolve(interface)
