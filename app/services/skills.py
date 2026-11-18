"""Extraction des compétences techniques à partir d'un texte libre (CV ou offre de stage).

L'approche est déterministe : un catalogue de compétences, chacune avec ses synonymes,
et une recherche par expressions régulières. Elle fonctionne sans IA et sert de base
fiable à l'agent (le LLM vient ensuite enrichir l'analyse).
"""

import re
import unicodedata
from dataclasses import dataclass

# Catalogue : nom canonique -> (catégorie, liste de synonymes)
SKILL_CATALOG: dict[str, tuple[str, list[str]]] = {
    # Langages
    "Java": ("Langages", ["java", "java 17", "java 21", "jee", "j2ee", "jakarta ee"]),
    "Python": ("Langages", ["python", "python3"]),
    "JavaScript": ("Langages", ["javascript", "js", "es6"]),
    "TypeScript": ("Langages", ["typescript", "ts"]),
    "Kotlin": ("Langages", ["kotlin"]),
    "Dart": ("Langages", ["dart"]),
    "PHP": ("Langages", ["php"]),
    "C#": ("Langages", ["c#", "csharp"]),
    "C++": ("Langages", ["c++", "cpp"]),
    "Go": ("Langages", ["golang"]),
    "SQL": ("Langages", ["sql", "pl/sql", "t-sql"]),
    # Backend
    "Spring Boot": ("Backend", ["spring boot", "springboot", "spring"]),
    "Spring Security": ("Backend", ["spring security"]),
    "JPA / Hibernate": ("Backend", ["jpa", "hibernate", "spring data jpa"]),
    "Node.js": ("Backend", ["node.js", "nodejs", "node js", "node"]),
    "Express": ("Backend", ["express", "express.js", "expressjs"]),
    "NestJS": ("Backend", ["nestjs", "nest.js"]),
    "FastAPI": ("Backend", ["fastapi"]),
    "Django": ("Backend", ["django"]),
    "Flask": ("Backend", ["flask"]),
    "Laravel": ("Backend", ["laravel"]),
    ".NET": ("Backend", [".net", "dotnet", "asp.net"]),
    # Frontend
    "Angular": ("Frontend", ["angular", "angularjs"]),
    "React": ("Frontend", ["react", "react.js", "reactjs"]),
    "Vue.js": ("Frontend", ["vue", "vue.js", "vuejs"]),
    "HTML/CSS": ("Frontend", ["html", "html5", "css", "css3"]),
    "Tailwind CSS": ("Frontend", ["tailwind", "tailwindcss"]),
    # Mobile
    "Flutter": ("Mobile", ["flutter"]),
    "React Native": ("Mobile", ["react native", "react-native"]),
    "Android": ("Mobile", ["android", "android studio"]),
    "iOS / Swift": ("Mobile", ["ios", "swift", "swiftui"]),
    # Bases de données
    "MySQL": ("Bases de données", ["mysql", "mariadb"]),
    "PostgreSQL": ("Bases de données", ["postgresql", "postgres"]),
    "MongoDB": ("Bases de données", ["mongodb", "mongo"]),
    "Redis": ("Bases de données", ["redis"]),
    "SQLite": ("Bases de données", ["sqlite"]),
    "Oracle": ("Bases de données", ["oracle"]),
    # Architecture & API
    "API REST": ("Architecture", ["rest", "restful", "api rest", "rest api"]),
    "GraphQL": ("Architecture", ["graphql"]),
    "gRPC": ("Architecture", ["grpc"]),
    "Microservices": ("Architecture", ["microservices", "microservice", "micro-services"]),
    "Kafka": ("Architecture", ["kafka", "apache kafka"]),
    "RabbitMQ": ("Architecture", ["rabbitmq"]),
    "WebSocket": ("Architecture", ["websocket", "websockets", "socket.io"]),
    "JWT / OAuth2": ("Architecture", ["jwt", "oauth2", "oauth", "keycloak"]),
    # DevOps & Cloud
    "Docker": ("DevOps", ["docker", "docker compose", "docker-compose"]),
    "Kubernetes": ("DevOps", ["kubernetes", "k8s", "openshift"]),
    "CI/CD": ("DevOps", ["ci/cd", "ci cd", "cicd", "intégration continue", "continuous integration"]),
    "Jenkins": ("DevOps", ["jenkins"]),
    "GitHub Actions": ("DevOps", ["github actions"]),
    "GitLab CI": ("DevOps", ["gitlab ci", "gitlab-ci"]),
    "Git": ("DevOps", ["git", "github", "gitlab"]),
    "Linux": ("DevOps", ["linux", "bash", "shell"]),
    "AWS": ("Cloud", ["aws", "amazon web services"]),
    "Azure": ("Cloud", ["azure"]),
    "GCP": ("Cloud", ["gcp", "google cloud"]),
    # IA & Data
    "Machine Learning": ("IA & Data", ["machine learning", "apprentissage automatique", "scikit-learn", "sklearn"]),
    "Deep Learning": ("IA & Data", ["deep learning", "tensorflow", "pytorch", "keras"]),
    "LLM / IA générative": ("IA & Data", ["llm", "llms", "ia générative", "generative ai", "genai", "gpt", "openai"]),
    "Agents IA": (
        "IA & Data",
        [
            "agents ia",
            "agent ia",
            "agents llm",
            "agent llm",
            "llm agents",
            "ai agents",
            "ai agent",
            "agentic",
            "ia agentique",
            "langchain",
            "langgraph",
            "crewai",
        ],
    ),
    "RAG": ("IA & Data", ["rag", "retrieval augmented generation"]),
    "Prompt Engineering": ("IA & Data", ["prompt engineering", "prompting"]),
    "Pandas / NumPy": ("IA & Data", ["pandas", "numpy"]),
    "Power BI": ("IA & Data", ["power bi", "powerbi"]),
    # Méthodes
    "Agile / Scrum": ("Méthodes", ["agile", "scrum", "kanban"]),
    "UML": ("Méthodes", ["uml"]),
    "Tests unitaires": ("Méthodes", ["junit", "pytest", "jest", "tests unitaires", "unit tests", "tdd"]),
}


@dataclass(frozen=True)
class Skill:
    """Une compétence reconnue dans un texte."""

    name: str
    category: str


def normalize(text: str) -> str:
    """Met le texte en minuscules et uniformise les apostrophes et espaces."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'")
    return re.sub(r"\s+", " ", text)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    """Construit une regex qui trouve l'alias comme mot entier.

    On n'utilise pas \\b car certains alias contiennent des symboles (c++, .net, ci/cd).
    """
    escaped = re.escape(alias)
    return re.compile(rf"(?<![\w+#.]){escaped}(?![\w+#])")


# Compilation unique des regex au chargement du module (plus rapide)
_COMPILED: list[tuple[str, str, list[re.Pattern[str]]]] = [
    (name, category, [_alias_pattern(a) for a in aliases]) for name, (category, aliases) in SKILL_CATALOG.items()
]


def extract_skills(text: str) -> list[Skill]:
    """Retourne les compétences trouvées dans le texte, sans doublon, dans l'ordre du catalogue."""
    clean = normalize(text)
    found: list[Skill] = []
    for name, category, patterns in _COMPILED:
        if any(p.search(clean) for p in patterns):
            found.append(Skill(name=name, category=category))

    names = {s.name for s in found}
    # "Spring" seul ne doit pas compter deux fois si Spring Security est déjà présent
    # et "React" ne doit pas être ajouté uniquement à cause de "React Native"
    if "React Native" in names and "React" in names and not _mentions_react_alone(clean):
        found = [s for s in found if s.name != "React"]
    return found


def _mentions_react_alone(clean: str) -> bool:
    """Vrai si "react" apparaît ailleurs que dans "react native"."""
    return bool(re.search(r"(?<![\w.])react(?!\s*-?\s*native)(?![\w])", clean))


def extract_years_of_experience(text: str) -> int | None:
    """Cherche une mention du type « 2 ans d'expérience » ou « 3+ years »."""
    clean = normalize(text)
    match = re.search(r"(\d{1,2})\s*\+?\s*(?:ans|an|years|year)\b", clean)
    return int(match.group(1)) if match else None
