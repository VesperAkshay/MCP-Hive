"""Utilities for handling JSON schemas."""

def clean_schema(schema):
    """
    Remove fields from JSON schemas to ensure compatibility with LLM APIs.
    
    Args:
        schema: JSON schema dictionary
        
    Returns:
        Cleaned schema dictionary suitable for LLM APIs
    """
    if isinstance(schema, dict):
        # Remove problematic fields that might cause validation errors
        keys_to_remove = ["title", "$schema", "additionalProperties", "$id", "default", "examples"]
        for key in keys_to_remove:
            schema.pop(key, None)
        
        # Process type field if it's a list (some LLMs don't support multiple types)
        if "type" in schema and isinstance(schema["type"], list):
            # Use the first type in the list
            schema["type"] = schema["type"][0]
        
        # Recursively process nested properties
        if "properties" in schema and isinstance(schema["properties"], dict):
            for key in schema["properties"]:
                schema["properties"][key] = clean_schema(schema["properties"][key])
        
        # Process items for arrays
        if "items" in schema and isinstance(schema["items"], dict):
            schema["items"] = clean_schema(schema["items"])
        
        # Process oneOf, anyOf, allOf
        for key in ["oneOf", "anyOf", "allOf"]:
            if key in schema and isinstance(schema[key], list):
                schema[key] = [clean_schema(item) for item in schema[key]]
    
    return schema 