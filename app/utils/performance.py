"""Performance optimization utilities for the ERP system.

This module provides utilities for:
- Memory management and garbage collection
- Thread-safe operations
- Resource pooling
- Cache management
"""
import gc
import threading
import weakref
from functools import wraps
from contextlib import contextmanager
import time

__all__ = ['gc_context', 'memoize_with_ttl', 'thread_safe', 'ResourcePool', 'profile_memory']

# Global lock for thread-safe operations
_OPERATION_LOCK = threading.RLock()


@contextmanager
def gc_context():
    """Context manager for garbage collection.
    
    Disables GC during operation for performance, then enables and collects.
    """
    gc.disable()
    try:
        yield
    finally:
        gc.enable()
        gc.collect()


def memoize_with_ttl(ttl_seconds=300):
    """Decorator to memoize function results with time-to-live.
    
    Args:
        ttl_seconds: Cache validity period in seconds
    """
    def decorator(func):
        cache = {}
        timestamps = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            
            if key in cache and (now - timestamps.get(key, 0)) < ttl_seconds:
                return cache[key]
            
            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = now
            
            # Cleanup old entries
            expired = [k for k, t in timestamps.items() if now - t > ttl_seconds]
            for k in expired:
                cache.pop(k, None)
                timestamps.pop(k, None)
            
            return result
        
        return wrapper
    return decorator


def thread_safe(func):
    """Decorator to make a function thread-safe using a lock."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with _OPERATION_LOCK:
            return func(*args, **kwargs)
    return wrapper


class ResourcePool:
    """Simple resource pooling for database connections or file handles.
    
    Usage:
        pool = ResourcePool(create_func, max_size=10)
        resource = pool.acquire()
        try:
            # use resource
        finally:
            pool.release(resource)
    """
    __slots__ = ('_create_func', '_pool', '_size', '_lock', '_max_size')
    
    def __init__(self, create_func, max_size=10):
        self._create_func = create_func
        self._pool = []
        self._size = 0
        self._lock = threading.Lock()
        self._max_size = max_size
    
    def acquire(self):
        """Acquire a resource from the pool."""
        with self._lock:
            if self._pool:
                return self._pool.pop()
            elif self._size < self._max_size:
                self._size += 1
                return self._create_func()
            else:
                raise RuntimeError("Resource pool exhausted")
    
    def release(self, resource):
        """Return a resource to the pool."""
        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(resource)
            else:
                # Discard if pool is full
                if hasattr(resource, 'close'):
                    resource.close()


def profile_memory(func):
    """Decorator to profile memory usage of a function.
    
    Prints memory delta before/after execution.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        gc.collect()
        start_mem = _get_memory_usage()
        
        result = func(*args, **kwargs)
        
        gc.collect()
        end_mem = _get_memory_usage()
        delta = end_mem - start_mem
        
        print(f"{func.__name__} memory delta: {delta:+.2f} MB")
        return result
    
    return wrapper


def _get_memory_usage():
    """Get current memory usage in MB (platform-specific)."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        # Fallback: use os-specific methods
        try:
            import os
            if hasattr(os, 'getpidrusage'):
                return os.getpidrusage(0)[0] / 1024
        except:
            return 0.0


class WeakRefCache:
    """Cache using weak references for automatic cleanup."""
    __slots__ = ('_cache', '_lock')
    
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()
        self._lock = threading.Lock()
    
    def set(self, key, value):
        """Store a value in the cache."""
        with self._lock:
            self._cache[key] = value
    
    def get(self, key, default=None):
        """Retrieve a value from the cache."""
        with self._lock:
            return self._cache.get(key, default)
    
    def clear(self):
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
