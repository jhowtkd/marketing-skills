const ENDPOINT_BRANDS = "/api/v2/brands";
const ENDPOINT_PROJECTS = "/api/v2/projects";
const ENDPOINT_THREADS = "/api/v2/threads";

const brandForm = document.getElementById("brand-create-form");
const brandIdInput = document.getElementById("brand-id-input");
const brandNameInput = document.getElementById("brand-name-input");
const brandsList = document.getElementById("brands-list");

const projectForm = document.getElementById("project-create-form");
const projectIdInput = document.getElementById("project-id-input");
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
const timelineList = document.getElementById("timeline-list");
const tasksList = document.getElementById("tasks-list");
const approvalsList = document.getElementById("approvals-list");

let activeBrandId = null;
let activeProjectId = null;
let activeThreadId = null;

const brandsState = [];
const projectsState = [];
const threadsState = [];

function buildIdempotencyKey(prefix) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail || `Request failed (${response.status})`;
    throw new Error(detail);
  }
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
    const node = renderItem(row);
    container.appendChild(node);
  }
}

function renderBrands() {
  clearAndRender(brandsList, brandsState, (row) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "item ghost";
    item.textContent = `${row.brand_id} - ${row.name}`;
    item.addEventListener("click", async () => {
      activeBrandId = row.brand_id;
      await loadProjects(activeBrandId);
    });
    return item;
  });
}

function renderProjects() {
  const rows = projectsState.filter((row) => row.brand_id === activeBrandId);
  clearAndRender(projectsList, rows, (row) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "item ghost";
    item.textContent = `${row.project_id} - ${row.name}`;
    item.addEventListener("click", () => {
      activeProjectId = row.project_id;
    });
    return item;
  });
}

function renderThreads() {
  const rows = threadsState.filter((row) => row.project_id === activeProjectId);
  clearAndRender(threadsList, rows, (row) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "item ghost";
    item.textContent = `${row.thread_id} - ${row.title}`;
    item.addEventListener("click", async () => {
      activeThreadId = row.thread_id;
      await loadThreadWorkspace();
    });
    return item;
  });
}

async function loadProjects(brandId) {
  if (!brandId) {
    renderProjects();
    return;
  }
  const body = await fetchJson(`${ENDPOINT_PROJECTS}?brand_id=${encodeURIComponent(brandId)}`);
  projectsState.length = 0;
  projectsState.push(...(body.projects || []));
  if (!activeProjectId && projectsState.length) {
    activeProjectId = projectsState[0].project_id;
  }
  renderProjects();
  renderThreads();
}

function renderTimeline(items) {
  clearAndRender(timelineList, items, (itemRow) => {
    const node = document.createElement("div");
    node.className = "item";
    node.textContent = `${itemRow.event_type} @ ${itemRow.occurred_at}`;
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

    const commentButton = document.createElement("button");
    commentButton.type = "button";
    commentButton.className = "ghost";
    commentButton.textContent = "Comment";
    commentButton.addEventListener("click", async () => {
      const message = window.prompt("Comment for task:", "Need stronger KPI rationale");
      if (!message) {
        return;
      }
      await postV2(`/api/v2/tasks/${encodeURIComponent(task.task_id)}/comment`, { message }, "task-comment");
      await loadThreadWorkspace();
    });
    actions.appendChild(commentButton);

    const completeButton = document.createElement("button");
    completeButton.type = "button";
    completeButton.className = "ghost";
    completeButton.textContent = "Complete";
    completeButton.addEventListener("click", async () => {
      await postV2(`/api/v2/tasks/${encodeURIComponent(task.task_id)}/complete`, {}, "task-complete");
      await loadThreadWorkspace();
    });
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
      const grantButton = document.createElement("button");
      grantButton.type = "button";
      grantButton.className = "ghost";
      grantButton.textContent = "Grant";
      grantButton.addEventListener("click", async () => {
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

async function loadThreadWorkspace() {
  if (!activeThreadId) {
    renderTimeline([]);
    renderTasks([]);
    renderApprovals([]);
    return;
  }
  const timeline = await fetchJson(
    `/api/v2/threads/${encodeURIComponent(activeThreadId)}/timeline`
  );
  const tasks = await fetchJson(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/tasks`);
  const approvals = await fetchJson(
    `/api/v2/threads/${encodeURIComponent(activeThreadId)}/approvals`
  );
  renderTimeline(timeline.items || []);
  renderTasks(tasks.items || []);
  renderApprovals(approvals.items || []);
}

brandForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const brand_id = brandIdInput.value.trim();
  const name = brandNameInput.value.trim();
  if (!brand_id || !name) {
    return;
  }
  await postV2(ENDPOINT_BRANDS, { brand_id, name }, "brand-create");
  brandsState.push({ brand_id, name });
  activeBrandId = brand_id;
  renderBrands();
  brandForm.reset();
});

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeBrandId) {
    window.alert("Create/select a brand first.");
    return;
  }
  const project_id = projectIdInput.value.trim();
  const name = projectNameInput.value.trim();
  if (!project_id || !name) {
    return;
  }
  const channels = projectChannelsInput.value
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const payload = {
    project_id,
    brand_id: activeBrandId,
    name,
    objective: projectObjectiveInput.value.trim(),
    channels,
    due_date: projectDueDateInput.value.trim() || null,
  };
  await postV2(ENDPOINT_PROJECTS, payload, "project-create");
  await loadProjects(activeBrandId);
  activeProjectId = project_id;
  projectForm.reset();
  renderThreads();
});

threadCreateButton.addEventListener("click", async () => {
  if (!activeBrandId || !activeProjectId) {
    window.alert("Create/select brand and project first.");
    return;
  }
  const title = threadTitleInput.value.trim() || "Planning Thread";
  const thread_id = `t-${Date.now().toString(36)}`;
  await postV2(
    ENDPOINT_THREADS,
    {
      thread_id,
      project_id: activeProjectId,
      brand_id: activeBrandId,
      title,
    },
    "thread-create"
  );
  threadsState.unshift({ thread_id, project_id: activeProjectId, title });
  activeThreadId = thread_id;
  renderThreads();
  await loadThreadWorkspace();
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
  await loadThreadWorkspace();
});

renderBrands();
renderProjects();
renderThreads();
loadThreadWorkspace().catch(() => undefined);
