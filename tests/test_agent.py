"""Tests de l'agent, avec de faux LLM (aucun appel réseau)."""

from app.agent.career_agent import CareerAgent
from app.agent.llm import LLMError

CV = "Java, Spring Boot, Angular, Docker, Flutter, agents LLM"
OFFER = "Compétences requises : Java, Spring Boot, Kafka. PostgreSQL serait un plus."


class FakeLLM:
    """Faux modèle qui renvoie une réponse JSON valide (entourée de texte, comme un vrai LLM)."""

    name = "fake:model"

    def complete(self, system: str, prompt: str) -> str:
        assert "Kafka" in prompt  # l'agent transmet bien les compétences manquantes
        return 'Voici : {"conseils": ["Conseil A", "Conseil B"], "lettre": "Madame, Monsieur..."}'


class BrokenLLM:
    name = "broken:model"

    def complete(self, system: str, prompt: str) -> str:
        raise LLMError("serveur injoignable")


def test_agent_sans_llm_utilise_les_regles():
    report = CareerAgent().run(CV, OFFER, "Stage Java", "Acme")
    assert report.llm_used is None
    assert report.match.score > 0
    assert "Acme" in report.cover_letter
    assert [s.name for s in report.steps] == [
        "Analyse de l'offre",
        "Analyse du CV",
        "Calcul de la compatibilité",
        "Plan de progression",
        "Rédaction des conseils",
    ]
    assert any(item["skill"] == "Kafka" for item in report.learning_plan)


def test_agent_avec_llm():
    report = CareerAgent(llm=FakeLLM()).run(CV, OFFER)
    assert report.llm_used == "fake:model"
    assert report.advice == ["Conseil A", "Conseil B"]
    assert report.cover_letter == "Madame, Monsieur..."


def test_agent_repli_si_le_llm_echoue():
    report = CareerAgent(llm=BrokenLLM()).run(CV, OFFER)
    assert report.llm_used is None
    assert report.steps[-1].status == "fallback"
    assert report.advice  # les conseils par règles sont quand même produits
