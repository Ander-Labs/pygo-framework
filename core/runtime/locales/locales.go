// Package locales provides i18n support for Python handlers. Loads JSON dictionaries
// from core/runtime/locales/{en,es}.json and exposes t(key) function.
package locales

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

var (
	locales     map[string]map[string]string
	localesOnce sync.Once
	localesErr  error
)

// Load loads locale dictionaries from the locales directory.
// Called once at startup by the Python runtime (pyclient serve).
func Load(localesDir string) error {
	localesOnce.Do(func() {
		entries, err := os.ReadDir(localesDir)
		if err != nil {
			localesErr = err
			return
		}
		locales = make(map[string]map[string]string)
		for _, e := range entries {
			if e.IsDir() || filepath.Ext(e.Name()) != ".json" {
				continue
			}
			lang := e.Name()[:len(e.Name())-5] // strip .json
			data, err := os.ReadFile(filepath.Join(localesDir, e.Name()))
			if err != nil {
				localesErr = err
				return
			}
			var dict map[string]string
			if err := json.Unmarshal(data, &dict); err != nil {
				localesErr = err
				return
			}
			locales[lang] = dict
		}
		if len(locales) == 0 {
			locales["en"] = map[string]string{} // fallback empty
		}
	})
	return localesErr
}

// T translates a key for the given locale. Falls back to "en" then key itself.
func T(locale, key string) string {
	_ = Load("") // no-op if already loaded
	if locales == nil {
		return key
	}
	if dict, ok := locales[locale]; ok {
		if val, ok := dict[key]; ok {
			return val
		}
	}
	if dict, ok := locales["en"]; ok {
		if val, ok := dict[key]; ok {
			return val
		}
	}
	return key
}

// GetAll returns all loaded locales (for debugging/inspection).
func GetAll() map[string]map[string]string {
	_ = Load("")
	return locales
}