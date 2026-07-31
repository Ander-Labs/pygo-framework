"""PyGo Source Map Generator (v1.0.0).

Generates source maps for error translation from generated code back to .pgo files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SourceMap:
    """Represents a source map entry."""
    generated_line: int
    source_file: str
    source_line: int
    offset: int = 0


class SourceMapGenerator:
    """Generates and manages source maps for error translation."""
    
    def __init__(self):
        self.maps: Dict[str, List[SourceMap]] = {}
    
    def generate_for_file(self, source_file: Path, generated_file: Path) -> List[SourceMap]:
        """Generate source map for a single file."""
        source_lines = source_file.read_text().split('\n')
        generated_lines = generated_file.read_text().split('\n')
        
        maps = []
        
        for gen_line, gen_content in enumerate(generated_lines, 1):
            # Look for PYGO_ORIGINAL comment
            if 'PYGO_ORIGINAL:' in gen_content:
                match = re.search(r'PYGO_ORIGINAL:\s*(\S+):(\d+)', gen_content)
                if match:
                    source_file_name = match.group(1)
                    source_line = int(match.group(2))
                    maps.append(SourceMap(
                        generated_line=gen_line,
                        source_file=source_file_name,
                        source_line=source_line
                    ))
        
        self.maps[str(generated_file)] = maps
        return maps
    
    def translate_error(self, generated_file: str, line: int) -> Tuple[str, int]:
        """Translate a generated file error to source location."""
        if generated_file not in self.maps:
            return generated_file, line
        
        # Find the closest source map entry
        maps = self.maps[generated_file]
        best_match = None
        best_diff = float('inf')
        
        for entry in maps:
            diff = abs(entry.generated_line - line)
            if diff < best_diff:
                best_diff = diff
                best_match = entry
        
        if best_match:
            return best_match.source_file, best_match.source_line
        
        return generated_file, line
    
    def format_error_message(self, error: str, generated_file: str, line: int) -> str:
        """Format error message with source location."""
        source_file, source_line = self.translate_error(generated_file, line)
        return f"{source_file}:{source_line}: {error}"


def inject_source_map_comment(source_file: Path, generated_file: Path, line_map: Dict[int, int]) -> None:
    """Inject source map comments into generated file."""
    generated_lines = generated_file.read_text().split('\n')
    
    new_lines = []
    for gen_line, content in enumerate(generated_lines, 1):
        new_lines.append(content)
        
        # Inject comment for tracked lines
        if gen_line in line_map:
            source_line = line_map[gen_line]
            new_lines.append(f"// PYGO_ORIGINAL: {source_file.name}:{source_line}")
    
    generated_file.write_text('\n'.join(new_lines))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python source_map.py <source.pgo> <generated.py>")
        sys.exit(1)
    
    source = Path(sys.argv[1])
    generated = Path(sys.argv[2])
    
    generator = SourceMapGenerator()
    maps = generator.generate_for_file(source, generated)
    
    print(f"Generated {len(maps)} source map entries")
    for entry in maps:
        print(f"  Line {entry.generated_line} -> {entry.source_file}:{entry.source_line}")