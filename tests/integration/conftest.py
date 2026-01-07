"""Shared fixtures for integration tests."""

import json

import pytest

from notebooklm.auth import AuthTokens


@pytest.fixture
def auth_tokens():
    """Create test authentication tokens."""
    return AuthTokens(
        cookies={
            "SID": "test_sid",
            "HSID": "test_hsid",
            "SSID": "test_ssid",
            "APISID": "test_apisid",
            "SAPISID": "test_sapisid",
        },
        csrf_token="test_csrf_token",
        session_id="test_session_id",
    )


@pytest.fixture
def build_rpc_response():
    """Factory for building RPC responses."""

    def _build(rpc_id: str, data) -> str:
        inner = json.dumps(data)
        chunk = json.dumps(["wrb.fr", rpc_id, inner, None, None])
        return f")]}}'\n{len(chunk)}\n{chunk}\n"

    return _build


@pytest.fixture
def mock_list_notebooks_response():
    """Mock response for listing notebooks."""
    inner_data = json.dumps(
        [
            [
                [
                    "My First Notebook",
                    [],
                    "nb_001",
                    "📘",
                    None,
                    [None, None, None, None, None, [1704067200, 0]],
                ],
                [
                    "Research Notes",
                    [],
                    "nb_002",
                    "📚",
                    None,
                    [None, None, None, None, None, [1704153600, 0]],
                ],
            ]
        ]
    )
    chunk = json.dumps([["wrb.fr", "wXbhsf", inner_data, None, None]])
    return f")]}}'\n{len(chunk)}\n{chunk}\n"
