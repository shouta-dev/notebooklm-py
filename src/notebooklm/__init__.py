"""NotebookLM Automation - RPC-based automation for Google NotebookLM."""

__version__ = "0.1.0"

from .rpc import (
    RPCMethod,
    StudioContentType,
    BATCHEXECUTE_URL,
    QUERY_URL,
    encode_rpc_request,
    build_request_body,
    decode_response,
    RPCError,
)
from .auth import (
    AuthTokens,
    extract_cookies_from_storage,
    extract_csrf_from_html,
    extract_session_id_from_html,
    load_auth_from_storage,
    MINIMUM_REQUIRED_COOKIES,
    ALLOWED_COOKIE_DOMAINS,
    DEFAULT_STORAGE_PATH,
)
from .api_client import NotebookLMClient

__all__ = [
    "__version__",
    "RPCMethod",
    "StudioContentType",
    "BATCHEXECUTE_URL",
    "QUERY_URL",
    "encode_rpc_request",
    "build_request_body",
    "decode_response",
    "RPCError",
    "AuthTokens",
    "extract_cookies_from_storage",
    "extract_csrf_from_html",
    "extract_session_id_from_html",
    "load_auth_from_storage",
    "MINIMUM_REQUIRED_COOKIES",
    "ALLOWED_COOKIE_DOMAINS",
    "DEFAULT_STORAGE_PATH",
    "NotebookLMClient",
]
