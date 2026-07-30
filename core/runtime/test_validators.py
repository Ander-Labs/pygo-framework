"""Test suite for type validators (v0.18.0)."""
import pytest
from core.runtime.validators import (
    validate_uuid,
    validate_email,
    validate_url,
    validate_phone,
    validate_datetime,
    validate_string,
    validate_int,
    validate_float,
    validate_bool,
    validate_field,
)
from datetime import datetime


class TestValidateUUID:
    """Tests for UUID validation."""
    
    def test_valid_uuid(self):
        """Valid UUID should pass validation."""
        assert validate_uuid("123e4567-e89b-12d3-a456-426614174000") == "123e4567-e89b-12d3-a456-426614174000"
    
    def test_valid_uuid_uppercase(self):
        """Valid UUID with uppercase letters should pass."""
        assert validate_uuid("123E4567-E89B-12D3-A456-426614174000") == "123E4567-E89B-12D3-A456-426614174000"
    
    def test_invalid_uuid(self):
        """Invalid UUID should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            validate_uuid("not-a-uuid")
    
    def test_non_string_uuid(self):
        """Non-string input should raise ValueError."""
        with pytest.raises(ValueError, match="Expected string for UUID"):
            validate_uuid(12345)


class TestValidateEmail:
    """Tests for email validation."""
    
    def test_valid_email(self):
        """Valid email should pass validation."""
        assert validate_email("test@example.com") == "test@example.com"
    
    def test_valid_email_with_plus(self):
        """Email with plus sign should pass."""
        assert validate_email("user+tag@example.org") == "user+tag@example.org"
    
    def test_invalid_email(self):
        """Invalid email should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid email format"):
            validate_email("not-an-email")
    
    def test_non_string_email(self):
        """Non-string input should raise ValueError."""
        with pytest.raises(ValueError, match="Expected string for email"):
            validate_email(12345)


class TestValidateURL:
    """Tests for URL validation."""
    
    def test_valid_http_url(self):
        """Valid HTTP URL should pass validation."""
        assert validate_url("http://example.com") == "http://example.com"
    
    def test_valid_https_url(self):
        """Valid HTTPS URL should pass validation."""
        assert validate_url("https://example.com/path?query=value") == "https://example.com/path?query=value"
    
    def test_invalid_url(self):
        """Invalid URL should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid URL format"):
            validate_url("not-a-url")
    
    def test_non_string_url(self):
        """Non-string input should raise ValueError."""
        with pytest.raises(ValueError, match="Expected string for URL"):
            validate_url(12345)


class TestValidatePhone:
    """Tests for phone validation."""
    
    def test_valid_phone_international(self):
        """Valid international phone should pass."""
        assert validate_phone("+1234567890") == "+1234567890"
    
    def test_valid_phone_local(self):
        """Valid local phone should pass."""
        assert validate_phone("1234567890") == "1234567890"
    
    def test_valid_phone_with_spaces(self):
        """Phone with spaces should be normalized."""
        assert validate_phone("+1 234 567 8900") == "+12345678900"
    
    def test_invalid_phone(self):
        """Invalid phone should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid phone format"):
            validate_phone("abc")
    
    def test_non_string_phone(self):
        """Non-string input should raise ValueError."""
        with pytest.raises(ValueError, match="Expected string for phone"):
            validate_phone(12345)


class TestValidateDateTime:
    """Tests for datetime validation."""
    
    def test_valid_iso_datetime(self):
        """Valid ISO 8601 datetime should pass."""
        result = validate_datetime("2024-01-15T10:30:00")
        assert isinstance(result, datetime)
    
    def test_valid_datetime_with_z(self):
        """Valid datetime with Z suffix should pass."""
        result = validate_datetime("2024-01-15T10:30:00Z")
        assert isinstance(result, datetime)
    
    def test_valid_date_only(self):
        """Valid date-only string should pass."""
        result = validate_datetime("2024-01-15")
        assert isinstance(result, datetime)
    
    def test_datetime_object_passes(self):
        """datetime object should pass through."""
        dt = datetime(2024, 1, 15, 10, 30)
        assert validate_datetime(dt) == dt
    
    def test_invalid_datetime(self):
        """Invalid datetime should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            validate_datetime("not-a-datetime")
    
    def test_non_string_datetime(self):
        """Non-string/non-datetime input should raise ValueError."""
        with pytest.raises(ValueError, match="Expected string or datetime"):
            validate_datetime(12345)


class TestValidateField:
    """Tests for the generic validate_field function."""
    
    def test_validate_field_uuid(self):
        """validate_field with UUID type should work."""
        assert validate_field("UUID", "123e4567-e89b-12d3-a456-426614174000") == "123e4567-e89b-12d3-a456-426614174000"
    
    def test_validate_field_email(self):
        """validate_field with Email type should work."""
        assert validate_field("Email", "test@example.com") == "test@example.com"
    
    def test_validate_field_unknown_type(self):
        """validate_field with unknown type should return value as-is."""
        assert validate_field("UnknownType", "anything") == "anything"
    
    def test_validate_field_model_type(self):
        """validate_field with model type should return value as-is."""
        # Model types are not validated at runtime
        assert validate_field("User", {"id": 1}) == {"id": 1}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])