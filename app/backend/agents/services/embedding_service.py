"""
Embedding Service for KidSpark AI
Generates text embeddings using OpenAI's embedding API for vector similarity search.
"""

from openai import OpenAI
from typing import List
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Embedding model configuration
EMBEDDING_MODEL = "text-embedding-ada-002"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingService:
    """Service for generating text embeddings using OpenAI's API"""

    def __init__(self):
        """Initialize the embedding service with OpenAI client"""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = EMBEDDING_MODEL

    def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: The text to generate an embedding for

        Returns:
            List of floats representing the embedding vector (1536 dimensions)

        Raises:
            ValueError: If text is empty or invalid
            Exception: If OpenAI API call fails
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")

        # Clean and prepare text
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty or whitespace only")

        try:
            logger.info(f"Generating embedding for text: {text[:50]}...")

            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )

            embedding = response.data[0].embedding
            logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to generate embeddings for

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Clean texts
        cleaned_texts = [t.strip() for t in texts if t and t.strip()]

        if not cleaned_texts:
            return []

        try:
            logger.info(f"Generating embeddings for {len(cleaned_texts)} texts...")

            response = self.client.embeddings.create(
                input=cleaned_texts,
                model=self.model
            )

            embeddings = [item.embedding for item in response.data]
            logger.info(f"Successfully generated {len(embeddings)} embeddings")

            return embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise


# Singleton instance for convenience
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create a singleton EmbeddingService instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_embedding(text: str) -> List[float]:
    """
    Convenience function to generate an embedding for text.

    Args:
        text: The text to generate an embedding for

    Returns:
        List of floats representing the embedding vector
    """
    service = get_embedding_service()
    return service.get_embedding(text)
