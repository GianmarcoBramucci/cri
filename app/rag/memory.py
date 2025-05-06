"""Conversation memory management for the CroceRossa Qdrant Cloud application."""

from typing import Dict, List, Tuple, Optional
from collections import deque

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Manages conversation history with a fixed window size.
    
    Stores pairs of user questions and system responses in a sliding window,
    allowing for context-aware follow-up question handling.
    """
    
    def __init__(self, window_size: Optional[int] = None):
        """Initialize the conversation memory.
        
        Args:
            window_size: Maximum number of exchanges to keep in memory.
                         Defaults to MEMORY_WINDOW_SIZE from settings.
        """
        self.window_size = window_size or settings.MEMORY_WINDOW_SIZE
        self.memory: deque[Tuple[str, str]] = deque(maxlen=self.window_size)
        self.transcript: List[Dict[str, str]] = []
        logger.info("Initialized conversation memory", window_size=self.window_size)
        
    def add_exchange(self, question: str, answer: str) -> None:
        """Add a question-answer exchange to the memory.
        
        Args:
            question: The user's question
            answer: The system's response
        """
        self.memory.append((question, answer))
        self.transcript.append({"user": question, "assistant": answer})
        logger.debug("Added exchange to memory", 
                    memory_size=len(self.memory), 
                    transcript_size=len(self.transcript))
        
    def get_history(self) -> List[Tuple[str, str]]:
        """Get the current conversation history.
        
        Returns:
            List of (question, answer) tuples from the conversation
        """
        return list(self.memory)
    
    def get_transcript(self) -> List[Dict[str, str]]:
        """Get the full conversation transcript.
        
        Returns:
            List of dictionaries with user questions and assistant answers
        """
        return self.transcript
    
    def reset(self) -> None:
        """Reset the conversation memory and transcript."""
        self.memory.clear()
        self.transcript = []
        logger.info("Conversation memory reset")

    def is_follow_up_question(self) -> bool:
        """Check if there's any conversation history, indicating a follow-up question.
        
        Returns:
            True if there is conversation history, False otherwise
        """
        return len(self.memory) > 0