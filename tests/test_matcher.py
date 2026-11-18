"""Tests du calcul de compatibilité CV / offre."""

from app.services.matcher import compute_match, score_level, split_offer_requirements

OFFER = """Stage PFE développeur.
Compétences requises : Java, Spring Boot, Angular, Docker.
Une expérience avec Kubernetes serait un plus."""


def test_separe_exigences_et_atouts():
    req = split_offer_requirements(OFFER)
    assert {s.name for s in req.required} == {"Java", "Spring Boot", "Angular", "Docker"}
    assert {s.name for s in req.optional} == {"Kubernetes"}


def test_score_parfait():
    result = compute_match("Java, Spring Boot, Angular, Docker, Kubernetes", OFFER)
    assert result.score == 100
    assert result.level == "Excellent"
    assert not result.missing_required


def test_score_partiel_et_competences_manquantes():
    result = compute_match("Java et Angular, plus Flutter", OFFER)
    # 2 exigences sur 4 (poids 1) et 0 atout sur 1 (poids 0,4) -> 2 / 4,4 = 45 %
    assert result.score == 45
    assert {s.name for s in result.missing_required} == {"Spring Boot", "Docker"}
    assert {s.name for s in result.extra_skills} == {"Flutter"}


def test_une_exigence_citee_aussi_comme_atout_reste_exigee():
    offer = "Docker obligatoire. Docker Swarm serait un plus."
    req = split_offer_requirements(offer)
    assert [s.name for s in req.required] == ["Docker"]
    assert req.optional == []


def test_niveaux():
    assert score_level(85) == "Excellent"
    assert score_level(65) == "Bon"
    assert score_level(45) == "Moyen"
    assert score_level(10) == "Faible"
