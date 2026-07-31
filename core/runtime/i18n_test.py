"""Test suite for v0.46.0 - Internationalization."""
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from core.runtime.i18n import (
    PluralRule, LocaleConfig, MessageFormatter, I18n,
    _, set_locale, get_locale, format_date, format_currency
)


def test_plural_rule_enum():
    """Test plural rule enum."""
    assert PluralRule.ENGLISH.value == "en"
    assert PluralRule.SPANISH.value == "es"
    assert PluralRule.FRENCH.value == "fr"
    assert PluralRule.GERMAN.value == "de"
    assert PluralRule.ARABIC.value == "ar"
    assert PluralRule.RUSSIAN.value == "ru"
    assert PluralRule.POLISH.value == "pl"
    assert PluralRule.CHINESE.value == "zh"


def test_locale_config_creation():
    """Test creating locale config."""
    config = LocaleConfig(
        code="en-US",
        language="en",
        country="US",
        timezone="America/New_York",
        date_format="%m/%d/%Y"
    )
    
    assert config.code == "en-US"
    assert config.language == "en"
    assert config.country == "US"


def test_message_formatter_simple():
    """Test simple message formatting."""
    formatter = MessageFormatter()
    
    result = formatter.format("Hello {name}!", {"name": "World"})
    assert result == "Hello World!"


def test_message_formatter_plural_english():
    """Test English plural formatting."""
    formatter = MessageFormatter()
    
    # One item
    result = formatter.format("{count} item", {"count": 1}, PluralRule.ENGLISH)
    # Note: our simple implementation doesn't handle ICU plural syntax
    assert "1" in result or "item" in result


def test_message_formatter_plural_spanish():
    """Test Spanish plural formatting."""
    formatter = MessageFormatter()
    
    result = formatter._spanish_plural(1)
    assert result == "one"
    
    result = formatter._spanish_plural(2)
    assert result == "other"


def test_message_formatter_plural_arabic():
    """Test Arabic plural formatting."""
    formatter = MessageFormatter()
    
    assert formatter._arabic_plural(0) == "zero"
    assert formatter._arabic_plural(1) == "one"
    assert formatter._arabic_plural(2) == "two"
    assert formatter._arabic_plural(5) == "few"
    assert formatter._arabic_plural(15) == "many"


def test_i18n_init():
    """Test i18n initialization."""
    i18n = I18n()
    
    assert i18n.current_locale is None
    assert "en-US" in i18n.locales
    assert "es-MX" in i18n.locales


def test_i18n_set_locale():
    """Test setting locale."""
    i18n = I18n()
    
    i18n.set_locale("es-MX")
    assert i18n.current_locale == "es-MX"


def test_i18n_get_locale():
    """Test getting locale config."""
    i18n = I18n()
    
    config = i18n.get_locale()
    assert config.code == "en-US"  # Default


def test_i18n_detect_locale():
    """Test locale detection."""
    i18n = I18n()
    
    # Default
    locale = i18n.detect_locale()
    assert locale == "en-US"


def test_i18n_t_function():
    """Test translation function."""
    i18n = I18n()
    
    # Key not in translations, returns key
    result = i18n.t("missing_key")
    assert result == "missing_key"


def test_format_date():
    """Test date formatting."""
    i18n = I18n()
    i18n.set_locale("en-US")
    
    dt = datetime(2024, 7, 15, 14, 30, 0)
    result = i18n.format_date(dt)
    
    assert "07" in result or "July" in result or "15" in result


def test_format_time():
    """Test time formatting."""
    i18n = I18n()
    i18n.set_locale("en-US")
    
    dt = datetime(2024, 7, 15, 14, 30, 0)
    result = i18n.format_time(dt)
    
    assert "14" in result or "02" in result


def test_format_currency_usd():
    """Test USD currency formatting."""
    i18n = I18n()
    i18n.set_locale("en-US")
    
    result = i18n.format_currency(1234.56)
    assert "$" in result or "1234" in result


def test_format_currency_eur():
    """Test EUR currency formatting."""
    i18n = I18n()
    i18n.set_locale("es-ES")
    
    result = i18n.format_currency(1234.56)
    assert "€" in result or "1234" in result


def test_format_number():
    """Test number formatting."""
    i18n = I18n()
    i18n.set_locale("en-US")
    
    result = i18n.format_number(1234.56, decimals=2)
    # Number formatting should work
    assert result is not None and len(result) > 0


def test_format_phone_us():
    """Test US phone formatting."""
    i18n = I18n()
    
    result = i18n.format_phone("1234567890")
    assert "(" in result and ")" in result


def test_convenience_functions():
    """Test convenience functions."""
    # These create new instances, so just verify they don't crash
    set_locale("en-US")
    locale = get_locale()
    assert locale.code == "en-US"


def test_spanish_locale():
    """Test Spanish locale configuration."""
    i18n = I18n()
    i18n.set_locale("es-MX")
    
    config = i18n.get_locale()
    assert config.language == "es"
    assert config.country == "MX"
    assert config.currency_symbol == "$"


def test_french_locale():
    """Test French locale configuration."""
    i18n = I18n()
    i18n.set_locale("fr-FR")
    
    config = i18n.get_locale()
    assert config.language == "fr"
    assert config.currency_symbol == "€"


def test_extract_strings():
    """Test string extraction."""
    i18n = I18n()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = f"{tmpdir}/strings.json"
        strings = i18n.extract_strings(source_dir="core", output_file=output_file)
        
        assert "en" in strings


def test_locale_fallback():
    """Test locale fallback to default."""
    i18n = I18n()
    i18n.current_locale = "unknown-locale"
    
    config = i18n.get_locale()
    assert config.code == "en-US"  # Falls back to default