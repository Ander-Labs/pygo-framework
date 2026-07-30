"""PyGo i18n System (v0.33.0).

Provides internationalization, localization, and timezone support.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, date, time, timezone
import locale
import threading
import csv
import json
from pathlib import Path


@dataclass
class LocaleConfig:
    """Configuration for a locale."""
    code: str  # e.g., 'es_ES', 'en_US'
    name: str  # e.g., 'Spanish (Spain)', 'English (US)'
    language: str  # e.g., 'es', 'en'
    country: Optional[str] = None
    timezone: str = "UTC"
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    decimal_separator: str = "."
    thousands_separator: str = ","
    currency_symbol: str = "$"
    currency_code: str = "USD"


class TranslationManager:
    """Manages translations for different locales."""
    
    def __init__(self, locales_dir: str = "locales"):
        self.locales_dir = Path(locales_dir)
        self._translations: Dict[str, Dict[str, str]] = {}
        self._current_locale: str = "en"
        self._lock = threading.Lock()
    
    def load_locale(self, locale_code: str) -> bool:
        """Load translations for a locale."""
        locale_path = self.locales_dir / f"{locale_code}.json"
        
        if not locale_path.exists():
            # Try language-only
            lang_path = self.locales_dir / f"{locale_code.split('_')[0]}.json"
            if lang_path.exists():
                locale_path = lang_path
            else:
                return False
        
        try:
            with open(locale_path, 'r', encoding='utf-8') as f:
                self._translations[locale_code] = json.load(f)
            return True
        except Exception:
            return False
    
    def set_locale(self, locale_code: str) -> bool:
        """Set the current locale."""
        if locale_code not in self._translations:
            if not self.load_locale(locale_code):
                return False
        
        with self._lock:
            self._current_locale = locale_code
        return True
    
    def get_locale(self) -> str:
        """Get the current locale."""
        with self._lock:
            return self._current_locale
    
    def translate(self, key: str, **kwargs) -> str:
        """Translate a key to the current locale."""
        with self._lock:
            locale_code = self._current_locale
        
        translations = self._translations.get(locale_code, {})
        result = translations.get(key, key)
        
        # Replace placeholders {{ name }} with values
        for k, v in kwargs.items():
            result = result.replace("{{ " + k + " }}", str(v))
        
        return result
    
    def load_csv(self, locale_code: str, csv_path: str) -> bool:
        """Load translations from a CSV file."""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self._translations[locale_code] = {
                    row['key']: row.get('value', row.get('translation', ''))
                    for row in reader
                }
            return True
        except Exception:
            return False


class LocaleManager:
    """Manages locale configurations and detection."""
    
    def __init__(self):
        self._locales: Dict[str, LocaleConfig] = {}
        self._default_locale = LocaleConfig(
            code="en_US",
            name="English (US)",
            language="en",
            country="US",
            timezone="America/New_York",
            date_format="%m/%d/%Y",
            time_format="%I:%M:%S %p",
            decimal_separator=".",
            thousands_separator=",",
            currency_symbol="$",
            currency_code="USD"
        )
        self._current_locale = self._default_locale
    
    def add_locale(self, config: LocaleConfig):
        """Add a locale configuration."""
        self._locales[config.code] = config
    
    def detect_locale(self, accept_language: Optional[str] = None) -> LocaleConfig:
        """Detect locale from Accept-Language header or system."""
        if accept_language:
            # Parse Accept-Language header
            langs = accept_language.split(',')
            for lang in langs:
                lang = lang.strip().split(';')[0]
                if lang in self._locales:
                    return self._locales[lang]
        
        # Try system locale
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale and system_locale in self._locales:
                return self._locales[system_locale]
        except Exception:
            pass
        
        return self._default_locale
    
    def set_locale(self, locale_code: str) -> bool:
        """Set the current locale."""
        if locale_code in self._locales:
            self._current_locale = self._locales[locale_code]
            return True
        return False
    
    def get_locale(self) -> LocaleConfig:
        """Get the current locale configuration."""
        return self._current_locale


# Format utilities
def format_date(dt: datetime, fmt: Optional[str] = None, locale_code: str = "en_US") -> str:
    """Format a date according to locale."""
    if fmt is None:
        # Use locale-specific format
        lm = LocaleManager()
        config = lm.get_locale()
        fmt = config.date_format
    
    return dt.strftime(fmt)


def format_time(dt: datetime, fmt: Optional[str] = None, locale_code: str = "en_US") -> str:
    """Format a time according to locale."""
    if fmt is None:
        lm = LocaleManager()
        config = lm.get_locale()
        fmt = config.time_format
    
    return dt.strftime(fmt)


def format_number(value: float, locale_code: str = "en_US") -> str:
    """Format a number according to locale."""
    lm = LocaleManager()
    config = lm.get_locale()
    
    # Simple formatting (could be enhanced)
    parts = f"{value:.2f}".split('.')
    integer = parts[0]
    decimal = parts[1] if len(parts) > 1 else "00"
    
    # Add thousands separator
    if config.thousands_separator != ',':
        integer = integer.replace(',', config.thousands_separator)
    
    return f"{integer}{config.decimal_separator}{decimal}"


def format_currency(value: float, locale_code: str = "en_US") -> str:
    """Format currency according to locale."""
    lm = LocaleManager()
    config = lm.get_locale()
    
    return f"{config.currency_symbol}{value:,.2f}"


def detect_locale(accept_language: Optional[str] = None) -> str:
    """Detect locale from Accept-Language header."""
    lm = LocaleManager()
    config = lm.detect_locale(accept_language)
    return config.code


# Global instances
_translator = TranslationManager()
_locale_manager = LocaleManager()


def _(key: str, **kwargs) -> str:
    """Translate a key."""
    return _translator.translate(key, **kwargs)


def set_locale(locale_code: str) -> bool:
    """Set the current locale."""
    _translator.set_locale(locale_code)
    return _locale_manager.set_locale(locale_code)
