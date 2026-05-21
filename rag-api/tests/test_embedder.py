from unittest.mock import MagicMock, patch

import numpy as np


class TestEmbedder:
    def _make_embedder(self, model_return: list[float] | None = None):
        vec = np.array(model_return or [0.1] * 1024)
        mock_model = MagicMock()
        mock_model.encode.return_value = vec

        mock_st_module = MagicMock()
        mock_st_module.SentenceTransformer.return_value = mock_model

        with patch.dict("sys.modules", {"sentence_transformers": mock_st_module}):
            from src.embedder import Embedder
            embedder = Embedder()

        return embedder, mock_model

    def test_model_name_is_set(self):
        embedder, _ = self._make_embedder()
        assert embedder.model_name == "multilingual-e5-large"

    def test_vector_size_is_1024_for_local(self):
        embedder, _ = self._make_embedder()
        assert embedder.vector_size == 1024

    def test_encode_returns_list_of_floats(self):
        embedder, _ = self._make_embedder()
        result = embedder.encode("test")
        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(v, float) for v in result)

    def test_encode_adds_normalize(self):
        embedder, mock_model = self._make_embedder()
        embedder.encode("hello")
        mock_model.encode.assert_called_once_with("hello", normalize_embeddings=True)

    def test_fallback_to_ollama_on_load_failure(self):
        mock_st_module = MagicMock()
        mock_st_module.SentenceTransformer.side_effect = RuntimeError("no GPU")

        with patch.dict("sys.modules", {"sentence_transformers": mock_st_module}):
            from src.embedder import Embedder
            embedder = Embedder()

        assert embedder.model_name == "nomic-embed-text (fallback)"
        assert embedder.vector_size == 768

    def test_ollama_encode(self):
        mock_st_module = MagicMock()
        mock_st_module.SentenceTransformer.side_effect = RuntimeError("no GPU")

        with patch.dict("sys.modules", {"sentence_transformers": mock_st_module}):
            from src.embedder import Embedder
            embedder = Embedder()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.2] * 768}

        with patch("src.embedder.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = embedder.encode("test")

        assert result == [0.2] * 768
