"""Source management service."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..api_client import NotebookLMClient


@dataclass
class Source:
    """Represents a NotebookLM source."""

    id: str
    title: Optional[str] = None
    url: Optional[str] = None
    source_type: str = "text"

    @classmethod
    def from_api_response(
        cls, data: list[Any], notebook_id: Optional[str] = None
    ) -> "Source":
        # Handle nested response: [[[[id], title, metadata, ...]]]
        if data and isinstance(data[0], list) and len(data[0]) > 0:
            if isinstance(data[0][0], list) and len(data[0][0]) > 0:
                entry = data[0][0]
                source_id = entry[0][0] if isinstance(entry[0], list) else entry[0]
                title = entry[1] if len(entry) > 1 else None
                url = None
                if len(entry) > 2 and isinstance(entry[2], list) and len(entry[2]) > 7:
                    url_list = entry[2][7]
                    if isinstance(url_list, list) and len(url_list) > 0:
                        url = url_list[0]
                return cls(
                    id=str(source_id),
                    title=title,
                    url=url,
                    source_type="url" if url else "text",
                )

        source_id = data[0] if len(data) > 0 else ""
        title = data[1] if len(data) > 1 else None
        return cls(id=str(source_id), title=title, source_type="text")


class SourceService:
    """High-level service for source operations."""

    def __init__(self, client: "NotebookLMClient"):
        self._client = client

    async def add_url(self, notebook_id: str, url: str) -> Source:
        result = await self._client.add_source_url(notebook_id, url)
        return Source.from_api_response(result)

    async def add_text(self, notebook_id: str, title: str, content: str) -> Source:
        result = await self._client.add_source_text(notebook_id, title, content)
        return Source.from_api_response(result)

    async def add_file(
        self,
        notebook_id: str,
        file_path: Union[str, Path],
        mime_type: Optional[str] = None,
    ) -> Source:
        """Add a file source to a notebook.

        Args:
            notebook_id: The notebook ID.
            file_path: Path to the file to upload.
            mime_type: MIME type. Auto-detected if None.

        Returns:
            Source object with the uploaded file's source ID.
        """
        from pathlib import Path

        result = await self._client.add_source_file(
            notebook_id, Path(file_path), mime_type
        )
        return Source.from_api_response(result)

    async def get(self, notebook_id: str, source_id: str) -> Source:
        """Get details of a specific source."""
        result = await self._client.get_source(notebook_id, source_id)
        return Source.from_api_response(result)

    async def delete(self, notebook_id: str, source_id: str) -> bool:
        """Delete a source from a notebook."""
        result = await self._client.delete_source(notebook_id, source_id)
        return bool(result[0]) if result else False
