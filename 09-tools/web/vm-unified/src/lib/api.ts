const API_BASE = '/api/v2'

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail = payload.detail || `Request failed (${response.status})`
    throw new APIError(detail, response.status, detail)
  }

  return response.json() as T
}

export async function get<T>(path: string): Promise<T> {
  return fetchJson<T>(`${API_BASE}${path}`)
}

export async function post<T>(path: string, payload: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  return fetchJson<T>(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
}

export async function patch<T>(path: string, payload: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  return fetchJson<T>(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload),
  })
}

export async function del(path: string, idempotencyKey?: string): Promise<void> {
  const headers: Record<string, string> = {}
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers,
  })
  
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new APIError(payload.detail || `Delete failed (${response.status})`, response.status)
  }
}

export function buildIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
