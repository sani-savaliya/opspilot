FROM python:3.13-slim

WORKDIR /app

# Install the package and its dependencies.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

# Runtime data dirs (mounted/ephemeral).
RUN mkdir -p data uploads

EXPOSE 8050

# Deploy-anywhere entrypoint. Cloud hosts inject $PORT; default to 8050 locally.
CMD ["sh", "-c", "uvicorn opspilot.app:app --host 0.0.0.0 --port ${PORT:-8050}"]
