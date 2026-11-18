// Interface web de CareerMatch AI : appelle l'API REST et affiche le rapport de l'agent.

const $ = (id) => document.getElementById(id);

// Exemple pour tester rapidement l'application
const EXAMPLE = {
  job: "Stage PFE — Développeur Full-Stack Java / Angular",
  company: "Acme Tunisie",
  offer: `Dans le cadre de son projet de fin d'études, Acme recherche un(e) stagiaire.
Missions : développer des API REST avec Java et Spring Boot, créer des interfaces Angular.
Compétences requises : Java, Spring Boot, Angular, PostgreSQL, Git, Docker.
Une expérience avec Kubernetes ou Kafka serait un plus.
Des connaissances en LLM et agents IA sont appréciées.`,
  cv: `Élève-ingénieure en génie logiciel.
Compétences : Java, Spring Boot, Spring Security (JWT), Angular, React, Flutter, Node.js.
Microservices : gRPC, Kafka, GraphQL. Bases de données : MySQL, MongoDB.
DevOps : Git, GitHub, Docker, Jenkins, CI/CD. IA : Prompt Engineering, agents LLM.`,
};

// Échappe le texte avant de l'insérer dans le HTML (sécurité contre l'injection)
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function chips(container, skills, cls) {
  container.innerHTML = skills.length
    ? skills.map((s) => `<span class="chip ${cls}" title="${esc(s.category)}">${esc(s.name)}</span>`).join("")
    : '<span class="chip-none">—</span>';
}

// Couleur du score selon le niveau
function scoreColor(score) {
  if (score >= 80) return "#059669";
  if (score >= 60) return "#2563eb";
  if (score >= 40) return "#d97706";
  return "#dc2626";
}

function renderReport(report) {
  $("results").hidden = false;

  // Anneau de score animé (circonférence = 2 * π * 52 ≈ 327)
  const ring = $("ring-fg");
  ring.style.stroke = scoreColor(report.score);
  ring.style.strokeDashoffset = String(327 - (327 * report.score) / 100);
  $("score-value").textContent = report.score;
  $("score-level").textContent = report.level;
  $("score-level").style.color = scoreColor(report.score);

  // Barres de couverture par domaine
  $("coverage").innerHTML = Object.entries(report.category_coverage)
    .map(([cat, val]) => `
      <div class="cov-row">
        <span>${esc(cat)}</span>
        <div class="cov-bar"><span style="width:${val}%"></span></div>
        <span class="cov-val">${val}%</span>
      </div>`)
    .join("") || '<span class="chip-none">—</span>';

  chips($("matched-required"), report.matched_required, "chip-ok");
  chips($("missing-required"), report.missing_required, "chip-ko");
  chips($("optional"), [
    ...report.matched_optional.map((s) => ({ ...s, name: `✔ ${s.name}` })),
    ...report.missing_optional,
  ], "chip-warn");
  chips($("extra"), report.extra_skills, "chip-info");

  $("advice").innerHTML = report.advice.map((a) => `<li>${esc(a)}</li>`).join("");
  $("plan").innerHTML = report.learning_plan.length
    ? report.learning_plan
        .map((p) => `<li><span class="tag">${esc(p.skill)}</span><br>${esc(p.action)}</li>`)
        .join("")
    : "<li>Aucune compétence manquante : bravo !</li>";

  $("letter").textContent = report.cover_letter;

  $("steps").innerHTML = report.steps
    .map((s) => `
      <li class="${s.status === "fallback" ? "fallback" : ""}">
        <div><span class="s-name">${esc(s.name)}</span><span class="s-detail">${esc(s.detail)}</span></div>
        <span class="s-time">${s.duration_ms} ms</span>
      </li>`)
    .join("");

  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadHistory() {
  const list = $("history-list");
  try {
    const res = await fetch("/api/analyses?limit=30");
    const items = await res.json();
    list.innerHTML = items.length
      ? items
          .map((a) => `
            <li data-id="${a.id}">
              <span class="h-title">${esc(a.job_title || "Analyse sans titre")}</span>
              <span class="h-meta"><span>${esc(a.company || "—")}</span><strong style="color:${scoreColor(a.score)}">${a.score}/100</strong></span>
            </li>`)
          .join("")
      : '<li class="empty">Aucune analyse pour l\'instant.</li>';
  } catch {
    list.innerHTML = '<li class="empty">Historique indisponible.</li>';
  }
}

async function openAnalysis(id) {
  const res = await fetch(`/api/analyses/${id}`);
  if (!res.ok) return;
  const data = await res.json();
  $("job-title").value = data.job_title;
  $("company").value = data.company;
  renderReport(data.report);
}

async function submitAnalysis(event) {
  event.preventDefault();
  const btn = $("submit-btn");
  const errorBox = $("form-error");
  errorBox.hidden = true;
  btn.disabled = true;
  btn.textContent = "L'agent analyse…";

  try {
    const res = await fetch("/api/analyses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_title: $("job-title").value.trim(),
        company: $("company").value.trim(),
        offer_text: $("offer-text").value,
        cv_text: $("cv-text").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      // FastAPI renvoie soit un message, soit une liste d'erreurs de validation
      const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join(" · ") : data.detail;
      throw new Error(detail || "Erreur inconnue");
    }
    renderReport(data.report);
    loadHistory();
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.hidden = false;
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyser ma candidature";
  }
}

async function loadHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const badge = $("llm-badge");
    if (data.llm_provider === "none") {
      badge.textContent = "Mode règles (sans LLM)";
    } else {
      badge.textContent = `LLM : ${data.llm_provider}`;
      badge.className = "badge badge-ai";
    }
  } catch {
    /* l'API ne répond pas : on laisse le badge par défaut */
  }
}

// Branchement des événements
$("analysis-form").addEventListener("submit", submitAnalysis);
$("refresh-history").addEventListener("click", loadHistory);
$("history-list").addEventListener("click", (e) => {
  const li = e.target.closest("li[data-id]");
  if (li) openAnalysis(li.dataset.id);
});
$("fill-example").addEventListener("click", () => {
  $("job-title").value = EXAMPLE.job;
  $("company").value = EXAMPLE.company;
  $("offer-text").value = EXAMPLE.offer;
  $("cv-text").value = EXAMPLE.cv;
});
$("copy-letter").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("letter").textContent);
  $("copy-letter").textContent = "Copié ✓";
  setTimeout(() => ($("copy-letter").textContent = "Copier"), 1500);
});

loadHealth();
loadHistory();
