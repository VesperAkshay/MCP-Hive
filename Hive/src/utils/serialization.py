"""Serialization utilities for MCP-Hive."""

def ensure_json_serializable(obj):
    """
    Ensure an object is JSON serializable by converting complex objects to strings.
    
    Args:
        obj: Object to make JSON serializable
        
    Returns:
        JSON serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [ensure_json_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Handle custom objects by converting to dict
        return ensure_json_serializable(obj.__dict__)
    elif hasattr(obj, 'to_dict'):
        # Use to_dict method if available
        return ensure_json_serializable(obj.to_dict())
    elif hasattr(obj, 'as_dict'):
        # Use as_dict method if available
        return ensure_json_serializable(obj.as_dict())
    else:
        # Convert anything else to string if it's not a primitive type
        if not isinstance(obj, (str, int, float, bool, type(None))):
            return str(obj)
        return obj 