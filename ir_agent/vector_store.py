"""
Vector Store for Nutrition IR Agent
------------------------------------
Manages local ChromaDB vector database and sentence-transformers embeddings
for semantic similarity search over USDA and curated nutrition data.
"""

import os
import json
import pathlib
from typing import List, Dict, Any, Optional

# Enforce PyTorch backend for Transformers & SentenceTransformers
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


from ir_agent.data_processor import load_and_process_dataset

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "nutrition_food_db"


class VectorStore:
    def __init__(self, db_dir: Optional[str] = None, force_reindex: bool = False):
        if db_dir is None:
            base_dir = pathlib.Path(__file__).resolve().parent
            db_dir = str(base_dir / "chroma_db")

        self.db_dir = db_dir
        os.makedirs(self.db_dir, exist_ok=True)

        print(f"[VectorStore] Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)

        print(f"[VectorStore] Initializing ChromaDB at: {self.db_dir}")
        self.client = chromadb.PersistentClient(path=self.db_dir)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        self._ensure_indexed(force=force_reindex)

    def _ensure_indexed(self, force: bool = False):
        """Index dataset into ChromaDB if collection is empty or force is True."""
        count = self.collection.count()
        if not force and count > 0:
            print(f"[VectorStore] Collection '{COLLECTION_NAME}' already indexed with {count} items.")
            return

        print("[VectorStore] Loading and preparing dataset for indexing...")
        foods = load_and_process_dataset()
        if not foods:
            print("[VectorStore] Warning: No food items found to index.")
            return

        total_items = len(foods)

        if count > 0:
            print(f"[VectorStore] Updating ChromaDB collection (current: {count}, target: {total_items}). Re-indexing...")
            try:
                self.client.delete_collection(name=COLLECTION_NAME)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )

        print(f"[VectorStore] Indexing {total_items} food items into ChromaDB...")

        batch_size = 256
        for i in range(0, total_items, batch_size):
            batch = foods[i : i + batch_size]
            ids = [f"food_{i + idx}" for idx in range(len(batch))]
            documents = [item["document_text"] for item in batch]
            
            # Generate dense embeddings
            embeddings = self.model.encode(documents, show_progress_bar=False, normalize_embeddings=True).tolist()

            metadatas = [
                {
                    "name": item["name"],
                    "category": item["category"],
                    "calories": float(item["calories"]),
                    "protein_g": float(item["protein_g"]),
                    "carbs_g": float(item["carbs_g"]),
                    "fat_g": float(item["fat_g"]),
                    "allergens": json.dumps(item["allergens"]),
                    "dietary_flags": json.dumps(item["dietary_flags"]),
                    "source": item["source"]
                }
                for item in batch
            ]

            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            processed_so_far = min(i + batch_size, total_items)
            if processed_so_far % 2560 == 0 or processed_so_far == total_items:
                print(f"[VectorStore] Indexed {processed_so_far} / {total_items} items ({processed_so_far * 100 // total_items}%)...")

        print(f"[VectorStore] Successfully indexed {self.collection.count()} items into ChromaDB.")

    def search(self, query_text: str, n_results: int = 25) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search on query_text.
        Returns a list of matching food records with similarity score and metadata.
        """
        query_embedding = self.model.encode([query_text], normalize_embeddings=True).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, max(1, self.collection.count()))
        )

        matches = []
        if results and "metadatas" in results and results["metadatas"]:
            metas = results["metadatas"][0]
            docs = results["documents"][0] if "documents" in results else []
            distances = results["distances"][0] if "distances" in results else []

            for idx, meta in enumerate(metas):
                allergens = json.loads(meta.get("allergens", "[]"))
                dietary_flags = json.loads(meta.get("dietary_flags", "[]"))
                
                # Cosine distance to similarity (1 - distance)
                distance = distances[idx] if idx < len(distances) else 0.0
                similarity_score = round(1.0 - distance, 4)

                matches.append({
                    "name": meta.get("name"),
                    "category": meta.get("category"),
                    "calories": meta.get("calories", 0.0),
                    "protein_g": meta.get("protein_g", 0.0),
                    "carbs_g": meta.get("carbs_g", 0.0),
                    "fat_g": meta.get("fat_g", 0.0),
                    "allergens": allergens,
                    "dietary_flags": dietary_flags,
                    "source": meta.get("source", "usda_curated_nutrition_db"),
                    "document_text": docs[idx] if idx < len(docs) else "",
                    "score": similarity_score
                })

        return matches

    def count(self) -> int:
        return self.collection.count()


if __name__ == "__main__":
    vs = VectorStore()
    print(f"Vector store initialized with {vs.count()} items.")
    test_query = "high protein vegetarian dinner"
    print(f"\nSearching for: '{test_query}'...")
    results = vs.search(test_query, n_results=5)
    for r in results:
        print(f"- {r['name']} (Calories: {r['calories']}, Protein: {r['protein_g']}g, Score: {r['score']})")
