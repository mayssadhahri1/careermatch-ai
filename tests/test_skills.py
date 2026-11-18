"""Tests de l'extraction des compétences."""

from app.services.skills import extract_skills, extract_years_of_experience


def names(text: str) -> set[str]:
    return {s.name for s in extract_skills(text)}


def test_detecte_les_competences_simples():
    assert {"Java", "Spring Boot", "Angular", "Docker"} <= names("Java, Spring Boot, Angular et Docker")


def test_gere_les_symboles_dans_les_noms():
    found = names("Expérience en C++, C#, Node.js, .NET et CI/CD")
    assert {"C++", "C#", "Node.js", ".NET", "CI/CD"} <= found


def test_ne_confond_pas_les_mots_proches():
    # "reste" ne doit pas être reconnu comme REST, ni "javascript" comme Java
    found = names("Le reste du temps, je fais du javascript")
    assert "API REST" not in found
    assert "Java" not in found
    assert "JavaScript" in found


def test_react_native_ne_compte_pas_comme_react():
    assert "React" not in names("Application mobile en React Native")
    assert {"React", "React Native"} <= names("React pour le web et React Native pour le mobile")


def test_synonymes_agents_ia():
    assert "Agents IA" in names("Développement d'agents LLM avec LangChain")


def test_annees_experience():
    assert extract_years_of_experience("3 ans d'expérience en Java") == 3
    assert extract_years_of_experience("Débutant motivé") is None
