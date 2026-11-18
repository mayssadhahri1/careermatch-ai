"""Clients pour les modèles de langage (LLM).

Tous les clients respectent la même interface `LLMClient` : l'agent ne sait pas
quel modèle il utilise (principe d'inversion des dépendances / pattern Strategy).
"""

from typing import Protocol

import httpx

from app.core.config import Settings


class LLMError(RuntimeError):
    """Erreur lors de l'appel au modèle (réseau, clé invalide, modèle absent...)."""


class LLMClient(Protocol):
    """Interface commune à tous les fournisseurs de LLM."""

    name: str

    def complete(self, system: str, prompt: str) -> str:
        """Envoie une consigne système + une demande, et retourne la réponse texte."""
        ...


class OllamaClient:
    """Modèle local servi par Ollama (https://ollama.com)."""

    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.name = f"ollama:{model}"
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._timeout = timeout

    def complete(self, system: str, prompt: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "options": {"temperature": 0.3},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            response = httpx.post(self._url, json=payload, timeout=self._timeout)
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"Ollama indisponible : {exc}") from exc


class OpenAICompatibleClient:
    """Toute API compatible OpenAI : OpenAI, Groq, Mistral, OpenRouter, LM Studio..."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float) -> None:
        self.name = f"openai:{model}"
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._model = model
        self._timeout = timeout

    def complete(self, system: str, prompt: str) -> str:
        payload = {
            "model": self._model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            response = httpx.post(self._url, json=payload, headers=self._headers, timeout=self._timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"API LLM indisponible : {exc}") from exc


def build_llm_client(settings: Settings) -> LLMClient | None:
    """Fabrique (Factory) : crée le bon client selon la configuration, ou None si aucun LLM."""
    if settings.llm_provider == "ollama":
        return OllamaClient(settings.ollama_base_url, settings.llm_model, settings.llm_timeout_seconds)
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAICompatibleClient(
            settings.openai_base_url, settings.openai_api_key, settings.llm_model, settings.llm_timeout_seconds
        )
    return None
