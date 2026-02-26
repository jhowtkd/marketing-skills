# VM Studio 2.0 (Chat-First Pilot)

Interface visual do Vibe Marketing Studio com fluxo piloto orientado por chat.

## Desenvolvimento

```bash
npm install
npm run dev
```

Acesse: `http://localhost:3000`

## Fluxo Oficial do Piloto

1. `chat_input` - usuario descreve objetivo no chat inicial.
2. `template_suggestion` - sistema sugere 3 templates com justificativa.
3. `generating` - usuario ajusta controles e gera conteudo.
4. `deliverable_ready` - tela deliverable-first com conteudo e proximos passos.
5. `refining` - chat de refinamento com historico e instrucoes iterativas.

## Observacoes do Piloto

- O refinamento em chat e local (sem backend adicional nesta fase).
- A sugestao de templates usa heuristica simples com fallback deterministico.
- O CTA primario apos geracao e `Refinar no chat`.

## Validacao

```bash
npm run test -- --run
npm run build
```

## Integracao com Backend

O backend FastAPI serve os arquivos estaticos em `/studio` quando o build existe em `dist/`.

## Templates Disponiveis

1. Plano de Lancamento 90 dias
2. Landing Page de Conversao
3. Sequencia de Emails Nurture

## Estrutura

```text
src/
├── api/          # Cliente API e adapters
├── components/   # Views por fase e componentes de UI
│   └── ui/       # Componentes base
├── lib/          # Utilidades
├── store/        # Estado global (Zustand)
├── types/        # Contratos TypeScript
├── App.tsx       # Roteamento por fase
└── main.tsx      # Entry point
```
