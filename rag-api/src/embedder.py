import os

import httpx

EMBED_MODEL = os.environ.get("EMBED_MODEL", "intfloat/multilingual-e5-large")
FALLBACK_OLLAMA_URL = os.environ.get("FALLBACK_OLLAMA_URL", "http://ollama:11434")


class Embedder:
    def __init__(self) -> None:
        self._model = None
        self._model_name = ""
        self._vector_size = 1024
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBED_MODEL)
            self._model_name = EMBED_MODEL.split("/")[-1]
            print(f"Loaded model: {EMBED_MODEL}")
        except Exception as e:
            print(f"Failed to load {EMBED_MODEL}: {e}. Falling back to Ollama.")
            self._model_name = "nomic-embed-text (fallback)"
            self._vector_size = 768

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def vector_size(self) -> int:
        return self._vector_size

    def encode(self, text: str) -> list[float]:
        if self._model is not None:
            vec = self._model.encode(text, normalize_embeddings=True)
            return vec.tolist()
        return self._encode_ollama(text)

    def _encode_ollama(self, text: str) -> list[float]:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{FALLBACK_OLLAMA_URL}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
