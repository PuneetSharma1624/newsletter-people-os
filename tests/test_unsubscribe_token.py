"""Tests for unsubscribe token generation."""
import sys
import os
from unittest.mock import MagicMock

for mod in ["supabase", "resend", "anthropic", "tavily"]:
    sys.modules.setdefault(mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from newsletter.utils import generate_token


class TestTokenGeneration:
    def test_default_length(self):
        token = generate_token()
        assert len(token) == 48

    def test_custom_length(self):
        token = generate_token(32)
        assert len(token) == 32

    def test_alphanumeric_only(self):
        token = generate_token(100)
        assert token.isalnum(), "Token should be alphanumeric only"

    def test_uniqueness(self):
        tokens = {generate_token() for _ in range(100)}
        assert len(tokens) == 100, "All 100 tokens should be unique"

    def test_not_predictable(self):
        t1 = generate_token()
        t2 = generate_token()
        assert t1 != t2

    def test_minimum_entropy(self):
        token = generate_token(48)
        assert len(token) >= 32, "Token should have sufficient length for security"
