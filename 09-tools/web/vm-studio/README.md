# VM Studio 2.0

Interface visual para o Vibe Marketing - crie conteudo de marketing profissional em minutos.

## Desenvolvimento

```bash
npm install
npm run dev
```

Acesse: http://localhost:3000

## Build

```bash
npm run build
```

## Integracao com Backend

O backend FastAPI serve os arquivos estaticos em `/studio` quando o build esta presente em `dist/`.

## Templates Disponiveis

1. **Plano de Lancamento 90 dias** - Estrategia completa B2B
2. **Landing Page de Conversao** - Copy completa para landing
3. **Sequencia de Emails Nurture** - Serie de emails de nutricao

## Estrutura

```text
src/
├── api/          # Cliente API
├── components/   # Views e componentes de UI
│   └── ui/       # Componentes base
├── lib/          # Utilidades
├── store/        # Estado (Zustand)
├── types/        # TypeScript types
├── App.tsx       # App principal
└── main.tsx      # Entry point
```
