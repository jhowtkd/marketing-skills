const ENDPOINT_BRANDS = "/api/v2/brands";
const ENDPOINT_PROJECTS = "/api/v2/projects";
const ENDPOINT_THREADS = "/api/v2/threads";

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

let activeBrandId = null;
let activeProjectId = null;
let activeThreadId = null;

const brandsState = [];
const projectsState = [];
const threadsState = [];

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
    const node = renderItem(row);
    container.appendChild(node);
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

    const modes = Array.isArray(row.modes) && row.modes.length ? ` [${row.modes.join(", ")}]` : "";
    const select = createActionButton(`${row.thread_id} - ${row.title}${modes}`, async () => {
      activeThreadId = row.thread_id;
      renderModes();
      await loadThreadWorkspace();
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

async function loadBrands() {
  const body = await fetchJson(ENDPOINT_BRANDS);
  brandsState.length = 0;
  brandsState.push(...(body.brands || []));

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

    const commentButton = createActionButton("Comment", async () => {
      const message = window.prompt("Comment for task:", "Need stronger KPI rationale");
      if (!message) {
        return;
      }
      await postV2(`/api/v2/tasks/${encodeURIComponent(task.task_id)}/comment`, { message }, "task-comment");
      await loadThreadWorkspace();
    });
    actions.appendChild(commentButton);

    const completeButton = createActionButton("Complete", async () => {
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
      const grantButton = createActionButton("Grant", async () => {
        await postV2(`/api/v2/approvals/${encodeURIComponent(approval.approval_id)}/grant`, {}, "approval-grant");
        await loadThreadWorkspace();
      });
      row.appendChild(grantButton);
    }
    return row;
  });
}

async function loadThreadWorkspace() {
  if (!activeThreadId) {
    renderModes();
    renderTimeline([]);
    renderTasks([]);
    renderApprovals([]);
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

  await postV2(`/api/v2/threads/${encodeURIComponent(activeThreadId)}/modes`, { mode }, "thread-mode");
  threadModeForm.reset();
  await loadThreads(activeProjectId);
});

loadBrands().catch((error) => {
  console.error(error);
});
