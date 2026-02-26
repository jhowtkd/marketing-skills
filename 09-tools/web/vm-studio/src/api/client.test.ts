import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, suggestTemplatesFromRequest } from './client';
import type { Project, Template } from '../types';

const templates: Template[] = [
  {
    id: 'plan-launch-90d',
    name: 'Plano de Lançamento 90 dias',
    description: 'Estratégia de lançamento com cronograma e canais.',
    tags: ['Lançamento', 'Estratégia'],
    estimatedTime: '10 min',
    parameters: [],
  },
  {
    id: 'landing-conversion',
    name: 'Landing Page de Conversão',
    description: 'Copy para página de captura e venda.',
    tags: ['Landing Page', 'Conversão'],
    estimatedTime: '5 min',
    parameters: [],
  },
  {
    id: 'email-nurture',
    name: 'Sequência de Emails Nurture',
    description: 'Fluxo de emails para aquecer leads.',
    tags: ['Email', 'Nurture'],
    estimatedTime: '7 min',
    parameters: [],
  },
];

describe('suggestTemplatesFromRequest', () => {
  it('returns 3 ordered suggestions with short reason when request has clear intent', () => {
    const result = suggestTemplatesFromRequest('Preciso de uma landing page para converter leads de SaaS', templates);

    expect(result.fallbackToManualSelection).toBe(false);
    expect(result.suggestions).toHaveLength(3);
    expect(result.suggestions[0]?.templateId).toBe('landing-conversion');
    expect(result.suggestions.every((item) => item.reason.length > 0 && item.reason.length <= 120)).toBe(true);
  });

  it('uses deterministic fallback ordering and flags manual fallback when heuristics fail', () => {
    const result = suggestTemplatesFromRequest('blablabla sem contexto de marketing', templates);

    expect(result.fallbackToManualSelection).toBe(true);
    expect(result.suggestions.map((item) => item.templateId)).toEqual([
      'plan-launch-90d',
      'landing-conversion',
      'email-nurture',
    ]);
  });
});

describe('api.generateContent workflow', () => {
  const baseProject: Project = {
    id: 'proj-123',
    name: 'Campanha Primavera',
    templateId: 'landing-conversion',
    templateName: 'Landing Page de Conversão',
    status: 'draft',
    createdAt: '2026-02-26T00:00:00.000Z',
    updatedAt: '2026-02-26T00:00:00.000Z',
  };

  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    vi.spyOn(globalThis, 'setTimeout').mockImplementation(((callback: TimerHandler) => {
      if (typeof callback === 'function') {
        callback();
      }
      return 0 as unknown as number;
    }) as typeof setTimeout);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('runs backend v2 path end-to-end with approvals, resume and primary artifact', async () => {
    fetchMock
      .mockResolvedValueOnce(okJson({ brands: [] }))
      .mockResolvedValueOnce(okJson({ brand_id: 'b-vmstudio-proj-123' }))
      .mockResolvedValueOnce(okJson({ projects: [] }))
      .mockResolvedValueOnce(okJson({ project_id: 'p-vmstudio-proj-123' }))
      .mockResolvedValueOnce(okJson({ threads: [] }))
      .mockResolvedValueOnce(okJson({ thread_id: 't-vmstudio-proj-123' }))
      .mockResolvedValueOnce(okJson({ run_id: 'run-1', status: 'queued' }))
      .mockResolvedValueOnce(
        okJson({
          run_id: 'run-1',
          thread_id: 't-vmstudio-proj-123',
          status: 'waiting_approval',
          pending_approvals: [{ approval_id: 'apr-1', status: 'pending' }],
        })
      )
      .mockResolvedValueOnce(okJson({ approval_id: 'apr-1' }))
      .mockResolvedValueOnce(okJson({ run_id: 'run-1', status: 'running' }))
      .mockResolvedValueOnce(
        okJson({
          run_id: 'run-1',
          thread_id: 't-vmstudio-proj-123',
          status: 'completed',
          pending_approvals: [],
        })
      )
      .mockResolvedValueOnce(
        okJson({
          stages: [
            {
              stage_dir: '03-delivery',
              artifacts: [{ path: 'deliverable/final.md' }],
            },
          ],
        })
      )
      .mockResolvedValueOnce(okJson({ content: '# Conteudo final do backend' }));

    const response = await api.generateContent({
      templateId: 'landing-conversion',
      controls: {
        productName: 'Produto X',
        problem: 'Baixa conversão',
      },
      project: baseProject,
      chatRequest: 'Preciso de uma landing page para B2B',
    });

    expect(response.content).toContain('Conteudo final do backend');
    expect(response.runId).toBe('run-1');
    expect(response.backendContext.brandId).toBe('b-vmstudio-proj-123');
    expect(response.backendContext.projectId).toBe('p-vmstudio-proj-123');
    expect(response.backendContext.threadId).toBe('t-vmstudio-proj-123');

    const workflowRunCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes('/api/v2/threads/t-vmstudio-proj-123/workflow-runs')
    );
    expect(workflowRunCall).toBeDefined();
    const workflowRunPayload = JSON.parse(String(workflowRunCall?.[1]?.body ?? '{}'));
    expect(workflowRunPayload.mode).toBe('content_calendar');

    const postCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST');
    expect(postCalls.length).toBeGreaterThan(0);
    expect(
      postCalls.every(([, init]) => {
        const headers = (init?.headers ?? {}) as Record<string, string>;
        return typeof headers['Idempotency-Key'] === 'string' && headers['Idempotency-Key'].length > 0;
      })
    ).toBe(true);

    const calledUrls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calledUrls).toContain('/api/v2/workflow-runs/run-1/artifacts');
    expect(calledUrls.some((url) => url.includes('/api/v2/workflow-runs/run-1/artifact-content?'))).toBe(true);
  });

  it('grants and resumes when backend reports pending approvals while status is running', async () => {
    const projectWithContext: Project = {
      ...baseProject,
      backendContext: {
        brandId: 'b-vmstudio-proj-123',
        projectId: 'p-vmstudio-proj-123',
        threadId: 't-vmstudio-proj-123',
      },
    };

    fetchMock
      .mockResolvedValueOnce(okJson({ brands: [{ brand_id: 'b-vmstudio-proj-123' }] }))
      .mockResolvedValueOnce(okJson({ projects: [{ project_id: 'p-vmstudio-proj-123' }] }))
      .mockResolvedValueOnce(okJson({ threads: [{ thread_id: 't-vmstudio-proj-123' }] }))
      .mockResolvedValueOnce(okJson({ run_id: 'run-2', status: 'queued' }))
      .mockResolvedValueOnce(
        okJson({
          run_id: 'run-2',
          thread_id: 't-vmstudio-proj-123',
          status: 'running',
          pending_approvals: [{ approval_id: 'apr-2', status: 'pending' }],
        })
      )
      .mockResolvedValueOnce(okJson({ approval_id: 'apr-2' }))
      .mockResolvedValueOnce(okJson({ run_id: 'run-2', status: 'running' }))
      .mockResolvedValueOnce(
        okJson({
          run_id: 'run-2',
          thread_id: 't-vmstudio-proj-123',
          status: 'completed',
          pending_approvals: [],
        })
      )
      .mockResolvedValueOnce(
        okJson({
          stages: [
            {
              stage_dir: '03-delivery',
              artifacts: [{ path: 'deliverable/final.md' }],
            },
          ],
        })
      )
      .mockResolvedValueOnce(okJson({ content: '# Conteudo final apos approvals em running' }));

    const response = await api.generateContent({
      templateId: 'landing-conversion',
      controls: {
        productName: 'Produto Y',
      },
      project: projectWithContext,
      chatRequest: 'Refine para decisor B2B',
    });

    expect(response.runId).toBe('run-2');
    expect(response.content).toContain('final apos approvals');

    const calledUrls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calledUrls).toContain('/api/v2/approvals/apr-2/grant');
    expect(calledUrls).toContain('/api/v2/workflow-runs/run-2/resume');
  });

  it('falls back to thread approvals when status is running and stage waits approval', async () => {
    const projectWithContext: Project = {
      ...baseProject,
      backendContext: {
        brandId: 'b-vmstudio-proj-123',
        projectId: 'p-vmstudio-proj-123',
        threadId: 't-vmstudio-proj-123',
      },
    };

    fetchMock
      .mockResolvedValueOnce(okJson({ brands: [{ brand_id: 'b-vmstudio-proj-123' }] }))
      .mockResolvedValueOnce(okJson({ projects: [{ project_id: 'p-vmstudio-proj-123' }] }))
      .mockResolvedValueOnce(okJson({ threads: [{ thread_id: 't-vmstudio-proj-123' }] }))
      .mockResolvedValueOnce(okJson({ run_id: 'run-3', status: 'queued' }))
      .mockResolvedValueOnce(
        okJson({
          run_id: 'run-3',
          thread_id: 't-vmstudio-proj-123',
          status: 'running',
          pending_approvals: [],
          stages: [{ status: 'waiting_approval' }],
        })
      )
      .mockResolvedValueOnce(
        okJson({
          items: [
            {
              approval_id: 'apr-3',
              status: 'pending',
              reason: 'workflow_gate:run-3:brand-voice',
            },
          ],
        })
      )
      .mockResolvedValueOnce(okJson({ approval_id: 'apr-3' }))
      .mockResolvedValueOnce(okJson({ run_id: 'run-3', status: 'running' }))
      .mockResolvedValueOnce(
        okJson({
          run_id: 'run-3',
          thread_id: 't-vmstudio-proj-123',
          status: 'completed',
          pending_approvals: [],
          stages: [],
        })
      )
      .mockResolvedValueOnce(
        okJson({
          stages: [
            {
              stage_dir: '03-delivery',
              artifacts: [{ path: 'deliverable/final.md' }],
            },
          ],
        })
      )
      .mockResolvedValueOnce(okJson({ content: '# Conteudo final apos fallback por stage waiting_approval' }));

    const response = await api.generateContent({
      templateId: 'landing-conversion',
      controls: {
        productName: 'Produto Z',
      },
      project: projectWithContext,
      chatRequest: 'Preciso de refinamento com aprovacao',
    });

    expect(response.runId).toBe('run-3');
    expect(response.content).toContain('fallback por stage');

    const calledUrls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calledUrls).toContain('/api/v2/threads/t-vmstudio-proj-123/approvals');
    expect(calledUrls).toContain('/api/v2/approvals/apr-3/grant');
    expect(calledUrls).toContain('/api/v2/workflow-runs/run-3/resume');
  });
});

function okJson(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  } as Response;
}
