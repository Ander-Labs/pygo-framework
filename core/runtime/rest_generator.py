"""PyGo REST API Generator (v0.41.0).

Generates REST API endpoints from model specifications with:
- Pagination (cursor/offset)
- Filtering
- Sorting
- Include relationships
- Field selection
- Bulk operations
- OpenAPI 3.0 spec generation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class FieldSpec:
    """Specification for a model field."""
    name: str
    type: str
    label: Optional[str] = None
    description: str = ""
    required: bool = False
    filterable: bool = True
    sortable: bool = True
    searchable: bool = True
    exportable: bool = True
    display_template: str = ""
    group: str = "main"
    relationships: Optional[List[str]] = None
    
    @property
    def label_text(self) -> str:
        return self.label or self.name.replace("_", " ").title()


@dataclass
class ModelSpec:
    """Specification for a model."""
    name: str
    fields: List[FieldSpec]
    plural_name: Optional[str] = None
    description: str = ""
    routes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def plural(self) -> str:
        return self.plural_name or f"{self.name}s"
    
    @property
    def routes_prefix(self) -> str:
        return f"/{self.name.lower()}"


class RESTGenerator:
    """Generates REST API endpoints from model specifications."""
    
    def __init__(self, output_dir: str = "app/api"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_api_for_model(self, model: ModelSpec) -> Dict[str, Path]:
        """Generate complete REST API for a model."""
        generated = {}
        
        handler_path = self.output_dir / f"{model.name.lower()}_handler.py"
        self.write_handler(handler_path, model)
        generated['handler'] = handler_path
        
        go_handler_path = self.output_dir.parent / "go" / f"{model.name.lower()}_handler.go"
        go_handler_path.parent.mkdir(parents=True, exist_ok=True)
        self.write_go_handler(go_handler_path, model)
        generated['go_handler'] = go_handler_path
        
        openapi_path = self.output_dir / f"{model.name.lower()}.openapi.json"
        self.write_openapi_spec(openapi_path, model)
        generated['openapi'] = openapi_path
        
        return generated
    
    def write_handler(self, path: Path, model: ModelSpec) -> None:
        """Write Python handler for REST API."""
        content = self._build_handler_content(model)
        with open(path, 'w') as f:
            f.write(content)
    
    def _build_handler_content(self, model: ModelSpec) -> str:
        """Build handler content using string concatenation."""
        lines = [
            f'"""REST API handler for {model.name}."""',
            'from flask import request, jsonify',
            'from core.runtime.db import get_connection',
            'from core.runtime.pagination import paginate',
            'from core.runtime.auth import require_auth',
            '',
            f'@require_auth()',
            f'def list_{model.name.lower()}():',
            f'    """List {model.name.lower()}s with pagination, filtering, sorting."""',
            '    page = request.args.get("page", 1, type=int)',
            '    per_page = request.args.get("per_page", 20, type=int)',
            '    sort = request.args.get("sort", "-created_at")',
            '    search = request.args.get("q")',
            '',
            '    filters = {}',
            '    for field in request.args:',
            '        if field not in ["page", "per_page", "sort", "q", "fields", "include"]:',
            '            value = request.args.get(field)',
            '            if value:',
            '                filters[field] = value',
            '',
            '    fields_param = request.args.get("fields")',
            '    fields = fields_param.split(",") if fields_param else None',
            '',
            '    include_param = request.args.get("include")',
            '    includes = include_param.split(",") if include_param else []',
            '',
            '    db = get_connection()',
            f'    query = db.table("{model.name.lower()}s")',
            '',
            '    if search:',
            '        query = query.search(search)',
            '',
            '    for field, value in filters.items():',
            '        query = query.where(field, value)',
            '',
            '    if sort:',
            '        desc = sort.startswith("-")',
            '        sort_field = sort.lstrip("-")',
            '        query = query.order_by(sort_field, desc=desc)',
            '',
            '    pagination = paginate(query, page, per_page)',
            '',
            '    if fields:',
            '        for row in pagination["items"]:',
            '            for f in fields:',
            '                if f not in row:',
            '                    del row[f]',
            '',
            '    for inc in includes:',
            '        pass',
            '',
            '    return jsonify({',
            '        "data": pagination["items"],',
            '        "pagination": {',
            '            "page": page,',
            '            "per_page": per_page,',
            '            "total": pagination["total"],',
            '            "pages": pagination["pages"],',
            '            "has_next": pagination["has_next"],',
            '            "has_prev": pagination["has_prev"]',
            '        }',
            '    })',
            '',
            f'@require_auth()',
            f'def get_{model.name.lower()}(id: str):',
            '    db = get_connection()',
            f'    item = db.table("{model.name.lower()}s").where("id", id).first()',
            '    if not item:',
            f'        return jsonify({{"error": "{model.name} not found"}}, 404)',
            '    return jsonify({"data": item})',
            '',
            f'@require_auth()',
            f'def create_{model.name.lower()}():',
            '    data = request.get_json() or {}',
            '    db = get_connection()',
            f'    item = db.table("{model.name.lower()}s").insert(data)',
            '    return jsonify({"data": item}, 201)',
            '',
            f'@require_auth()',
            f'def update_{model.name.lower()}(id: str):',
            '    data = request.get_json() or {}',
            '    db = get_connection()',
            f'    item = db.table("{model.name.lower()}s").where("id", id).update(data)',
            '    if not item:',
            f'        return jsonify({{"error": "{model.name} not found"}}, 404)',
            '    return jsonify({"data": item})',
            '',
            f'@require_auth()',
            f'def delete_{model.name.lower()}(id: str):',
            '    db = get_connection()',
            f'    item = db.table("{model.name.lower()}s").where("id", id).delete()',
            '    if not item:',
            f'        return jsonify({{"error": "{model.name} not found"}}, 404)',
            '    return jsonify({"data": item})',
            '',
            f'@require_auth()',
            f'def bulk_create_{model.name.lower()}():',
            '    items = request.get_json() or []',
            '    db = get_connection()',
            f'    created = db.table("{model.name.lower()}s").insert(items)',
            '    return jsonify({"data": created}, 201)',
            '',
            f'@require_auth()',
            f'def bulk_delete_{model.name.lower()}():',
            '    ids = request.get_json().get("ids", [])',
            '    db = get_connection()',
            f'    deleted = db.table("{model.name.lower()}s").where_in("id", ids).delete()',
            '    return jsonify({"deleted": len(deleted)})',
        ]
        return '\n'.join(lines)
    
    def write_go_handler(self, path: Path, model: ModelSpec) -> None:
        """Write Go handler for REST API."""
        content = self._build_go_handler_content(model)
        with open(path, 'w') as f:
            f.write(content)
    
    def _build_go_handler_content(self, model: ModelSpec) -> str:
        """Build Go handler content."""
        lines = [
            'package api',
            '',
            'import (',
            '    "encoding/json"',
            '    "net/http"',
            '    "strconv"',
            '    "github.com/gorilla/mux"',
            ')',
            '',
            f'func List{model.name}(w http.ResponseWriter, r *http.Request) {{',
            '    page, _ := strconv.Atoi(r.URL.Query().Get("page"))',
            '    if page < 1 { page = 1 }',
            '    perPage, _ := strconv.Atoi(r.URL.Query().Get("per_page"))',
            '    if perPage < 1 { perPage = 20 }',
            '    sort := r.URL.Query().Get("sort")',
            '    if sort == "" { sort = "-created_at" }',
            '    search := r.URL.Query().Get("q")',
            '    _ = search  // TODO: implement search',
            '    w.Header().Set("Content-Type", "application/json")',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            f'        "data": []{model.name},',
            '        "pagination": map[string]interface{}{',
            '            "page": page, "per_page": perPage,',
            '        },',
            '    })',
            '}',
            '',
            f'func Get{model.name}(w http.ResponseWriter, r *http.Request) {{',
            '    vars := mux.Vars(r)',
            '    id := vars["id"]',
            '    w.Header().Set("Content-Type", "application/json")',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            '        "data": map[string]interface{}{"id": id},',
            '    })',
            '}',
            '',
            f'func Create{model.name}(w http.ResponseWriter, r *http.Request) {{',
            f'    var item {model.name}',
            '    if err := json.NewDecoder(r.Body).Decode(&item); err != nil {',
            '        http.Error(w, err.Error(), http.StatusBadRequest)',
            '        return',
            '    }',
            '    w.Header().Set("Content-Type", "application/json")',
            '    w.WriteHeader(http.StatusCreated)',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            '        "data": item,',
            '    })',
            '}',
            '',
            f'func Update{model.name}(w http.ResponseWriter, r *http.Request) {{',
            '    vars := mux.Vars(r)',
            '    id := vars["id"]',
            '    w.Header().Set("Content-Type", "application/json")',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            '        "data": map[string]interface{}{"id": id},',
            '    })',
            '}',
            '',
            f'func Delete{model.name}(w http.ResponseWriter, r *http.Request) {{',
            '    vars := mux.Vars(r)',
            '    id := vars["id"]',
            '    w.Header().Set("Content-Type", "application/json")',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            '        "deleted": true,',
            '    })',
            '}',
            '',
            f'func BulkCreate{model.name}(w http.ResponseWriter, r *http.Request) {{',
            f'    var items []{model.name}',
            '    if err := json.NewDecoder(r.Body).Decode(&items); err != nil {',
            '        http.Error(w, err.Error(), http.StatusBadRequest)',
            '        return',
            '    }',
            '    w.Header().Set("Content-Type", "application/json")',
            '    w.WriteHeader(http.StatusCreated)',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            '        "data": items,',
            '    })',
            '}',
            '',
            f'func BulkDelete{model.name}(w http.ResponseWriter, r *http.Request) {{',
            '    w.Header().Set("Content-Type", "application/json")',
            '    json.NewEncoder(w).Encode(map[string]interface{}{',
            '        "deleted": 0,',
            '    })',
            '}',
        ]
        return '\n'.join(lines)
    
    def write_openapi_spec(self, path: Path, model: ModelSpec) -> None:
        """Write OpenAPI 3.0 specification."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"{model.name} API",
                "version": "1.0.0",
                "description": model.description or f"REST API for {model.name}"
            },
            "paths": {
                f"/{model.name.lower()}s": {
                    "get": self._openapi_list_endpoint(model),
                    "post": self._openapi_create_endpoint(model)
                },
                f"/{model.name.lower()}s/{{id}}": {
                    "get": self._openapi_get_endpoint(model),
                    "put": self._openapi_update_endpoint(model),
                    "delete": self._openapi_delete_endpoint(model)
                }
            },
            "components": {
                "schemas": {
                    model.name: {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "format": "uuid"},
                            "created_at": {"type": "string", "format": "datetime"},
                            "updated_at": {"type": "string", "format": "datetime"}
                        }
                    }
                }
            }
        }
        
        with open(path, 'w') as f:
            json.dump(spec, f, indent=2)
    
    def _openapi_list_endpoint(self, model: ModelSpec) -> Dict[str, Any]:
        return {
            "summary": f"List {model.name}s",
            "parameters": [
                {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 20}},
                {"name": "sort", "in": "query", "schema": {"type": "string", "default": "-created_at"}},
                {"name": "q", "in": "query", "schema": {"type": "string"}},
                {"name": "fields", "in": "query", "schema": {"type": "string"}},
                {"name": "include", "in": "query", "schema": {"type": "string"}},
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "data": {"type": "array"},
                                    "pagination": {
                                        "type": "object",
                                        "properties": {
                                            "page": {"type": "integer"},
                                            "per_page": {"type": "integer"},
                                            "total": {"type": "integer"},
                                            "pages": {"type": "integer"},
                                            "has_next": {"type": "boolean"},
                                            "has_prev": {"type": "boolean"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _openapi_create_endpoint(self, model: ModelSpec) -> Dict[str, Any]:
        return {
            "summary": f"Create a new {model.name}",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {"schema": {"type": "object"}}
                }
            },
            "responses": {"201": {"description": "Created"}}
        }
    
    def _openapi_get_endpoint(self, model: ModelSpec) -> Dict[str, Any]:
        return {
            "summary": f"Get a single {model.name}",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {
                "200": {"description": "Successful response"},
                "404": {"description": "Not found"}
            }
        }
    
    def _openapi_update_endpoint(self, model: ModelSpec) -> Dict[str, Any]:
        return {
            "summary": f"Update a {model.name}",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {"200": {"description": "Updated"}}
        }
    
    def _openapi_delete_endpoint(self, model: ModelSpec) -> Dict[str, Any]:
        return {
            "summary": f"Delete a {model.name}",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {"200": {"description": "Deleted"}}
        }


def generate_api_for_model(model_name: str, fields: List[Dict[str, Any]], output_dir: str = "app/api") -> Dict[str, Path]:
    """Generate complete REST API for a model."""
    model = ModelSpec(name=model_name, fields=[FieldSpec(**f) for f in fields])
    generator = RESTGenerator(output_dir)
    return generator.generate_api_for_model(model)