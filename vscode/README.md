# PyGo VS Code Extension

Syntax highlighting and snippets for PyGo files (.pgo).

## Features

- **Syntax Highlighting**: Full syntax highlighting for PyGo DSL
- **Code Snippets**: Common patterns as snippets
  - `model` → Model definition
  - `handler` → Handler function
  - `route` → Route definition
  - `view` → View definition
  - `crud` → CRUD generator
  - `import` → Import statement
  - `struct` → Struct definition

## Installation

1. Clone this repository
2. Open VS Code
3. Press `Ctrl+Shift+P` (Cmd+Shift+P on Mac)
4. Run "Extensions: Install from VSIX"
5. Select the generated VSIX file

Or install manually:
1. Copy the `vscode` folder to your VS Code extensions directory
2. Reload VS Code

## Usage

Simply open a `.pgo` file to get syntax highlighting.

### Available Snippets

| Prefix | Description |
|--------|-------------|
| `model` | Model definition |
| `handler` | Handler function |
| `route` | Route definition |
| `view` | View definition |
| `crud` | CRUD generator |
| `import` | Import statement |
| `struct` | Struct definition |

## Language Support

- Keywords: `crud`, `import`, `model`, `handler`, `view`, `route`, `struct`, `type`, `enum`
- Operators: `+`, `-`, `*`, `/`, `=`, `==`, `!=`, `<`, `>`, `<=`, `>=`
- Control: `if`, `else`, `for`, `while`, `end`, `do`, `done`, `return`
- Literals: strings, numbers, booleans, null

## License

MIT