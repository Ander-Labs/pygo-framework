import yaml
import sys
from pathlib import Path

def validate_module_yaml(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    
    required = ['module.name', 'module.version', 'module.description']
    for field in required:
        parts = field.split('.')
        obj = data
        for part in parts:
            if part not in obj:
                print(f'ERROR: Missing field {field}')
                sys.exit(1)
            obj = obj[part]
    
    print(f'OK: {path} is valid')

for yaml_file in Path('.').rglob('module.yaml'):
    validate_module_yaml(yaml_file)

print("All module.yaml files validated successfully!")
