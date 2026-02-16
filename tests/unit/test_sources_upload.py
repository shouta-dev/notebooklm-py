"""Unit tests for SourcesAPI file upload pipeline and YouTube detection."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from notebooklm._sources import SourcesAPI
from notebooklm.types import Source


@pytest.fixture
def mock_core():
    """Create a mocked ClientCore for SourcesAPI."""
    core = MagicMock()
    core.rpc_call = AsyncMock()
    core.auth = MagicMock()
    core.auth.cookie_header = "SID=test_sid; HSID=test_hsid"
    return core


@pytest.fixture
def sources_api(mock_core):
    """Create SourcesAPI with mocked core."""
    return SourcesAPI(mock_core)


# =============================================================================
# _extract_youtube_video_id() tests
# =============================================================================


class TestExtractYoutubeVideoId:
    """Tests for YouTube video ID extraction."""

    def test_extract_youtube_short_url(self, sources_api):
        """Test extraction from youtu.be short URLs."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "dQw4w9WgXcQ"

    def test_extract_youtube_short_url_http(self, sources_api):
        """Test extraction from HTTP youtu.be URLs."""
        url = "http://youtu.be/abc123_XYZ"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "abc123_XYZ"

    def test_extract_youtube_standard_watch_url(self, sources_api):
        """Test extraction from standard watch URLs."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "dQw4w9WgXcQ"

    def test_extract_youtube_watch_url_no_www(self, sources_api):
        """Test extraction from watch URLs without www."""
        url = "https://youtube.com/watch?v=abc123-_XY"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "abc123-_XY"

    def test_extract_youtube_shorts_url(self, sources_api):
        """Test extraction from shorts URLs."""
        url = "https://www.youtube.com/shorts/abc123DEF"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "abc123DEF"

    def test_extract_youtube_shorts_url_no_www(self, sources_api):
        """Test extraction from shorts URLs without www."""
        url = "https://youtube.com/shorts/xyz789"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "xyz789"

    def test_extract_youtube_returns_none_for_non_youtube(self, sources_api):
        """Test that non-YouTube URLs return None."""
        url = "https://example.com/video"
        result = sources_api._extract_youtube_video_id(url)
        assert result is None

    def test_extract_youtube_returns_none_for_invalid_format(self, sources_api):
        """Test that invalid YouTube URLs return None."""
        url = "https://youtube.com/invalid/format"
        result = sources_api._extract_youtube_video_id(url)
        assert result is None

    def test_extract_youtube_with_hyphen_underscore_in_id(self, sources_api):
        """Test extraction with hyphens and underscores in video ID."""
        url = "https://youtu.be/a-b_c-D_E-f"
        result = sources_api._extract_youtube_video_id(url)
        assert result == "a-b_c-D_E-f"


# =============================================================================
# _register_file_source() tests
# =============================================================================


class TestRegisterFileSource:
    """Tests for file source registration."""

    @pytest.mark.asyncio
    async def test_register_file_source_success(self, sources_api, mock_core):
        """Test successful file source registration."""
        # Response structure: [[[["source_id_123"]]]] - 4 levels with string at deepest
        mock_core.rpc_call.return_value = [[[["source_id_abc"]]]]

        result = await sources_api._register_file_source("nb_123", "test.pdf")

        assert result == "source_id_abc"
        mock_core.rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_file_source_parses_deeply_nested(self, sources_api, mock_core):
        """Test parsing deeply nested response."""
        mock_core.rpc_call.return_value = [[[["my_source_id"]]]]

        result = await sources_api._register_file_source("nb_123", "doc.docx")

        assert result == "my_source_id"

    @pytest.mark.asyncio
    async def test_register_file_source_raises_on_null_response(self, sources_api, mock_core):
        """Test that null response raises SourceAddError."""
        from notebooklm.exceptions import SourceAddError

        mock_core.rpc_call.return_value = None

        with pytest.raises(SourceAddError, match="Failed to get SOURCE_ID"):
            await sources_api._register_file_source("nb_123", "test.pdf")

    @pytest.mark.asyncio
    async def test_register_file_source_raises_on_empty_response(self, sources_api, mock_core):
        """Test that empty response raises SourceAddError."""
        from notebooklm.exceptions import SourceAddError

        mock_core.rpc_call.return_value = []

        with pytest.raises(SourceAddError, match="Failed to get SOURCE_ID"):
            await sources_api._register_file_source("nb_123", "test.pdf")

    @pytest.mark.asyncio
    async def test_register_file_source_extracts_id_from_nested_lists(self, sources_api, mock_core):
        """Test that ID is extracted from arbitrarily nested lists."""
        # The flexible parser should extract "source_id_123" from any nesting depth
        mock_core.rpc_call.return_value = [[["source_id_123"]]]

        result = await sources_api._register_file_source("nb_123", "test.pdf")
        assert result == "source_id_123"

    @pytest.mark.asyncio
    async def test_register_file_source_raises_on_non_string_id(self, sources_api, mock_core):
        """Test that non-string source ID raises SourceAddError."""
        from notebooklm.exceptions import SourceAddError

        mock_core.rpc_call.return_value = [[[[[[12345]]]]]]

        with pytest.raises(SourceAddError, match="Failed to get SOURCE_ID"):
            await sources_api._register_file_source("nb_123", "test.pdf")


# =============================================================================
# _start_resumable_upload() tests
# =============================================================================


class TestStartResumableUpload:
    """Tests for starting resumable upload."""

    @pytest.mark.asyncio
    async def test_start_resumable_upload_success(self, sources_api, mock_core):
        """Test successful upload start."""
        mock_response = MagicMock()
        mock_response.headers = {"x-goog-upload-url": "https://upload.example.com/session123"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = await sources_api._start_resumable_upload(
                "nb_123", "test.pdf", 1024, "src_456"
            )

        assert result == "https://upload.example.com/session123"

    @pytest.mark.asyncio
    async def test_start_resumable_upload_includes_correct_headers(self, sources_api, mock_core):
        """Test that upload start includes correct headers."""
        mock_response = MagicMock()
        mock_response.headers = {"x-goog-upload-url": "https://upload.example.com"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            await sources_api._start_resumable_upload("nb_123", "test.pdf", 2048, "src_789")

            call_kwargs = mock_client.post.call_args[1]
            headers = call_kwargs["headers"]

            assert headers["x-goog-upload-command"] == "start"
            assert headers["x-goog-upload-header-content-length"] == "2048"
            assert headers["x-goog-upload-protocol"] == "resumable"
            assert "Cookie" in headers

    @pytest.mark.asyncio
    async def test_start_resumable_upload_includes_json_body(self, sources_api, mock_core):
        """Test that upload start includes correct JSON body."""
        import json

        mock_response = MagicMock()
        mock_response.headers = {"x-goog-upload-url": "https://upload.example.com"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            await sources_api._start_resumable_upload("nb_test", "myfile.pdf", 1000, "src_abc")

            call_kwargs = mock_client.post.call_args[1]
            body = json.loads(call_kwargs["content"])

            assert body["PROJECT_ID"] == "nb_test"
            assert body["SOURCE_NAME"] == "myfile.pdf"
            assert body["SOURCE_ID"] == "src_abc"

    @pytest.mark.asyncio
    async def test_start_resumable_upload_raises_on_missing_url_header(
        self, sources_api, mock_core
    ):
        """Test that missing upload URL header raises SourceAddError."""
        from notebooklm.exceptions import SourceAddError

        mock_response = MagicMock()
        mock_response.headers = {}  # No x-goog-upload-url

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with pytest.raises(SourceAddError, match="Failed to get upload URL"):
                await sources_api._start_resumable_upload("nb_123", "test.pdf", 1024, "src_456")

    @pytest.mark.asyncio
    async def test_start_resumable_upload_raises_on_http_error(self, sources_api, mock_core):
        """Test that HTTP error raises exception."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=MagicMock()
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await sources_api._start_resumable_upload("nb_123", "test.pdf", 1024, "src_456")


# =============================================================================
# _upload_file_streaming() tests
# =============================================================================


class TestUploadFileStreaming:
    """Tests for streaming file upload."""

    @pytest.mark.asyncio
    async def test_upload_file_streaming_success(self, sources_api, mock_core, tmp_path):
        """Test successful streaming file upload."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"file content here")
        mock_response = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            # Should not raise
            await sources_api._upload_file_streaming(
                "https://upload.example.com/session", test_file
            )

            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_streaming_includes_correct_headers(
        self, sources_api, mock_core, tmp_path
    ):
        """Test that streaming upload includes correct headers."""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"content")
        mock_response = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            await sources_api._upload_file_streaming(
                "https://upload.example.com/session", test_file
            )

            call_kwargs = mock_client.post.call_args[1]
            headers = call_kwargs["headers"]

            assert headers["x-goog-upload-command"] == "upload, finalize"
            assert headers["x-goog-upload-offset"] == "0"
            assert "Cookie" in headers

    @pytest.mark.asyncio
    async def test_upload_file_streaming_uses_generator(self, sources_api, mock_core, tmp_path):
        """Test that file content is streamed via generator."""
        test_file = tmp_path / "test.txt"
        test_content = b"This is my file content"
        test_file.write_bytes(test_content)
        mock_response = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            await sources_api._upload_file_streaming("https://upload.example.com", test_file)

            call_kwargs = mock_client.post.call_args[1]
            # Content should be a generator, not bytes
            content = call_kwargs["content"]
            # Consume the generator to verify it yields the file content
            chunks = [chunk async for chunk in content]
            assert b"".join(chunks) == test_content

    @pytest.mark.asyncio
    async def test_upload_file_streaming_raises_on_http_error(
        self, sources_api, mock_core, tmp_path
    ):
        """Test that HTTP error raises exception."""
        import httpx

        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"content")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Upload Failed", request=MagicMock(), response=MagicMock()
            )
            mock_client_cls.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                await sources_api._upload_file_streaming("https://upload.example.com", test_file)


# =============================================================================
# add_file() tests
# =============================================================================


class TestAddFile:
    """Tests for the add_file() public method."""

    @pytest.mark.asyncio
    async def test_add_file_complete_flow(self, sources_api, mock_core, tmp_path):
        """Test complete file upload flow."""
        # Create a temp file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        # Mock the registration response - 4 levels with string at deepest
        mock_core.rpc_call.return_value = [[[["src_new_123"]]]]

        # Mock HTTP calls
        mock_start_response = MagicMock()
        mock_start_response.headers = {"x-goog-upload-url": "https://upload.example.com/session"}

        mock_upload_response = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = [mock_start_response, mock_upload_response]
            mock_client_cls.return_value = mock_client

            result = await sources_api.add_file("nb_123", str(test_file))

        assert result.id == "src_new_123"
        assert result.title == "test.pdf"
        assert result.kind == "unknown"

    @pytest.mark.asyncio
    async def test_add_file_raises_file_not_found(self, sources_api, mock_core):
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            await sources_api.add_file("nb_123", "/nonexistent/path/file.pdf")

    @pytest.mark.asyncio
    async def test_add_file_with_path_object(self, sources_api, mock_core, tmp_path):
        """Test add_file accepts Path objects."""
        test_file = tmp_path / "doc.txt"
        test_file.write_bytes(b"text content")

        mock_core.rpc_call.return_value = [[[["src_txt"]]]]

        mock_start_response = MagicMock()
        mock_start_response.headers = {"x-goog-upload-url": "https://upload.example.com"}
        mock_upload_response = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = [mock_start_response, mock_upload_response]
            mock_client_cls.return_value = mock_client

            result = await sources_api.add_file("nb_123", test_file)  # Path object

        assert result.id == "src_txt"
        assert result.title == "doc.txt"


# =============================================================================
# add_url() with YouTube detection tests
# =============================================================================


class TestAddUrlWithYouTube:
    """Tests for add_url() with YouTube auto-detection."""

    @pytest.mark.asyncio
    async def test_add_url_detects_youtube_and_uses_youtube_method(self, sources_api, mock_core):
        """Test that YouTube URLs are detected and routed correctly."""
        mock_core.rpc_call.return_value = [[["src_yt"], "YouTube Video"]]

        await sources_api.add_url("nb_123", "https://youtu.be/dQw4w9WgXcQ")

        # Check that the RPC was called with YouTube-specific params
        call_args = mock_core.rpc_call.call_args
        params = call_args[0][1]
        # YouTube params have the URL at position [0][0][7]
        assert params[0][0][7] == ["https://youtu.be/dQw4w9WgXcQ"]

    @pytest.mark.asyncio
    async def test_add_url_uses_regular_method_for_non_youtube(self, sources_api, mock_core):
        """Test that non-YouTube URLs use regular add method."""
        mock_core.rpc_call.return_value = [[["src_url"], "Example Site"]]

        await sources_api.add_url("nb_123", "https://example.com/article")

        # Check that the RPC was called with regular URL params
        call_args = mock_core.rpc_call.call_args
        params = call_args[0][1]
        # Regular URL params have the URL at position [0][0][2] (different from YouTube's [7])
        assert params[0][0][2] == ["https://example.com/article"]


# =============================================================================
# _add_youtube_source() tests
# =============================================================================


class TestAddYoutubeSource:
    """Tests for _add_youtube_source() helper."""

    @pytest.mark.asyncio
    async def test_add_youtube_source_structure(self, sources_api, mock_core):
        """Test YouTube source params structure."""
        mock_core.rpc_call.return_value = [[["src_123"]]]

        await sources_api._add_youtube_source("nb_123", "https://youtu.be/abc123")

        call_args = mock_core.rpc_call.call_args
        params = call_args[0][1]

        # Verify structure: [[None, None, None, ..., [url], None, None, 1]]
        assert params[0][0][7] == ["https://youtu.be/abc123"]
        assert params[0][0][10] == 1  # YouTube indicator
        assert params[1] == "nb_123"


# =============================================================================
# _add_url_source() tests
# =============================================================================


class TestAddUrlSource:
    """Tests for _add_url_source() helper."""

    @pytest.mark.asyncio
    async def test_add_url_source_structure(self, sources_api, mock_core):
        """Test regular URL source params structure."""
        mock_core.rpc_call.return_value = [[["src_123"]]]

        await sources_api._add_url_source("nb_123", "https://example.com/page")

        call_args = mock_core.rpc_call.call_args
        params = call_args[0][1]

        # Verify structure: URL at position 2 (different from YouTube which uses position 7)
        assert params[0][0][2] == ["https://example.com/page"]
        assert params[1] == "nb_123"
        assert params[2] == [2]
        assert params[3] is None
        assert params[4] is None


# =============================================================================
# add_files() tests
# =============================================================================


class TestAddFiles:
    """Tests for add_files() batch registration + parallel upload."""

    def _make_files(self, tmp_path, names):
        """Helper to create temp files and return their paths."""
        paths = []
        for name in names:
            f = tmp_path / name
            f.write_text(f"content of {name}")
            paths.append(str(f))
        return paths

    def _mock_upload(self, sources_api, mock_core):
        """Setup mocks for batch registration + upload steps."""
        mock_start = MagicMock()
        mock_start.headers = {"x-goog-upload-url": "https://upload.example.com/session"}
        mock_upload = MagicMock()

        # Patch the shared upload client
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=lambda *a, **kw: mock_start if "upload/_" in str(kw.get("url", a[0] if a else "")) or "x-goog-upload-command" not in str(kw.get("headers", {})) else mock_upload)
        # Simpler: always return mock_start (has upload URL header) for session start,
        # and mock_upload for data upload
        mock_client.post = AsyncMock(return_value=mock_start)
        sources_api._upload_client = mock_client

    def _batch_response(self, id_name_pairs):
        """Build mock batch registration response matching real API format.

        Real format: [[['id1'], 'filename1', [...]], [['id2'], 'filename2', [...]], ...], None, [...]]
        """
        entries = [[[ pair[0] ], pair[1], [None, None, None, None, 0]] for pair in id_name_pairs]
        return [entries, None, None]

    @pytest.mark.asyncio
    async def test_add_files_basic(self, sources_api, mock_core, tmp_path):
        """3ファイルのバッチ登録 + 並列アップロード"""
        files = self._make_files(tmp_path, ["a.md", "b.md", "c.md"])

        # Batch registration returns 3 source IDs (real API format)
        mock_core.rpc_call.return_value = self._batch_response([
            ("s1", "a.md"), ("s2", "b.md"), ("s3", "c.md")
        ])
        self._mock_upload(sources_api, mock_core)

        results = await sources_api.add_files("nb1", files)
        assert len(results) == 3
        assert [r.id for r in results] == ["s1", "s2", "s3"]
        # Only 1 RPC call for batch registration
        mock_core.rpc_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_files_concurrency_limit(self, sources_api, mock_core, tmp_path):
        """concurrency=2 で最大2並列に制限される"""
        names = [f"file{i}.md" for i in range(10)]
        files = self._make_files(tmp_path, names)
        mock_core.rpc_call.return_value = self._batch_response(
            [(f"s{i}", names[i]) for i in range(10)]
        )

        max_concurrent = 0
        current = 0
        original_start = sources_api._start_resumable_upload

        async def mock_start(nb_id, filename, file_size, source_id):
            nonlocal max_concurrent, current
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.01)
            current -= 1
            return "https://upload.example.com/session"

        mock_upload = MagicMock()
        sources_api._upload_client = AsyncMock()
        sources_api._upload_client.post = AsyncMock(return_value=mock_upload)

        with patch.object(sources_api, "_start_resumable_upload", side_effect=mock_start):
            await sources_api.add_files("nb1", files, concurrency=2)
            assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_add_files_upload_partial_failure(self, sources_api, mock_core, tmp_path):
        """アップロード一部失敗時: 成功分を返す"""
        files = self._make_files(tmp_path, ["good.md", "bad.md", "ok.md"])
        mock_core.rpc_call.return_value = self._batch_response([
            ("s1", "good.md"), ("s2", "bad.md"), ("s3", "ok.md")
        ])

        call_count = 0

        async def mock_start(nb_id, filename, file_size, source_id):
            nonlocal call_count
            call_count += 1
            if "bad" in filename:
                raise ConnectionError(f"Upload failed: {filename}")
            return "https://upload.example.com/session"

        sources_api._upload_client = AsyncMock()
        sources_api._upload_client.post = AsyncMock(return_value=MagicMock())

        with patch.object(sources_api, "_start_resumable_upload", side_effect=mock_start):
            results = await sources_api.add_files("nb1", files)
            assert len(results) == 2  # bad.md以外の2件

    @pytest.mark.asyncio
    async def test_add_files_all_upload_fail(self, sources_api, mock_core, tmp_path):
        """全アップロード失敗時: 例外をraise"""
        files = self._make_files(tmp_path, ["a.md", "b.md"])
        mock_core.rpc_call.return_value = self._batch_response([
            ("s1", "a.md"), ("s2", "b.md")
        ])

        async def mock_start(*args, **kwargs):
            raise ConnectionError("upload failed")

        with patch.object(sources_api, "_start_resumable_upload", side_effect=mock_start):
            with pytest.raises(ConnectionError):
                await sources_api.add_files("nb1", files)

    @pytest.mark.asyncio
    async def test_add_files_empty(self, sources_api):
        """空リスト → 空リスト返却"""
        results = await sources_api.add_files("nb1", [])
        assert results == []

    @pytest.mark.asyncio
    async def test_add_files_with_progress(self, sources_api, mock_core, tmp_path):
        """on_progressコールバックが呼ばれる"""
        files = self._make_files(tmp_path, ["a.md"])
        mock_core.rpc_call.return_value = self._batch_response([("s1", "a.md")])
        self._mock_upload(sources_api, mock_core)

        progress_calls = []
        await sources_api.add_files(
            "nb1",
            files,
            on_progress=lambda f, s: progress_calls.append((f, s)),
        )
        statuses = [s for _, s in progress_calls]
        assert "registering" in statuses
        assert "registered" in statuses
        assert "uploading" in statuses
        assert "done" in statuses

    @pytest.mark.asyncio
    async def test_add_files_file_not_found(self, sources_api, tmp_path):
        """存在しないファイルでFileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            await sources_api.add_files("nb1", ["/nonexistent/file.md"])

    @pytest.mark.asyncio
    async def test_add_files_single_rpc_call(self, sources_api, mock_core, tmp_path):
        """バッチ登録が1回のRPCで行われることを確認"""
        files = self._make_files(tmp_path, ["x.md", "y.md", "z.md"])
        mock_core.rpc_call.return_value = self._batch_response([
            ("s1", "x.md"), ("s2", "y.md"), ("s3", "z.md")
        ])
        self._mock_upload(sources_api, mock_core)

        await sources_api.add_files("nb1", files)

        # Verify batch registration params
        call_args = mock_core.rpc_call.call_args
        params = call_args[0][1]
        # First param should be [[x.md], [y.md], [z.md]]
        assert params[0] == [["x.md"], ["y.md"], ["z.md"]]
        assert params[1] == "nb1"


# =============================================================================
# _get_upload_client() / close() tests
# =============================================================================


class TestUploadClient:
    """Tests for shared upload client lifecycle."""

    @pytest.mark.asyncio
    async def test_get_upload_client_creates_once(self, sources_api):
        """_get_upload_client() は同一インスタンスを返す"""
        client1 = await sources_api._get_upload_client()
        client2 = await sources_api._get_upload_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self, sources_api):
        """close() でクライアントがNoneになる"""
        client = await sources_api._get_upload_client()
        assert sources_api._upload_client is not None
        await sources_api.close()
        assert sources_api._upload_client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self, sources_api):
        """close() はクライアント未生成でもエラーにならない"""
        await sources_api.close()  # Should not raise
