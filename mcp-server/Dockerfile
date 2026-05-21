FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv pip install --system -e .

COPY src/ ./src/

EXPOSE 8080
CMD ["python", "-m", "src.server"]
