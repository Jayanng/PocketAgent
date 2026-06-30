"""Tests for backend/services/agent_token_service.py."""
from backend.services.agent_token_service import (
    generate_access_token,
    hash_access_token,
)


def test_generate_produces_unique_tokens():
    tokens = {generate_access_token() for _ in range(1000)}
    assert len(tokens) == 1000


def test_hash_is_deterministic():
    tok = generate_access_token()
    assert hash_access_token(tok) == hash_access_token(tok)


def test_hash_differs_for_different_tokens():
    a = hash_access_token(generate_access_token())
    b = hash_access_token(generate_access_token())
    assert a != b


def test_hash_length_is_sha256_hex():
    tok = generate_access_token()
    h = hash_access_token(tok)
    assert isinstance(h, str)
    assert len(h) == 64
