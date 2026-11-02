# API de SaludCerca (Starlette + uvicorn) para la demo local.
FROM python:3.11-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN useradd --create-home app && chown -R app /srv
USER app
EXPOSE 8000
CMD ["python", "dev_server.py"]
