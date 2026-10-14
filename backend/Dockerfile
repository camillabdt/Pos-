FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY percurso ./percurso
RUN pip install --no-cache-dir ".[firebase]"
ENV PERCURSO_ARMAZENAMENTO=firestore PERCURSO_AUTH=firebase PORT=8080
CMD ["sh", "-c", "uvicorn percurso.main:app --host 0.0.0.0 --port ${PORT}"]
