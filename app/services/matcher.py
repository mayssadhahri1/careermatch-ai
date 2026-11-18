"""Calcul du score de compatibilité entre un CV et une offre de stage."""

import re
from dataclasses import dataclass, field

from app.services.skills import Skill, extract_skills, normalize

# Mots qui indiquent qu'une compétence est un "plus" et non une exigence
OPTIONAL_MARKERS = (
    "souhaité",
    "souhaitée",
    "souhaitable",
    "un plus",
    "un atout",
    "atout",
    "apprécié",
    "appréciée",
    "bonus",
    "idéalement",
    "serait un plus",
    "nice to have",
    "is a plus",
    "preferred",
    "optionnel",
    "optional",
)

# Poids dans le score : une exigence compte plus qu'un "plus"
REQUIRED_WEIGHT = 1.0
OPTIONAL_WEIGHT = 0.4


@dataclass
class OfferRequirements:
    """Compétences demandées par l'offre, séparées en obligatoires et souhaitées."""

    required: list[Skill] = field(default_factory=list)
    optional: list[Skill] = field(default_factory=list)

    @property
    def all(self) -> list[Skill]:
        return self.required + self.optional


@dataclass
class MatchResult:
    """Résultat détaillé de la comparaison CV / offre."""

    score: int
    level: str
    matched_required: list[Skill]
    missing_required: list[Skill]
    matched_optional: list[Skill]
    missing_optional: list[Skill]
    extra_skills: list[Skill]
    category_coverage: dict[str, int]


def split_offer_requirements(offer_text: str) -> OfferRequirements:
    """Sépare les compétences obligatoires des compétences « souhaitées » dans l'offre.

    On découpe l'offre en lignes / phrases : une compétence citée dans une phrase
    qui contient un marqueur comme « un plus » est considérée comme optionnelle.
    """
    # On coupe sur les retours à la ligne, les puces et les fins de phrase,
    # sans casser les noms comme "Node.js", ".NET" ou "React-Native"
    chunks = [c for c in re.split(r"\n|•|(?<=[.;!?])\s+|\s[-–]\s", offer_text) if c and c.strip()]
    optional_names: set[str] = set()
    required_names: set[str] = set()

    for chunk in chunks:
        chunk_norm = normalize(chunk)
        is_optional = any(marker in chunk_norm for marker in OPTIONAL_MARKERS)
        for skill in extract_skills(chunk):
            (optional_names if is_optional else required_names).add(skill.name)

    # Si une compétence est citée à la fois comme exigence et comme "plus", elle reste exigée
    optional_names -= required_names

    all_skills = extract_skills(offer_text)
    return OfferRequirements(
        required=[s for s in all_skills if s.name in required_names],
        optional=[s for s in all_skills if s.name in optional_names],
    )


def score_level(score: int) -> str:
    """Traduit un score en niveau lisible."""
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Bon"
    if score >= 40:
        return "Moyen"
    return "Faible"


def compute_match(cv_text: str, offer_text: str) -> MatchResult:
    """Compare le CV à l'offre et calcule un score pondéré sur 100."""
    requirements = split_offer_requirements(offer_text)
    cv_skills = extract_skills(cv_text)
    cv_names = {s.name for s in cv_skills}

    matched_req = [s for s in requirements.required if s.name in cv_names]
    missing_req = [s for s in requirements.required if s.name not in cv_names]
    matched_opt = [s for s in requirements.optional if s.name in cv_names]
    missing_opt = [s for s in requirements.optional if s.name not in cv_names]

    total = len(requirements.required) * REQUIRED_WEIGHT + len(requirements.optional) * OPTIONAL_WEIGHT
    earned = len(matched_req) * REQUIRED_WEIGHT + len(matched_opt) * OPTIONAL_WEIGHT
    score = round(100 * earned / total) if total else 0

    asked_names = {s.name for s in requirements.all}
    extra = [s for s in cv_skills if s.name not in asked_names]

    # Couverture par catégorie : % des compétences demandées dans chaque catégorie que le CV possède
    coverage: dict[str, int] = {}
    for category in sorted({s.category for s in requirements.all}):
        asked = [s for s in requirements.all if s.category == category]
        have = [s for s in asked if s.name in cv_names]
        coverage[category] = round(100 * len(have) / len(asked))

    return MatchResult(
        score=score,
        level=score_level(score),
        matched_required=matched_req,
        missing_required=missing_req,
        matched_optional=matched_opt,
        missing_optional=missing_opt,
        extra_skills=extra,
        category_coverage=coverage,
    )
