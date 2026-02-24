const API_BASE = "/api/v1";
const ENDPOINT_BRANDS = "/api/v1/brands";
const ENDPOINT_PRODUCTS = "/api/v1/products";
const ENDPOINT_THREADS = "/api/v1/threads";
const ENDPOINT_CHAT = "/api/v1/chat";
const ENDPOINT_RUN_FOUNDATION = "/api/v1/runs/foundation";
const ENDPOINT_RUNS = "/api/v1/runs";

const brandTabs = document.getElementById("brand-tabs");
const productSelect = document.getElementById("product-select");
const threadsList = document.getElementById("threads-list");
const newThreadButton = document.getElementById("new-thread-button");
const closeThreadButton = document.getElementById("close-thread-button");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const startRunButton = document.getElementById("start-foundation-run");
const runStatus = document.getElementById("run-status");
const runsTimeline = document.getElementById("runs-timeline");

let activeBrandId = "";
let activeThreadId = "";
let activeThreads = [];
let cachedBrands = [];
let activeRunId = null;
let runsEventSource = null;
const approvingRunIds = new Set();

function appendMessage(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = `message message-${role}`;
  wrapper.textContent = `${role}: ${content}`;
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderMessages(messages) {
  chatMessages.innerHTML = "";
  if (!messages.length) {
    const empty = document.createElement("div");
    empty.className = "placeholder";
    empty.textContent = "No messages yet.";
    chatMessages.appendChild(empty);
    return;
  }
  for (const message of messages) {
    appendMessage(message.role || "system", message.content || "");
  }
}

function appendRunEvent(event) {
  const line = document.createElement("div");
  line.className = "run-event";
  const stage = event.stage_id ? ` (${event.stage_id})` : "";
  line.textContent = `${event.type || "event"}${stage}`;
  runsTimeline.prepend(line);
}

function setRunStatus(message, isError = false) {
  runStatus.textContent = message;
  runStatus.style.color = isError ? "#b91c1c" : "#6b7280";
}

async function fetchJson(url, options = undefined) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail || `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return body;
}

function populateSelect(selectElement, rows, valueKey, labelKey) {
  selectElement.innerHTML = "";
  if (!rows.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No data";
    selectElement.appendChild(option);
    return;
  }
  for (const row of rows) {
    const option = document.createElement("option");
    option.value = row[valueKey];
    option.textContent = row[labelKey];
    selectElement.appendChild(option);
  }
}

function renderBrandTabs(brands) {
  brandTabs.innerHTML = "";
  if (!brands.length) {
    const empty = document.createElement("div");
    empty.className = "placeholder";
    empty.textContent = "No brands.";
    brandTabs.appendChild(empty);
    return;
  }

  for (const brand of brands) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "thread-item";
    if (brand.brand_id === activeBrandId) {
      button.classList.add("active");
    }
    button.textContent = brand.name;
    button.addEventListener("click", async () => {
      if (activeBrandId === brand.brand_id) {
        return;
      }
      activeBrandId = brand.brand_id;
      renderBrandTabs(cachedBrands);
      await loadProducts(activeBrandId);
      await loadThreads();
    });
    brandTabs.appendChild(button);
  }
}

async function loadBrands() {
  const body = await fetchJson(ENDPOINT_BRANDS);
  cachedBrands = body.brands || [];
  if (!cachedBrands.length) {
    activeBrandId = "";
    renderBrandTabs(cachedBrands);
    populateSelect(productSelect, [], "product_id", "name");
    renderThreads([]);
    renderMessages([]);
    return;
  }
  if (!activeBrandId || !cachedBrands.some((brand) => brand.brand_id === activeBrandId)) {
    activeBrandId = cachedBrands[0].brand_id;
  }
  renderBrandTabs(cachedBrands);
  await loadProducts(activeBrandId);
}

async function loadProducts(brandId) {
  if (!brandId) {
    populateSelect(productSelect, [], "product_id", "name");
    return;
  }
  const body = await fetchJson(`${ENDPOINT_PRODUCTS}?brand_id=${encodeURIComponent(brandId)}`);
  populateSelect(productSelect, body.products || [], "product_id", "name");
}

function renderThreads(threads) {
  activeThreads = threads;
  threadsList.innerHTML = "";
  if (!threads.length) {
    activeThreadId = "";
    const empty = document.createElement("div");
    empty.className = "placeholder";
    empty.textContent = "No threads.";
    threadsList.appendChild(empty);
    return;
  }

  for (const thread of threads) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "thread-item";
    if (thread.thread_id === activeThreadId) {
      item.classList.add("active");
    }
    item.textContent = `${thread.title} (${thread.status})`;
    item.addEventListener("click", () => selectThread(thread.thread_id));
    threadsList.appendChild(item);
  }
}

function getActiveThread() {
  return activeThreads.find((thread) => thread.thread_id === activeThreadId) || null;
}

function syncWorkspaceActions(activeThread) {
  if (!activeThread || activeThread.status === "closed") {
    chatInput.disabled = true;
    startRunButton.disabled = true;
    return;
  }
  chatInput.disabled = false;
  startRunButton.disabled = false;
}

async function loadThreads() {
  if (!activeBrandId || !productSelect.value) {
    renderThreads([]);
    syncWorkspaceActions(null);
    renderMessages([]);
    return;
  }
  const body = await fetchJson(
    `${ENDPOINT_THREADS}?brand_id=${encodeURIComponent(activeBrandId)}&product_id=${encodeURIComponent(productSelect.value)}`
  );
  const threads = body.threads || [];
  if (!threads.some((thread) => thread.thread_id === activeThreadId)) {
    activeThreadId = threads[0] ? threads[0].thread_id : "";
  }
  renderThreads(threads);
  syncWorkspaceActions(getActiveThread());
  await loadThreadMessages();
  await loadRuns();
}

function selectThread(threadId) {
  activeThreadId = threadId;
  renderThreads(activeThreads);
  syncWorkspaceActions(getActiveThread());
  loadThreadMessages().catch((error) => appendMessage("system", error.message));
  loadRuns().catch((error) => setRunStatus(error.message, true));
}

async function loadThreadMessages() {
  if (!activeThreadId) {
    renderMessages([]);
    return;
  }
  const body = await fetchJson(
    `${ENDPOINT_THREADS}/${encodeURIComponent(activeThreadId)}/messages`
  );
  renderMessages(body.messages || []);
}

function renderRuns(runs) {
  runsTimeline.innerHTML = "";
  if (!runs.length) {
    const empty = document.createElement("div");
    empty.className = "placeholder";
    empty.textContent = "No runs yet.";
    runsTimeline.appendChild(empty);
    return;
  }

  for (const run of runs) {
    const runCard = document.createElement("div");
    runCard.className = "run-card";

    const title = document.createElement("div");
    title.className = "run-title";
    title.textContent = `${run.run_id} (${run.status})`;
    runCard.appendChild(title);

    const stageList = document.createElement("ul");
    stageList.className = "stage-list";
    for (const stage of run.stages || []) {
      const item = document.createElement("li");
      item.textContent = `${stage.stage_id}: ${stage.status}`;
      if (stage.status === "waiting_approval") {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "Approve";
        button.addEventListener("click", async () => {
          await approveRun(run.run_id, button);
        });
        item.append(" ");
        item.appendChild(button);
      }
      stageList.appendChild(item);
    }
    runCard.appendChild(stageList);
    runsTimeline.appendChild(runCard);
  }
}

function connectRunEvents(runId) {
  if (!runId) {
    return;
  }
  if (runsEventSource) {
    runsEventSource.close();
  }
  const eventsUrl = `${API_BASE}/runs/${encodeURIComponent(runId)}/events?max_events=500`; // /events
  runsEventSource = new EventSource(eventsUrl); // new EventSource
  runsEventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      appendRunEvent(payload);
      if (
        payload.type === "stage_completed" ||
        payload.type === "approval_required" ||
        payload.type === "run_completed"
      ) {
        loadRuns().catch((error) => setRunStatus(error.message, true));
      }
    } catch (_error) {
      appendRunEvent({ type: "event", stage_id: "" });
    }
  };
  runsEventSource.onerror = () => {
    setRunStatus("Run stream disconnected; retrying...", true);
    runsEventSource.close();
    runsEventSource = null;
    setTimeout(() => {
      if (activeRunId === runId) {
        connectRunEvents(runId);
      }
    }, 1000);
  };
}

async function loadRuns() {
  if (!activeThreadId) {
    renderRuns([]);
    activeRunId = null;
    setRunStatus("No active run.");
    return;
  }

  const body = await fetchJson(`${ENDPOINT_RUNS}?thread_id=${encodeURIComponent(activeThreadId)}`);
  const runs = body.runs || [];
  renderRuns(runs);
  if (!runs.length) {
    activeRunId = null;
    setRunStatus("No active run.");
    return;
  }

  const latest = runs[0];
  setRunStatus(`Run ${latest.run_id} status: ${latest.status}`);
  if (activeRunId !== latest.run_id) {
    activeRunId = latest.run_id;
    connectRunEvents(activeRunId);
  }
}

async function approveRun(runId, buttonEl = null) {
  if (approvingRunIds.has(runId)) {
    return;
  }
  approvingRunIds.add(runId);
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Approving...";
  }

  try {
    const body = await fetchJson(`${API_BASE}/runs/${encodeURIComponent(runId)}/approve`, {
      method: "POST",
    }); // /approve
    setRunStatus(`Run ${body.run_id} status: ${body.status}`);
    await loadRuns();
  } catch (error) {
    setRunStatus(`Approve failed: ${error.message}`, true);
  } finally {
    approvingRunIds.delete(runId);
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = "Approve";
    }
  }
}

async function createThread() {
  if (!activeBrandId || !productSelect.value) {
    return;
  }
  const body = await fetchJson(ENDPOINT_THREADS, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      brand_id: activeBrandId,
      product_id: productSelect.value,
    }),
  });
  activeThreadId = body.thread_id;
  await loadThreads();
}

async function closeActiveThread() {
  if (!activeThreadId) {
    return;
  }
  await fetchJson(`${ENDPOINT_THREADS}/${encodeURIComponent(activeThreadId)}/close`, {
    method: "POST",
  });
  await loadThreads();
}

async function startFoundationRun(userRequest) {
  if (!activeThreadId) {
    throw new Error("Select a thread first.");
  }
  const payload = {
    brand_id: activeBrandId,
    product_id: productSelect.value,
    thread_id: activeThreadId,
    user_request: userRequest,
  };
  const body = await fetchJson(ENDPOINT_RUN_FOUNDATION, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setRunStatus(`Run ${body.run_id} status: ${body.status}`);
  await loadRuns();
  return body;
}

async function sendChatMessage(message) {
  if (!activeThreadId) {
    throw new Error("Select a thread first.");
  }
  const payload = {
    brand_id: activeBrandId,
    product_id: productSelect.value,
    thread_id: activeThreadId,
    message,
  };
  return fetchJson(ENDPOINT_CHAT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function handleChatSubmit(event) {
  event.preventDefault();
  const raw = chatInput.value.trim();
  if (!raw) {
    return;
  }

  if (raw.startsWith("/run foundation")) {
    try {
      const run = await startFoundationRun(raw);
      appendMessage("system", `Foundation run started: ${run.run_id}`);
    } catch (error) {
      appendMessage("system", `Failed to start run: ${error.message}`);
      setRunStatus(error.message, true);
    }
    chatInput.value = "";
    return;
  }

  appendMessage("user", raw);
  try {
    const out = await sendChatMessage(raw);
    appendMessage("assistant", out.assistant_message || "(empty)");
  } catch (error) {
    appendMessage("system", `Chat failed: ${error.message}`);
  }
  chatInput.value = "";
}

async function handleStartButtonClick() {
  try {
    const run = await startFoundationRun("Start Foundation Run button");
    appendMessage("system", `Foundation run started: ${run.run_id}`);
  } catch (error) {
    appendMessage("system", `Failed to start run: ${error.message}`);
    setRunStatus(error.message, true);
  }
}

async function bootstrap() {
  syncWorkspaceActions(null);
  productSelect.addEventListener("change", async () => {
    await loadThreads();
  });
  newThreadButton.addEventListener("click", () => {
    createThread().catch((error) => appendMessage("system", error.message));
  });
  closeThreadButton.addEventListener("click", () => {
    closeActiveThread().catch((error) => appendMessage("system", error.message));
  });
  chatForm.addEventListener("submit", handleChatSubmit);
  startRunButton.addEventListener("click", handleStartButtonClick);

  try {
    await loadBrands();
    await loadThreads();
  } catch (error) {
    setRunStatus(`Failed to initialize UI: ${error.message}`, true);
  }
}

bootstrap();
