"""Test script to diagnose RAG engine issues"""
import os
from app.rag.engine import RAGEngine
from app.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

print("Environment variables:")
# Print environment variables without showing actual values
for key in [
    "OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY", 
    "QDRANT_COLLECTION", "COHERE_API_KEY"
]:
    print(f"  {key}: {'Present' if os.environ.get(key) else 'MISSING'}")

try:
    print("\nInitializing RAG Engine...")
    rag_engine = RAGEngine()
    print("RAG Engine initialized successfully!")
    
    # Test a simple query
    print("\nTesting query functionality...")
    result = rag_engine.query("Chi è la Croce Rossa?")
    print(f"Query response: {result['answer'][:100]}...")
    
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc() 