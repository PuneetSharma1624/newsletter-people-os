"""Tests for email validation and normalization."""
import sys
import os
from unittest.mock import MagicMock

for mod in ["supabase", "resend", "anthropic", "tavily"]:
    sys.modules.setdefault(mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from newsletter.utils import is_valid_email, normalize_email


class TestEmailValidation:
    def test_valid_simple(self):
        assert is_valid_email("user@example.com")

    def test_valid_subdomain(self):
        assert is_valid_email("user@mail.example.co.uk")

    def test_valid_plus_address(self):
        assert is_valid_email("user+tag@example.com")

    def test_invalid_no_at(self):
        assert not is_valid_email("userexample.com")

    def test_invalid_no_domain(self):
        assert not is_valid_email("user@")

    def test_invalid_empty(self):
        assert not is_valid_email("")

    def test_invalid_spaces(self):
        assert not is_valid_email("user @example.com")

    def test_invalid_double_at(self):
        assert not is_valid_email("user@@example.com")

    def test_invalid_no_tld(self):
        assert not is_valid_email("user@example")


class TestEmailNormalization:
    def test_lowercase(self):
        assert normalize_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_strip_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_mixed_case_and_spaces(self):
        assert normalize_email("  User@Example.COM  ") == "user@example.com"

    def test_already_normalized(self):
        assert normalize_email("user@example.com") == "user@example.com"
