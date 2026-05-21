FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv pip install --system -e .

COPY src/ ./src/
COPY data/ ./data/

CMD ["python", "-m", "src.main"]
