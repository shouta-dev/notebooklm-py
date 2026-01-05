"""Unit tests for RPC response decoder."""

import pytest
import json

from notebooklm.rpc.decoder import (
    strip_anti_xssi,
    parse_chunked_response,
    extract_rpc_result,
    decode_response,
    RPCError,
)


class TestStripAntiXSSI:
    def test_strips_prefix(self):
        """Test removal of anti-XSSI prefix."""
        response = ')]}\'\n{"data": "test"}'
        result = strip_anti_xssi(response)
        assert result == '{"data": "test"}'

    def test_no_prefix_unchanged(self):
        """Test response without prefix is unchanged."""
        response = '{"data": "test"}'
        result = strip_anti_xssi(response)
        assert result == response

    def test_handles_windows_newlines(self):
        """Test handles CRLF."""
        response = ')]}\'\r\n{"data": "test"}'
        result = strip_anti_xssi(response)
        assert result == '{"data": "test"}'

    def test_handles_double_newline(self):
        """Test handles double newline after prefix."""
        response = ')]}\'\n\n{"data": "test"}'
        result = strip_anti_xssi(response)
        assert result.startswith("\n{") or result == '{"data": "test"}'


class TestParseChunkedResponse:
    def test_parses_single_chunk(self):
        """Test parsing response with single chunk."""
        chunk_data = ["chunk", "data"]
        chunk_json = json.dumps(chunk_data)
        response = f"{len(chunk_json)}\n{chunk_json}\n"

        chunks = parse_chunked_response(response)

        assert len(chunks) == 1
        assert chunks[0] == ["chunk", "data"]

    def test_parses_multiple_chunks(self):
        """Test parsing response with multiple chunks."""
        chunk1 = json.dumps(["one"])
        chunk2 = json.dumps(["two"])
        response = f"{len(chunk1)}\n{chunk1}\n{len(chunk2)}\n{chunk2}\n"

        chunks = parse_chunked_response(response)

        assert len(chunks) == 2
        assert chunks[0] == ["one"]
        assert chunks[1] == ["two"]

    def test_handles_nested_json(self):
        """Test parsing chunks with nested JSON."""
        inner = json.dumps([["nested", "data"]])
        chunk = ["wrb.fr", "wXbhsf", inner]
        chunk_json = json.dumps(chunk)
        response = f"{len(chunk_json)}\n{chunk_json}\n"

        chunks = parse_chunked_response(response)

        assert len(chunks) == 1
        assert chunks[0][0] == "wrb.fr"
        assert chunks[0][1] == "wXbhsf"

    def test_empty_response(self):
        """Test empty response returns empty list."""
        chunks = parse_chunked_response("")
        assert chunks == []

    def test_whitespace_only_response(self):
        """Test whitespace-only response returns empty list."""
        chunks = parse_chunked_response("   \n\n  ")
        assert chunks == []

    def test_ignores_malformed_chunks(self):
        """Test malformed chunks are ignored."""
        valid = json.dumps(["valid"])
        response = f"{len(valid)}\n{valid}\n99\nnot-json\n"

        chunks = parse_chunked_response(response)

        assert len(chunks) == 1
        assert chunks[0] == ["valid"]


class TestExtractRPCResult:
    def test_extracts_result_for_rpc_id(self):
        """Test extracting result for specific RPC ID."""
        inner_data = json.dumps([["notebook1"]])
        chunks = [
            ["wrb.fr", "wXbhsf", inner_data, None, None],
            ["di", 123],  # Some other chunk type
        ]

        result = extract_rpc_result(chunks, "wXbhsf")
        assert result == [["notebook1"]]

    def test_returns_none_if_not_found(self):
        """Test returns None if RPC ID not in chunks."""
        inner_data = json.dumps([])
        chunks = [
            ["wrb.fr", "other_id", inner_data, None, None],
        ]

        result = extract_rpc_result(chunks, "wXbhsf")
        assert result is None

    def test_handles_double_encoded_json(self):
        """Test handles JSON string inside JSON (common pattern)."""
        inner_json = json.dumps([["notebook1", "id1"]])
        chunks = [
            ["wrb.fr", "wXbhsf", inner_json, None, None],
        ]

        result = extract_rpc_result(chunks, "wXbhsf")
        assert result == [["notebook1", "id1"]]

    def test_handles_non_json_string_result(self):
        """Test handles string results that aren't JSON."""
        chunks = [
            ["wrb.fr", "wXbhsf", "plain string result", None, None],
        ]

        result = extract_rpc_result(chunks, "wXbhsf")
        assert result == "plain string result"

    def test_raises_on_error_chunk(self):
        """Test raises RPCError for error chunks."""
        chunks = [
            ["er", "wXbhsf", "Some error message", None, None],
        ]

        with pytest.raises(RPCError, match="Some error message"):
            extract_rpc_result(chunks, "wXbhsf")

    def test_handles_numeric_error_code(self):
        """Test handles numeric error codes."""
        chunks = [
            ["er", "wXbhsf", 403, None, None],
        ]

        with pytest.raises(RPCError):
            extract_rpc_result(chunks, "wXbhsf")


class TestDecodeResponse:
    def test_full_decode_pipeline(self):
        """Test complete decode from raw response to result."""
        inner_data = json.dumps([["My Notebook", "nb_123"]])
        chunk = json.dumps(["wrb.fr", "wXbhsf", inner_data, None, None])
        raw_response = f")]}}'\n{len(chunk)}\n{chunk}\n"

        result = decode_response(raw_response, "wXbhsf")

        assert result == [["My Notebook", "nb_123"]]

    def test_decode_raises_on_missing_result(self):
        """Test decode raises if RPC ID not found."""
        inner_data = json.dumps([])
        chunk = json.dumps(["wrb.fr", "other_id", inner_data, None, None])
        raw_response = f")]}}'\n{len(chunk)}\n{chunk}\n"

        with pytest.raises(RPCError, match="No result found"):
            decode_response(raw_response, "wXbhsf")

    def test_decode_with_error_response(self):
        """Test decode when response contains error."""
        chunk = json.dumps(["er", "wXbhsf", "Authentication failed", None])
        raw_response = f")]}}'\n{len(chunk)}\n{chunk}\n"

        with pytest.raises(RPCError, match="Authentication failed"):
            decode_response(raw_response, "wXbhsf")

    def test_decode_complex_nested_data(self):
        """Test decoding complex nested data structures."""
        data = {
            "notebooks": [{"id": "nb1", "title": "Test", "sources": [{"id": "s1"}]}]
        }
        inner = json.dumps(data)
        chunk = json.dumps(["wrb.fr", "wXbhsf", inner, None, None])
        raw_response = f")]}}'\n{len(chunk)}\n{chunk}\n"

        result = decode_response(raw_response, "wXbhsf")

        assert result["notebooks"][0]["id"] == "nb1"
