"""
Semantic search engine for AI marketplace product recommendations.

Uses sentence transformers and FAISS for efficient similarity search.
Includes graceful fallbacks and performance monitoring.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class SemanticSearchResult:
    """Result from semantic search."""
    app_id: str
    similarity_score: float


class SemanticSearchEngine:
    """
    Semantic search engine using sentence transformers and FAISS.

    Features:
    - Lazy initialization to avoid startup delays
    - Graceful fallback if dependencies unavailable
    - Performance timing and metrics
    - Thread-safe operations
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", enabled: bool = True):
        """
        Initialize the semantic search engine.

        Args:
            model_name: Name of the sentence transformer model to use
            enabled: Whether semantic search is enabled
        """
        self.model_name = model_name
        self.enabled = enabled
        self._model = None
        self._index = None
        self._app_ids: List[str] = []
        self._initialized = False
        self._init_error: Optional[str] = None

    def _lazy_init(self) -> bool:
        """
        Lazily initialize the model and FAISS index.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return self._init_error is None

        if not self.enabled:
            self._initialized = True
            self._init_error = "Semantic search disabled"
            return False

        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
            import faiss

            logger.info(f"Initializing semantic search with model: {self.model_name}")
            start_time = time.perf_counter()

            # Load sentence transformer model
            self._model = SentenceTransformer(self.model_name)

            # Get embedding dimension
            self._embedding_dim = self._model.get_sentence_embedding_dimension()

            # Initialize empty FAISS index (will be populated when products added)
            self._index = faiss.IndexFlatIP(self._embedding_dim)  # Inner product for cosine similarity

            init_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"Semantic search initialized in {init_time_ms}ms (dim={self._embedding_dim})")

            self._initialized = True
            self._init_error = None
            return True

        except ImportError as e:
            self._init_error = f"Missing dependencies: {e}"
            logger.warning(f"Semantic search unavailable: {self._init_error}")
            self._initialized = True
            return False

        except Exception as e:
            self._init_error = f"Initialization failed: {e}"
            logger.error(f"Semantic search initialization error: {e}", exc_info=True)
            self._initialized = True
            return False

    def add_products(self, products: List[dict]) -> bool:
        """
        Add products to the semantic search index.

        Args:
            products: List of product dictionaries with 'id', 'name', 'description', 'capabilities'

        Returns:
            True if products were added successfully, False otherwise
        """
        if not self._lazy_init():
            return False

        try:
            import numpy as np
            import faiss

            if not products:
                logger.warning("No products to add to semantic index")
                return False

            start_time = time.perf_counter()

            # Create text representations for each product
            texts = []
            app_ids = []

            for prod in products:
                # Combine name, description, and capabilities into searchable text
                name = prod.get("name", "")
                desc = prod.get("description", "")
                caps = prod.get("capabilities", [])
                caps_text = " ".join(caps) if isinstance(caps, list) else ""

                text = f"{name} {desc} {caps_text}".strip()
                if text:
                    texts.append(text)
                    app_ids.append(prod.get("id", ""))

            if not texts:
                logger.warning("No valid product texts to index")
                return False

            # Generate embeddings
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)

            # Reset and populate index
            self._index.reset()
            self._index.add(embeddings)
            self._app_ids = app_ids

            index_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"Indexed {len(texts)} products in {index_time_ms}ms")

            return True

        except Exception as e:
            logger.error(f"Error adding products to semantic index: {e}", exc_info=True)
            return False

    def search(
        self,
        query: str,
        top_k: int = 10,
        timeout_ms: Optional[int] = None
    ) -> Tuple[List[SemanticSearchResult], int]:
        """
        Search for products semantically similar to the query.

        Args:
            query: Search query text
            top_k: Number of top results to return
            timeout_ms: Optional timeout in milliseconds (not enforced, for monitoring only)

        Returns:
            Tuple of (list of search results, search time in ms)
        """
        start_time = time.perf_counter()

        if not self._lazy_init():
            return [], 0

        try:
            import numpy as np
            import faiss

            if not query or not query.strip():
                logger.warning("Empty search query")
                return [], 0

            if self._index.ntotal == 0:
                logger.warning("Semantic index is empty")
                return [], 0

            # Generate query embedding
            query_embedding = self._model.encode([query], convert_to_numpy=True, show_progress_bar=False)

            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)

            # Search the index
            k = min(top_k, self._index.ntotal)
            scores, indices = self._index.search(query_embedding, k)

            # Build results
            results = []
            for idx, score in zip(indices[0], scores[0]):
                if 0 <= idx < len(self._app_ids):
                    results.append(SemanticSearchResult(
                        app_id=self._app_ids[idx],
                        similarity_score=float(score)
                    ))

            search_time_ms = int((time.perf_counter() - start_time) * 1000)

            if timeout_ms and search_time_ms > timeout_ms:
                logger.warning(f"Semantic search exceeded timeout: {search_time_ms}ms > {timeout_ms}ms")

            logger.debug(f"Semantic search completed in {search_time_ms}ms, found {len(results)} results")

            return results, search_time_ms

        except Exception as e:
            search_time_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Semantic search error: {e}", exc_info=True)
            return [], search_time_ms

    def get_stats(self) -> dict:
        """
        Get statistics about the semantic search engine.

        Returns:
            Dictionary with engine statistics
        """
        stats = {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "error": self._init_error,
            "model_name": self.model_name,
            "total_products": 0,
        }

        if self._initialized and self._init_error is None:
            stats["total_products"] = self._index.ntotal if self._index else 0
            stats["embedding_dim"] = self._embedding_dim if hasattr(self, "_embedding_dim") else None

        return stats

    def is_available(self) -> bool:
        """
        Check if semantic search is available and initialized.

        Returns:
            True if available, False otherwise
        """
        if not self.enabled:
            return False
        self._lazy_init()
        return self._init_error is None
