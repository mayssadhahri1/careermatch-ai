"""Schémas Pydantic : format des données échangées par l'API (validation automatique)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnalysisRequest(BaseModel):
    """Données envoyées par le client pour lancer une analyse."""

    cv_text: str = Field(..., min_length=30, max_length=20_000, description="Texte du CV")
    offer_text: str = Field(..., min_length=30, max_length=20_000, description="Texte de l'offre de stage")
    job_title: str = Field("", max_length=200, description="Intitulé du poste (optionnel)")
    company: str = Field("", max_length=200, description="Nom de l'entreprise (optionnel)")


class SkillOut(BaseModel):
    name: str
    category: str


class StepOut(BaseModel):
    name: str
    detail: str
    duration_ms: int
    status: str


class LearningItem(BaseModel):
    skill: str
    category: str
    action: str


class AnalysisReport(BaseModel):
    """Rapport complet renvoyé par l'agent."""

    score: int
    level: str
    matched_required: list[SkillOut]
    missing_required: list[SkillOut]
    matched_optional: list[SkillOut]
    missing_optional: list[SkillOut]
    extra_skills: list[SkillOut]
    category_coverage: dict[str, int]
    cv_years: int | None
    learning_plan: list[LearningItem]
    advice: list[str]
    cover_letter: str
    llm_used: str | None
    steps: list[StepOut]


class AnalysisOut(BaseModel):
    """Une analyse enregistrée, avec son rapport."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    job_title: str
    company: str
    score: int
    level: str
    report: AnalysisReport


class AnalysisSummary(BaseModel):
    """Version courte pour l'historique."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    job_title: str
    company: str
    score: int
    level: str
