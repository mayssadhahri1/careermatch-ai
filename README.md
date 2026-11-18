# 🎯 CareerMatch AI — Agent IA d'analyse de candidature

> Un agent qui compare un **CV** à une **offre de stage** : score de compatibilité, compétences manquantes, plan de progression et paragraphe de lettre de motivation.
> Il fonctionne **sans IA** (règles déterministes) et devient plus fin avec un **LLM** local (Ollama) ou distant (API compatible OpenAI).

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2-D71F00?logo=sqlalchemy&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI-7c3aed)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/licence-MIT-green)

---

## ✨ Fonctionnalités

- 🧠 **Agent en 5 étapes** avec trace visible : analyse de l'offre → analyse du CV → calcul du score → plan de progression → rédaction
- 📊 **Score pondéré sur 100** : une compétence *exigée* compte plus qu'une compétence *souhaitée* (« un plus », « apprécié »…)
- 🔍 **Extraction de près de 70 compétences** (langages, backend, frontend, mobile, DevOps, IA…) avec synonymes (`Node.js`, `CI/CD`, `C++`, `.NET`…)
- 🗺️ **Plan de progression** : une action concrète pour chaque compétence manquante
- ✍️ **Conseils + paragraphe de lettre de motivation**, rédigés par le LLM s'il est configuré
- 🛟 **Repli automatique** : si le LLM ne répond pas, l'agent continue avec ses règles
- 🗂️ **Historique** des analyses enregistré en base (SQLite par défaut)
- 🖥️ **Interface web** responsive + **documentation Swagger** de l'API

## 🏗️ Architecture

```
                 ┌──────────────────────────┐
  Navigateur ───►│  FastAPI  (app/main.py)  │
                 └────────────┬─────────────┘
                              │  /api/analyses
                 ┌────────────▼─────────────┐
                 │   CareerAgent (agent)    │──► LLMClient (Strategy)
                 │  1. analyse offre        │      ├── OllamaClient
                 │  2. analyse CV           │      ├── OpenAICompatibleClient
                 │  3. matching / score     │      └── aucun → règles
                 │  4. plan de progression  │
                 │  5. rédaction            │
                 └────────────┬─────────────┘
                              │
                 ┌────────────▼─────────────┐
                 │ SQLAlchemy → SQLite / PG │
                 └──────────────────────────┘
```

```
app/
├── main.py              # Application FastAPI + interface web
├── core/config.py       # Configuration par variables d'environnement
├── api/                 # Routes REST + schémas Pydantic (validation)
├── agent/
│   ├── career_agent.py  # Orchestration des étapes de l'agent
│   └── llm.py           # Clients LLM interchangeables (Factory + Strategy)
├── services/
│   ├── skills.py        # Catalogue et extraction des compétences
│   └── matcher.py       # Exigences vs atouts, score pondéré, couverture
├── db/database.py       # Modèle ORM et session
└── static/              # Interface web (HTML, CSS, JS)
tests/                   # 20 tests pytest (unitaires + API)
```

**Choix techniques**
- **Pattern Strategy** pour les LLM : l'agent dépend d'une interface, pas d'un fournisseur.
- **Base déterministe d'abord** : le score ne dépend jamais du LLM, il est donc reproductible et testable.
- **Le LLM ne fait que rédiger**, à partir des compétences détectées : on limite les risques d'invention.

## 🚀 Lancer le projet

### En local

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate   |   Linux / macOS : source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # optionnel
uvicorn app.main:app --reload
```

- Interface : http://localhost:8000
- Swagger : http://localhost:8000/docs

### Avec Docker

```bash
docker compose up --build

# Avec un modèle local (Ollama)
LLM_PROVIDER=ollama docker compose --profile llm up --build
docker compose exec ollama ollama pull llama3.1
```

### Activer un LLM

| Variable | Exemple | Rôle |
|---|---|---|
| `LLM_PROVIDER` | `none` · `ollama` · `openai` | Fournisseur du modèle |
| `LLM_MODEL` | `llama3.1`, `gpt-4o-mini` | Nom du modèle |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Serveur Ollama |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Toute API compatible OpenAI (Groq, Mistral…) |
| `OPENAI_API_KEY` | `sk-...` | Clé de l'API |

## 🔌 API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | État de l'API et fournisseur LLM |
| `POST` | `/api/analyses` | Lance l'agent sur un CV et une offre |
| `GET` | `/api/analyses` | Historique des analyses |
| `GET` | `/api/analyses/{id}` | Détail d'une analyse |
| `DELETE` | `/api/analyses/{id}` | Supprime une analyse |

Exemple :

```bash
curl -X POST http://localhost:8000/api/analyses \
  -H "Content-Type: application/json" \
  -d '{"job_title":"Stage PFE","company":"Acme",
       "offer_text":"Compétences requises : Java, Spring Boot, Docker. Kubernetes serait un plus.",
       "cv_text":"Élève-ingénieure : Java, Spring Boot, Angular, Docker et Git."}'
```

## ✅ Qualité

```bash
pytest -q        # 20 tests
ruff check .     # analyse statique
```

L'intégration continue (GitHub Actions) lance le linter, les tests et la construction de l'image Docker à chaque push.

## 🛣️ Pistes d'amélioration

- Import direct d'un CV en PDF
- Recherche sémantique des compétences (embeddings) en plus des règles
- Comparaison d'un CV avec plusieurs offres à la fois

---

👩‍💻 **Mayssa Dhahri** — Élève-ingénieure en Génie Logiciel · [LinkedIn](https://www.linkedin.com/in/mayssa-dhahri-38b1373bb/) · [GitHub](https://github.com/mayssadhahri1)
