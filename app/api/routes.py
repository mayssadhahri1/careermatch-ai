"""Routes REST de l'API."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.career_agent import AgentReport, CareerAgent
from app.agent.llm import build_llm_client
from app.api.schemas import AnalysisOut, AnalysisReport, AnalysisRequest, AnalysisSummary
from app.core.config import Settings, get_settings
from app.db.database import AnalysisRecord, get_session

router = APIRouter(prefix="/api", tags=["analyses"])


def get_agent(settings: Settings = Depends(get_settings)) -> CareerAgent:
    """Dépendance : crée l'agent avec le LLM configuré (ou sans LLM)."""
    return CareerAgent(llm=build_llm_client(settings))


def to_report(report: AgentReport) -> AnalysisReport:
    """Convertit le rapport interne de l'agent en schéma de réponse."""
    m = report.match
    return AnalysisReport(
        score=m.score,
        level=m.level,
        matched_required=[asdict(s) for s in m.matched_required],
        missing_required=[asdict(s) for s in m.missing_required],
        matched_optional=[asdict(s) for s in m.matched_optional],
        missing_optional=[asdict(s) for s in m.missing_optional],
        extra_skills=[asdict(s) for s in m.extra_skills],
        category_coverage=m.category_coverage,
        cv_years=report.cv_years,
        learning_plan=report.learning_plan,
        advice=report.advice,
        cover_letter=report.cover_letter,
        llm_used=report.llm_used,
        steps=[asdict(s) for s in report.steps],
    )


@router.get("/health", tags=["système"])
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Vérifie que l'API fonctionne et indique le fournisseur LLM configuré."""
    return {"status": "ok", "llm_provider": settings.llm_provider}


@router.post("/analyses", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def create_analysis(
    payload: AnalysisRequest,
    agent: CareerAgent = Depends(get_agent),
    session: Session = Depends(get_session),
) -> AnalysisRecord:
    """Lance l'agent sur un CV et une offre, enregistre le résultat et le renvoie."""
    report = to_report(agent.run(payload.cv_text, payload.offer_text, payload.job_title, payload.company))
    if not (report.matched_required or report.missing_required or report.matched_optional or report.missing_optional):
        raise HTTPException(
            status_code=422,
            detail="Aucune compétence technique reconnue dans l'offre. Colle le texte complet de l'annonce.",
        )

    record = AnalysisRecord(
        job_title=payload.job_title,
        company=payload.company,
        score=report.score,
        level=report.level,
        offer_text=payload.offer_text,
        cv_text=payload.cv_text,
        report=report.model_dump(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses(
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[AnalysisRecord]:
    """Historique des analyses, de la plus récente à la plus ancienne."""
    stmt = select(AnalysisRecord).order_by(AnalysisRecord.id.desc()).limit(limit)
    return list(session.scalars(stmt))


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, session: Session = Depends(get_session)) -> AnalysisRecord:
    """Détail d'une analyse."""
    record = session.get(AnalysisRecord, analysis_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    return record


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: int, session: Session = Depends(get_session)) -> None:
    """Supprime une analyse de l'historique."""
    record = session.get(AnalysisRecord, analysis_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analyse introuvable")
    session.delete(record)
    session.commit()
