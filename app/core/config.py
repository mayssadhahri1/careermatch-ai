"""Configuration de l'application, lue depuis les variables d'environnement (ou un fichier .env)."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres globaux. Chaque champ peut être surchargé par une variable d'environnement."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CareerMatch AI"
    # URL de la base de données (SQLite par défaut, PostgreSQL possible en production)
    database_url: str = "sqlite:///./careermatch.db"

    # Fournisseur du modèle de langage :
    #  - "none"   : aucun LLM, l'agent utilise uniquement ses règles (fonctionne hors ligne)
    #  - "ollama" : modèle local via Ollama
    #  - "openai" : toute API compatible OpenAI (OpenAI, Groq, Mistral, LM Studio...)
    llm_provider: Literal["none", "ollama", "openai"] = "none"
    llm_model: str = "llama3.1"
    llm_timeout_seconds: float = 60.0

    ollama_base_url: str = "http://localhost:11434"

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique des paramètres (mise en cache)."""
    return Settings()
