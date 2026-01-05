"""Conversation service for chat interactions with notebooks."""

from dataclasses import dataclass
from typing import Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..api_client import NotebookLMClient


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""

    query: str
    answer: str
    turn_number: int


@dataclass
class AskResult:
    """Result of asking the notebook a question."""

    answer: str
    conversation_id: str
    turn_number: int
    is_follow_up: bool
    raw_response: str = ""


class ConversationService:
    """Service for conversational interactions with notebooks."""

    def __init__(self, client: "NotebookLMClient"):
        self._client = client

    async def ask(
        self,
        notebook_id: str,
        question: str,
        source_ids: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
    ) -> AskResult:
        """Ask the notebook a question.

        Args:
            notebook_id: The notebook to query
            question: The question to ask
            source_ids: Limit to specific sources (None = all sources)
            conversation_id: Continue existing conversation (None = new)

        Returns:
            AskResult with answer and conversation metadata
        """
        result = await self._client.ask(
            notebook_id, question, source_ids, conversation_id
        )
        return AskResult(
            answer=result["answer"],
            conversation_id=result["conversation_id"],
            turn_number=result["turn_number"],
            is_follow_up=result["is_follow_up"],
            raw_response=result.get("raw_response", ""),
        )

    async def get_history(self, notebook_id: str, limit: int = 20) -> Any:
        """Get conversation history from server.

        Args:
            notebook_id: The notebook to get history for
            limit: Maximum number of turns to retrieve

        Returns:
            List of conversation IDs (not full content)

        Note:
            TODO: The current GET_CONVERSATION_HISTORY RPC only returns conversation
            IDs, not the actual Q&A content. To get full conversation messages,
            we need to discover the RPC method used by the NotebookLM web UI
            when displaying chat history. Capture network traffic from the web UI
            to find this endpoint.
        """
        return await self._client.get_conversation_history(notebook_id, limit)

    def get_cached_turns(self, conversation_id: str) -> List[ConversationTurn]:
        """Get locally cached conversation turns.

        Args:
            conversation_id: The conversation to retrieve

        Returns:
            List of ConversationTurn from the client's local cache (this session only)
        """
        turns_data = self._client._conversation_cache.get(conversation_id, [])
        return [
            ConversationTurn(
                query=turn["query"],
                answer=turn["answer"],
                turn_number=turn["turn_number"],
            )
            for turn in turns_data
        ]

    def clear_cache(self, conversation_id: Optional[str] = None) -> bool:
        """Clear local conversation cache.

        Args:
            conversation_id: Clear specific conversation (None = clear all)

        Returns:
            True if cleared successfully
        """
        if conversation_id:
            if conversation_id in self._client._conversation_cache:
                del self._client._conversation_cache[conversation_id]
                return True
            return False
        else:
            self._client._conversation_cache.clear()
            return True

    async def delete_history(self, notebook_id: str) -> bool:
        """Delete conversation history from server.

        Args:
            notebook_id: The notebook whose history to delete

        Returns:
            True if deleted successfully

        Raises:
            NotImplementedError: Server-side deletion RPC not yet discovered

        Note:
            TODO: Implement after discovering DELETE_CONVERSATION_HISTORY RPC
            from UI vertical menu > delete history option.
        """
        # TODO: await self._client.delete_conversation_history(notebook_id)
        raise NotImplementedError("Server-side history deletion not yet implemented")
