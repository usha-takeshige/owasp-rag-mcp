import os

import httpx

from src.chunker import Chunk
from src.upserter import EmbeddedChunk

BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "32"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "intfloat/multilingual-e5-large")
FALLBACK_OLLAMA_URL = os.environ.get("FALLBACK_OLLAMA_URL", "http://ollama:11434")


class Embedder:
    def __init__(self) -> None:
        self._use_local = True
        self._model = None
        self._vector_size = 1024
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBED_MODEL)
            print(f"Loaded model: {EMBED_MODEL}")
        except Exception as e:
            print(f"Failed to load {EMBED_MODEL}: {e}. Falling back to Ollama.")
            self._use_local = False
            self._vector_size = 768

    @property
    def vector_size(self) -> int:
        return self._vector_size

    def _encode_local(self, texts: list[str]) -> list[list[float]]:
        assert self._model is not None
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def _encode_ollama(self, texts: list[str]) -> list[list[float]]:
        results = []
        with httpx.Client(timeout=60) as client:
            for text in texts:
                resp = client.post(
                    f"{FALLBACK_OLLAMA_URL}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text},
                )
                resp.raise_for_status()
                results.append(resp.json()["embedding"])
        return results

    def embed(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        embedded = []
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            texts = [c.embedding_text for c in batch]
            if self._use_local:
                vectors = self._encode_local(texts)
            else:
                vectors = self._encode_ollama(texts)
            for c, vector in zip(batch, vectors):
                embedded.append(EmbeddedChunk(
                    point_id=c.point_id,
                    vector=vector,
                    payload=c.payload,
                ))
        return embedded
