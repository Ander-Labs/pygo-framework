"""PyGo Admin Panel Generator (v0.40.0).

Generates HTMX-based admin UI from model definitions.
"""

from __future__ import annotations

import os
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
    
    @property
    def plural(self) -> str:
        return self.plural_name or f"{self.name}s"


class AdminGenerator:
    """Generates admin UI from model specifications."""
    
    TEMPLATES_DIR = Path(__file__).parent / "templates"
    
    def __init__(self, output_dir: str = "app/views/admin"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.TEMPLATES_DIR.exists():
            self.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    
    def generate_crud_views(self, model: ModelSpec) -> Dict[str, Path]:
        """Generate CRUD views for a model."""
        generated = {}
        
        list_path = self.output_dir / f"{model.name.lower()}_list.html"
        self._write_template(list_path, self._render_list_template(model))
        generated['list'] = list_path
        
        detail_path = self.output_dir / f"{model.name.lower()}_detail.html"
        self._write_template(detail_path, self._render_detail_template(model))
        generated['detail'] = detail_path
        
        form_path = self.output_dir / f"{model.name.lower()}_form.html"
        self._write_template(form_path, self._render_form_template(model))
        generated['form'] = form_path
        
        delete_path = self.output_dir / f"{model.name.lower()}_delete.html"
        self._write_template(delete_path, self._render_delete_template(model))
        generated['delete'] = delete_path
        
        return generated
    
    def _render_list_template(self, model: ModelSpec) -> str:
        return f'''{{{{ extends "admin/base.html" }}}}
{{% block title %}}{model.name} - List{{% endblock %}}
{{% block content %}}
<div class="admin-container">
    <div class="admin-header">
        <h1 class="admin-title">{model.name}</h1>
        <a href="/admin/{model.name.lower()}/create" class="btn btn-primary">
            <span class="btn-icon">+</span> Add {model.name}
        </a>
    </div>
    
    <div class="admin-filters" hx-get="/admin/{model.name.lower()}/filter">
        <form class="filter-form">
            <input type="search" name="q" placeholder="Search..." class="search-input">
            <select name="sort" class="sort-select">
                <option value="">Sort by...</option>
                {self._render_sort_options(model)}
            </select>
            <button type="submit" class="btn btn-secondary">Apply</button>
            <a href="/admin/{model.name.lower()}/export" class="btn btn-success">
                <span class="btn-icon">📥</span> Export
            </a>
        </form>
    </div>
    
    <table id="list-table" class="admin-table">
        <thead>
            <tr>
                <th><input type="checkbox" class="select-all"></th>
                {self._render_column_headers(model)}
                <th>Actions</th>
            </tr>
        </thead>
        <tbody hx-swap="body"></tbody>
    </table>
</div>
{{% endblock %}}'''
    
    def _render_detail_template(self, model: ModelSpec) -> str:
        return f'''{{{{ extends "admin/base.html" }}}}
{{% block title %}}{model.name} - Details{{% endblock %}}
{{% block content %}}
<div class="admin-container">
    <h1 class="admin-title">{model.name} Details</h1>
    <div class="admin-card">
        <dl class="admin-details">
            {self._render_detail_fields(model)}
        </dl>
    </div>
    <div class="admin-actions">
        <a href="/admin/{model.name.lower()}/{{ .ID }}/edit" class="btn btn-primary">Edit</a>
        <a href="/admin/{model.name.lower()}/{{ .ID }}/delete" class="btn btn-danger">Delete</a>
        <a href="/admin/{model.name.lower()}" class="btn btn-secondary">Back</a>
    </div>
</div>
{{% endblock %}}'''
    
    def _render_form_template(self, model: ModelSpec) -> str:
        fields_form = [f for f in model.fields if f.type not in ('id', 'created_at', 'updated_at', 'deleted_at')]
        return f'''{{{{ extends "admin/base.html" }}}}
{{% block title %}}{model.name} - Create{{% endblock %}}
{{% block content %}}
<div class="admin-container">
    <h1 class="admin-title">{model.name} Create</h1>
    <form method="POST" class="admin-form" hx-post="/admin/{model.name.lower()}/create">
        <input type="hidden" name="_csrf" value="{{ .CSRF }}">
        <div class="form-grid">
            {self._render_form_fields(model, fields_form)}
        </div>
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Save</button>
            <a href="/admin/{model.name.lower()}" class="btn btn-secondary">Cancel</a>
        </div>
    </form>
</div>
{{% endblock %}}'''
    
    def _render_delete_template(self, model: ModelSpec) -> str:
        return f'''{{{{ extends "admin/base.html" }}}}
{{% block title %}}{model.name} - Delete{{% endblock %}}
{{% block content %}}
<div class="admin-container">
    <h1 class="admin-title">Delete {model.name}</h1>
    <div class="admin-card admin-warning">
        <p>Are you sure you want to delete this {model.name.lower()}?</p>
    </div>
    <form method="POST" class="admin-form">
        <input type="hidden" name="_csrf" value="{{ .CSRF }}">
        <input type="hidden" name="_method" value="DELETE">
        <button type="submit" class="btn btn-danger">Yes, Delete</button>
        <a href="/admin/{model.name.lower()}" class="btn btn-secondary">Cancel</a>
    </form>
</div>
{{% endblock %}}'''
    
    def _render_sort_options(self, model: ModelSpec) -> str:
        return '\n'.join(f'<option value="{f.name}">Sort by {f.label_text}</option>' for f in model.fields if f.sortable)
    
    def _render_column_headers(self, model: ModelSpec) -> str:
        return '\n'.join(f'<th data-field="{f.name}">{f.label_text}</th>' for f in model.fields if f.filterable)
    
    def _render_detail_fields(self, model: ModelSpec) -> str:
        return '\n'.join(f'<dt class="field-name">{f.label_text}</dt>\n<dd class="field-value">{{{{ .{f.name} }}}}</dd>' for f in model.fields)
    
    def _render_form_fields(self, model: ModelSpec, fields: List[FieldSpec]) -> str:
        groups: Dict[str, List[FieldSpec]] = {}
        for field in fields:
            groups.setdefault(field.group, []).append(field)
        
        html = []
        for group_name, group_fields in groups.items():
            if len(groups) > 1:
                html.append(f'<div class="form-group form-group-{group_name}">')
            html.extend(self._render_form_field(f) for f in group_fields)
            if len(groups) > 1:
                html.append('</div>')
        return '\n'.join(html)
    
    def _render_form_field(self, field: FieldSpec) -> str:
        input_type = self._get_input_type(field.type)
        required = 'required' if field.required else ''
        return f'''<div class="form-field">
            <label for="{field.name}" class="field-label">{field.label_text}</label>
            <input type="{input_type}" id="{field.name}" name="{field.name}" class="form-input" {required} placeholder="{field.description}">
        </div>'''
    
    def _get_input_type(self, field_type: str) -> str:
        mapping = {
            'string': 'text', 'email': 'email', 'password': 'password',
            'text': 'textarea', 'integer': 'number', 'float': 'number',
            'boolean': 'checkbox', 'date': 'date', 'datetime': 'datetime-local', 'uuid': 'text',
        }
        return mapping.get(field_type, 'text')
    
    def _write_template(self, path: Path, content: str) -> None:
        with open(path, 'w') as f:
            f.write(content)


class DashboardGenerator:
    """Generates dashboard widgets and layouts."""
    
    def __init__(self, output_dir: str = "app/views/admin"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_dashboard(self, widgets: List[Dict[str, Any]]) -> Path:
        dashboard_path = self.output_dir / "dashboard.html"
        widgets_html = self._render_widgets(widgets)
        content = f'''{{{{ extends "admin/base.html" }}}}
{{% block title %}}Dashboard{{% endblock %}}
{{% block content %}}
<div class="admin-container">
    <h1 class="admin-title">Dashboard</h1>
    <div class="dashboard-grid">
{widgets_html}
    </div>
</div>
{{% endblock %}}'''
        with open(dashboard_path, 'w') as f:
            f.write(content)
        return dashboard_path
    
    def _render_widgets(self, widgets: List[Dict[str, Any]]) -> str:
        return '\n'.join(self._render_widget(w) for w in widgets)
    
    def _render_widget(self, widget: Dict[str, Any]) -> str:
        return f'''        <div class="dashboard-widget {widget.get('type', 'card')}">
            <div class="widget-header"><h3 class="widget-title">{widget.get('title', 'Widget')}</h3></div>
            <div class="widget-content">{widget.get('content', '')}</div>
        </div>'''


def generate_admin_for_model(model_name: str, fields: List[Dict[str, Any]], output_dir: str = "app/views/admin") -> Dict[str, Path]:
    """Generate admin CRUD views for a model."""
    model = ModelSpec(name=model_name, fields=[FieldSpec(**f) for f in fields])
    return AdminGenerator(output_dir).generate_crud_views(model)


def generate_dashboard(widgets: List[Dict[str, Any]], output_dir: str = "app/views/admin") -> Path:
    """Generate admin dashboard."""
    return DashboardGenerator(output_dir).generate_dashboard(widgets)