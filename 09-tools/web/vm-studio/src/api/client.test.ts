import { describe, expect, it } from 'vitest';
import { suggestTemplatesFromRequest } from './client';
import type { Template } from '../types';

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
