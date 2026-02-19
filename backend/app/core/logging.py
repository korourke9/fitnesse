"""Logging utilities and decorators."""
import asyncio
import functools
import logging
import pprint
from datetime import date, datetime
from typing import Any, Callable, TypeVar

# Max lines / chars for pretty-printed dicts in logs
_PPRINT_MAX_LINES = 60
_PPRINT_MAX_CHARS = 4000

from app.core.config import settings

# Set up logging level based on DEBUG setting
_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(level=_level, format="%(levelname)s:     %(name)s - %(message)s")
logging.getLogger("app").setLevel(_level)

F = TypeVar("F", bound=Callable[..., Any])


def log_function_call(logger: logging.Logger | None = None) -> Callable[[F], F]:
    """
    Decorator to log function calls with parameters and return values.
    Supports both sync and async functions.
    
    Usage:
        @log_function_call()
        def my_function(arg1, arg2):
            return result
        
        @log_function_call()
        async def my_async_function(arg1, arg2):
            return result
        
        # Or with a specific logger:
        logger = logging.getLogger(__name__)
        @log_function_call(logger=logger)
        def my_function(arg1, arg2):
            return result
    """
    def decorator(func: F) -> F:
        func_logger = logger or logging.getLogger(func.__module__)
        is_async = asyncio.iscoroutinefunction(func)
        
        def _format_value(val: Any, max_len: int = 200) -> str:
            """Format a value for logging: readable and bounded in length."""
            if isinstance(val, (str, int, float, bool, type(None))):
                return repr(val)
            if isinstance(val, (date, datetime)):
                return repr(val)  # e.g. date(2025, 2, 13)
            if isinstance(val, dict):
                keys = list(val.keys())[:8]
                keys_str = ", ".join(repr(k) for k in keys)
                if len(val) > 8:
                    keys_str += ", ..."
                return f"dict({len(val)} keys: {keys_str})"
            if isinstance(val, list):
                return f"list(len={len(val)})"
            # SQLAlchemy Session / engine – avoid dumping internals
            cls_name = type(val).__name__
            if "Session" in cls_name or "session" in cls_name.lower():
                return f"<{cls_name}>"
            # Pydantic model
            if hasattr(val, "model_dump"):
                try:
                    d = val.model_dump()
                    if "id" in d:
                        return f"{cls_name}(id={d['id']!r})"
                    return f"{cls_name}({list(d.keys())[:4]})"
                except Exception:
                    return f"{cls_name}(...)"
            if hasattr(val, "id"):
                return f"{cls_name}(id={getattr(val, 'id')!r})"
            return f"<{cls_name}>"
        
        def _format_arg(arg: Any) -> str:
            return _format_value(arg)
        
        def _pretty_format(val: Any) -> str:
            """Pretty-print dict/list-like structures, truncated to avoid huge logs."""
            try:
                s = pprint.pformat(val, width=120, compact=False)
            except Exception:
                return repr(val)[:_PPRINT_MAX_CHARS]
            lines = s.splitlines()
            if len(lines) > _PPRINT_MAX_LINES:
                s = "\n".join(lines[:_PPRINT_MAX_LINES]) + "\n  ... (truncated)"
            if len(s) > _PPRINT_MAX_CHARS:
                s = s[:_PPRINT_MAX_CHARS] + "\n  ... (truncated)"
            return s

        def _format_result(result: Any) -> str:
            """Format return value: pretty-print dicts and Pydantic models."""
            if isinstance(result, (str, int, float, bool, type(None))):
                return repr(result)
            if isinstance(result, (date, datetime)):
                return repr(result)
            if isinstance(result, dict):
                return _pretty_format(result)
            if isinstance(result, list):
                return _pretty_format(result)
            cls_name = type(result).__name__
            if hasattr(result, "model_dump"):
                try:
                    return f"{cls_name}\n" + _pretty_format(result.model_dump())
                except Exception:
                    return f"{cls_name}(...)"
            if hasattr(result, "id"):
                return f"{cls_name}(id={getattr(result, 'id')!r})"
            return f"{cls_name}(...)"
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Format args (skip 'self' for methods)
                args_repr = []
                if args:
                    start_idx = 1 if args and hasattr(args[0], func.__name__) else 0
                    args_repr = [_format_arg(arg) for arg in args[start_idx:]]
                
                # Format kwargs
                kwargs_repr = [f"{k}={_format_arg(v)}" for k, v in kwargs.items()]
                params_str = ", ".join(args_repr + kwargs_repr)
                func_logger.debug(f"{func.__name__}({params_str})")
                
                try:
                    result = await func(*args, **kwargs)
                    func_logger.debug(f"{func.__name__} -> {_format_result(result)}")
                    return result
                except Exception as e:
                    func_logger.debug(f"{func.__name__} -> Exception: {type(e).__name__}: {e}")
                    raise
            
            return async_wrapper  # type: ignore
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Format args (skip 'self' for methods)
                args_repr = []
                if args:
                    start_idx = 1 if args and hasattr(args[0], func.__name__) else 0
                    args_repr = [_format_arg(arg) for arg in args[start_idx:]]
                
                # Format kwargs
                kwargs_repr = [f"{k}={_format_arg(v)}" for k, v in kwargs.items()]
                params_str = ", ".join(args_repr + kwargs_repr)
                func_logger.debug(f"{func.__name__}({params_str})")
                
                try:
                    result = func(*args, **kwargs)
                    func_logger.debug(f"{func.__name__} -> {_format_result(result)}")
                    return result
                except Exception as e:
                    func_logger.debug(f"{func.__name__} -> Exception: {type(e).__name__}: {e}")
                    raise
            
            return sync_wrapper  # type: ignore
    
    return decorator
