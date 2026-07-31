"""PyGo Syntax Validator (v1.0.0).

Validates .pgo files against their declared extensions.
Enforces that declarations only appear in appropriate files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error."""
    file: str
    line: int
    message: str
    code: str


class SyntaxValidator:
    """Validates PyGo DSL syntax and file structure."""
    
    # Allowed declarations per file type/extension
    ALLOWED_DECLARATIONS = {
        'handlers': ['handler', 'route', 'crud'],
        'models': ['model', 'enum', 'type', 'struct'],
        'config': ['import', 'module', 'settings'],
        'yaml': ['name', 'version', 'description', 'author', 'license', 'dependencies'],
    }
    
    # Block patterns for different file types
    FILE_PATTERNS = {
        'models': [
            r'^model\s+\w+',
            r'^enum\s+\w+',
            r'^type\s+\w+',
            r'^struct\s+\w+',
        ],
        'handlers': [
            r'^handler\s+\w+',
            r'^route\s*\{',
            r'^crud\s+\w+',
        ],
        'config': [
            r'^import\s+',
            r'^module\s+',
            r'^settings\s*\{',
        ],
    }
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.current_file: Optional[Path] = None
    
    def validate_file(self, file_path: Path) -> List[ValidationError]:
        """Validate a single file."""
        self.errors = []
        self.current_file = file_path
        
        # Determine file type from path
        file_type = self._get_file_type(file_path)
        
        # Read file content
        try:
            content = file_path.read_text()
        except Exception as e:
            self.errors.append(ValidationError(
                file=str(file_path),
                line=0,
                message=f"Cannot read file: {e}",
                code="FILE_READ_ERROR"
            ))
            return self.errors
        
        # Validate each line
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._validate_line(line.strip(), line_num, file_type, file_path)
        
        return self.errors
    
    def _get_file_type(self, file_path: Path) -> str:
        """Determine file type from path."""
        path_str = str(file_path).lower()
        
        if 'models' in path_str:
            return 'models'
        elif 'handlers' in path_str:
            return 'handlers'
        elif file_path.name.endswith('.yaml') or 'config' in path_str:
            return 'config'
        elif file_path.name.endswith('.pgo'):
            # Determine from content
            return 'handlers'  # default
        return 'unknown'
    
    def _validate_line(self, line: str, line_num: int, file_type: str, file_path: Path):
        """Validate a single line."""
        # Skip empty lines and comments
        if not line or line.startswith('//') or line.startswith('#'):
            return
        
        # Check for invalid declarations
        for decl_type, patterns in self.FILE_PATTERNS.items():
            if file_type != decl_type:
                for pattern in patterns:
                    if re.match(pattern, line):
                        self.errors.append(ValidationError(
                            file=str(file_path),
                            line=line_num,
                            message=f"'{decl_type}' declarations are not valid in {file_type} files. "
                                   f"Move this declaration to a {decl_type} file.",
                            code=f"INVALID_{decl_type.upper()}_IN_{file_type.upper()}"
                        ))
    
    def validate_project(self, project_dir: Path) -> List[ValidationError]:
        """Validate all files in a project."""
        all_errors = []
        
        # Find all .pgo files
        for pgo_file in project_dir.rglob('*.pgo'):
            errors = self.validate_file(pgo_file)
            all_errors.extend(errors)
        
        # Find all .yaml files
        for yaml_file in project_dir.rglob('*.yaml'):
            errors = self.validate_file(yaml_file)
            all_errors.extend(errors)
        
        return all_errors


class SourceMapGenerator:
    """Generates source maps for error translation."""
    
    def __init__(self):
        self.maps: Dict[str, Dict[int, str]] = {}
    
    def generate_map(self, source_file: Path, generated_file: Path) -> Dict[int, str]:
        """Generate a mapping from generated lines to source lines."""
        source_lines = source_file.read_text().split('\n')
        generated_lines = generated_file.read_text().split('\n')
        
        mapping = {}
        
        # Simple line-to-line mapping with offset
        for gen_line, gen_content in enumerate(generated_lines, 1):
            # Look for PYGO_ORIGINAL comment
            if 'PYGO_ORIGINAL:' in gen_content:
                match = re.search(r'PYGO_ORIGINAL:\s*(\S+):(\d+)', gen_content)
                if match:
                    source_file_name = match.group(1)
                    source_line = int(match.group(2))
                    mapping[gen_line] = f"{source_file_name}:{source_line}"
        
        return mapping
    
    def translate_error(self, generated_file: Path, line: int) -> Tuple[str, int]:
        """Translate a generated file error to source location."""
        source_lines = generated_file.read_text().split('\n')
        
        for gen_line, content in enumerate(source_lines, 1):
            if 'PYGO_ORIGINAL:' in content:
                match = re.search(r'PYGO_ORIGINAL:\s*(\S+):(\d+)', content)
                if match:
                    source_file = match.group(1)
                    source_line = int(match.group(2))
                    return source_file, source_line
        
        return str(generated_file), line


def validate_syntax(project_dir: str) -> bool:
    """Validate syntax of all .pgo files in project."""
    validator = SyntaxValidator()
    project_path = Path(project_dir)
    
    errors = validator.validate_project(project_path)
    
    if errors:
        print("❌ Syntax validation failed:")
        for error in errors:
            print(f"  {error.file}:{error.line}: {error.message}")
            print(f"    Error code: {error.code}")
        return False
    
    print("✅ Syntax validation passed")
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python syntax_validator.py <project_dir>")
        sys.exit(1)
    
    success = validate_syntax(sys.argv[1])
    sys.exit(0 if success else 1)