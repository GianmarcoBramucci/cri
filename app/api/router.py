"""API router for the CroceRossa Qdrant Cloud application."""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, Optional

from app.api.models import (
    QueryRequest,
    QueryResponse,
    ResetRequest,
    ResetResponse,
    TranscriptResponse,
    ContactResponse,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.rag.engine import RAGEngine
from app.rag.memory import ConversationMemory

logger = get_logger(__name__)

router = APIRouter()

# Global store for session-specific memories
session_memories: Dict[str, ConversationMemory] = {}

def get_session_memory(session_id: Optional[str] = None) -> ConversationMemory:
    """Dependency to get or create session-specific conversation memory."""
    # If no session_id is provided (e.g. for a new session from a client that doesn't send one initially),
    # we could generate one, but for now, we rely on client sending it.
    # For /query, session_id comes from QueryRequest. For /reset and /transcript, it comes from their respective requests.
    if not session_id:
        # This case should ideally be handled by the client always sending a session_id.
        # If RAGEngine is used without a session_id, it might default to a non-persistent memory.
        # For simplicity in this refactor, we'll assume session_id is usually present when needed.
        logger.warning("Accessing memory without a session_id. A default, non-persistent memory might be used or created.")
        # Fallback to a new, temporary memory if no ID. This won't be persisted in session_memories.
        return ConversationMemory()

    if session_id not in session_memories:
        logger.info(f"Creating new conversation memory for session_id: {session_id}")
        session_memories[session_id] = ConversationMemory()
    return session_memories[session_id]

# Dependency to get RAG engine, now aware of session-specific memory
def get_rag_engine(session_memory: ConversationMemory = Depends(get_session_memory)) -> RAGEngine:
    """Dependency to provide the RAG engine instance, initialized with session-specific memory."""
    try:
        # Pass the session-specific memory to the RAGEngine
        engine = RAGEngine(memory=session_memory)
        # Check for the internal failure flag set during RAGEngine init
        if hasattr(engine, '_initialization_failed') and engine._initialization_failed:
            logger.error("RAGEngine initialization failed (detected in get_rag_engine via flag)")
            # We can't raise HTTPException here directly as it's a dependency setup
            # The endpoint using this engine should handle the failure flag if needed.
        return engine
    except Exception as e:
        logger.error("Failed to initialize RAG engine in dependency", error=str(e))
        # To allow the app to start and report errors, return a minimally functional engine
        # The RAGEngine's own __init__ should set a failure flag if critical parts fail.
        # This part is tricky; ideally, RAGEngine manages its own partial failure state.
        # For now, we assume RAGEngine's __init__ handles its state properly.
        # Fallback RAGEngine creation for extreme cases:
        engine = RAGEngine.__new__(RAGEngine) # Create instance without calling __init__
        setattr(engine, '_initialization_failed', True) # Manually set failure flag
        setattr(engine, 'memory', session_memory) # Assign the session memory
        logger.warning("Returning a minimally functional RAGEngine due to init error.")
        return engine


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, rag_engine: RAGEngine = Depends(get_rag_engine)):
    """Process a user query and return a response."""
    logger.info("Received query request", query=request.query, session_id=request.session_id, history_len=len(request.conversation_history or []))

    # Ensure the RAG engine uses the correct session memory and loads client history
    # The get_rag_engine dependency should now provide an engine with the right memory object
    # if session_id was correctly passed to get_session_memory implicitly by FastAPI's DI
    # However, get_session_memory needs the session_id. Let's adjust get_rag_engine or how session_id is passed.

    # Simplification: The endpoint is responsible for ensuring its session_memory is used.
    # We need to get session_memory based on request.session_id explicitly here.
    current_session_memory = get_session_memory(request.session_id)
    
    # Load client history into this session's memory
    # The client sends the full history including the current user query as the last item if it was just added.
    # The load_history method is designed to build pairs.
    # The conversationHistory from client also contains the *current* query at the end.
    # We should load history *before* the current query is processed as new by RAGEngine.
    if request.conversation_history:
        # The client sends [{type:user, content:q1}, {type:assistant, content:a1}, {type:user, content:current_q_pending_ans}]
        # load_history will pair up q1/a1. current_q_pending_ans will be a trailing user message.
        current_session_memory.load_history(request.conversation_history)
    
    # Initialize RAGEngine with this specific, potentially rehydrated memory
    # This is a bit redundant if get_rag_engine is already supposed to do this.
    # Let's ensure get_rag_engine gets session_id to pick the right memory for RAGEngine init.
    # To do this, `get_session_memory` needs to be called with `request.session_id`
    # This means `get_rag_engine` also needs access to `request.session_id` or the `QueryRequest` object.

    # Revised dependency structure for get_rag_engine:
    # Change get_rag_engine to accept session_id directly or make get_session_memory use request.session_id.
    # For now, we'll re-initialize the engine's memory reference for clarity, assuming RAGEngine can accept it.
    # This requires RAGEngine.__init__ to accept a memory argument.
    rag_engine.memory = current_session_memory # Ensure RAGEngine uses the rehydrated memory
    
    # The RAGEngine's _initialization_failed flag should be checked.
    if hasattr(rag_engine, '_initialization_failed') and rag_engine._initialization_failed:
        logger.error("RAGEngine initialization failed, cannot process query.")
        raise HTTPException(
            status_code=500,
            detail="Errore interno del server: impossibile inizializzare il motore RAG."
        )

    try:
        # The RAGEngine.query method will use its self.memory, which we've now set.
        # It does not need session_id or history passed directly if its self.memory is correct.
        result = rag_engine.query(request.query) # RAGEngine.query should use its self.memory
        return QueryResponse(**result)
    
    except Exception as e:
        logger.error("Error processing query", error=str(e), query=request.query)
        # traceback.print_exc() # For more detailed server logs
        raise HTTPException(
            status_code=500,
            detail=f"Si è verificato un errore durante l'elaborazione della richiesta: {str(e)}"
        )


@router.post("/reset", response_model=ResetResponse)
async def reset(request: ResetRequest): # Removed rag_engine dependency for now
    """Reset the conversation memory for a given session_id."""
    logger.info("Received reset request", session_id=request.session_id)
    
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required for reset")

    session_memory_instance = get_session_memory(request.session_id)
    try:
        session_memory_instance.reset()
        # Also remove from global store if you want a full reset beyond ConversationMemory's clear
        if request.session_id in session_memories:
            del session_memories[request.session_id]
            logger.info(f"Cleared and removed memory for session_id: {request.session_id} from global store.")
        
        return ResetResponse(
            success=True,
            message="Conversazione resettata con successo."
        )
    
    except Exception as e:
        logger.error("Error resetting conversation", error=str(e), session_id=request.session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Si è verificato un errore durante il reset della conversazione: {str(e)}"
        )


@router.get("/transcript", response_model=TranscriptResponse)
async def transcript(session_id: Optional[str] = Body(None, embed=True)): # Get session_id from request body or query param
    """Get the conversation transcript for a given session_id."""
    logger.info("Received transcript request", session_id=session_id)

    if not session_id:
        # If client doesn't send session_id, we can't provide a specific transcript.
        # Return empty or error.
        logger.warning("Transcript requested without session_id.")
        return TranscriptResponse(transcript=[]) # Or raise HTTPException

    session_memory_instance = get_session_memory(session_id)
    try:
        transcript_data = session_memory_instance.get_transcript()
        return TranscriptResponse(transcript=transcript_data)
    
    except Exception as e:
        logger.error("Error retrieving transcript", error=str(e), session_id=session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Si è verificato un errore durante il recupero della trascrizione: {str(e)}"
        )


@router.get("/contact", response_model=ContactResponse)
async def contact():
    """Get the CRI contact information.
    
    Returns:
        The CRI contact information
    """
    logger.info("Received contact information request")
    
    try:
        return ContactResponse(
            name="Croce Rossa Italiana",
            website=settings.CRI_WEBSITE,
            email=settings.CRI_CONTACT_EMAIL,
            phone=settings.CRI_CONTACT_PHONE,
            headquarters="Via Bernardino Ramazzini, 31, 00151 Roma RM",
            description=(
                "La Croce Rossa Italiana, fondata il 15 giugno 1864, è un'associazione "
                "di soccorso volontario, parte integrante del Movimento Internazionale "
                "della Croce Rossa e della Mezzaluna Rossa. Opera in Italia nei campi "
                "sanitario, sociale e umanitario, secondo i sette Principi Fondamentali "
                "del Movimento: Umanità, Imparzialità, Neutralità, Indipendenza, "
                "Volontariato, Unità e Universalità."
            )
        )
    
    except Exception as e:
        logger.error("Error retrieving contact information", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Si è verificato un errore durante il recupero delle informazioni di contatto: {str(e)}"
        )