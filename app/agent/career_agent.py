"""Agent d'analyse de candidature.

L'agent enchaîne plusieurs étapes (« outils ») et garde une trace de chacune,
pour que l'utilisateur voie comment le résultat a été construit :

    1. analyser l'offre      -> compétences obligatoires / souhaitées
    2. analyser le CV        -> compétences du candidat
    3. calculer le matching  -> score pondéré, points forts, manques
    4. planifier             -> plan de progression pour les compétences manquantes
    5. rédiger               -> conseils + paragraphe de lettre (LLM si disponible, sinon règles)
"""

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.agent.llm import LLMClient, LLMError
from app.services.matcher import MatchResult, compute_match, split_offer_requirements
from app.services.skills import Skill, extract_skills, extract_years_of_experience

# Ressources conseillées par catégorie pour combler une compétence manquante
LEARNING_TIPS: dict[str, str] = {
    "Langages": "suivre un cours officiel puis résoudre 10 exercices (ex. Exercism)",
    "Backend": "construire une petite API CRUD avec tests et la publier sur GitHub",
    "Frontend": "refaire l'interface d'un de tes projets avec cette technologie",
    "Mobile": "créer une mini-application de 3 écrans connectée à une API",
    "Bases de données": "modéliser une base pour un de tes projets et écrire 10 requêtes",
    "Architecture": "ajouter cette brique à un projet existant et expliquer le choix dans le README",
    "DevOps": "conteneuriser un projet et ajouter un pipeline qui lance les tests",
    "Cloud": "déployer un projet sur l'offre gratuite du fournisseur",
    "IA & Data": "réaliser un notebook ou un petit agent sur un cas concret et le documenter",
    "Méthodes": "appliquer la méthode sur ton prochain projet et le montrer dans le README",
}

SYSTEM_PROMPT = (
    "Tu es un conseiller carrière pour des élèves-ingénieurs en informatique. "
    "Tu réponds en français simple et professionnel. "
    "Tu n'inventes jamais d'expérience : tu t'appuies uniquement sur les compétences fournies. "
    "Tu réponds uniquement avec un objet JSON valide."
)


@dataclass
class AgentStep:
    """Une étape exécutée par l'agent (affichée dans l'interface)."""

    name: str
    detail: str
    duration_ms: int
    status: str = "ok"


@dataclass
class AgentReport:
    """Rapport final produit par l'agent."""

    match: MatchResult
    cv_years: int | None
    learning_plan: list[dict[str, str]]
    advice: list[str]
    cover_letter: str
    llm_used: str | None
    steps: list[AgentStep] = field(default_factory=list)


class CareerAgent:
    """Agent qui orchestre les étapes d'analyse d'une candidature."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    def run(self, cv_text: str, offer_text: str, job_title: str = "", company: str = "") -> AgentReport:
        steps: list[AgentStep] = []

        requirements = self._timed(
            steps,
            "Analyse de l'offre",
            lambda: split_offer_requirements(offer_text),
            lambda r: f"{len(r.required)} compétence(s) exigée(s), {len(r.optional)} souhaitée(s)",
        )
        cv_skills = self._timed(
            steps,
            "Analyse du CV",
            lambda: extract_skills(cv_text),
            lambda s: f"{len(s)} compétence(s) détectée(s)",
        )
        match = self._timed(
            steps,
            "Calcul de la compatibilité",
            lambda: compute_match(cv_text, offer_text),
            lambda m: f"Score {m.score}/100 ({m.level})",
        )
        plan = self._timed(
            steps,
            "Plan de progression",
            lambda: self._learning_plan(match.missing_required + match.missing_optional),
            lambda p: f"{len(p)} action(s) proposée(s)",
        )

        # Étape de rédaction : LLM si configuré, sinon règles (et repli automatique en cas d'erreur)
        start = time.perf_counter()
        llm_used: str | None = None
        advice, letter = self._rule_based_writing(match, cv_skills, job_title, company)
        detail = "Rédaction par règles (aucun LLM configuré)"
        status = "ok"
        if self._llm is not None:
            try:
                advice, letter = self._llm_writing(match, cv_skills, requirements.all, job_title, company)
                llm_used = self._llm.name
                detail = f"Rédaction par le modèle {self._llm.name}"
            except LLMError as exc:
                detail = f"LLM indisponible, repli sur les règles ({exc})"
                status = "fallback"
        steps.append(AgentStep("Rédaction des conseils", detail, self._ms(start), status))

        return AgentReport(
            match=match,
            cv_years=extract_years_of_experience(cv_text),
            learning_plan=plan,
            advice=advice,
            cover_letter=letter,
            llm_used=llm_used,
            steps=steps,
        )

    # ---------- Outils internes ----------

    @staticmethod
    def _learning_plan(missing: list[Skill]) -> list[dict[str, str]]:
        """Une action concrète par compétence manquante (6 au maximum)."""
        default_tip = "pratiquer sur un petit projet"
        return [
            {"skill": s.name, "category": s.category, "action": LEARNING_TIPS.get(s.category, default_tip)}
            for s in missing[:6]
        ]

    @staticmethod
    def _rule_based_writing(
        match: MatchResult, cv_skills: list[Skill], job_title: str, company: str
    ) -> tuple[list[str], str]:
        """Conseils et lettre générés sans IA, à partir du résultat du matching."""
        advice: list[str] = []
        strong = [s.name for s in match.matched_required][:4]
        missing = [s.name for s in match.missing_required][:3]

        if strong:
            advice.append(f"Mets en avant dès le début du CV : {', '.join(strong)}.")
        if missing:
            advice.append(
                f"Compétences exigées absentes du CV : {', '.join(missing)}. "
                "Si tu les as déjà utilisées, ajoute-les avec un projet concret ; sinon, prépare-toi à en parler."
            )
        if match.extra_skills:
            extra = ", ".join(s.name for s in match.extra_skills[:3])
            advice.append(f"Tes compétences en plus ({extra}) peuvent te distinguer : cite-les dans la lettre.")
        if match.score < 60:
            advice.append("Adapte le titre de ton CV et ton résumé au vocabulaire exact de l'offre.")
        if not advice:
            advice.append("Ton profil correspond bien : personnalise la lettre avec un projet lié à l'entreprise.")

        poste = job_title or "ce stage"
        entreprise = f" chez {company}" if company else ""
        skills_txt = ", ".join(strong or [s.name for s in cv_skills][:3]) or "le développement logiciel"
        letter = (
            f"Votre offre pour {poste}{entreprise} a retenu toute mon attention. "
            f"À travers mes projets et mes stages, j'ai développé des compétences en {skills_txt}, "
            "que je souhaite mettre au service de votre équipe. "
            "La rigueur et la curiosité guident mon travail : j'apprends vite et j'aime livrer "
            "des solutions propres, testées et documentées."
        )
        return advice, letter

    def _llm_writing(
        self, match: MatchResult, cv_skills: list[Skill], asked: list[Skill], job_title: str, company: str
    ) -> tuple[list[str], str]:
        """Demande au LLM des conseils personnalisés et un paragraphe de lettre de motivation."""
        assert self._llm is not None
        prompt = (
            f"Poste : {job_title or 'stage en informatique'}\n"
            f"Entreprise : {company or 'non précisée'}\n"
            f"Compétences demandées : {', '.join(s.name for s in asked) or 'non précisées'}\n"
            f"Compétences du candidat : {', '.join(s.name for s in cv_skills) or 'non précisées'}\n"
            f"Compétences exigées manquantes : {', '.join(s.name for s in match.missing_required) or 'aucune'}\n"
            f"Score de compatibilité : {match.score}/100\n\n"
            'Réponds avec ce JSON : {"conseils": ["3 conseils courts et concrets"], '
            '"lettre": "un paragraphe de lettre de motivation de 4 phrases maximum"}'
        )
        raw = self._llm.complete(SYSTEM_PROMPT, prompt)
        data = self._parse_json(raw)
        advice = [str(a).strip() for a in data.get("conseils", []) if str(a).strip()][:5]
        letter = str(data.get("lettre", "")).strip()
        if not advice or not letter:
            raise LLMError("réponse du modèle incomplète")
        return advice, letter

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Extrait le premier objet JSON de la réponse (les modèles ajoutent parfois du texte autour)."""
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise LLMError("aucun JSON dans la réponse du modèle")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError("JSON invalide renvoyé par le modèle") from exc

    # ---------- Utilitaires ----------

    @staticmethod
    def _ms(start: float) -> int:
        return round((time.perf_counter() - start) * 1000)

    def _timed(self, steps: list[AgentStep], name: str, func: Callable[[], Any], describe: Callable[[Any], str]) -> Any:
        """Exécute une étape, mesure sa durée et l'ajoute à la trace."""
        start = time.perf_counter()
        result = func()
        steps.append(AgentStep(name, describe(result), self._ms(start)))
        return result
