import os

VALID_STANDARDS = {"ASVS", "AISVS"}
VALID_LEVELS = {1, 2, 3}
SEARCH_TOP_K_MAX = 20
COVERAGE_TOP_K_MAX = 50
RAG_API_URL = os.environ.get("RAG_API_URL", "http://rag-api:8000")
RAG_API_TIMEOUT = int(os.environ.get("RAG_API_TIMEOUT", "30"))
