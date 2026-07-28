"""PyGo Python runtime client.

Connects to the Go-owned Unix Domain Socket, receives {handler, args} frames,
dispatches to the function registered in HANDLERS (populated by the transpiler's
gen_py.py), executes it, and returns the msgpack-serialized result. Failures are
returned as the unified cross-language error struct (ARCHITECTURE.md §6).

Wire format mirrors the Go side (core/runtime/socket): each frame is a 4-byte
big-endian length prefix followed by a msgpack body.

Request frame  (Go -> Python): {"handler": str, "args": {...}}
Response frame (Python -> Go): {"result": <any>, "error": <CrossError|None>}
"""

from __future__ import annotations

import inspect
import os
import socket
import struct
import sys
import traceback
from typing import Any, Callable, Dict, Optional

import msgpack

# HANDLERS is populated by the transpiler-generated gen_py.py, which does:
#     from core.runtime.pyclient import HANDLERS
#     HANDLERS["get_customer"] = get_customer
# We define it here so both this module and gen_py.py share the same dict object.
HANDLERS: Dict[str, Callable[..., Any]] = {}

# Per-request tenant, set from Go-side args["tenant"]. Because the Go
# supervisor serializes CallPython with a mutex, a single global is safe.
from core.runtime.db import set_tenant as _set_tenant  # noqa: E402

DEFAULT_SOCKET_PATH = "/tmp/pygo.sock"


def register(name: str, fn: Callable[..., Any]) -> None:
    """Register a handler. Convenience for gen_py.py."""
    HANDLERS[name] = fn


def make_error(
    type_: str,
    message: str,
    *,
    field: str = "",
    stack: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the unified cross-language error struct (source='python')."""
    return {
        "type": type_,
        "message": message,
        "field": field,
        "source": "python",
        "stack": stack,
        "context": context or {},
    }


class _FramedConn:
    """Length-prefixed msgpack framing over a socket, matching the Go Conn."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock

    def _read_exactly(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed while reading")
            buf.extend(chunk)
        return bytes(buf)

    def recv(self) -> Any:
        header = self._read_exactly(4)
        (length,) = struct.unpack(">I", header)
        body = self._read_exactly(length)
        return msgpack.unpackb(body, raw=False)

    def send(self, obj: Any) -> None:
        body = msgpack.packb(obj, use_bin_type=True) or b""
        self._sock.sendall(struct.pack(">I", len(body)) + body)

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


def _to_wire(obj: Any) -> Any:
    """Make obj msgpack-serializable.

    Model instances (Greeting, Customer, ...) carry state in __dict__; we
    downcast them to plain dicts for the wire. Containers are handled
    recursively. Anything msgpack-native passes through untouched.
    """
    if obj is None or isinstance(obj, (str, int, float, bool, bytes)):
        return obj
    if isinstance(obj, dict):
        return {k: _to_wire(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_wire(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return {k: _to_wire(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    # Fallback: best-effort string.
    return str(obj)


def dispatch(handler: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Look up and execute a handler, returning a response dict.

    The response is always {"result": ..., "error": ...} with exactly one of the
    two populated. Args keys prefixed with '_' are Go-side metadata (e.g. _auth,
    _user) and are stripped before calling the Python handler. The "tenant"
    key (injected by the Go tenancy middleware) selects the isolated DB.
    String args from the Go side are coerced to the handler's declared types.
    """
    _set_tenant((args or {}).get("tenant"))
    fn = HANDLERS.get(handler)
    if fn is None:
        return {
            "result": None,
            "error": {
                "type": "HandlerNotFound",
                "message": f"no handler registered for {handler!r}",
                "source": "python",
            },
        }
    try:
        # Lightweight boundary validation: coerce URL-string args to the
        # handler's declared parameter types.
        sig = inspect.signature(fn)
        clean = {
            k: v
            for k, v in (args or {}).items()
            if not k.startswith("_") and k != "tenant"
        }
        for name, param in sig.parameters.items():
            if name in clean and isinstance(clean[name], str):
                ann = param.annotation
                if ann is int:
                    try:
                        clean[name] = int(clean[name])
                    except ValueError:
                        pass
                elif ann is float:
                    try:
                        clean[name] = float(clean[name])
                    except ValueError:
                        pass
        result = fn(**clean)
        return {"result": _to_wire(result), "error": None}
    except TypeError as exc:
        # Typically a signature mismatch (bad/missing args).
        return {
            "result": None,
            "error": make_error(
                "TypeError",
                str(exc),
                stack=traceback.format_exc(),
                context={"handler": handler},
            ),
        }
    except Exception as exc:  # noqa: BLE001 - deliberately catch-all for cross-lang boundary
        return {
            "result": None,
            "error": make_error(
                type(exc).__name__,
                str(exc),
                stack=traceback.format_exc(),
                context={"handler": handler},
            ),
        }


def serve(socket_path: Optional[str] = None) -> None:
    """Connect to the UDS and serve request frames until the socket closes."""
    path = socket_path or os.environ.get("PYGO_SOCKET") or DEFAULT_SOCKET_PATH
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(path)
    conn = _FramedConn(sock)
    print(f"pyclient: connected to {path}", file=sys.stderr, flush=True)
    try:
        while True:
            try:
                req = conn.recv()
            except (ConnectionError, EOFError):
                break
            handler = req.get("handler", "") if isinstance(req, dict) else ""
            args = req.get("args", {}) if isinstance(req, dict) else {}
            conn.send(dispatch(handler, args))
    finally:
        conn.close()


def main() -> None:
    serve()


if __name__ == "__main__":
    main()
