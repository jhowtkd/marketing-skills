const API_BASE = "/api/v1";
const ENDPOINT_BRANDS = "/api/v1/brands";
const ENDPOINT_PRODUCTS = "/api/v1/products";
const ENDPOINT_CHAT = "/api/v1/chat";
const ENDPOINT_RUN_FOUNDATION = "/api/v1/runs/foundation";
const THREAD_STORAGE_KEY = "vm_webapp_thread_id";

const brandSelect = document.getElementById("brand-select");
const productSelect = document.getElementById("product-select");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const startRunButton = document.getElementById("start-foundation-run");
const runStatus = document.getElementById("run-status");

function getThreadId() {
  const existing = localStorage.getItem(THREAD_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const generated = `thread-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(THREAD_STORAGE_KEY, generated);
  return generated;
}

function appendMessage(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = `message message-${role}`;
  wrapper.textContent = `${role}: ${content}`;
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
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

async function loadBrands() {
  const body = await fetchJson(ENDPOINT_BRANDS);
  populateSelect(brandSelect, body.brands || [], "brand_id", "name");
  if (brandSelect.value) {
    await loadProducts(brandSelect.value);
  }
}

async function loadProducts(brandId) {
  if (!brandId) {
    populateSelect(productSelect, [], "product_id", "name");
    return;
  }
  const body = await fetchJson(`${ENDPOINT_PRODUCTS}?brand_id=${encodeURIComponent(brandId)}`);
  populateSelect(productSelect, body.products || [], "product_id", "name");
}

async function startFoundationRun(userRequest) {
  const payload = {
    brand_id: brandSelect.value,
    product_id: productSelect.value,
    thread_id: getThreadId(),
    user_request: userRequest,
  };
  const body = await fetchJson(ENDPOINT_RUN_FOUNDATION, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setRunStatus(`Run ${body.run_id} status: ${body.status}`);
  return body;
}

async function sendChatMessage(message) {
  const payload = {
    brand_id: brandSelect.value,
    product_id: productSelect.value,
    thread_id: getThreadId(),
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
  brandSelect.addEventListener("change", async () => {
    await loadProducts(brandSelect.value);
  });
  chatForm.addEventListener("submit", handleChatSubmit);
  startRunButton.addEventListener("click", handleStartButtonClick);

  try {
    await loadBrands();
  } catch (error) {
    setRunStatus(`Failed to load brands: ${error.message}`, true);
  }
}

bootstrap();
