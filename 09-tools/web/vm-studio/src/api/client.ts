import type { BackendContext, Project, SuggestedTemplate, Template, TemplateControls } from '../types';

const API_BASE = '/api/v2';
const WAITING_STATUSES = new Set(['waiting_approval', 'paused', 'waiting']);
const MAX_POLL_ATTEMPTS = 90;
const POLL_INTERVAL_MS = 1200;
const MAX_REFINE_CONTEXT_CHARS = 6000;

type JsonObject = Record<string, unknown>;

interface BrandRow {
  brand_id: string;
}

interface ProjectRow {
  project_id: string;
}

interface ThreadRow {
  thread_id: string;
}

interface ApprovalRow {
  approval_id: string;
  status?: string;
  reason?: string;
}

interface WorkflowRunStartResponse {
  run_id: string;
  status: string;
}

interface WorkflowRunDetailResponse {
  run_id: string;
  thread_id?: string;
  status: string;
  pending_approvals?: ApprovalRow[];
  stages?: Array<{ status?: string }>;
  error_message?: string;
}

interface ArtifactItem {
  path?: string;
  filename?: string;
}

interface ArtifactStage {
  stage_dir: string;
  artifacts?: Array<string | ArtifactItem>;
}

export interface GenerateRequest {
  templateId: string;
  controls: TemplateControls;
  project: Project;
  chatRequest?: string;
}

export interface RefineRequest {
  templateId: string;
  prompt: string;
  currentContent: string;
  project: Project;
}

export interface GenerateResponse {
  content: string;
  runId: string;
  backendContext: BackendContext;
  assistantSummary: string;
}

function buildIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

async function parseJsonSafe(response: Response): Promise<JsonObject> {
  try {
    const payload = await response.json();
    if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
      return payload as JsonObject;
    }
  } catch {
    // ignore
  }
  return {};
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (response.ok) {
    return (await response.json()) as T;
  }

  const payload = await parseJsonSafe(response);
  const detail = typeof payload.detail === 'string' ? payload.detail : `Request failed (${response.status})`;
  throw new Error(detail);
}

async function postJson<T>(url: string, payload: unknown, prefix: string): Promise<T> {
  return fetchJson<T>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': buildIdempotencyKey(prefix),
    },
    body: JSON.stringify(payload),
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function normalizeId(value: string): string {
  const normalized = value
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  return normalized || `proj-${Date.now().toString(36)}`;
}

function buildDeterministicContext(project: Project): BackendContext {
  const suffix = normalizeId(project.id).slice(0, 40);
  return {
    brandId: `b-vmstudio-${suffix}`,
    projectId: `p-vmstudio-${suffix}`,
    threadId: `t-vmstudio-${suffix}`,
  };
}

function chooseContext(project: Project): BackendContext {
  const deterministic = buildDeterministicContext(project);
  return {
    brandId: project.backendContext?.brandId || deterministic.brandId,
    projectId: project.backendContext?.projectId || deterministic.projectId,
    threadId: project.backendContext?.threadId || deterministic.threadId,
  };
}

async function ensureBrandExists(brandId: string, name: string): Promise<void> {
  const brands = await fetchJson<{ brands: BrandRow[] }>(`${API_BASE}/brands`);
  if (brands.brands.some((brand) => brand.brand_id === brandId)) {
    return;
  }

  try {
    await postJson<{ brand_id: string }>(`${API_BASE}/brands`, { brand_id: brandId, name }, 'brand-create');
  } catch (error) {
    const refreshed = await fetchJson<{ brands: BrandRow[] }>(`${API_BASE}/brands`);
    if (!refreshed.brands.some((brand) => brand.brand_id === brandId)) {
      throw error;
    }
  }
}

async function ensureProjectExists(brandId: string, projectId: string, name: string): Promise<void> {
  const projects = await fetchJson<{ projects: ProjectRow[] }>(
    `${API_BASE}/projects?brand_id=${encodeURIComponent(brandId)}`
  );
  if (projects.projects.some((project) => project.project_id === projectId)) {
    return;
  }

  try {
    await postJson<{ project_id: string }>(
      `${API_BASE}/projects`,
      {
        project_id: projectId,
        brand_id: brandId,
        name,
        objective: '',
        channels: [],
      },
      'project-create'
    );
  } catch (error) {
    const refreshed = await fetchJson<{ projects: ProjectRow[] }>(
      `${API_BASE}/projects?brand_id=${encodeURIComponent(brandId)}`
    );
    if (!refreshed.projects.some((project) => project.project_id === projectId)) {
      throw error;
    }
  }
}

async function ensureThreadExists(
  brandId: string,
  projectId: string,
  threadId: string,
  title: string
): Promise<void> {
  const threads = await fetchJson<{ threads: ThreadRow[] }>(
    `${API_BASE}/threads?project_id=${encodeURIComponent(projectId)}`
  );
  if (threads.threads.some((thread) => thread.thread_id === threadId)) {
    return;
  }

  try {
    await postJson<{ thread_id: string }>(
      `${API_BASE}/threads`,
      {
        thread_id: threadId,
        project_id: projectId,
        brand_id: brandId,
        title,
      },
      'thread-create'
    );
  } catch (error) {
    const refreshed = await fetchJson<{ threads: ThreadRow[] }>(
      `${API_BASE}/threads?project_id=${encodeURIComponent(projectId)}`
    );
    if (!refreshed.threads.some((thread) => thread.thread_id === threadId)) {
      throw error;
    }
  }
}

async function ensureBackendContext(project: Project): Promise<BackendContext> {
  const context = chooseContext(project);
  const normalizedProjectName = project.name.trim() || 'Projeto VM Studio';

  await ensureBrandExists(context.brandId, `VM Studio - ${normalizedProjectName}`);
  await ensureProjectExists(context.brandId, context.projectId, normalizedProjectName);
  await ensureThreadExists(context.brandId, context.projectId, context.threadId, normalizedProjectName);

  return context;
}

export function mapTemplateToMode(templateId: string): string {
  if (templateId === 'plan-launch-90d') {
    return 'plan_90d';
  }
  if (templateId === 'landing-conversion' || templateId === 'email-nurture') {
    return 'content_calendar';
  }
  return 'plan_90d';
}

function formatControlLabel(key: string): string {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .trim();
}

function controlsToBulletList(controls: TemplateControls): string[] {
  return Object.entries(controls)
    .filter(([, value]) => String(value ?? '').trim().length > 0)
    .map(([key, value]) => `- ${formatControlLabel(key)}: ${String(value).trim()}`);
}

function buildGenerateRequestText(request: GenerateRequest): string {
  const lines: string[] = ['Crie um entregavel de marketing pronto para uso.'];
  if (request.chatRequest && request.chatRequest.trim()) {
    lines.push(`Objetivo inicial: ${request.chatRequest.trim()}`);
  }
  lines.push(`Template selecionado: ${request.templateId}`);

  const controlLines = controlsToBulletList(request.controls);
  if (controlLines.length > 0) {
    lines.push('Parametros definidos:');
    lines.push(...controlLines);
  }

  return lines.join('\n');
}

function buildRefineRequestText(prompt: string, currentContent: string): string {
  const trimmedPrompt = prompt.trim();
  const current = currentContent.trim().slice(0, MAX_REFINE_CONTEXT_CHARS);

  if (!current) {
    return `Refine o entregavel com esta instrucao:\n${trimmedPrompt}`;
  }

  return [
    'Refine o entregavel existente mantendo a estrutura que ainda faz sentido.',
    `Instrucao do usuario: ${trimmedPrompt}`,
    'Entregavel atual:',
    current,
  ].join('\n\n');
}

function resolveArtifactPath(item: string | ArtifactItem): string | null {
  if (typeof item === 'string') {
    return item;
  }
  return item.path || item.filename || null;
}

function scoreArtifactPath(path: string): number {
  let score = 0;
  if (path.endsWith('.md')) {
    score += 3;
  }
  if (path.includes('final') || path.includes('deliverable') || path.includes('output')) {
    score += 2;
  }
  return score;
}

function pickPrimaryArtifact(stages: ArtifactStage[]): { stageDir: string; artifactPath: string } | null {
  const orderedStages = [...stages].reverse();
  for (const stage of orderedStages) {
    const stageArtifacts = Array.isArray(stage.artifacts) ? stage.artifacts : [];
    const candidatePaths = stageArtifacts
      .map((item) => resolveArtifactPath(item))
      .filter((path): path is string => Boolean(path));

    if (candidatePaths.length === 0) {
      continue;
    }

    const artifactPath = [...candidatePaths].sort((left, right) => scoreArtifactPath(right) - scoreArtifactPath(left))[0];
    if (artifactPath) {
      return {
        stageDir: stage.stage_dir,
        artifactPath,
      };
    }
  }

  return null;
}

function collectDetailPendingApprovals(detail: WorkflowRunDetailResponse): string[] {
  const pending = Array.isArray(detail.pending_approvals) ? detail.pending_approvals : [];
  return pending
    .filter((approval) => (approval.status || 'pending') === 'pending')
    .map((approval) => approval.approval_id)
    .filter((approvalId) => approvalId.length > 0);
}

async function collectThreadPendingApprovals(threadId: string, runId: string): Promise<string[]> {
  const response = await fetchJson<{ items: ApprovalRow[] }>(
    `${API_BASE}/threads/${encodeURIComponent(threadId)}/approvals`
  );
  const approvals = Array.isArray(response.items) ? response.items : [];
  const runPrefix = `workflow_gate:${runId}:`;

  return approvals
    .filter((approval) => approval.status === 'pending')
    .filter((approval) => typeof approval.reason === 'string' && approval.reason.startsWith(runPrefix))
    .map((approval) => approval.approval_id)
    .filter((approvalId) => approvalId.length > 0);
}

async function handleWaitingRun(
  runId: string,
  fallbackThreadId: string,
  detail: WorkflowRunDetailResponse
): Promise<void> {
  let approvalIds = collectDetailPendingApprovals(detail);

  if (approvalIds.length === 0) {
    const threadId = detail.thread_id || fallbackThreadId;
    approvalIds = await collectThreadPendingApprovals(threadId, runId);
  }

  for (const approvalId of approvalIds) {
    await postJson<{ approval_id: string }>(
      `${API_BASE}/approvals/${encodeURIComponent(approvalId)}/grant`,
      {},
      `approval-grant-${runId}`
    );
  }

  await postJson<{ run_id: string; status: string }>(
    `${API_BASE}/workflow-runs/${encodeURIComponent(runId)}/resume`,
    {},
    `run-resume-${runId}`
  );
}

async function waitForRunTerminalState(runId: string, threadId: string): Promise<WorkflowRunDetailResponse> {
  let lastKnownStatus = 'queued';

  for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt += 1) {
    const detail = await fetchJson<WorkflowRunDetailResponse>(
      `${API_BASE}/workflow-runs/${encodeURIComponent(runId)}`
    );
    const status = String(detail.status || '').toLowerCase();
    lastKnownStatus = status || lastKnownStatus;

    if (status === 'completed') {
      return detail;
    }

    if (status === 'failed') {
      const message =
        typeof detail.error_message === 'string' && detail.error_message.trim().length > 0
          ? detail.error_message
          : 'Execucao falhou no backend.';
      throw new Error(message);
    }

    const hasPendingApprovals = collectDetailPendingApprovals(detail).length > 0;
    const hasApprovalLikeStage = Array.isArray(detail.stages)
      ? detail.stages.some((stage) => {
          const stageStatus = String(stage.status || '').toLowerCase();
          return stageStatus === 'waiting_approval' || WAITING_STATUSES.has(stageStatus);
        })
      : false;

    if (WAITING_STATUSES.has(status) || hasPendingApprovals || hasApprovalLikeStage) {
      await handleWaitingRun(runId, threadId, detail);
    }

    await sleep(POLL_INTERVAL_MS);
  }

  throw new Error(`Tempo limite ao aguardar execucao do backend (status: ${lastKnownStatus}).`);
}

async function fetchPrimaryArtifactContent(runId: string): Promise<string> {
  const listing = await fetchJson<{ stages?: ArtifactStage[] }>(
    `${API_BASE}/workflow-runs/${encodeURIComponent(runId)}/artifacts`
  );
  const stages = Array.isArray(listing.stages) ? listing.stages : [];
  const primary = pickPrimaryArtifact(stages);

  if (!primary) {
    throw new Error('Execucao concluida sem artefato principal disponivel.');
  }

  const query = new URLSearchParams({
    stage_dir: primary.stageDir,
    artifact_path: primary.artifactPath,
  });

  const payload = await fetchJson<{ content?: string }>(
    `${API_BASE}/workflow-runs/${encodeURIComponent(runId)}/artifact-content?${query.toString()}`
  );
  const content = String(payload.content ?? '');

  if (!content.trim()) {
    throw new Error('Artefato principal retornou vazio.');
  }

  return content;
}

async function runWorkflow(threadId: string, mode: string, requestText: string): Promise<{ runId: string; content: string }> {
  const started = await postJson<WorkflowRunStartResponse>(
    `${API_BASE}/threads/${encodeURIComponent(threadId)}/workflow-runs`,
    {
      mode,
      request_text: requestText.trim(),
      skill_overrides: {},
    },
    'workflow-run'
  );

  if (!started.run_id) {
    throw new Error('Backend nao retornou identificador de execucao.');
  }

  await waitForRunTerminalState(started.run_id, threadId);
  const content = await fetchPrimaryArtifactContent(started.run_id);

  return {
    runId: started.run_id,
    content,
  };
}

function summarizeAssistantReply(content: string): string {
  const firstLine = content
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.length > 0);

  if (!firstLine) {
    return 'Nova versao pronta para revisao.';
  }

  const sanitized = firstLine.replace(/^#+\s*/, '').trim();
  if (sanitized.length <= 80) {
    return `Nova versao pronta: ${sanitized}`;
  }

  return `Nova versao pronta: ${sanitized.slice(0, 77)}...`;
}

export const api = {
  async generateContent(request: GenerateRequest): Promise<GenerateResponse> {
    const backendContext = await ensureBackendContext(request.project);
    const mode = mapTemplateToMode(request.templateId);
    const requestText = buildGenerateRequestText(request);
    const workflow = await runWorkflow(backendContext.threadId, mode, requestText);

    return {
      content: workflow.content,
      runId: workflow.runId,
      backendContext,
      assistantSummary: summarizeAssistantReply(workflow.content),
    };
  },

  async refineContent(request: RefineRequest): Promise<GenerateResponse> {
    const backendContext = await ensureBackendContext(request.project);
    const mode = mapTemplateToMode(request.templateId);
    const requestText = buildRefineRequestText(request.prompt, request.currentContent);
    const workflow = await runWorkflow(backendContext.threadId, mode, requestText);

    return {
      content: workflow.content,
      runId: workflow.runId,
      backendContext,
      assistantSummary: summarizeAssistantReply(workflow.content),
    };
  },

  async getWorkflowStatus(runId: string): Promise<{ status: string; content?: string }> {
    return fetchJson(`${API_BASE}/workflow-runs/${encodeURIComponent(runId)}`);
  },
};

const FALLBACK_TEMPLATE_ORDER = ['plan-launch-90d', 'landing-conversion', 'email-nurture'] as const;

const TEMPLATE_KEYWORDS: Record<string, string[]> = {
  'landing-conversion': ['landing', 'pagina', 'página', 'conversao', 'conversão', 'cta', 'captura', 'venda'],
  'email-nurture': ['email', 'nurture', 'lead', 'funil', 'newsletter', 'sequencia', 'sequência', 'onboarding'],
  'plan-launch-90d': ['lancamento', 'lançamento', 'estrategia', 'estratégia', 'campanha', 'go-to-market', 'gtm'],
};

function normalizeText(input: string): string {
  return input
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function toSummary(description: string): string {
  const trimmed = description.trim();
  if (trimmed.length <= 80) {
    return trimmed;
  }
  return `${trimmed.slice(0, 77)}...`;
}

function toReason(templateId: string, fallback: boolean): string {
  if (fallback) {
    return 'Fallback sugeriu opção estável enquanto você escolhe manualmente.';
  }

  if (templateId === 'landing-conversion') {
    return 'Pedido indica foco direto em conversão de página.';
  }
  if (templateId === 'email-nurture') {
    return 'Pedido indica relacionamento e nutrição de leads.';
  }
  return 'Pedido indica planejamento estratégico de campanha.';
}

function scoreTemplate(template: Template, normalizedRequest: string): number {
  const templateKeywords = TEMPLATE_KEYWORDS[template.id] ?? [];
  const keywordScore = templateKeywords.reduce((score, keyword) => {
    const normalizedKeyword = normalizeText(keyword);
    return normalizedRequest.includes(normalizedKeyword) ? score + 3 : score;
  }, 0);

  const nameAndTagTokens = [template.name, ...template.tags]
    .map((value) => normalizeText(value))
    .flatMap((value) => value.split(/\s+/).filter(Boolean));

  const semanticScore = nameAndTagTokens.reduce((score, token) => {
    if (token.length < 4) {
      return score;
    }
    return normalizedRequest.includes(token) ? score + 1 : score;
  }, 0);

  return keywordScore + semanticScore;
}

function buildOrderedTemplateList(
  templates: Template[],
  normalizedRequest: string,
  fallback: boolean
): Template[] {
  if (fallback) {
    const fallbackTemplates = FALLBACK_TEMPLATE_ORDER
      .map((templateId) => templates.find((template) => template.id === templateId))
      .filter((template): template is Template => Boolean(template));

    if (fallbackTemplates.length >= 3) {
      return fallbackTemplates.slice(0, 3);
    }

    const missingTemplates = templates.filter((template) => !fallbackTemplates.some((item) => item.id === template.id));
    return [...fallbackTemplates, ...missingTemplates].slice(0, 3);
  }

  return [...templates]
    .sort((left, right) => {
      const scoreDiff = scoreTemplate(right, normalizedRequest) - scoreTemplate(left, normalizedRequest);
      if (scoreDiff !== 0) {
        return scoreDiff;
      }
      return left.name.localeCompare(right.name, 'pt-BR');
    })
    .slice(0, 3);
}

export interface TemplateSuggestionResult {
  suggestions: SuggestedTemplate[];
  fallbackToManualSelection: boolean;
}

export function suggestTemplatesFromRequest(requestText: string, templates: Template[]): TemplateSuggestionResult {
  const normalizedRequest = normalizeText(requestText.trim());
  const hasSignal =
    normalizedRequest.length > 0 &&
    templates.some((template) => scoreTemplate(template, normalizedRequest) > 0);

  const fallbackToManualSelection = !hasSignal;
  const orderedTemplates = buildOrderedTemplateList(templates, normalizedRequest, fallbackToManualSelection);

  return {
    fallbackToManualSelection,
    suggestions: orderedTemplates.map((template) => ({
      templateId: template.id,
      templateName: template.name,
      summary: toSummary(template.description),
      reason: toReason(template.id, fallbackToManualSelection),
    })),
  };
}
