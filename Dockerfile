# Image légère Python
FROM python:3.12-slim

WORKDIR /app

# Installation des dépendances en premier (meilleur cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Utilisateur non-root pour la sécurité
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser /app
USER appuser

ENV DATABASE_URL=sqlite:////app/data/careermatch.db
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
