"""PyGo Internationalization (v0.46.0).

Provides complete i18n support with:
- Automatic locale detection
- Pluralization rules
- Regional formatting
- Timezone support
- ICU message format
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import locale


class PluralRule(str, Enum):
    """Pluralization rules per CLDR."""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ARABIC = "ar"
    RUSSIAN = "ru"
    POLISH = "pl"
    CHINESE = "zh"


@dataclass
class LocaleConfig:
    """Locale configuration."""
    code: str  # e.g., "en-US", "es-MX"
    language: str  # e.g., "en", "es"
    country: Optional[str] = None
    timezone: str = "UTC"
    plural_rule: PluralRule = PluralRule.ENGLISH
    date_format: str = "%Y-%m-%d"
    time_format: str = "%H:%M:%S"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    currency_symbol: str = "$"
    currency_code: str = "USD"
    decimal_separator: str = "."
    thousands_separator: str = ","
    direction: str = "ltr"  # ltr, rtl


class MessageFormatter:
    """Formats ICU messages."""
    
    def __init__(self):
        self.plural_rules = {
            PluralRule.ENGLISH: self._english_plural,
            PluralRule.SPANISH: self._spanish_plural,
            PluralRule.FRENCH: self._french_plural,
            PluralRule.GERMAN: self._german_plural,
            PluralRule.ARABIC: self._arabic_plural,
            PluralRule.RUSSIAN: self._russian_plural,
            PluralRule.POLISH: self._polish_plural,
            PluralRule.CHINESE: self._chinese_plural,
        }
    
    def format(self, message: str, args: Dict[str, Any], plural_rule: PluralRule = PluralRule.ENGLISH) -> str:
        """Format ICU message."""
        result = message
        
        # Handle simple variable substitution
        for key, value in args.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        # Handle plural forms
        for key, value in args.items():
            if isinstance(value, int):
                plural_key = f"{{{key}, plural}}"
                if plural_key in result:
                    plural_form = self._get_plural_form(value, plural_rule)
                    result = self._extract_plural(result, key, plural_form)
        
        return result
    
    def _english_plural(self, count: int) -> str:
        """English plural: one vs other."""
        return "one" if count == 1 else "other"
    
    def _spanish_plural(self, count: int) -> str:
        """Spanish plural: one vs other."""
        return "one" if count == 1 else "other"
    
    def _french_plural(self, count: int) -> str:
        """French plural: one vs other."""
        return "one" if count == 0 or count == 1 else "other"
    
    def _german_plural(self, count: int) -> str:
        """German plural: one vs other."""
        return "one" if count == 1 else "other"
    
    def _arabic_plural(self, count: int) -> str:
        """Arabic plural: 0, 1, 2, few, many, other."""
        if count == 0:
            return "zero"
        elif count == 1:
            return "one"
        elif count == 2:
            return "two"
        elif 3 <= count <= 10:
            return "few"
        elif 11 <= count <= 99:
            return "many"
        else:
            return "other"
    
    def _russian_plural(self, count: int) -> str:
        """Russian plural: one, few, many, other."""
        n = count % 100
        if n == 1:
            return "one"
        elif 2 <= n <= 4:
            return "few"
        elif 5 <= n <= 20:
            return "many"
        else:
            n1 = n % 10
            if n1 >= 5:
                return "many"
            return "other"
    
    def _polish_plural(self, count: int) -> str:
        """Polish plural: one, few, many, other."""
        if count == 1:
            return "one"
        elif count % 10 >= 2 and count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "few"
        else:
            return "other"
    
    def _chinese_plural(self, count: int) -> str:
        """Chinese has no plural."""
        return "other"
    
    def _get_plural_form(self, count: int, rule: PluralRule) -> str:
        """Get plural form for count and rule."""
        return self.plural_rules[rule](count)
    
    def _extract_plural(self, message: str, key: str, form: str) -> str:
        """Extract plural form from message."""
        # Simple extraction - look for pattern {key, plural, one{...} other{...}}
        import re
        pattern = r"{" + key + ", plural, one{(.*?)}} other{(.*?)}}"
        match = re.search(pattern, message)
        if match:
            if form == "one":
                return match.group(1)
            else:
                return match.group(2)
        return message


class I18n:
    """Internationalization manager."""
    
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = Path(translations_dir)
        self.translations_dir.mkdir(parents=True, exist_ok=True)
        self.current_locale: Optional[str] = None
        self.locales: Dict[str, LocaleConfig] = {}
        self.formatter = MessageFormatter()
        self._load_locales()
    
    def _load_locales(self) -> None:
        """Load locale configurations."""
        # Default locales
        self.locales["en-US"] = LocaleConfig(
            code="en-US", language="en", country="US",
            timezone="America/New_York",
            date_format="%m/%d/%Y",
            time_format="%I:%M:%S %p",
            datetime_format="%m/%d/%Y %I:%M:%S %p",
            currency_symbol="$", currency_code="USD"
        )
        self.locales["es-MX"] = LocaleConfig(
            code="es-MX", language="es", country="MX",
            timezone="America/Mexico_City",
            date_format="%d/%m/%Y",
            time_format="%H:%M:%S",
            datetime_format="%d/%m/%Y %H:%M:%S",
            currency_symbol="$", currency_code="MXN"
        )
        self.locales["es-ES"] = LocaleConfig(
            code="es-ES", language="es", country="ES",
            timezone="Europe/Madrid",
            date_format="%d/%m/%Y",
            time_format="%H:%M:%S",
            datetime_format="%d/%m/%Y %H:%M:%S",
            currency_symbol="€", currency_code="EUR"
        )
        self.locales["fr-FR"] = LocaleConfig(
            code="fr-FR", language="fr", country="FR",
            timezone="Europe/Paris",
            date_format="%d/%m/%Y",
            time_format="%H:%M:%S",
            datetime_format="%d/%m/%Y %H:%M:%S",
            currency_symbol="€", currency_code="EUR"
        )
    
    def detect_locale(self, request: Optional[Any] = None) -> str:
        """Detect locale from request or defaults."""
        # Priority order: session, cookie, header, subdomain, URL param, Accept-Language
        if request:
            # Try session
            if hasattr(request, 'session') and request.session.get('locale'):
                return request.session['locale']
            
            # Try cookie
            if hasattr(request, 'cookies') and request.cookies.get('locale'):
                return request.cookies['locale']
            
            # Try header
            if hasattr(request, 'headers'):
                accept_lang = request.headers.get('Accept-Language', '')
                if accept_lang:
                    return self._parse_accept_language(accept_lang)
        
        return "en-US"
    
    def _parse_accept_language(self, header: str) -> str:
        """Parse Accept-Language header."""
        parts = header.split(',')
        if parts:
            lang = parts[0].strip().split(';')[0]
            if lang in self.locales:
                return lang
            # Try language only
            lang_code = lang.split('-')[0]
            for code in self.locales:
                if code.startswith(lang_code):
                    return code
        return "en-US"
    
    def set_locale(self, locale_code: str) -> None:
        """Set current locale."""
        if locale_code in self.locales:
            self.current_locale = locale_code
        else:
            raise ValueError(f"Unknown locale: {locale_code}")
    
    def get_locale(self) -> LocaleConfig:
        """Get current locale config."""
        if self.current_locale and self.current_locale in self.locales:
            return self.locales[self.current_locale]
        return self.locales["en-US"]
    
    def t(self, key: str, **kwargs) -> str:
        """Translate a string."""
        # Load translations
        translations = self._load_translations()
        
        locale_config = self.get_locale()
        lang = locale_config.language
        
        if lang in translations and key in translations[lang]:
            message = translations[lang][key]
            return self.formatter.format(message, kwargs, locale_config.plural_rule)
        
        return key
    
    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """Load translation files."""
        translations = {}
        
        for locale_code, config in self.locales.items():
            lang = config.language
            translation_file = self.translations_dir / f"{lang}.json"
            
            if translation_file.exists():
                with open(translation_file) as f:
                    translations[lang] = json.load(f)
            else:
                translations[lang] = {}
        
        return translations
    
    def extract_strings(self, source_dir: str = "app", output_file: str = "translations/strings.json") -> Dict[str, List[str]]:
        """Extract translatable strings from source code."""
        import re
        
        strings = {"en": [], "es": [], "fr": []}
        
        # Find .pygo, .py, .html files
        for ext in ['*.pgo', '*.py', '*.html']:
            for file_path in Path(source_dir).rglob(ext):
                try:
                    content = file_path.read_text()
                    # Find t("...") or _("...") patterns
                    matches = re.findall(r't\(["\']([^"\']+)["\']\)', content)
                    matches += re.findall(r'_\((["\'])(.+?)\1\)', content)
                    strings["en"].extend(matches)
                except Exception:
                    pass
        
        # Write extraction file
        with open(output_file, 'w') as f:
            json.dump(strings, f, indent=2, ensure_ascii=False)
        
        return strings
    
    def format_date(self, date: datetime, format: Optional[str] = None) -> str:
        """Format date according to locale."""
        locale_config = self.get_locale()
        fmt = format or locale_config.date_format
        return date.strftime(fmt)
    
    def format_time(self, time: datetime, format: Optional[str] = None) -> str:
        """Format time according to locale."""
        locale_config = self.get_locale()
        fmt = format or locale_config.time_format
        return time.strftime(fmt)
    
    def format_datetime(self, dt: datetime, format: Optional[str] = None) -> str:
        """Format datetime according to locale."""
        locale_config = self.get_locale()
        fmt = format or locale_config.datetime_format
        return dt.strftime(fmt)
    
    def format_number(self, number: float, decimals: int = 2) -> str:
        """Format number according to locale."""
        locale_config = self.get_locale()
        sep = locale_config.thousands_separator
        dec = locale_config.decimal_separator
        
        formatted = f"{number:.{decimals}f}"
        if sep:
            parts = formatted.split('.')
            parts[0] = '{:,}'.format(float(parts[0])).replace(',', sep)
            formatted = dec.join(parts)
        
        return formatted
    
    def format_currency(self, amount: float, currency: Optional[str] = None) -> str:
        """Format currency according to locale."""
        locale_config = self.get_locale()
        curr = currency or locale_config.currency_code
        symbol = locale_config.currency_symbol
        
        formatted = self.format_number(amount)
        return f"{symbol}{formatted}"
    
    def format_phone(self, phone: str, format: str = "default") -> str:
        """Format phone number according to locale."""
        # Simplified formatting
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone[0] == '1':
            return f"1 ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        return phone


# Convenience functions
def _(key: str, **kwargs) -> str:
    """Translate string (alias for t)."""
    i18n = I18n()
    return i18n.t(key, **kwargs)


def set_locale(locale_code: str) -> None:
    """Set current locale."""
    i18n = I18n()
    i18n.set_locale(locale_code)


def get_locale() -> LocaleConfig:
    """Get current locale config."""
    i18n = I18n()
    return i18n.get_locale()


def format_date(date: datetime, fmt: Optional[str] = None) -> str:
    """Format date according to locale."""
    i18n = I18n()
    return i18n.format_date(date, fmt)


def format_currency(amount: float, currency: Optional[str] = None) -> str:
    """Format currency according to locale."""
    i18n = I18n()
    return i18n.format_currency(amount, currency)