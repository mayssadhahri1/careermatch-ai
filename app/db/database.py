"""Connexion à la base de données et modèle ORM des analyses (SQLAlchemy 2)."""

from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Classe de base des modèles ORM."""


class AnalysisRecord(Base):
    """Une analyse CV / offre enregistrée en base."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    job_title: Mapped[str] = mapped_column(String(200), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    offer_text: Mapped[str] = mapped_column(Text)
    cv_text: Mapped[str] = mapped_column(Text)
    # Le rapport complet est stocké en JSON pour pouvoir le réafficher tel quel
    report: Mapped[dict] = mapped_column(JSON)


def _make_engine(url: str):
    # SQLite a besoin de cette option pour être utilisé par plusieurs threads (serveur web)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Crée les tables si elles n'existent pas encore."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : ouvre une session par requête et la ferme ensuite."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
