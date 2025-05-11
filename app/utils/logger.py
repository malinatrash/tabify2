import logging
import time
import json
from functools import wraps
from typing import Callable, Dict, Any, Optional
from fastapi import Request
import inspect
import os
from datetime import datetime, timezone, timedelta

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure the main logger
logger = logging.getLogger("tabify2")
logger.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create file handler for detailed logs
# Use UTC+8 timezone for log files
utc_plus_8 = timezone(timedelta(hours=8))
file_handler = logging.FileHandler(
    f"logs/tabify2_{datetime.now(timezone.utc).astimezone(utc_plus_8).strftime('%Y%m%d')}.log")
file_handler.setLevel(logging.DEBUG)

# Create formatters
console_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

# Set formatters to handlers
console_handler.setFormatter(console_format)
file_handler.setFormatter(file_format)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_request_details(request: Request) -> Dict[str, Any]:
    """Extract relevant details from a FastAPI request."""
    details = {
        "method": request.method,
        "url": str(request.url),
        "client": {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None
        },
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "path_params": request.path_params,
    }

    # Remove sensitive information
    if "authorization" in details["headers"]:
        details["headers"]["authorization"] = "[REDACTED]"
    if "cookie" in details["headers"]:
        details["headers"]["cookie"] = "[REDACTED]"

    return details


def log_endpoint(func: Callable) -> Callable:
    """Decorator to log API endpoint calls with timing and request details."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Extract request object if present
        request = None
        request_details = {}
        for arg_name, arg_value in bound_args.arguments.items():
            if isinstance(arg_value, Request):
                request = arg_value
                break

        if request:
            request_details = get_request_details(request)

        # Log input parameters (excluding request and large objects)
        params = {}
        for arg_name, arg_value in bound_args.arguments.items():
            if arg_name != "request" and not isinstance(arg_value, Request):
                if hasattr(arg_value, "__dict__"):
                    # For complex objects, just log their type and id
                    params[arg_name] = f"{type(arg_value).__name__}(id={id(arg_value)})"
                else:
                    try:
                        # Try to convert to JSON to check if serializable
                        json.dumps(arg_value)
                        params[arg_name] = arg_value
                    except (TypeError, OverflowError):
                        params[arg_name] = str(arg_value)

        endpoint_name = f"{func.__module__}.{func.__name__}"
        logger.info(f"ENDPOINT CALL START: {endpoint_name}")
        logger.debug(f"Request: {json.dumps(request_details, default=str)}")
        logger.debug(f"Parameters: {json.dumps(params, default=str)}")

        try:
            # Execute the original function
            response = await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Log response summary (avoid logging full response for large objects)
            response_summary = {
                "type": type(response).__name__,
                "execution_time_ms": round(execution_time * 1000, 2)
            }

            logger.info(
                f"ENDPOINT CALL END: {endpoint_name} - Time: {response_summary['execution_time_ms']}ms")
            logger.debug(
                f"Response summary: {json.dumps(response_summary, default=str)}")

            return response
        except Exception as e:
            # Log exceptions
            execution_time = time.time() - start_time
            logger.error(
                f"ENDPOINT ERROR: {endpoint_name} - {type(e).__name__}: {str(e)} - Time: {round(execution_time * 1000, 2)}ms")
            # Re-raise the exception
            raise

    return wrapper


def log_function(func: Callable) -> Callable:
    """Decorator to log function calls with timing and parameters."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()

        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Log input parameters (excluding large objects)
        params = {}
        for arg_name, arg_value in bound_args.arguments.items():
            if hasattr(arg_value, "__dict__"):
                # For complex objects, just log their type and id
                params[arg_name] = f"{type(arg_value).__name__}(id={id(arg_value)})"
            else:
                try:
                    # Try to convert to JSON to check if serializable
                    json.dumps(arg_value)
                    params[arg_name] = arg_value
                except (TypeError, OverflowError):
                    params[arg_name] = str(arg_value)

        function_name = f"{func.__module__}.{func.__name__}"
        logger.debug(f"FUNCTION CALL START: {function_name}")
        logger.debug(f"Parameters: {json.dumps(params, default=str)}")

        try:
            # Execute the original function
            response = await func(*args, **kwargs)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Log response summary
            logger.debug(
                f"FUNCTION CALL END: {function_name} - Time: {round(execution_time * 1000, 2)}ms")

            return response
        except Exception as e:
            # Log exceptions
            execution_time = time.time() - start_time
            logger.error(
                f"FUNCTION ERROR: {function_name} - {type(e).__name__}: {str(e)} - Time: {round(execution_time * 1000, 2)}ms")
            # Re-raise the exception
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()

        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Log input parameters (excluding large objects)
        params = {}
        for arg_name, arg_value in bound_args.arguments.items():
            if hasattr(arg_value, "__dict__"):
                # For complex objects, just log their type and id
                params[arg_name] = f"{type(arg_value).__name__}(id={id(arg_value)})"
            else:
                try:
                    # Try to convert to JSON to check if serializable
                    json.dumps(arg_value)
                    params[arg_name] = arg_value
                except (TypeError, OverflowError):
                    params[arg_name] = str(arg_value)

        function_name = f"{func.__module__}.{func.__name__}"
        logger.debug(f"FUNCTION CALL START: {function_name}")
        logger.debug(f"Parameters: {json.dumps(params, default=str)}")

        try:
            # Execute the original function
            response = func(*args, **kwargs)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Log response summary
            logger.debug(
                f"FUNCTION CALL END: {function_name} - Time: {round(execution_time * 1000, 2)}ms")

            return response
        except Exception as e:
            # Log exceptions
            execution_time = time.time() - start_time
            logger.error(
                f"FUNCTION ERROR: {function_name} - {type(e).__name__}: {str(e)} - Time: {round(execution_time * 1000, 2)}ms")
            # Re-raise the exception
            raise

    return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper


def log_middleware_timing(request_id: Optional[str] = None):
    """Log middleware timing information."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, call_next):
            # Generate a unique request ID if not provided
            req_id = request_id or f"{time.time()}-{id(request)}"

            # Log request details
            request_details = get_request_details(request)
            logger.info(
                f"REQUEST START [{req_id}]: {request.method} {request.url.path}")
            logger.debug(
                f"Request details [{req_id}]: {json.dumps(request_details, default=str)}")

            # Process request and measure time
            start_time = time.time()
            try:
                response = await func(request, call_next)

                # Calculate and log execution time
                execution_time = time.time() - start_time
                logger.info(
                    f"REQUEST END [{req_id}]: {request.method} {request.url.path} - Status: {response.status_code} - Time: {round(execution_time * 1000, 2)}ms")

                return response
            except Exception as e:
                # Log exceptions
                execution_time = time.time() - start_time
                logger.error(f"REQUEST ERROR [{req_id}]: {request.method} {request.url.path} - {type(e).__name__}: {str(e)} - Time: {round(execution_time * 1000, 2)}ms")
                # Re-raise the exception
                raise
        
        return wrapper
    
    return decorator
