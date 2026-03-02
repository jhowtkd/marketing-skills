/**
 * First-success templates library for v30 onboarding
 * Pre-built templates to help users achieve first value quickly
 */

export interface Template {
  id: string;
  name: string;
  description: string;
  category: TemplateCategory;
  icon: string;
  defaultPrompt: string;
  variables?: TemplateVariable[];
}

export interface TemplateVariable {
  name: string;
  label: string;
  placeholder: string;
  required: boolean;
}

export type TemplateCategory =
  | 'content'
  | 'conversion'
  | 'social'
  | 'email'
  | 'ads'
  | 'all';

export const TEMPLATE_CATEGORIES: { value: TemplateCategory; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'content', label: 'Conteúdo' },
  { value: 'conversion', label: 'Conversão' },
  { value: 'social', label: 'Social' },
  { value: 'email', label: 'Email' },
  { value: 'ads', label: 'Anúncios' },
];

export const FIRST_SUCCESS_TEMPLATES: Template[] = [
  {
    id: 'blog-post',
    name: 'Blog Post',
    description: 'Crie conteúdo de blog envolvente e otimizado para SEO',
    category: 'content',
    icon: '📝',
    defaultPrompt: 'Escreva um post de blog sobre {tópico} com tom {tom} e aproximadamente {palavras} palavras.',
    variables: [
      { name: 'tópico', label: 'Tópico', placeholder: 'Ex: Marketing Digital', required: true },
      { name: 'tom', label: 'Tom de voz', placeholder: 'Ex: Profissional', required: false },
      { name: 'palavras', label: 'Quantidade de palavras', placeholder: 'Ex: 800', required: false },
    ],
  },
  {
    id: 'landing-page',
    name: 'Landing Page',
    description: 'Copy de alta conversão para páginas de destino',
    category: 'conversion',
    icon: '🎯',
    defaultPrompt: 'Crie copy para landing page de {produto/serviço} focado em {benefício principal}.',
    variables: [
      { name: 'produto/serviço', label: 'Produto ou Serviço', placeholder: 'Ex: Curso de Marketing', required: true },
      { name: 'benefício principal', label: 'Benefício Principal', placeholder: 'Ex: Aumentar vendas', required: true },
    ],
  },
  {
    id: 'social-media',
    name: 'Social Media',
    description: 'Posts engajadores para redes sociais',
    category: 'social',
    icon: '📱',
    defaultPrompt: 'Crie {quantidade} posts para {rede social} sobre {tópico} com tom {tom}.',
    variables: [
      { name: 'quantidade', label: 'Quantidade', placeholder: 'Ex: 3', required: true },
      { name: 'rede social', label: 'Rede Social', placeholder: 'Ex: Instagram', required: true },
      { name: 'tópico', label: 'Tópico', placeholder: 'Ex: Lançamento', required: true },
      { name: 'tom', label: 'Tom', placeholder: 'Ex: Descontraído', required: false },
    ],
  },
  {
    id: 'email-marketing',
    name: 'Email Marketing',
    description: 'Emails que convertem leads em clientes',
    category: 'email',
    icon: '✉️',
    defaultPrompt: 'Escreva um email de {tipo} para {público} sobre {assunto}.',
    variables: [
      { name: 'tipo', label: 'Tipo de Email', placeholder: 'Ex: Newsletter', required: true },
      { name: 'público', label: 'Público-alvo', placeholder: 'Ex: Clientes', required: true },
      { name: 'assunto', label: 'Assunto', placeholder: 'Ex: Nova funcionalidade', required: true },
    ],
  },
  {
    id: 'google-ads',
    name: 'Google Ads',
    description: 'Anúncios otimizados para Google Ads',
    category: 'ads',
    icon: '🔍',
    defaultPrompt: 'Crie {quantidade} variações de anúncio Google Ads para {produto} com foco em {palavra-chave}.',
    variables: [
      { name: 'quantidade', label: 'Quantidade', placeholder: 'Ex: 3', required: true },
      { name: 'produto', label: 'Produto', placeholder: 'Ex: Software CRM', required: true },
      { name: 'palavra-chave', label: 'Palavra-chave Principal', placeholder: 'Ex: CRM gratuito', required: true },
    ],
  },
  {
    id: 'meta-ads',
    name: 'Meta Ads',
    description: 'Anúncios criativos para Facebook e Instagram',
    category: 'ads',
    icon: '📢',
    defaultPrompt: 'Crie copy para anúncio Meta Ads de {produto} destacando {benefício}.',
    variables: [
      { name: 'produto', label: 'Produto', placeholder: 'Ex: Curso Online', required: true },
      { name: 'benefício', label: 'Benefício Principal', placeholder: 'Ex: Certificação', required: true },
    ],
  },
];

export const RECOMMENDED_FIRST_TEMPLATE = 'blog-post';

export function getTemplateById(id: string): Template | undefined {
  return FIRST_SUCCESS_TEMPLATES.find((t) => t.id === id);
}

export function getTemplatesByCategory(category: TemplateCategory): Template[] {
  if (category === 'all') return FIRST_SUCCESS_TEMPLATES;
  return FIRST_SUCCESS_TEMPLATES.filter((t) => t.category === category);
}

export function searchTemplates(query: string): Template[] {
  const normalizedQuery = query.toLowerCase().trim();
  return FIRST_SUCCESS_TEMPLATES.filter(
    (t) =>
      t.name.toLowerCase().includes(normalizedQuery) ||
      t.description.toLowerCase().includes(normalizedQuery)
  );
}

export function fillTemplatePrompt(
  template: Template,
  values: Record<string, string>
): string {
  let prompt = template.defaultPrompt;
  template.variables?.forEach((variable) => {
    const value = values[variable.name] || `{${variable.name}}`;
    prompt = prompt.replace(`{${variable.name}}`, value);
  });
  return prompt;
}
