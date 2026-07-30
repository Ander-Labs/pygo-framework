"""OpenAPI 3.0 specification generator for PyGo models and routes.

This module generates OpenAPI specs from the AST, enabling automatic
documentation for REST APIs built with PyGo DSL.
"""

import json
from typing import Dict, List, Any, Optional


# DSL type to OpenAPI type mapping
TYPE_MAP = {
    "String": {"type": "string"},
    "Int": {"type": "integer", "format": "int64"},
    "Float": {"type": "number", "format": "double"},
    "Bool": {"type": "boolean"},
    "DateTime": {"type": "string", "format": "date-time"},
    "UUID": {"type": "string", "format": "uuid"},
    "Decimal": {"type": "string"},
    "Email": {"type": "string", "format": "email"},
    "URL": {"type": "string", "format": "uri"},
    "Phone": {"type": "string"},
}


def generate_openapi_spec(models: List[Dict], routes: List[Dict]) -> Dict[str, Any]:
    """Generate an OpenAPI 3.0 specification from models and routes.
    
    Args:
        models: List of model definitions with 'name' and 'fields'
        routes: List of route definitions with 'method', 'path', 'handler'
    
    Returns:
        Complete OpenAPI 3.0 specification dictionary
    """
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "PyGo API",
            "description": "Automatically generated OpenAPI documentation",
            "version": "1.0.0",
        },
        "paths": {},
        "components": {"schemas": {}},
    }
    
    # Generate schemas for each model
    for model in models:
        schema = generate_model_schema(model)
        spec["components"]["schemas"][model["name"]] = schema
    
    # Generate paths for each route
    for route in routes:
        path_spec = generate_path_spec(route, models)
        path_key = route["path"]
        if path_key not in spec["paths"]:
            spec["paths"][path_key] = {}
        spec["paths"][path_key][route["method"].lower()] = path_spec
    
    return spec


def generate_model_schema(model: Dict) -> Dict[str, Any]:
    """Generate OpenAPI schema for a model."""
    properties = {}
    required = []
    
    for field in model.get("fields", []):
        field_name = field["name"]
        field_type = field.get("type", "String")
        
        if field_type in TYPE_MAP:
            prop = TYPE_MAP[field_type].copy()
        else:
            # Assume it's a model reference
            prop = {"$ref": f"#/components/schemas/{field_type}"}
        
        properties[field_name] = prop
        required.append(field_name)
    
    return {
        "type": "object",
        "required": required,
        "properties": properties,
    }

def generate_path_spec(route: Dict, models: List[Dict]) -> Dict[str, Any]:
    """Generate OpenAPI operation spec for a route."""
    path = route["path"]
    
    # Extract path parameters (e.g., /users/:id -> {id})
    params = []
    param_pattern = r":([a-zA-Z_][a-zA-Z0-9_]*)"
    import re
    matches = re.findall(param_pattern, path)
    for match in matches:
        params.append({
            "name": match,
            "in": "path",
            "required": True,
            "schema": {"type": "string"},
        })
    
    # Find the model for this route
    operation_id = route.get("handler", "unknown")
    method = route["method"].lower()
    
    responses = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"type": "object"},
                }
            },
        }
    }
    
    if method == "post":
        responses["201"] = responses["200"]
    elif method == "delete":
        responses["204"] = {"description": "No content"}
    
    return {
        "tags": ["api"],
        "summary": f"{operation_id}",
        "description": f"Generated endpoint for {path}",
        "operationId": operation_id,
        "parameters": params if params else None,
        "responses": responses,
    }
