# PyGo PoC entrypoint (Fase 0).
# Imports the transpiled handlers and serves them over the UDS.
import os
import sys

# Make the generated module importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gen_py  # registers handlers into core.runtime.pyclient.HANDLERS
from core.runtime.pyclient import serve

if __name__ == "__main__":
    serve()
