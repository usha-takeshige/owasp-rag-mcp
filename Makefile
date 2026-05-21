.PHONY: up down ingest logs test test-integration lint

up:
	docker compose up -d

down:
	docker compose down

ingest:
	docker compose run --rm ingest

logs:
	docker compose logs -f

test:
	cd mcp-server && uv run pytest tests/ -v
	cd rag-api && uv run pytest tests/ -v
	cd ingest && uv run pytest tests/ -v

test-integration:
	cd tests && uv run pytest integration/ -v

lint:
	cd mcp-server && uv run ruff check src/
	cd rag-api && uv run ruff check src/
	cd ingest && uv run ruff check src/
