"""PyGo Admin Panel Generator (v0.30.0).

Generates admin panel UI and API endpoints from model definitions.
"""

from __future__ import annotations

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ModelField:
    """Represents a field in a model."""
    name: str
    type: str
    required: bool = True
    unique: bool = False
    description: str = ""


@dataclass
class Model:
    """Represents a PyGo model."""
    name: str
    fields: List[ModelField]
    table: Optional[str] = None
    
    def __post_init__(self):
        if self.table is None:
            self.table = self.name.lower()


class AdminGenerator:
    """Generates admin panel and API from models."""
    
    def __init__(self, models: Dict[str, Model]):
        self.models = models
    
    def generate_crud_routes(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate CRUD routes for all models."""
        routes = {}
        
        for model_name, model in self.models.items():
            routes[model_name] = [
                {
                    "method": "GET",
                    "path": f"/{model_name}",
                    "handler": f"list_{model_name.lower()}",
                    "description": f"List all {model_name} with pagination and filters"
                },
                {
                    "method": "GET",
                    "path": f"/{model_name}/:id",
                    "handler": f"get_{model_name.lower()}",
                    "description": f"Get a single {model_name} by ID"
                },
                {
                    "method": "POST",
                    "path": f"/{model_name}",
                    "handler": f"create_{model_name.lower()}",
                    "description": f"Create a new {model_name}"
                },
                {
                    "method": "PUT",
                    "path": f"/{model_name}/:id",
                    "handler": f"update_{model_name.lower()}",
                    "description": f"Update a {model_name}"
                },
                {
                    "method": "DELETE",
                    "path": f"/{model_name}/:id",
                    "handler": f"delete_{model_name.lower()}",
                    "description": f"Delete a {model_name}"
                }
            ]
        
        return routes
    
    def generate_openapi_spec(self, title: str = "PyGo API", version: str = "1.0.0") -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification for the models."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "version": version
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }
        
        # Generate schemas for each model
        for model_name, model in self.models.items():
            properties = {}
            required = []
            
            for field in model.fields:
                properties[field.name] = {
                    "type": self._map_type_to_openapi(field.type),
                    "description": field.description
                }
                if field.required:
                    required.append(field.name)
            
            spec["components"]["schemas"][model_name] = {
                "type": "object",
                "properties": properties,
                "required": required if required else None
            }
        
        # Generate paths for each model
        for model_name, model in self.models.items():
            model_lower = model_name.lower()
            
            spec["paths"][f"/{model_lower}"] = {
                "get": {
                    "summary": f"List all {model_name}",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "default": 20}
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer", "default": 0}
                        },
                        {
                            "name": "filter",
                            "in": "query",
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "List of items",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": f"#/components/schemas/{model_name}"}
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": f"Create a new {model_name}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{model_name}"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created item",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{model_name}"}
                                }
                            }
                        }
                    }
                }
            }
            
            spec["paths"][f"/{model_lower}/{{id}}"] = {
                "get": {
                    "summary": f"Get {model_name} by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Item",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{model_name}"}
                                }
                            }
                        }
                    }
                },
                "put": {
                    "summary": f"Update {model_name}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{model_name}"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Updated item",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": f"#/components/schemas/{model_name}"}
                                }
                            }
                        }
                    }
                },
                "delete": {
                    "summary": f"Delete {model_name}",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "204": {
                            "description": "Deleted"
                        }
                    }
                }
            }
        
        return spec
    
    def _map_type_to_openapi(self, pygo_type: str) -> str:
        """Map PyGo type to OpenAPI type."""
        type_map = {
            "string": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "decimal": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "uuid": "string",
            "email": "string",
            "url": "string",
            "datetime": "string",
            "date": "string",
            "array": "array",
            "map": "object"
        }
        return type_map.get(pygo_type.lower(), "string")
    
    def generate_admin_ui(self) -> str:
        """Generate admin panel HTML template."""
        # This would generate HTMX-based admin UI
        # For now, return a placeholder
        return "<!-- Admin panel template -->"


# Convenience functions
def generate_api(models: Dict[str, Model], title: str = "PyGo API") -> Dict[str, Any]:
    """Generate OpenAPI spec from models."""
    gen = AdminGenerator(models)
    return gen.generate_openapi_spec(title=title)


def generate_routes(models: Dict[str, Model]) -> Dict[str, List[Dict[str, Any]]]:
    """Generate CRUD routes from models."""
    gen = AdminGenerator(models)
    return gen.generate_crud_routes()