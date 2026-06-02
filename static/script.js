const state = {
    token: localStorage.getItem("talentforge_token") || "",
    user: JSON.parse(localStorage.getItem("talentforge_user") || "null"),
    authMode: "login",
    jobs: [],
    applications: [],
    candidates: [],
    employees: [],
    selectedJob: null,
    rankings: [],
    currentView: "",
};

const authView = document.getElementById("auth-view");
const appView = document.getElementById("app-view");
const authForm = document.getElementById("auth-form");
const authTitle = document.getElementById("auth-title");
const authSubtitle = document.getElementById("auth-subtitle");
const authSubmit = document.getElementById("auth-submit");
const authMessage = document.getElementById("auth-message");
const toggleAuthMode = document.getElementById("toggle-auth-mode");
const nav = document.getElementById("nav");
const appMessage = document.getElementById("app-message");
const sectionTitle = document.getElementById("section-title");
const sectionEyebrow = document.getElementById("section-eyebrow");

const candidateViews = ["candidate-dashboard", "candidate-jobs", "candidate-job-details", "candidate-applications"];
const managementViews = ["management-dashboard", "management-jobs", "management-candidates", "management-applications"];
const allViews = [...candidateViews, ...managementViews];

function isManagementRole(role) {
    return ["hr", "manager", "admin"].includes(role);
}

function isJobManager(role) {
    return ["hr", "admin"].includes(role);
}

function setMessage(target, text = "", type = "") {
    target.textContent = text;
    target.className = `message ${type}`.trim();
}

function authHeaders(json = true) {
    const headers = {};
    if (json) headers["Content-Type"] = "application/json";
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    return headers;
}

async function readResponse(response) {
    const text = await response.text();
    if (!text) return {};
    try {
        return JSON.parse(text);
    } catch {
        return { error: text };
    }
}

async function api(path, options = {}) {
    const response = await fetch(path, {
        ...options,
        headers: {
            ...authHeaders(!(options.body instanceof FormData)),
            ...(options.headers || {}),
        },
    });
    const data = await readResponse(response);
    if (!response.ok) {
        throw new Error(data.error || data.detail || data.message || "Request failed");
    }
    return data;
}

function saveSession(data) {
    state.token = data.access_token;
    state.user = {
        id: data.user_id,
        username: data.username,
        role: data.role,
    };
    localStorage.setItem("talentforge_token", state.token);
    localStorage.setItem("talentforge_user", JSON.stringify(state.user));
}

function clearSession() {
    state.token = "";
    state.user = null;
    localStorage.removeItem("talentforge_token");
    localStorage.removeItem("talentforge_user");
}

function sanitize(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function switchAuthMode() {
    state.authMode = state.authMode === "login" ? "register" : "login";
    const register = state.authMode === "register";
    authTitle.textContent = register ? "Create account" : "Sign in";
    authSubtitle.textContent = register ? "Create your Day 1 workspace access." : "Access your hiring workspace.";
    authSubmit.querySelector("span").textContent = register ? "Register" : "Login";
    toggleAuthMode.textContent = register ? "Already have an account" : "Create an account";
    document.getElementById("auth-password").minLength = register ? 6 : 1;
    setMessage(authMessage);
}

authForm.addEventListener("submit", async event => {
    event.preventDefault();
    setMessage(authMessage, "Working...");
    const username = document.getElementById("auth-username").value.trim();
    const password = document.getElementById("auth-password").value;
    const payload = { username, password };
    const path = state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";

    try {
        const data = await api(path, { method: "POST", body: JSON.stringify(payload) });
        saveSession(data);
        setMessage(authMessage, "");
        await bootApp();
    } catch (error) {
        setMessage(authMessage, error.message, "error");
    }
});

toggleAuthMode.addEventListener("click", switchAuthMode);

document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    showAuth();
});

document.getElementById("refresh-btn").addEventListener("click", () => loadCurrentView());
document.getElementById("back-to-jobs").addEventListener("click", () => showView("candidate-jobs"));
document.getElementById("close-analysis-modal").addEventListener("click", closeAnalysisModal);
document.getElementById("load-rankings-btn").addEventListener("click", loadRankings);

function showAuth() {
    authView.classList.remove("hidden");
    appView.classList.add("hidden");
}

async function bootApp() {
    if (!state.token || !state.user) {
        showAuth();
        return;
    }

    authView.classList.add("hidden");
    appView.classList.remove("hidden");
    document.getElementById("current-username").textContent = state.user.username;
    document.getElementById("current-role").textContent = state.user.role;
    buildNav();

    if (state.user.role === "candidate") {
        await showView("candidate-dashboard");
    } else if (isManagementRole(state.user.role)) {
        await showView("management-dashboard");
    } else {
        sectionTitle.textContent = "Employee Dashboard";
        sectionEyebrow.textContent = "Dashboard";
        allViews.forEach(id => document.getElementById(id).classList.add("hidden"));
        setMessage(appMessage, "Employee functionality is reserved for a future phase.", "success");
    }
}

function buildNav() {
    const role = state.user.role;
    const items = [];

    if (role === "candidate") {
        items.push(["candidate-dashboard", "Dashboard", "fa-gauge"]);
        items.push(["candidate-jobs", "Job Listing", "fa-briefcase"]);
        items.push(["candidate-applications", "My Applications", "fa-file-lines"]);
    }

    if (isManagementRole(role)) {
        items.push(["management-dashboard", "Dashboard", "fa-gauge"]);
        if (isJobManager(role)) items.push(["management-jobs", "Jobs Management", "fa-pen-to-square"]);
        items.push(["management-candidates", "Candidates List", "fa-users"]);
        items.push(["management-applications", "Applications List", "fa-folder-open"]);
    }

    nav.innerHTML = items.map(([view, label, icon]) => `
        <button type="button" data-view="${view}">
            <i class="fa-solid ${icon}"></i>
            <span>${label}</span>
        </button>
    `).join("");

    nav.querySelectorAll("button").forEach(button => {
        button.addEventListener("click", () => showView(button.dataset.view));
    });
}

async function showView(viewId) {
    state.currentView = viewId;
    allViews.forEach(id => document.getElementById(id).classList.add("hidden"));
    document.getElementById(viewId).classList.remove("hidden");
    nav.querySelectorAll("button").forEach(button => {
        button.classList.toggle("active", button.dataset.view === viewId);
    });

    const labels = {
        "candidate-dashboard": ["Dashboard", "Candidate Dashboard"],
        "candidate-jobs": ["Jobs", "Job Listing"],
        "candidate-job-details": ["Apply", "Job Details"],
        "candidate-applications": ["Applications", "My Applications"],
        "management-dashboard": ["Dashboard", "Management Dashboard"],
        "management-jobs": ["Jobs", "Jobs Management"],
        "management-candidates": ["Candidates", "Candidates List"],
        "management-applications": ["Applications", "Applications List"],
    };
    const [eyebrow, title] = labels[viewId] || ["Dashboard", "Dashboard"];
    sectionEyebrow.textContent = eyebrow;
    sectionTitle.textContent = title;
    setMessage(appMessage);
    await loadCurrentView();
}

async function loadCurrentView() {
    try {
        if (state.currentView === "candidate-dashboard") await loadCandidateDashboard();
        if (state.currentView === "candidate-jobs") await loadCandidateJobs();
        if (state.currentView === "candidate-applications") await loadMyApplications();
        if (state.currentView === "management-dashboard") await loadManagementDashboard();
        if (state.currentView === "management-jobs") await loadManagementJobs();
        if (state.currentView === "management-candidates") await loadCandidates();
        if (state.currentView === "management-applications") await loadApplications();
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
}

async function loadCandidateDashboard() {
    const [jobs, applications] = await Promise.all([
        api("/api/jobs"),
        api("/api/applications/me"),
    ]);
    document.getElementById("candidate-total-jobs").textContent = jobs.length;
    document.getElementById("candidate-total-applications").textContent = applications.length;
}

async function loadCandidateJobs() {
    state.jobs = await api("/api/jobs");
    const container = document.getElementById("candidate-job-list");
    if (!state.jobs.length) {
        container.innerHTML = `<p class="empty-state">No jobs are available yet.</p>`;
        return;
    }
    container.innerHTML = state.jobs.map(job => jobCard(job, true)).join("");
    container.querySelectorAll("[data-open-job]").forEach(button => {
        button.addEventListener("click", () => openJobDetails(Number(button.dataset.openJob)));
    });
}

async function openJobDetails(jobId) {
    state.selectedJob = await api(`/api/jobs/${jobId}`);
    document.getElementById("job-detail-title").textContent = state.selectedJob.title;
    document.getElementById("job-detail-meta").textContent = `${state.selectedJob.department || "General"} · ${state.selectedJob.experience_required || "Experience not specified"}`;
    document.getElementById("job-detail-description").textContent = state.selectedJob.description;
    document.getElementById("job-detail-skills").textContent = state.selectedJob.required_skills || "Not specified";
    document.getElementById("job-detail-experience").textContent = state.selectedJob.experience_required || "Not specified";
    document.getElementById("job-detail-salary").textContent = state.selectedJob.salary_range || "Not specified";
    document.getElementById("apply-resume").value = "";
    await showView("candidate-job-details");
}

document.getElementById("apply-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.selectedJob) return;
    const file = document.getElementById("apply-resume").files[0];
    if (!file) return;
    const form = new FormData();
    form.append("job_id", String(state.selectedJob.id));
    form.append("file", file);
    try {
        await api("/api/applications/apply", { method: "POST", body: form });
        setMessage(appMessage, "Application saved.", "success");
        await showView("candidate-applications");
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
});

async function loadMyApplications() {
    state.applications = await api("/api/applications/me");
    document.getElementById("my-applications-list").innerHTML = renderApplicationsTable(state.applications, false);
}

async function loadManagementDashboard() {
    const calls = [api("/api/jobs"), api("/api/candidates"), api("/api/applications")];
    if (state.user.role === "admin") calls.push(api("/api/employees"));
    const [jobs, candidates, applications, employees = []] = await Promise.all(calls);
    document.getElementById("mgmt-total-jobs").textContent = jobs.length;
    document.getElementById("mgmt-total-candidates").textContent = candidates.length;
    document.getElementById("mgmt-total-applications").textContent = applications.length;
    const employeeCard = document.getElementById("admin-employee-card");
    employeeCard.classList.toggle("hidden", state.user.role !== "admin");
    document.getElementById("admin-total-employees").textContent = employees.length;
}

async function loadManagementJobs() {
    state.jobs = await api("/api/jobs");
    const container = document.getElementById("management-job-list");
    if (!state.jobs.length) {
        container.innerHTML = `<p class="empty-state">No jobs have been created.</p>`;
        return;
    }
    container.innerHTML = state.jobs.map(job => jobCard(job, false)).join("");
    container.querySelectorAll("[data-edit-job]").forEach(button => {
        button.addEventListener("click", () => fillJobForm(Number(button.dataset.editJob)));
    });
    container.querySelectorAll("[data-delete-job]").forEach(button => {
        button.addEventListener("click", () => deleteJob(Number(button.dataset.deleteJob)));
    });
}

function jobCard(job, candidateMode) {
    const action = candidateMode
        ? `<button class="primary-btn" type="button" data-open-job="${job.id}"><i class="fa-solid fa-arrow-right"></i><span>View Details</span></button>`
        : `<div class="button-row">
            <button class="ghost-btn" type="button" data-edit-job="${job.id}"><i class="fa-solid fa-pen"></i><span>Edit</span></button>
            <button class="ghost-btn danger-btn" type="button" data-delete-job="${job.id}"><i class="fa-solid fa-trash"></i><span>Delete</span></button>
        </div>`;

    return `
        <article class="job-card">
            <div>
                <h3>${sanitize(job.title)}</h3>
                <p class="muted">${sanitize(job.description).slice(0, 220)}${job.description.length > 220 ? "..." : ""}</p>
            </div>
            <div class="job-meta">
                <span class="pill">${sanitize(job.department || "General")}</span>
                <span class="pill">${sanitize(job.experience_required || "Experience not specified")}</span>
                <span class="pill">${sanitize(job.salary_range || "Salary not specified")}</span>
            </div>
            ${action}
        </article>
    `;
}

document.getElementById("job-form").addEventListener("submit", async event => {
    event.preventDefault();
    const jobId = document.getElementById("job-id").value;
    const payload = {
        title: document.getElementById("job-title").value.trim(),
        description: document.getElementById("job-description").value.trim(),
        required_skills: document.getElementById("job-skills").value.trim(),
        department: document.getElementById("job-department").value.trim(),
        salary_range: document.getElementById("job-salary").value.trim(),
        experience_required: document.getElementById("job-experience").value.trim(),
    };
    const path = jobId ? `/api/jobs/${jobId}` : "/api/jobs";
    const method = jobId ? "PUT" : "POST";

    try {
        await api(path, { method, body: JSON.stringify(payload) });
        clearJobForm();
        setMessage(appMessage, jobId ? "Job updated." : "Job created.", "success");
        await loadManagementJobs();
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
});

document.getElementById("clear-job-form").addEventListener("click", clearJobForm);

function fillJobForm(jobId) {
    const job = state.jobs.find(item => item.id === jobId);
    if (!job) return;
    document.getElementById("job-id").value = job.id;
    document.getElementById("job-title").value = job.title;
    document.getElementById("job-description").value = job.description;
    document.getElementById("job-skills").value = job.required_skills || "";
    document.getElementById("job-department").value = job.department || "";
    document.getElementById("job-salary").value = job.salary_range || "";
    document.getElementById("job-experience").value = job.experience_required || "";
    document.getElementById("job-form-action").textContent = "Update Job";
}

function clearJobForm() {
    document.getElementById("job-form").reset();
    document.getElementById("job-id").value = "";
    document.getElementById("job-form-action").textContent = "Create Job";
}

async function deleteJob(jobId) {
    try {
        await api(`/api/jobs/${jobId}`, { method: "DELETE" });
        setMessage(appMessage, "Job deleted.", "success");
        await loadManagementJobs();
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
}

async function loadCandidates() {
    state.candidates = await api("/api/candidates");
    document.getElementById("candidate-list").innerHTML = renderCandidatesTable(state.candidates);
    document.querySelectorAll("[data-view-candidate]").forEach(button => {
        button.addEventListener("click", () => openCandidateProfile(Number(button.dataset.viewCandidate)));
    });
}

async function loadApplications() {
    const [applications, jobs] = await Promise.all([api("/api/applications"), api("/api/jobs")]);
    state.applications = applications;
    state.jobs = jobs;
    renderRankingJobSelect();
    document.getElementById("applications-list").innerHTML = renderApplicationsTable(state.applications, true);
    bindApplicationActions();
}

function renderCandidatesTable(candidates) {
    if (!candidates.length) return `<p class="empty-state">No candidates registered yet.</p>`;
    return `
        <table>
            <thead><tr><th>Name</th><th>Location</th><th>Experience</th><th>Applications</th><th>Action</th></tr></thead>
            <tbody>
                ${candidates.map(candidate => `
                    <tr>
                        <td>${sanitize(candidate.username)}</td>
                        <td>${sanitize(candidate.location || "-")}</td>
                        <td>${sanitize(candidate.experience || "-")}</td>
                        <td>${candidate.application_count}</td>
                        <td><button class="ghost-btn" type="button" data-view-candidate="${candidate.id}">View Profile</button></td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

async function openCandidateProfile(candidateId) {
    try {
        const candidate = await api(`/api/candidates/${candidateId}`);
        const applications = Array.isArray(candidate.applications) ? candidate.applications : [];
        document.getElementById("analysis-modal-content").innerHTML = `
            <h3>${sanitize(candidate.username)}</h3>
            <p class="muted">${sanitize(candidate.location || "-")} · ${sanitize(candidate.experience || "-")} · ${applications.length} applications</p>
            ${applications.length
                ? applications.map(application => `
                    <section class="analysis-section">
                        ${renderAnalysisDetail(application, application.ai_analysis || {})}
                    </section>
                `).join("")
                : '<p class="empty-state">This candidate has not submitted any applications.</p>'}
        `;
        document.getElementById("analysis-modal").classList.remove("hidden");
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
}

function renderApplicationsTable(applications, includeCandidate) {
    if (!applications.length) return `<p class="empty-state">No applications found.</p>`;
    return `
        <table>
            <thead>
                <tr>
                    ${includeCandidate ? "<th>Candidate</th>" : ""}
                    <th>Job</th>
                    ${includeCandidate ? "<th>AI Fit</th><th>Recommendation</th>" : ""}
                    <th>Status</th>
                    <th>Applied</th>
                    ${includeCandidate ? "<th>Actions</th>" : ""}
                </tr>
            </thead>
            <tbody>
                ${applications.map(application => `
                    <tr>
                        ${includeCandidate ? `<td>${sanitize(application.candidate_username)}</td>` : ""}
                        <td>${sanitize(application.job_title)}</td>
                        ${includeCandidate ? `<td>${renderScore(application.ai_analysis)}</td><td>${renderRecommendation(application.ai_analysis)}</td>` : ""}
                        <td>${sanitize(application.status)}</td>
                        <td>${formatDate(application.application_date)}</td>
                        ${includeCandidate ? `
                            <td>
                                <div class="button-row">
                                    <button class="ghost-btn" type="button" data-view-analysis="${application.id}">View AI</button>
                                    <button class="ghost-btn" type="button" data-reanalyze="${application.id}">Re-analyze</button>
                                </div>
                            </td>
                        ` : ""}
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;
}

function renderScore(analysis) {
    if (!analysis) return '<span class="score-badge">--</span>';
    return `<span class="score-badge">${Number(analysis.fit_score || 0)}%</span>`;
}

function renderRecommendation(analysis) {
    if (!analysis) return '<span class="recommendation">Pending</span>';
    return `<span class="recommendation">${sanitize(analysis.recommendation || 'Consider')}</span>`;
}

function bindApplicationActions() {
    document.querySelectorAll("[data-view-analysis]").forEach(button => {
        button.addEventListener("click", () => {
            const application = state.applications.find(item => item.id === Number(button.dataset.viewAnalysis));
            if (application) openAnalysisModal(application);
        });
    });
    document.querySelectorAll("[data-reanalyze]").forEach(button => {
        button.addEventListener("click", () => reanalyzeApplication(Number(button.dataset.reanalyze)));
    });
}

async function reanalyzeApplication(applicationId) {
    try {
        const data = await api(`/api/applications/${applicationId}/analyze`, { method: "POST" });
        const index = state.applications.findIndex(item => item.id === applicationId);
        if (index >= 0) state.applications[index] = data.application;
        document.getElementById("applications-list").innerHTML = renderApplicationsTable(state.applications, true);
        bindApplicationActions();
        setMessage(appMessage, "AI analysis refreshed.", "success");
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
}

function openAnalysisModal(application) {
    const analysis = application.ai_analysis;
    document.getElementById("analysis-modal-content").innerHTML = analysis
        ? renderAnalysisDetail(application, analysis)
        : `<h3>No AI analysis yet</h3><p class="muted">Use Re-analyze to generate recruitment intelligence.</p>`;
    document.getElementById("analysis-modal").classList.remove("hidden");
}

function closeAnalysisModal() {
    document.getElementById("analysis-modal").classList.add("hidden");
}

function renderAnalysisDetail(application, analysis) {
    const prep = analysis.interview_prep || {};
    return `
        <h3>${sanitize(application.candidate_username)} for ${sanitize(application.job_title)}</h3>
        <p><span class="score-badge">${Number(analysis.fit_score || 0)}%</span> <span class="recommendation">${sanitize(analysis.recommendation || 'Consider')}</span></p>
        <p>${sanitize(analysis.summary || '')}</p>
        ${analysis.error_message ? `<p class="message error">${sanitize(analysis.error_message)}</p>` : ''}
        <div class="analysis-grid">
            ${analysisList('Strengths', analysis.strengths)}
            ${analysisList('Weaknesses', analysis.weaknesses)}
            ${analysisList('Missing Skills', analysis.missing_skills)}
            ${analysisList('Observations', analysis.observations)}
            ${analysisList('Technical Questions', prep.technical_questions)}
            ${analysisList('Behavioral Questions', prep.behavioral_questions)}
            ${analysisList('Areas To Probe', prep.probing_areas)}
        </div>
        <p class="muted">Source: ${sanitize(analysis.source || 'fallback')} · Status: ${sanitize(analysis.status || '')}</p>
    `;
}

function analysisList(title, items = []) {
    const safeItems = Array.isArray(items) ? items : [];
    return `
        <section class="analysis-section">
            <h4>${sanitize(title)}</h4>
            ${safeItems.length
                ? `<ul>${safeItems.map(item => `<li>${sanitize(item)}</li>`).join("")}</ul>`
                : '<p class="muted">No items generated.</p>'}
        </section>
    `;
}

function renderRankingJobSelect() {
    const select = document.getElementById("ranking-job-select");
    select.innerHTML = state.jobs.length
        ? state.jobs.map(job => `<option value="${job.id}">${sanitize(job.title)}</option>`).join("")
        : '<option value="">No jobs available</option>';
}

async function loadRankings() {
    const jobId = document.getElementById("ranking-job-select").value;
    if (!jobId) return;
    try {
        const data = await api(`/api/applications/rankings/${jobId}`);
        state.rankings = data.rankings || [];
        document.getElementById("rankings-list").innerHTML = renderRankings(state.rankings);
    } catch (error) {
        setMessage(appMessage, error.message, "error");
    }
}

function renderRankings(rankings) {
    if (!rankings.length) return '<p class="empty-state">No candidates have applied to this job yet.</p>';
    return rankings.map(item => `
        <article class="ranking-card">
            <header>
                <strong>#${item.rank} ${sanitize(item.candidate.username)}</strong>
                <span>${renderScore(item.analysis)} ${renderRecommendation(item.analysis)}</span>
            </header>
            <p>${sanitize(item.analysis.summary || '')}</p>
        </article>
    `).join("");
}

function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "-";
    return date.toLocaleDateString();
}

bootApp();
