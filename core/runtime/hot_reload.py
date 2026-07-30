"""PyGo Hot Reload System (v0.32.0).

Provides intelligent hot-reload for development.
"""

from __future__ import annotations

import os
import time
import subprocess
import signal
from pathlib import Path
from typing import Optional, Callable, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class PGoFileHandler(FileSystemEventHandler):
    """File system event handler for .pgo files."""
    
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if str(event.src_path).endswith('.pgo'):
            print(f"[hot-reload] Changed: {event.src_path}")
            self.callback(str(event.src_path))
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        if str(event.src_path).endswith('.pgo'):
            print(f"[hot-reload] Created: {event.src_path}")
            self.callback(str(event.src_path))


class HotReloader:
    """Hot reload manager for PyGo development."""
    
    def __init__(self, watch_dirs: List[str], callback: Callable[[str], None]):
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.callback = callback
        self.observer = Observer()
        self._running = False
    
    def start(self):
        """Start watching for file changes."""
        if self._running:
            return
        
        handler = PGoFileHandler(self.callback)
        
        for watch_dir in self.watch_dirs:
            if watch_dir.exists():
                self.observer.schedule(handler, str(watch_dir), recursive=True)
        
        self.observer.start()
        self._running = True
        print(f"[hot-reload] Watching: {[str(d) for d in self.watch_dirs]}")
    
    def stop(self):
        """Stop watching for file changes."""
        if self._running:
            self.observer.stop()
            self.observer.join()
            self._running = False


class DevServer:
    """Development server with hot-reload support."""
    
    def __init__(self, port: int = 8080, watch_dirs: Optional[List[str]] = None):
        self.port = port
        self.watch_dirs = watch_dirs or ["web", "models"]
        self.reloader: Optional[HotReloader] = None
        self._process = None
    
    def run(self):
        """Run the development server."""
        print(f"[dev-server] Starting on port {self.port}")
        
        # Start hot reload
        self.reloader = HotReloader(
            self.watch_dirs,
            self._on_file_change
        )
        self.reloader.start()
        
        # Start server (placeholder)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[dev-server] Shutting down...")
            self.stop()
    
    def _on_file_change(self, path: str):
        """Handle file change event."""
        print(f"[dev-server] File changed: {path}")
        print("[dev-server] Would recompile and reload...")
        # In real implementation, this would:
        # 1. Recompile the changed .pgo file
        # 2. Restart the server or trigger HMR
    
    def stop(self):
        """Stop the server."""
        if self.reloader:
            self.reloader.stop()


def watch(dirs: List[str], callback: Callable[[str], None]):
    """Watch directories for changes."""
    reloader = HotReloader(dirs, callback)
    reloader.start()
    return reloader


def run_dev_server(port: int = 8080, watch_dirs: Optional[List[str]] = None):
    """Run development server with hot-reload."""
    server = DevServer(port=port, watch_dirs=watch_dirs)
    server.run()
