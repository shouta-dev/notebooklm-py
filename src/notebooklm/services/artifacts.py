"""Artifact/Studio content service."""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..api_client import NotebookLMClient


@dataclass
class ArtifactStatus:
    """Status of an artifact generation task."""

    task_id: str
    status: str
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"


class ArtifactService:
    """High-level service for studio content operations."""

    def __init__(self, client: "NotebookLMClient"):
        self._client = client

    async def generate_audio(
        self,
        notebook_id: str,
        instructions: Optional[str] = None,
    ) -> ArtifactStatus:
        result = await self._client.generate_audio(
            notebook_id, instructions=instructions
        )
        if not result or "artifact_id" not in result:
            raise ValueError("Audio generation failed - no artifact_id returned")

        artifact_id: str = result["artifact_id"]
        status: str = result.get("status", "pending")
        return ArtifactStatus(task_id=artifact_id, status=status)

    async def generate_slides(self, notebook_id: str) -> ArtifactStatus:
        result = await self._client.generate_slides(notebook_id)
        if not result or "artifact_id" not in result:
            raise ValueError("Slides generation failed - no artifact_id returned")

        artifact_id: str = result["artifact_id"]
        status: str = result.get("status", "pending")
        return ArtifactStatus(task_id=artifact_id, status=status)

    async def poll_status(self, notebook_id: str, task_id: str) -> ArtifactStatus:
        """Poll the status of a generation task."""
        result = await self._client.poll_studio_status(notebook_id, task_id)

        # Result format: [task_id, status, url, error, metadata]
        # Note: Actual format varies by artifact type, this is a generalized parser
        status = result[1] if len(result) > 1 else "unknown"
        url = result[2] if len(result) > 2 else None
        error = result[3] if len(result) > 3 else None

        return ArtifactStatus(task_id=task_id, status=status, url=url, error=error)

    async def wait_for_completion(
        self,
        notebook_id: str,
        task_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> ArtifactStatus:
        """Wait for a task to complete."""
        start_time = asyncio.get_running_loop().time()

        while True:
            status = await self.poll_status(notebook_id, task_id)

            if status.is_complete or status.is_failed:
                return status

            if asyncio.get_running_loop().time() - start_time > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout}s")

            await asyncio.sleep(poll_interval)
