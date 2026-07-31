"""PyGo Code Formatter (v1.0.0).

Formats .pgo files with consistent style.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


class PyGoFormatter:
    """Formats PyGo DSL files with consistent style."""
    
    # Indentation
    INDENT_SIZE = 4
    INDENT_CHAR = ' '
    
    # Keywords
    KEYWORDS = ['model', 'enum', 'type', 'struct', 'handler', 'route', 
                'import', 'crud', 'module', 'settings']
    
    def __init__(self):
        self.indent_level = 0
    
    def format_file(self, file_path: Path) -> str:
        """Format a single file and return formatted content."""
        content = file_path.read_text()
        return self.format_content(content)
    
    def format_content(self, content: str) -> str:
        """Format content string."""
        lines = content.split('\n')
        formatted = []
        self.indent_level = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('//') or stripped.startswith('#'):
                formatted.append(line)
                i += 1
                continue
            
            # Handle block start/end
            if '{' in stripped:
                # Get the keyword/command
                keyword = self._get_keyword(stripped)
                
                # Format the line
                formatted_line = self._format_line(stripped)
                formatted.append(formatted_line)
                
                # Check if block ends on same line
                if '}' in stripped:
                    self.indent_level = max(0, self.indent_level - 1)
                
                i += 1
            elif '}' in stripped:
                # Dedent before the closing brace
                self.indent_level = max(0, self.indent_level - 1)
                formatted_line = self.INDENT_CHAR * (self.indent_level * self.INDENT_SIZE) + stripped
                formatted.append(formatted_line)
                i += 1
            else:
                # Regular line
                formatted_line = self._format_line(stripped)
                formatted.append(formatted_line)
                i += 1
        
        return '\n'.join(formatted)
    
    def _get_keyword(self, line: str) -> str:
        """Extract keyword from line."""
        for kw in self.KEYWORDS:
            if line.startswith(kw):
                return kw
        return ''
    
    def _format_line(self, line: str) -> str:
        """Format a single line."""
        # Get current indentation
        indent = self.INDENT_CHAR * (self.indent_level * self.INDENT_SIZE)
        
        # Check if this increases indent (block start without end)
        if '{' in line and '}' not in line:
            self.indent_level += 1
        
        return indent + line
    
    def format_model(self, content: str) -> str:
        """Format model definition."""
        lines = content.split('\n')
        result = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('model '):
                result.append(line)
            elif stripped.startswith('}'):
                result.append(line)
            elif ':' in stripped and '=' not in stripped:
                # Field definition
                result.append('    ' + stripped)
            else:
                result.append(line)
        
        return '\n'.join(result)


def format_file(file_path: str) -> str:
    """Format a .pgo file."""
    formatter = PyGoFormatter()
    return formatter.format_file(Path(file_path))


def format_project(project_dir: str) -> None:
    """Format all .pgo files in a project."""
    project = Path(project_dir)
    formatter = PyGoFormatter()
    
    for pgo_file in project.rglob('*.pgo'):
        formatted = formatter.format_file(pgo_file)
        pgo_file.write_text(formatted)
        print(f"✅ Formatted {pgo_file}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pygo_fmt.py <file_or_directory>")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    
    if target.is_file():
        formatted = format_file(str(target))
        print(formatted)
        target.write_text(formatted)
    elif target.is_dir():
        format_project(str(target))
    else:
        print(f"Error: {target} not found")
        sys.exit(1)