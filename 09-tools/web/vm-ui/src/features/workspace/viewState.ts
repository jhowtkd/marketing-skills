export type WorkspaceView = "chat" | "studio" | "control";

const KEY_PREFIX = "vm.job.activeView:";
const memoryStore = new Map<string, WorkspaceView>();

export function readWorkspaceView(jobId: string | null): WorkspaceView {
  if (!jobId) return "studio";
  const key = `${KEY_PREFIX}${jobId}`;
  try {
    const raw = window.localStorage.getItem(key);
    if (raw === "chat" || raw === "studio" || raw === "control") return raw;
  } catch {
    // ignore localStorage errors and fallback to memory
  }
  const memory = memoryStore.get(key);
  if (memory) return memory;
  return "studio";
}

export function writeWorkspaceView(jobId: string | null, view: WorkspaceView): void {
  if (!jobId) return;
  const key = `${KEY_PREFIX}${jobId}`;
  memoryStore.set(key, view);
  try {
    window.localStorage.setItem(key, view);
  } catch {
    // ignore localStorage errors
  }
}
