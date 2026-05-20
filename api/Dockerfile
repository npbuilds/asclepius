# Asclepius API — production container for Fly.io.
# Python 3.11 slim base; installs project via pyproject.toml; runs uvicorn.

FROM python:3.11-slim

WORKDIR /app

# Install dependencies + the project itself in one layer.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
