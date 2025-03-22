"""Internal utilities for the MeatWise API."""

import re
from typing import Dict, List, Optional, Union

# Define constant patterns for code matching
CODE_PATTERN = re.compile(r"^\d{8,13}$")


def validate_barcode(code: str) -> bool:
    """
    Validate if a string represents a valid barcode.
    
    Args:
        code: The code string to validate
        
    Returns:
        bool: True if the code is a valid barcode, False otherwise
    """
    if not code:
        return False
    return bool(CODE_PATTERN.match(code))


def filter_dict(data: Dict, keys: List[str]) -> Dict:
    """
    Filter a dictionary to include only specified keys.
    
    Args:
        data: The dictionary to filter
        keys: List of keys to keep
        
    Returns:
        Dict: Filtered dictionary
    """
    return {k: v for k, v in data.items() if k in keys}


def convert_none_to_empty_string(value: Optional[str]) -> str:
    """
    Convert None values to empty strings.
    
    Args:
        value: The value to convert
        
    Returns:
        str: Empty string if value is None, otherwise the value
    """
    return "" if value is None else value


def safe_get(data: Dict, key: str, default: Optional[Union[str, List, Dict]] = None) -> Union[str, List, Dict]:
    """
    Safely get a value from a dictionary.
    
    Args:
        data: The dictionary to get the value from
        key: The key to get
        default: The default value to return if the key is not found
        
    Returns:
        Union[str, List, Dict]: The value for the key or the default value
    """
    if data is None:
        return default
    return data.get(key, default) 