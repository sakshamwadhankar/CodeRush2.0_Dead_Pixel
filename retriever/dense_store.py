"""
Dense Vector Storage & Semantic Search using local ChromaDB.
"""

import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings


class ChromaDenseStore:
    """
    Local ChromaDB wrapper for dense vector semantic search.
    Operates completely offline using local embedding functions.
    """

    def __init__(
        self,
        collection_name: str = "aegis_rag_chunks",
        persist_directory: Optional[str] = None,
        embedding_function: Optional[Any] = None
    ):
        """
        Args:
            collection_name: Name of the ChromaDB collection.
            persist_directory: Path to store ChromaDB data. If None, uses in-memory DB.
            embedding_function: Custom ChromaDB embedding function. Default relies on sentence-transformers or default function.
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory

        if self.persist_directory:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
        else:
            self.client = chromadb.Client(Settings(anonymized_telemetry=False))

        # Retrieve or create collection
        if embedding_function:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=embedding_function
            )
        else:
            # Uses Chroma default embedding function (all-MiniLM-L6-v2)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )

    def add_passages(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Adds text passages to ChromaDB collection.

        Args:
            chunks: List of chunk dicts containing 'id', 'text', and optional 'metadata'.
        """
        if not chunks:
            return

        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = []

        for chunk in chunks:
            raw_meta = chunk.get("metadata", {})
            # Ensure metadata values are primitive types (str, int, float, bool)
            clean_meta = {}
            for k, v in raw_meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search for a given query text.

        Args:
            query_text: Input query string.
            top_k: Number of nearest neighbors to retrieve.

        Returns:
            List of result dicts sorted by similarity score with keys:
            ['id', 'text', 'metadata', 'distance', 'dense_score', 'dense_rank']
        """
        if self.collection.count() == 0:
            return []

        actual_k = min(top_k, self.collection.count())
        results = self.collection.query(
            query_texts=[query_text],
            n_results=actual_k
        )

        formatted_results = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            documents = results["documents"][0] if results.get("documents") else [""] * len(ids)
            metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
            distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

            for rank, (chunk_id, doc, meta, dist) in enumerate(zip(ids, documents, metadatas, distances), start=1):
                # Convert distance to similarity score (1 / (1 + distance))
                similarity_score = 1.0 / (1.0 + float(dist)) if dist is not None else 0.0
                formatted_results.append({
                    "id": chunk_id,
                    "text": doc,
                    "metadata": meta,
                    "distance": float(dist) if dist is not None else 0.0,
                    "dense_score": similarity_score,
                    "dense_rank": rank
                })

        return formatted_results

    def clear(self) -> None:
        """Deletes and recreates the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def count(self) -> int:
        """Returns total document count in the collection."""
        return self.collection.count()
