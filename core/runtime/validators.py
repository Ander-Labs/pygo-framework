# validators.py - Type validation helpers for PyGo DSL types.
#
# These validators are used by the runtime to validate field values
# before they are persisted to the database. They can be called
# from generated Python code or used in type annotations.

import re
from datetime import datetime
from typing import Any, Optional


# UUID regex: matches standard UUID format (8-4-4-4-12 hex digits)
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def validate_uuid(value: str) -> str:
    """Validate that a string is a valid UUID format.
    
    Args:
        value: String to validate as UUID.
        
    Returns:
        The validated UUID string.
        
    Raises:
        ValueError: If the string is not a valid UUID.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string for UUID, got {type(value).__name__}")
    if not UUID_PATTERN.match(value):
        raise ValueError(f"Invalid UUID format: {value}")
    return value


def validate_email(value: str) -> str:
    """Validate that a string is a valid email format.
    
    Args:
        value: String to validate as email.
        
    Returns:
        The validated email string.
        
    Raises:
        ValueError: If the string is not a valid email.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string for email, got {type(value).__name__}")
    # Simple email regex - not RFC 5322 compliant but covers most cases
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValueError(f"Invalid email format: {value}")
    return value


def validate_url(value: str) -> str:
    """Validate that a string is a valid URL format.
    
    Args:
        value: String to validate as URL.
        
    Returns:
        The validated URL string.
        
    Raises:
        ValueError: If the string is not a valid URL.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string for URL, got {type(value).__name__}")
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, value, re.IGNORECASE):
        raise ValueError(f"Invalid URL format: {value}")
    return value


def validate_phone(value: str) -> str:
    """Validate that a string is a valid phone number format.
    
    Supports international format: +1234567890 or 1234567890
    
    Args:
        value: String to validate as phone.
        
    Returns:
        The validated phone string.
        
    Raises:
        ValueError: If the string is not a valid phone.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string for phone, got {type(value).__name__}")
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    # Check if it's a valid phone (may start with + for international)
    pattern = r'^\+?[0-9]{7,15}$'
    if not re.match(pattern, cleaned):
        raise ValueError(f"Invalid phone format: {value}")
    return value


def validate_datetime(value: str) -> datetime:
    """Validate and parse a datetime string.
    
    Supports ISO 8601 format: 2024-01-15T10:30:00 or 2024-01-15 10:30:00
    
    Args:
        value: String to validate as datetime.
        
    Returns:
        The parsed datetime object.
        
    Raises:
        ValueError: If the string is not a valid datetime.
    """
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"Expected string or datetime, got {type(value).__name__}")
    
    # Try ISO 8601 format with T separator
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # Try space-separated format
    try:
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        pass
    
    # Try date-only format
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        pass
    
    raise ValueError(f"Invalid datetime format: {value}")


def validate_string(value: Any) -> str:
    """Validate that a value is a string.
    
    Args:
        value: Value to validate.
        
    Returns:
        The string value.
        
    Raises:
        ValueError: If the value is not a string.
    """
    if not isinstance(value, str):
        raise ValueError(f"Expected string, got {type(value).__name__}")
    return value


def validate_int(value: Any) -> int:
    """Validate that a value is an integer.
    
    Args:
        value: Value to validate.
        
    Returns:
        The integer value.
        
    Raises:
        ValueError: If the value is not an integer.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise ValueError(f"Expected int, got {type(value).__name__}")


def validate_float(value: Any) -> float:
    """Validate that a value is a float.
    
    Args:
        value: Value to validate.
        
    Returns:
        The float value.
        
    Raises:
        ValueError: If the value is not a float.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    raise ValueError(f"Expected float, got {type(value).__name__}")


def validate_bool(value: Any) -> bool:
    """Validate that a value is a boolean.
    
    Args:
        value: Value to validate.
        
    Returns:
        The boolean value.
        
    Raises:
        ValueError: If the value is not a boolean.
    """
    if isinstance(value, bool):
        return value
    raise ValueError(f"Expected bool, got {type(value).__name__}")


# Type mapping for DSL types to validator functions
TYPE_VALIDATORS = {
    'UUID': validate_uuid,
    'Email': validate_email,
    'URL': validate_url,
    'Phone': validate_phone,
    'DateTime': validate_datetime,
    'String': validate_string,
    'Int': validate_int,
    'Float': validate_float,
    'Bool': validate_bool,
}


def validate_field(type_name: str, value: Any) -> Any:
    """Validate a field value based on its DSL type.
    
    Args:
        type_name: The DSL type name (e.g., 'UUID', 'Email', 'String').
        value: The value to validate.
        
    Returns:
        The validated (and possibly converted) value.
        
    Raises:
        ValueError: If validation fails or type is unknown.
    """
    if type_name not in TYPE_VALIDATORS:
        # Unknown type - return as-is (model types, enums, etc.)
        return value
    return TYPE_VALIDATORS[type_name](value)