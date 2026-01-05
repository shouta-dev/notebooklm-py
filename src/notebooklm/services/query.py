"""Query types and conversation management."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ConversationTurn:
    """Represents a single turn in a conversation."""

    query: str
    answer: str
    turn_number: int


@dataclass
class QueryResult:
    """Result of a notebook query."""

    answer: str
    conversation_id: str
    turn_number: int
    is_follow_up: bool
    raw_response: str = ""
