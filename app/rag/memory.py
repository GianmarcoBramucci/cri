"""Conversation memory management for the CroceRossa Qdrant Cloud application."""

import os
import sys
from typing import Dict, List, Tuple, Optional
from collections import deque

# Add project root to Python path when running this file directly
if __name__ == "__main__":
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    sys.path.insert(0, PROJECT_ROOT)
    print(f"Added project root to Python path: {PROJECT_ROOT}")

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

    def load_history(self, history_items: List[Dict[str, str]]) -> None:
        """Load conversation history from a list of message dictionaries."""
        logger.info(f"Loading history with {len(history_items)} items")
    
        self.memory.clear()
        self.transcript = []

    # Costruisci coppie di messaggi (user, assistant)
        for i in range(0, len(history_items) - 1, 2):
            if i + 1 < len(history_items):
                user_msg = history_items[i]
                assistant_msg = history_items[i + 1]
                
                if user_msg.get("type") == "user" and assistant_msg.get("type") == "assistant":
                    user_content = user_msg.get("content", "")
                    assistant_content = assistant_msg.get("content", "")
                    
                    if user_content and assistant_content:
                        self.memory.append((user_content, assistant_content))
                        self.transcript.append({"user": user_content, "assistant": assistant_content})
                        logger.debug(f"Added exchange: Q={user_content[:20]}..., A={assistant_content[:20]}...")
        
        logger.info(f"Loaded {len(self.memory)} exchanges into memory")

    def is_follow_up_question(self) -> bool:
        """Check if there's any conversation history, indicating a follow-up question.
        
        Returns:
            True if there is conversation history, False otherwise
        """
        return len(self.memory) > 0