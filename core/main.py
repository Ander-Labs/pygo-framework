"""PyGo Framework — Python domain runtime server.

Serves handlers via UDS + MessagePack. Receives requests from Go bridge,
dispatches to registered handlers, returns results via msgpack.

Usage:
  python3 -m core.main --socket /path/to/.pygo.sock

Handlers register via @register decorator or HANDLERS dict.
Example:
  from core.main import register
  @register("core.services.users.get_profile")
  def get_profile(user_id):
      return {"id": user_id, "name": "John"}
"""
import argparse
import asyncio
import os
import socket
import sys
import traceback

import msgpack

# HANDLERS dict — populated by @register decorator
HANDLERS = {}


def register(name: str):
	"""Decorator to register a handler by qualified name."""
	def decorator(func):
		HANDLERS[name] = func
		return func
	return decorator


# Frame handler — receives one request, returns one response
def handle_request(payload: bytes) -> bytes:
	"""Process a single msgpack-encoded request frame.

	Request: {"method": "core.services.users.get", "args": {...}}
	Response: {"result": ..., "error": str | None}
	"""
	try:
		req = msgpack.unpackb(payload, raw=False)
		method = req.get("method", "")
		args = req.get("args", {}) or {}

		fn = HANDLERS.get(method)
		if fn is None:
			return msgpack.packb({
				"result": None,
				"error": f"Handler not found: {method}",
			})

		result = fn(**args)
		return msgpack.packb({
			"result": result,
			"error": None,
		})
	except Exception as e:
		# Capture full traceback for debugging
		trace = traceback.format_exc()
		return msgpack.packb({
			"result": None,
			"error": f"{e}\n{trace}",
		})


class UDSHandler:
	"""Async handler for UDS connections."""

	def __init__(self, reader, writer):
		self.reader = reader
		self.writer = writer

	async def handle(self):
		try:
			while True:
				# Read 4-byte length prefix
				header = await self.reader.readexactly(4)
				length = int.from_bytes(header, byteorder="big")
				if length == 0:
					continue
				# Read payload
				payload = await self.reader.readexactly(length)
				# Process
				response = handle_request(payload)
				# Write response
				resp_header = len(response).to_bytes(4, byteorder="big")
				self.writer.write(resp_header)
				self.writer.write(response)
				await self.writer.drain()
		except (asyncio.IncompleteReadError, ConnectionResetError):
			pass  # Client disconnected
		finally:
			self.writer.close()


async def start_server(socket_path: str):
	"""Start the UDS server and serve forever."""
	# Remove stale socket
	try:
		os.unlink(socket_path)
	except FileNotFoundError:
		pass

	os.makedirs(os.path.dirname(socket_path), exist_ok=True)

	server = await asyncio.start_unix_server(
		lambda r, w: UDSHandler(r, w).handle(),
		sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM),
	)
	server.sockets[0].bind(socket_path)
	os.chmod(socket_path, 0o660)

	print(f"PyGo Python domain server ready on {socket_path}", flush=True)
	print(f"Handlers registered: {list(HANDLERS.keys())}", flush=True)

	async with server:
		await server.serve_forever()


def main():
	parser = argparse.ArgumentParser(description="PyGo Python runtime")
	parser.add_argument("--socket", default="/tmp/pygo.sock", help="UDS socket path")
	args = parser.parse_args()

	asyncio.run(start_server(args.socket))


if __name__ == "__main__":
	main()
