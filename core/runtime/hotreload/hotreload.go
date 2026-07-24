// Package hotreload watches PyGo source files (.pgo/.yaml/.html/.toml) with
// fsnotify and dispatches per-extension callbacks. In this PoC it only detects
// and logs changes; a restart hook is left for the caller to wire up. The
// watcher keeps running even when a downstream compile fails so the dev process
// stays alive (ARCHITECTURE.md §5).
package hotreload

import (
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/fsnotify/fsnotify"
)

// Callback is invoked with the changed file path and the fsnotify op string.
type Callback func(path string, op string)

// watchedExts are the extensions PyGo cares about.
var watchedExts = map[string]bool{
	".pgo":  true,
	".yaml": true,
	".html": true,
	".toml": true,
}

// Watcher wraps fsnotify and routes events to per-extension callbacks.
type Watcher struct {
	fsw       *fsnotify.Watcher
	mu        sync.RWMutex
	callbacks map[string]Callback // keyed by extension incl. dot, e.g. ".pgo"
	restart   func(ext, path string)
	done      chan struct{}
}

// New creates a Watcher. Call On/OnRestart to register handlers, Add to watch
// directories, then Start.
func New() (*Watcher, error) {
	fsw, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, err
	}
	return &Watcher{
		fsw:       fsw,
		callbacks: map[string]Callback{},
		done:      make(chan struct{}),
	}, nil
}

// On registers a callback for a file extension (e.g. ".pgo", ".html").
func (w *Watcher) On(ext string, cb Callback) {
	if !strings.HasPrefix(ext, ".") {
		ext = "." + ext
	}
	w.mu.Lock()
	w.callbacks[strings.ToLower(ext)] = cb
	w.mu.Unlock()
}

// OnRestart installs the restart hook. It is invoked after the per-ext callback
// so a caller can trigger a Go/Python restart. Left as a hook in this PoC.
func (w *Watcher) OnRestart(fn func(ext, path string)) {
	w.mu.Lock()
	w.restart = fn
	w.mu.Unlock()
}

// Add starts watching a directory. When recursive is true, all existing
// subdirectories are added too (fsnotify is not recursive by default).
func (w *Watcher) Add(root string, recursive bool) error {
	if !recursive {
		return w.fsw.Add(root)
	}
	return filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if addErr := w.fsw.Add(path); addErr != nil {
				log.Printf("hotreload: cannot watch %s: %v", path, addErr)
			}
		}
		return nil
	})
}

// Start runs the event loop in a goroutine. It returns immediately.
func (w *Watcher) Start() {
	go w.loop()
}

func (w *Watcher) loop() {
	for {
		select {
		case <-w.done:
			return
		case ev, ok := <-w.fsw.Events:
			if !ok {
				return
			}
			w.handle(ev)
		case err, ok := <-w.fsw.Errors:
			if !ok {
				return
			}
			// Keep the process alive on watcher errors.
			log.Printf("hotreload: watcher error: %v", err)
		}
	}
}

func (w *Watcher) handle(ev fsnotify.Event) {
	// Ignore chmod-only events.
	if ev.Op == fsnotify.Chmod {
		return
	}
	ext := strings.ToLower(filepath.Ext(ev.Name))
	if !watchedExts[ext] {
		return
	}

	// A newly created directory should be watched too (for recursive setups).
	if ev.Op&fsnotify.Create == fsnotify.Create {
		if fi, err := os.Stat(ev.Name); err == nil && fi.IsDir() {
			_ = w.fsw.Add(ev.Name)
			return
		}
	}

	log.Printf("hotreload: %s changed (%s)", ev.Name, ev.Op.String())

	w.mu.RLock()
	cb := w.callbacks[ext]
	restart := w.restart
	w.mu.RUnlock()

	if cb != nil {
		// Isolate callback panics so a bad handler never kills the watcher
		// (process stays alive on compile/handler error).
		func() {
			defer func() {
				if r := recover(); r != nil {
					log.Printf("hotreload: callback panic for %s: %v", ev.Name, r)
				}
			}()
			cb(ev.Name, ev.Op.String())
		}()
	}
	if restart != nil {
		restart(ext, ev.Name)
	}
}

// Close stops the watcher.
func (w *Watcher) Close() error {
	close(w.done)
	return w.fsw.Close()
}
