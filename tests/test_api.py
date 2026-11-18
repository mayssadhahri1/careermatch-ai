"""Tests de bout en bout de l'API REST (base SQLite temporaire)."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_careermatch.db"
os.environ["LLM_PROVIDER"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PAYLOAD = {
    "job_title": "Stage PFE Full-Stack",
    "company": "Acme",
    "offer_text": "Compétences requises : Java, Spring Boot, Angular et Docker. Kubernetes serait un plus.",
    "cv_text": "Élève-ingénieure : Java, Spring Boot, Angular, Flutter, Git et Docker.",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
    if os.path.exists("test_careermatch.db"):
        os.remove("test_careermatch.db")


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok", "llm_provider": "none"}


def test_creer_puis_lire_une_analyse(client):
    res = client.post("/api/analyses", json=PAYLOAD)
    assert res.status_code == 201
    data = res.json()
    assert data["report"]["score"] == 91  # 4 exigences sur 4, 0 atout sur 1 -> 4 / 4,4
    assert data["report"]["level"] == "Excellent"

    detail = client.get(f"/api/analyses/{data['id']}")
    assert detail.status_code == 200
    assert detail.json()["company"] == "Acme"

    history = client.get("/api/analyses").json()
    assert history[0]["id"] == data["id"]


def test_validation_texte_trop_court(client):
    res = client.post("/api/analyses", json={**PAYLOAD, "cv_text": "trop court"})
    assert res.status_code == 422


def test_offre_sans_competence_reconnue(client):
    offer = "Nous cherchons une personne motivée et souriante."
    res = client.post("/api/analyses", json={**PAYLOAD, "offer_text": offer})
    assert res.status_code == 422


def test_suppression(client):
    analysis_id = client.post("/api/analyses", json=PAYLOAD).json()["id"]
    assert client.delete(f"/api/analyses/{analysis_id}").status_code == 204
    assert client.get(f"/api/analyses/{analysis_id}").status_code == 404


def test_interface_web(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "CareerMatch" in res.text
