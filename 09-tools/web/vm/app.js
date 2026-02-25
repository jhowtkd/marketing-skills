const ENDPOINT_BRANDS = "/api/v2/brands";
const ENDPOINT_PROJECTS = "/api/v2/projects";
const ENDPOINT_THREADS = "/api/v2/threads";
const ENDPOINT_WORKFLOW_PROFILES = "/api/v2/workflow-profiles";

const brandForm = document.getElementById("brand-create-form");
const brandNameInput = document.getElementById("brand-name-input");
const brandsList = document.getElementById("brands-list");

const projectForm = document.getElementById("project-create-form");
const projectNameInput = document.getElementById("project-name-input");
const projectObjectiveInput = document.getElementById("project-objective-input");
const projectChannelsInput = document.getElementById("project-channels-input");
const projectDueDateInput = document.getElementById("project-due-date-input");
const projectsList = document.getElementById("projects-list");

const threadTitleInput = document.getElementById("thread-title-input");
const threadCreateButton = document.getElementById("thread-create-button");
const threadModeForm = document.getElementById("thread-mode-form");
const threadModeInput = document.getElementById("thread-mode-input");
const threadsList = document.getElementById("threads-list");
const threadModesList = document.getElementById("thread-modes-list");
const timelineList = document.getElementById("timeline-list");
const tasksList = document.getElementById("tasks-list");
const approvalsList = document.getElementById("approvals-list");

const workflowRunForm = document.getElementById("workflow-run-form");
const workflowRequestInput = document.getElementById("workflow-request-input");
const workflowModeInput = document.getElementById("workflow-mode-input");
const workflowOverridesInput = document.getElementById("workflow-overrides-input");
const workflowProfilePreviewList = document.getElementById("workflow-profile-preview-list");
const workflowRunsList = document.getElementById("workflow-runs-list");
const workflowRunDetailList = document.getElementById("workflow-run-detail-list");
const workflowArtifactsList = document.getElementById("workflow-artifacts-list");
const workflowArtifactPreview = document.getElementById("workflow-artifact-preview");
const uiErrorBanner = document.getElementById("ui-error-banner");

const studioDevModeToggle = document.getElementById("studio-devmode-toggle");
const DEV_MODE_KEY = "vm_dev_mode";

const studioCreatePlanButton = document.getElementById("studio-create-plan-button");
const studioWizard = document.getElementById("studio-wizard");
const studioWizardForm = document.getElementById("studio-wizard-form");
const studioWizardCancel = document.getElementById("studio-wizard-cancel");
const studioPlanTitleInput = document.getElementById("studio-plan-title-input");
const studioPlanBriefInput = document.getElementById("studio-plan-brief-input");
const studioPlaybooks = document.getElementById("studio-playbooks");
const studioStatusText = document.getElementById("studio-status-text");
const studioStageProgress = document.getElementById("studio-stage-progress");
const studioArtifactPreview = document.getElementById("studio-artifact-preview");

const STATUS_LABEL = {
  queued: "Em fila",
  running: "Gerando…",
  waiting_approval: "Aguardando revisão",
  completed: "Pronto",
  failed: "Falhou",
};

function humanizeStageKey(key) {
  return String(key || "").replaceAll("_", " ");
}

function renderStudioRun(detail) {
  if (!detail) return;
  if (studioStatusText) {
    const label = STATUS_LABEL[detail.status] || detail.status;
    studioStatusText.textContent = `${label} · ${detail.effective_mode || detail.mode || ""}`.trim();
  }
  if (studioStageProgress) {
    const rows = Array.isArray(detail.stages)
      ? detail.stages.slice().sort((a, b) => a.position - b.position)
      : [];
    clearAndRender(studioStageProgress, rows, (stage) => {
      const node = document.createElement("div");
      node.className = "item";
      node.textContent = `${humanizeStageKey(stage.stage_id)} — ${stage.status}`;
      return node;
    });
  }
}

function setDevMode(enabled) {
  document.body.dataset.devMode = enabled ? "1" : "0";
  if (studioDevModeToggle) studioDevModeToggle.checked = !!enabled;
  window.localStorage.setItem(DEV_MODE_KEY, enabled ? "1" : "0");
}

function loadDevMode() {
  const raw = window.localStorage.getItem(DEV_MODE_KEY);
  setDevMode(raw === "1");
}

let studioSelectedMode = "plan_90d";

function renderStudioPlaybooks() {
  if (!studioPlaybooks) return;
  const allowed = new Set(["plan_90d", "content_calendar"]);
  const playbooks = (workflowProfilesState || []).filter((p) => allowed.has(p.mode));
  studioPlaybooks.innerHTML = "";
  for (const p of playbooks) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "border rounded p-3 text-left";
    btn.textContent = `${p.mode}: ${p.description || ""}`;
    btn.addEventListener("click", () => {
      studioSelectedMode = p.mode;
      renderStudioPlaybooks();
    });
    if (p.mode === studioSelectedMode) btn.classList.add("border-blue-500", "bg-blue-50");
    studioPlaybooks.appendChild(btn);
  }
}

function openStudioWizard() {
  if (!studioWizard) return;
  renderStudioPlaybooks();
  studioWizard.classList.remove("hidden");
}

function closeStudioWizard() {
  if (!studioWizard) return;
  studioWizard.classList.add("hidden");
}

const TIMELINE_EVENT_STYLE = {
  ApprovalRequested: { icon: "gavel", tone: "amber" },
  ApprovalGranted: { icon: "verified", tone: "green" },
  TaskCreated: { icon: "task_alt", tone: "blue" },
  WorkflowRunFailed: { icon: "error", tone: "red" },
};
const TIMELINE_TONE_CLASS = {
  amber: "text-amber-700 bg-amber-100",
  green: "text-green-700 bg-green-100",
  blue: "text-blue-700 bg-blue-100",
  red: "text-red-700 bg-red-100",
  slate: "text-slate-700 bg-slate-200",
};

function setUiError(message) {
  if (!uiErrorBanner) return;
  uiErrorBanner.textContent = message;
  uiErrorBanner.classList.remove("hidden");
}

function clearUiError() {
  if (!uiErrorBanner) return;
  uiErrorBanner.textContent = "";
  uiErrorBanner.classList.add("hidden");
}

let activeBrandId = null;
let activeProjectId = null;
let activeThreadId = null;
let activeWorkflowRunId = null;

let workflowPollTimer = null;

const brandsState = [];
const projectsState = [];
const threadsState = [];
const workflowProfilesState = [];

function buildEntityId(prefix) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function buildIdempotencyKey(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail || `Request failed (${response.status})`;
    setUiError(detail);
    throw new Error(detail);
  }
  clearUiError();
  return body;
}

async function postV2(url, payload, prefix) {
  return fetchJson(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": buildIdempotencyKey(prefix),
    },
    body: JSON.stringify(payload),
  });
}

async function patchV2(url, payload, prefix) {
  return fetchJson(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": buildIdempotencyKey(prefix),
    },
    body: JSON.stringify(payload),
  });
}

function clearAndRender(container, rows, renderItem) {
  container.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "item muted";
    empty.textContent = "No items yet.";
    container.appendChild(empty);
    return;
  }
  for (const row of rows) {
    container.appendChild(renderItem(row));
  }
}

function createActionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ghost";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function getActiveThreadRow() {
  return threadsState.find((row) => row.thread_id === activeThreadId) || null;
}

function getSelectedMode() {
  return workflowModeInput.value.trim() || "plan_90d";
}

function parseWorkflowOverrides() {
  const raw = workflowOverridesInput.value.trim();
  if (!raw) {
    return {};
  }
  const parsed = JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Overrides must be an object mapping stage key to array of skills.");
  }
  return parsed;
}

function renderBrands() {
  clearAndRender(brandsList, brandsState, (row) => {
    const wrapper = document.createElement("div");
    wrapper.className = "item";
    const bar = document.createElement("div");
    bar.className = "inline";

    const select = createActionButton(`${row.brand_id} - ${row.name}`, async () => {
      activeBrandId = row.brand_id;
      activeProjectId = null;
      activeThreadId = null;
      await loadProjects(activeBrandId);
    });
    const edit = createActionButton("Edit", async () => {
      const nextName = window.prompt("Brand name", row.name);
      if (!nextName || nextName.trim() === row.name) {
        return;
      }
      const updated = await patchV2(
        `${ENDPOINT_BRANDS}/${encodeURIComponent(row.brand_id)}`,
        { name: nextName.trim() },
        "brand-edit"
      );
      row.name = updated.name || nextName.trim();
      renderBrands();
    });
    bar.appendChild(select);
    bar.appendChild(edit);
    wrapper.appendChild(bar);
    return wrapper;
  });
}

function renderProjects() {
  const rows = projectsState.filter((row) => row.brand_id === activeBrandId);
  clearAndRender(projectsList, rows, (row) => {
    const wrapper = document.createElement("div");
    wrapper.className = "item";
    const bar = document.createElement("div");
    bar.className = "inline";

    const select = createActionButton(`${row.project_id} - ${row.name}`, async () => {
      activeProjectId = row.project_id;
      activeThreadId = null;
      await loadThreads(activeProjectId);
    });
    const edit = createActionButton("Edit", async () => {
      const nextName = window.prompt("Project name", row.name);
      if (!nextName) {
        return;
      }
      const nextObjective = window.prompt("Objective", row.objective || "");
      if (nextObjective === null) {
        return;
      }
      const nextChannelsRaw = window.prompt(
        "Channels (comma separated)",
        (row.channels || []).join(",")
      );
      if (nextChannelsRaw === null) {
        return;
      }
      const nextDueDate = window.prompt("Due date (YYYY-MM-DD)", row.due_date || "");
      if (nextDueDate === null) {
        return;
      }
      const payload = {
        name: nextName.trim(),
        objective: nextObjective.trim(),
        channels: nextChannelsRaw
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        due_date: nextDueDate.trim() || null,
      };
      const updated = await patchV2(
        `${ENDPOINT_PROJECTS}/${encodeURIComponent(row.project_id)}`,
        payload,
        "project-edit"
      );
      row.name = updated.name || payload.name;
      row.objective = updated.objective || payload.objective;
      row.channels = Array.isArray(updated.channels) ? updated.channels : payload.channels;
      row.due_date = updated.due_date ?? payload.due_date;
      renderProjects();
    });
    bar.appendChild(select);
    bar.appendChild(edit);
    wrapper.appendChild(bar);
    return wrapper;
  });
}

function renderThreads() {
  const rows = threadsState.filter((row) => row.project_id === activeProjectId);
  clearAndRender(threadsList, rows, (row) => {
    const wrapper = document.createElement("div");
    wrapper.className = "item";
    const bar = document.createElement("div");
    bar.className = "inline";
    const modes =
      Array.isArray(row.modes) && row.modes.length ? ` [${row.modes.join(", ")}]` : "";

    const select = createActionButton(`${row.thread_id} - ${row.title}${modes}`, async () => {
      activeThreadId = row.thread_id;
      activeWorkflowRunId = null;
      renderModes();
      await loadThreadWorkspace();
      restartWorkflowPolling();
    });
    const edit = createActionButton("Edit", async () => {
      const nextTitle = window.prompt("Thread title", row.title);
      if (!nextTitle || nextTitle.trim() === row.title) {
        return;
      }
      const updated = await patchV2(
        `${ENDPOINT_THREADS}/${encodeURIComponent(row.thread_id)}`,
        { title: nextTitle.trim() },
        "thread-edit"
      );
      row.title = updated.title || nextTitle.trim();
      renderThreads();
    });
    bar.appendChild(select);
    bar.appendChild(edit);
    wrapper.appendChild(bar);
    return wrapper;
  });
}

function renderModes() {
  const thread = getActiveThreadRow();
  const modes = thread && Array.isArray(thread.modes) ? thread.modes : [];
  clearAndRender(threadModesList, modes, (mode) => {
    const row = document.createElement("div");
    row.className = "item";
    const bar = document.createElement("div");
    bar.className = "inline";
    const label = document.createElement("div");
    label.className = "muted";
    label.textContent = mode;

    const edit = createActionButton("Edit", async () => {
      if (!activeThreadId) {
        return;
      }
      const nextMode = window.prompt("Mode name", mode);
      if (!nextMode || nextMode.trim() === mode) {
        return;
      }
      await postV2(
        `/api/v2/threads/${encodeURIComponent(activeThreadId)}/modes/${encodeURIComponent(mode)}/remove`,
        {},
        "mode-edit-remove"
      );
      await postV2(
        `/api/v2/threads/${encodeURIComponent(activeThreadId)}/modes`,
        { mode: nextMode.trim() },
        "mode-edit-add"
      );
      await loadThreads(activeProjectId);
    });
    const remove = createActionButton("Remove", async () => {
      if (!activeThreadId) {
        return;
      }
      await postV2(
        `/api/v2/threads/${encodeURIComponent(activeThreadId)}/modes/${encodeURIComponent(mode)}/remove`,
        {},
        "mode-remove"
      );
      await loadThreads(activeProjectId);
    });
    bar.appendChild(label);
    bar.appendChild(edit);
    bar.appendChild(remove);
    row.appendChild(bar);
    return row;
  });
}

function renderTimeline(items) {
  clearAndRender(timelineList, items, (itemRow) => {
    const style = TIMELINE_EVENT_STYLE[itemRow.event_type] || {
      icon: "schedule",
      tone: "slate",
    };
    const toneClass = TIMELINE_TONE_CLASS[style.tone] || TIMELINE_TONE_CLASS.slate;
    const node = document.createElement("div");
    node.className = "item";
    const bar = document.createElement("div");
    bar.className = "inline items-center";
    const icon = document.createElement("span");
    icon.className = `material-icons-outlined rounded-full p-1 text-sm ${toneClass}`;
    icon.textContent = style.icon;
    const text = document.createElement("div");
    text.textContent = `${itemRow.event_type} @ ${itemRow.occurred_at}`;
    bar.appendChild(icon);
    bar.appendChild(text);
    node.appendChild(bar);
    return node;
  });
}

function renderTasks(items) {
  clearAndRender(tasksList, items, (task) => {
    const row = document.createElement("div");
    row.className = "item";
    const title = document.createElement("div");
    title.textContent = `${task.task_id} (${task.status})`;
    row.appendChild(title);

    const actions = document.createElement("div");
    actions.className = "inline";
    const commentButton = createActionButton("Comment", async () => {
      const message = window.prompt("Comment for task:", "Need stronger KPI rationale");
      if (!message) {
        return;
      }
      await postV2(
        `/api/v2/tasks/${encodeURIComponent(task.task_id)}/comment`,
        { message },
        "task-comment"
      );
      await loadThreadWorkspace();
    });
    const completeButton = createActionButton("Complete", async () => {
      await postV2(
        `/api/v2/tasks/${encodeURIComponent(task.task_id)}/complete`,
        {},
        "task-complete"
      );
      await loadThreadWorkspace();
    });
    actions.appendChild(commentButton);
    actions.appendChild(completeButton);
    row.appendChild(actions);
    return row;
  });
}

function renderApprovals(items) {
  clearAndRender(approvalsList, items, (approval) => {
    const row = document.createElement("div");
    row.className = "item";
    const text = document.createElement("div");
    text.textContent = `${approval.approval_id} (${approval.status})`;
    row.appendChild(text);
    if (approval.status !== "granted") {
      const grantButton = createActionButton("Grant", async () => {
        await postV2(
          `/api/v2/approvals/${encodeURIComponent(approval.approval_id)}/grant`,
          {},
          "approval-grant"
        );
        await loadThreadWorkspace();
      });
      row.appendChild(grantButton);
    }
    return row;
  });
}

function renderWorkflowProfilePreview() {
  const selectedMode = getSelectedMode();
  const selected = workflowProfilesState.find((item) => item.mode === selectedMode);
  if (!selected) {
    clearAndRender(workflowProfilePreviewList, [], () => document.createElement("div"));
    return;
  }
  clearAndRender(workflowProfilePreviewList, selected.stages || [], (stage) => {
    const row = document.createElement("div");
    row.className = "item";
    const title = document.createElement("div");
    title.textContent = `${stage.key} ${stage.approval_required ? "(approval)" : ""}`;
    const details = document.createElement("div");
    details.className = "muted";
    details.textContent = (stage.skills || []).join(", ");
    row.appendChild(title);
    row.appendChild(details);
    return row;
  });
}

function renderWorkflowRuns(items) {
  clearAndRender(workflowRunsList, items, (run) => {
    const row = document.createElement("div");
    row.className = "item";
    const bar = document.createElement("div");
    bar.className = "inline";
    const label = document.createElement("div");
    const requestedMode = run.requested_mode || run.mode || "plan_90d";
    const effectiveMode = run.effective_mode || run.mode || requestedMode;
    const modeLabel =
      requestedMode === effectiveMode
        ? `mode=${effectiveMode}`
        : `mode=${requestedMode} -> ${effectiveMode}`;
    label.textContent = `${run.run_id} (${run.status}) ${run.completed_stages || 0}/${run.total_stages || 0} ${modeLabel}`;
    bar.appendChild(label);

    const openDetail = createActionButton("Details", async () => {
      activeWorkflowRunId = run.run_id;
      await loadWorkflowRunDetail(run.run_id);
      await loadWorkflowArtifacts(run.run_id);
    });
    bar.appendChild(openDetail);

    if (run.status === "waiting_approval") {
      const resume = createActionButton("Resume", async () => {
        await postV2(
          `/api/v2/workflow-runs/${encodeURIComponent(run.run_id)}/resume`,
          {},
          "workflow-resume"
        );
        await loadWorkflowRunDetail(run.run_id);
      });
      bar.appendChild(resume);
    }
    row.appendChild(bar);
    return row;
  });
}

function renderWorkflowRunDetail(detail) {
  if (!detail) {
    clearAndRender(workflowRunDetailList, [], () => document.createElement("div"));
    return;
  }
  workflowRunDetailList.innerHTML = "";
  const requestedMode = detail.requested_mode || detail.mode || "plan_90d";
  const effectiveMode = detail.effective_mode || detail.mode || requestedMode;
  const runMeta = document.createElement("div");
  runMeta.className = "item";
  runMeta.textContent =
    `${detail.run_id} (${detail.status}) mode=${requestedMode} -> ${effectiveMode}`;
  workflowRunDetailList.appendChild(runMeta);
  if (detail.fallback_applied) {
    const fallbackNotice = document.createElement("div");
    fallbackNotice.className = "item muted";
    fallbackNotice.textContent = "fallback_applied: selected mode was mapped to foundation execution.";
    workflowRunDetailList.appendChild(fallbackNotice);
  }

  const stages = Array.isArray(detail.stages) ? detail.stages : [];
  for (const stage of stages) {
    const row = document.createElement("div");
    row.className = "item";
    const title = document.createElement("div");
    title.textContent = `${stage.stage_id} (${stage.status}) attempts=${stage.attempts}`;
    row.appendChild(title);
    const skills = document.createElement("div");
    skills.className = "muted";
    skills.textContent = (stage.skills || []).join(", ");
    row.appendChild(skills);
    if (stage.error_code) {
      const errorLine = document.createElement("div");
      errorLine.className = "muted";
      const retryable = stage.retryable ? "retryable" : "non-retryable";
      errorLine.textContent =
        `error_code=${stage.error_code} error_message=${stage.error_message || ""} ${retryable}`;
      row.appendChild(errorLine);
    }
    workflowRunDetailList.appendChild(row);
  }

  const pendingApprovals = detail.pending_approvals || [];
  for (const approval of pendingApprovals) {
    const row = document.createElement("div");
    row.className = "item";
    const label = document.createElement("div");
    label.textContent = `Pending approval: ${approval.approval_id}`;
    row.appendChild(label);
    const actions = document.createElement("div");
    actions.className = "inline";
    actions.appendChild(
      createActionButton("Grant", async () => {
        await postV2(
          `/api/v2/approvals/${encodeURIComponent(approval.approval_id)}/grant`,
          {},
          "workflow-detail-grant"
        );
        await loadWorkflowRunDetail(detail.run_id);
      })
    );
    actions.appendChild(
      createActionButton("Resume", async () => {
        await postV2(
          `/api/v2/workflow-runs/${encodeURIComponent(detail.run_id)}/resume`,
          {},
          "workflow-detail-resume"
        );
        await loadWorkflowRunDetail(detail.run_id);
      })
    );
    row.appendChild(actions);
    workflowRunDetailList.appendChild(row);
  }
}

function renderWorkflowArtifacts(stages) {
  clearAndRender(workflowArtifactsList, stages, (stage) => {
    const row = document.createElement("div");
    row.className = "item";
    const title = document.createElement("div");
    title.textContent = `${stage.stage_key} (${stage.status})`;
    row.appendChild(title);
    const bar = document.createElement("div");
    bar.className = "inline";
    for (const artifact of stage.artifacts || []) {
      bar.appendChild(
        createActionButton(artifact.path, async () => {
          await loadWorkflowArtifactContent(stage.stage_dir, artifact.path);
        })
      );
    }
    row.appendChild(bar);
    return row;
  });
}

async function loadWorkflowProfiles() {
  const body = await fetchJson(ENDPOINT_WORKFLOW_PROFILES);
  workflowProfilesState.length = 0;
  workflowProfilesState.push(...(body.profiles || []));
  if (!workflowModeInput.value.trim() && workflowProfilesState.length) {
    workflowModeInput.value = workflowProfilesState[0].mode;
  }
  renderWorkflowProfilePreview();
}

async function loadWorkflowRuns() {
  if (!activeThreadId) {
    activeWorkflowRunId = null;
    renderWorkflowRuns([]);
    renderWorkflowRunDetail(null);
    renderWorkflowArtifacts([]);
    workflowArtifactPreview.textContent = "Select an artifact to preview.";
    return;
  }
  const body = await fetchJson(
    `/api/v2/threads/${encodeURIComponent(activeThreadId)}/workflow-runs`
  );
  const runs = body.runs || [];
  renderWorkflowRuns(runs);
  if (!runs.length) {
    activeWorkflowRunId = null;
    renderWorkflowRunDetail(null);
    renderWorkflowArtifacts([]);
    workflowArtifactPreview.textContent = "Select an artifact to preview.";
    return;
  }
  if (!activeWorkflowRunId || !runs.some((row) => row.run_id === activeWorkflowRunId)) {
    activeWorkflowRunId = runs[0].run_id;
  }
  await loadWorkflowRunDetail(activeWorkflowRunId);
  await loadWorkflowArtifacts(activeWorkflowRunId);
}

async function loadWorkflowRunDetail(runId) {
  if (!runId) {
    renderWorkflowRunDetail(null);
    return;
  }
  const detail = await fetchJson(`/api/v2/workflow-runs/${encodeURIComponent(runId)}`);
  renderWorkflowRunDetail(detail);
  renderStudioRun(detail);
}

async function loadWorkflowArtifacts(runId) {
  if (!runId) {
    renderWorkflowArtifacts([]);
    workflowArtifactPreview.textContent = "Select an artifact to preview.";
    return;
  }
  const body = await fetchJson(
    `/api/v2/workflow-runs/${encodeURIComponent(runId)}/artifacts`
  );
  renderWorkflowArtifacts(body.stages || []);
}

async function loadWorkflowArtifactContent(stageDir, artifactPath) {
  if (!activeWorkflowRunId) {
    return;
  }
  const query = new URLSearchParams({
    stage_dir: stageDir,
    artifact_path: artifactPath,
  });
  const body = await fetchJson(
    `/api/v2/workflow-runs/${encodeURIComponent(activeWorkflowRunId)}/artifact-content?${query.toString()}`
  );
  workflowArtifactPreview.textContent = body.content || "";
  if (studioArtifactPreview) studioArtifactPreview.textContent = body.content || "";
}

async function loadBrands() {
  const body = await fetchJson(ENDPOINT_BRANDS);
  brandsState.length = 0;
  brandsState.push(...body.brands || []);

  if (!activeBrandId || !brandsState.some((row) => row.brand_id === activeBrandId)) {
    activeBrandId = brandsState[0]?.brand_id || null;
  }
  renderBrands();
  if (activeBrandId) {
    await loadProjects(activeBrandId);
    return;
  }

  projectsState.length = 0;
  threadsState.length = 0;
  activeProjectId = null;
  activeThreadId = null;
  renderProjects();
  renderThreads();
  renderModes();
  renderTimeline([]);
  renderTasks([]);
  renderApprovals([]);
  renderWorkflowRuns([]);
  renderWorkflowRunDetail(null);
  renderWorkflowArtifacts([]);
}

async function loadProjects(brandId) {
  if (!brandId) {
    projectsState.length = 0;
    activeProjectId = null;
    renderProjects();
    await loadThreads(null);
    return;
  }
  const body = await fetchJson(`${ENDPOINT_PROJECTS}?brand_id=${encodeURIComponent(brandId)}`);
  projectsState.length = 0;
  projectsState.push(...(body.projects || []));

  if (!activeProjectId || !projectsState.some((row) => row.project_id === activeProjectId)) {
    activeProjectId = projectsState[0]?.project_id || null;
  }
  renderProjects();
  await loadThreads(activeProjectId);
}

async function loadThreads(projectId) {
  if (!projectId) {
    threadsState.length = 0;
    activeThreadId = null;
    renderThreads();
    renderModes();
    await loadThreadWorkspace();
    return;
  }
  const body = await fetchJson(`${ENDPOINT_THREADS}?project_id=${encodeURIComponent(projectId)}`);
  threadsState.length = 0;
  threadsState.push(...(body.threads || []));

  if (!activeThreadId || !threadsState.some((row) => row.thread_id === activeThreadId)) {
    activeThreadId = threadsState[0]?.thread_id || null;
  }
  renderThreads();
  renderModes();
  await loadThreadWorkspace();
  restartWorkflowPolling();
}

async function loadThreadWorkspace() {
  if (!activeThreadId) {
    activeWorkflowRunId = null;
    renderModes();
    renderTimeline([]);
    renderTasks([]);
    renderApprovals([]);
    renderWorkflowRuns([]);
    renderWorkflowRunDetail(null);
    renderWorkflowArtifacts([]);
    workflowArtifactPreview.textContent = "Select an artifact to preview.";
    return;
  }

  const [timeline, tasks, approvals] = await Promise.all([
    fetchJson(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/timeline`),
    fetchJson(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/tasks`),
    fetchJson(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/approvals`),
  ]);
  renderModes();
  renderTimeline(timeline.items || []);
  renderTasks(tasks.items || []);
  renderApprovals(approvals.items || []);
  await loadWorkflowRuns();
}

function restartWorkflowPolling() {
  if (workflowPollTimer) {
    window.clearInterval(workflowPollTimer);
    workflowPollTimer = null;
  }
  if (!activeThreadId) {
    return;
  }
  workflowPollTimer = window.setInterval(async () => {
    if (!activeThreadId) {
      return;
    }
    try {
      await loadWorkflowRuns();
    } catch (error) {
      console.error(error);
    }
  }, 2000);
}

brandForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = brandNameInput.value.trim();
  if (!name) {
    return;
  }
  const response = await postV2(ENDPOINT_BRANDS, { name }, "brand-create");
  const brand_id = response.brand_id || buildEntityId("b");
  brandsState.unshift({ brand_id, name });
  activeBrandId = brand_id;
  activeProjectId = null;
  activeThreadId = null;
  brandForm.reset();
  renderBrands();
  await loadProjects(activeBrandId);
});

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeBrandId) {
    window.alert("Create/select a brand first.");
    return;
  }
  const name = projectNameInput.value.trim();
  if (!name) {
    return;
  }
  const channels = projectChannelsInput.value
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const payload = {
    brand_id: activeBrandId,
    name,
    objective: projectObjectiveInput.value.trim(),
    channels,
    due_date: projectDueDateInput.value.trim() || null,
  };
  const response = await postV2(ENDPOINT_PROJECTS, payload, "project-create");
  const project_id = response.project_id || buildEntityId("p");
  projectsState.unshift({ project_id, ...payload });
  activeProjectId = project_id;
  activeThreadId = null;
  projectForm.reset();
  renderProjects();
  await loadThreads(activeProjectId);
});

threadCreateButton.addEventListener("click", async () => {
  if (!activeBrandId || !activeProjectId) {
    window.alert("Create/select brand and project first.");
    return;
  }
  const title = threadTitleInput.value.trim() || "Planning Thread";
  const response = await postV2(
    ENDPOINT_THREADS,
    {
      project_id: activeProjectId,
      brand_id: activeBrandId,
      title,
    },
    "thread-create"
  );
  const thread_id = response.thread_id || buildEntityId("t");
  threadsState.unshift({
    thread_id,
    project_id: activeProjectId,
    brand_id: activeBrandId,
    title,
    status: "open",
    modes: [],
  });
  activeThreadId = thread_id;
  renderThreads();
  renderModes();
  await loadThreadWorkspace();
  restartWorkflowPolling();
});

threadModeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeThreadId) {
    window.alert("Create/select a thread first.");
    return;
  }
  const mode = threadModeInput.value.trim();
  if (!mode) {
    return;
  }
  await postV2(
    `/api/v2/threads/${encodeURIComponent(activeThreadId)}/modes`,
    { mode },
    "thread-mode"
  );
  threadModeForm.reset();
  await loadThreads(activeProjectId);
});

workflowModeInput.addEventListener("change", () => {
  renderWorkflowProfilePreview();
});

workflowRunForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeThreadId) {
    window.alert("Create/select a thread first.");
    return;
  }
  const request_text = workflowRequestInput.value.trim();
  if (!request_text) {
    return;
  }
  let skill_overrides = {};
  try {
    skill_overrides = parseWorkflowOverrides();
  } catch (error) {
    window.alert(error.message || "Invalid overrides JSON.");
    return;
  }
  const payload = {
    request_text,
    mode: getSelectedMode(),
    skill_overrides,
  };
  const started = await postV2(
    `/api/v2/threads/${encodeURIComponent(activeThreadId)}/workflow-runs`,
    payload,
    "workflow-run"
  );
  activeWorkflowRunId = started.run_id || null;
  workflowRequestInput.value = "";
  await loadWorkflowRuns();
  restartWorkflowPolling();
});

if (studioDevModeToggle) {
  studioDevModeToggle.addEventListener("change", () => {
    setDevMode(studioDevModeToggle.checked);
  });
}

loadDevMode();

async function startStudioPlan() {
  if (!activeBrandId || !activeProjectId) {
    setUiError("Select a brand and project first.");
    return;
  }
  const title = (studioPlanTitleInput?.value || "").trim() || "New plan";
  const request_text = (studioPlanBriefInput?.value || "").trim();
  if (!request_text) return;

  const created = await postV2(
    ENDPOINT_THREADS,
    { project_id: activeProjectId, brand_id: activeBrandId, title },
    "studio-thread-create"
  );
  const thread_id = created.thread_id;
  await postV2(
    `/api/v2/threads/${encodeURIComponent(thread_id)}/modes`,
    { mode: studioSelectedMode },
    "studio-mode"
  );
  const started = await postV2(
    `/api/v2/threads/${encodeURIComponent(thread_id)}/workflow-runs`,
    { request_text, mode: studioSelectedMode, skill_overrides: {} },
    "studio-workflow-run"
  );

  activeThreadId = thread_id;
  activeWorkflowRunId = started.run_id || null;
  closeStudioWizard();
  await loadThreads(activeProjectId);
}

if (studioCreatePlanButton) studioCreatePlanButton.addEventListener("click", openStudioWizard);
if (studioWizardCancel) studioWizardCancel.addEventListener("click", closeStudioWizard);
if (studioWizardForm) {
  studioWizardForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await startStudioPlan();
  });
}

Promise.all([loadWorkflowProfiles(), loadBrands()])
  .then(() => {
    restartWorkflowPolling();
  })
  .catch((error) => {
    console.error(error);
  });
