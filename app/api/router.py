"""API router for the CroceRossa Qdrant Cloud application."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

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


# Dependency to get RAG engine
def get_rag_engine():
    """Dependency to provide the RAG engine instance."""
    try:
        return RAGEngine()
    except Exception as e:
        logger.error("Failed to initialize RAG engine in dependency", error=str(e))
        # Return a non-functional RAG engine that will return error messages
        engine = RAGEngine.__new__(RAGEngine)
        engine.memory = ConversationMemory()
        engine._initialization_failed = True
        return engine


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest, rag_engine: RAGEngine = Depends(get_rag_engine)):
    """Process a user query and return a response.
    
    Args:
        request: The query request containing the user's question
        rag_engine: The RAG engine dependency
        
    Returns:
        The query response with answer and metadata
    """
    logger.info("Received query request", query=request.query, session_id=request.session_id)
    
    try:
        result = rag_engine.query(request.query)
        return QueryResponse(**result)
    
    except Exception as e:
        logger.error("Error processing query", error=str(e), query=request.query)
        raise HTTPException(
            status_code=500,
            detail=f"Si è verificato un errore durante l'elaborazione della richiesta: {str(e)}"
        )


@router.post("/reset", response_model=ResetResponse)
async def reset(request: ResetRequest, rag_engine: RAGEngine = Depends(get_rag_engine)):
    """Reset the conversation memory.
    
    Args:
        request: The reset request
        rag_engine: The RAG engine dependency
        
    Returns:
        Confirmation of reset success
    """
    logger.info("Received reset request", session_id=request.session_id)
    
    try:
        rag_engine.reset_memory()
        return ResetResponse(
            success=True,
            message="Conversazione resettata con successo."
        )
    
    except Exception as e:
        logger.error("Error resetting conversation", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Si è verificato un errore durante il reset della conversazione: {str(e)}"
        )


@router.get("/transcript", response_model=TranscriptResponse)
async def transcript(rag_engine: RAGEngine = Depends(get_rag_engine)):
    """Get the conversation transcript.
    
    Args:
        rag_engine: The RAG engine dependency
        
    Returns:
        The full conversation transcript
    """
    logger.info("Received transcript request")
    
    try:
        transcript_data = rag_engine.get_transcript()
        return TranscriptResponse(transcript=transcript_data)
    
    except Exception as e:
        logger.error("Error retrieving transcript", error=str(e))
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