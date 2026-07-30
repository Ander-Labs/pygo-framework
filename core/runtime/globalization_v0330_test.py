"""Test suite for v0.33.0 - i18n and WebSockets."""
import pytest
import tempfile
import os
import json
from datetime import datetime

from core.runtime.i18n import (
    TranslationManager, LocaleManager, LocaleConfig,
    format_date, format_time, format_number, format_currency,
    _, set_locale, detect_locale
)


def test_v0330_translation_manager_load():
    """Test TranslationManager loading translations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test translation file
        trans_file = os.path.join(tmpdir, "es.json")
        with open(trans_file, 'w') as f:
            json.dump({
                "hello": "hola",
                "greeting": "hola {{ name }}"
            }, f)
        
        tm = TranslationManager(tmpdir)
        result = tm.load_locale("es")
        assert result is True
        # Set locale first
        tm.set_locale("es")
        assert tm.translate("hello") == "hola"


def test_v0330_translation_manager_missing_key():
    """Test TranslationManager with missing key."""
    tm = TranslationManager()
    assert tm.translate("nonexistent") == "nonexistent"


def test_v0330_translation_manager_placeholders():
    """Test TranslationManager with placeholders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        trans_file = os.path.join(tmpdir, "es.json")
        with open(trans_file, 'w') as f:
            json.dump({
                "greeting": "hola {{ name }}, bienvenido"
            }, f)
        
        tm = TranslationManager(tmpdir)
        tm.set_locale("es")
        
        result = tm.translate("greeting", name="Alice")
        assert result == "hola Alice, bienvenido"


def test_v0330_locale_manager_add():
    """Test LocaleManager adding locales."""
    lm = LocaleManager()
    
    es_config = LocaleConfig(
        code="es_ES",
        name="Spanish (Spain)",
        language="es",
        date_format="%d/%m/%Y",
        currency_symbol="€"
    )
    
    lm.add_locale(es_config)
    assert "es_ES" in lm._locales


def test_v0330_locale_manager_default():
    """Test LocaleManager default locale."""
    lm = LocaleManager()
    default = lm.get_locale()
    
    assert default.code == "en_US"
    assert default.currency_symbol == "$"


def test_v0330_format_date():
    """Test format_date function."""
    dt = datetime(2026, 7, 31, 14, 30, 0)
    
    # Default format
    result = format_date(dt)
    assert "2026" in result


def test_v0330_format_time():
    """Test format_time function."""
    dt = datetime(2026, 7, 31, 14, 30, 0)
    
    result = format_time(dt)
    assert "14:30" in result or "2:30" in result


def test_v0330_format_number():
    """Test format_number function."""
    result = format_number(1234.56)
    assert "1234" in result


def test_v0330_format_currency():
    """Test format_currency function."""
    result = format_currency(1234.56)
    assert "$" in result or "€" in result or "£" in result


def test_v0330_detect_locale():
    """Test detect_locale function."""
    result = detect_locale("es-ES")
    assert result is not None


# ============== WebSockets Tests ==============

from core.runtime.websockets import WebSocketServer, WebSocketClient, Message, PubSub, Channel


def test_v0330_websocket_message():
    """Test WebSocket Message."""
    msg = Message(
        type="test",
        data={"key": "value"},
        channel="test_channel"
    )
    
    assert msg.type == "test"
    assert msg.data == {"key": "value"}
    assert msg.channel == "test_channel"


def test_v0330_websocket_server_init():
    """Test WebSocketServer initialization."""
    server = WebSocketServer(host="localhost", port=8765)
    
    assert server.host == "localhost"
    assert server.port == 8765


def test_v0330_websocket_client_init():
    """Test WebSocketClient initialization."""
    client = WebSocketClient(url="ws://localhost:8765")
    
    assert client.url == "ws://localhost:8765"


def test_v0330_pubsub():
    """Test Pub/Sub functionality."""
    ps = PubSub()
    
    messages = []
    
    def handler(msg):
        messages.append(msg)
    
    ps.subscribe("test_channel", handler)
    ps.publish("test_channel", {"test": "data"})
    
    assert len(messages) == 1
    assert messages[0].data["test"] == "data"


def test_v0330_channels():
    """Test Channels functionality."""
    ch = Channel("notifications")
    
    assert ch.name == "notifications"
    assert ch.subscribers == []
