type JsonObject = Record<string, unknown>;

function buildIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

async function parseJsonSafe(response: Response): Promise<JsonObject> {
  try {
    const data = await response.json();
    if (data && typeof data === "object" && !Array.isArray(data)) return data as JsonObject;
  } catch {
    // ignore
  }
  return {};
}

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (response.ok) {
    return (await response.json()) as T;
  }
  const body = await parseJsonSafe(response);
  const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
  throw new Error(detail);
}

export async function postJson<T>(
  url: string,
  payload: unknown,
  prefix: string
): Promise<T> {
  return fetchJson<T>(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": buildIdempotencyKey(prefix),
    },
    body: JSON.stringify(payload),
  });
}

export async function patchJson<T>(
  url: string,
  payload: unknown,
  prefix: string
): Promise<T> {
  return fetchJson<T>(url, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": buildIdempotencyKey(prefix),
    },
    body: JSON.stringify(payload),
  });
}

