# VM Unified Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Criar interface unificada vm-unified combinando vm-ui (dev mode) e vm-studio (guided mode) com estética Raycast-style.

**Architecture:** Layout 3 colunas persistente (Navigation | Workspace | Command Rail) com toggle de modo na coluna central. Dark mode default, command palette, atalhos de teclado. Tech: React + TypeScript + Tailwind + Vite.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Vite, Zustand (state), Framer Motion (animações), Lucide React (ícones)

---

## Pré-requisitos

```bash
# Verificar node e npm
node --version  # >= 18
npm --version

# Entrar no diretório do projeto
 cd /Users/jhonatan/Repos/marketing-skills/09-tools/web
```

---

## Task 1: Setup do Projeto Base

**Files:**
- Create: `vm-unified/package.json`
- Create: `vm-unified/vite.config.ts`
- Create: `vm-unified/tsconfig.json`
- Create: `vm-unified/tailwind.config.ts`
- Create: `vm-unified/index.html`

**Step 1: Criar estrutura e package.json**

```bash
mkdir -p vm-unified/src/{app,components/{ui,layout,guided,dev},hooks,lib,styles,types}
mkdir -p vm-unified/public
cd vm-unified
```

**Step 2: Criar package.json**

Create: `vm-unified/package.json`

```json
{
  "name": "vm-unified",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.5.0",
    "framer-motion": "^11.0.0",
    "lucide-react": "^0.344.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.0"
  }
}
```

**Step 3: Instalar dependências**

```bash
npm install
```

Expected: `added XXX packages in Xs`

**Step 4: Criar tsconfig.json**

Create: `vm-unified/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

Create: `vm-unified/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

**Step 5: Criar vite.config.ts**

Create: `vm-unified/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8766',
        changeOrigin: true,
      },
    },
  },
})
```

**Step 6: Criar tailwind.config.ts**

Create: `vm-unified/tailwind.config.ts`

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        vm: {
          bg: '#0F0F0F',
          surface: '#1A1A1A',
          'surface-elevated': '#242424',
          border: '#2A2A2A',
          ink: '#F5F5F5',
          'ink-muted': '#8A8A8A',
          'ink-subtle': '#5A5A5A',
          primary: '#FF6B35',
          'primary-dim': 'rgba(255, 107, 53, 0.12)',
          success: '#4ADE80',
          warning: '#FBBF24',
          error: '#F87171',
          hover: 'rgba(255, 255, 255, 0.06)',
          active: 'rgba(255, 255, 255, 0.1)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'vm-sm': '6px',
        'vm-md': '10px',
        'vm-lg': '14px',
        'vm-xl': '20px',
      },
      boxShadow: {
        'vm-sm': '0 1px 2px rgba(0, 0, 0, 0.3)',
        'vm-md': '0 4px 12px rgba(0, 0, 0, 0.4)',
        'vm-lg': '0 8px 24px rgba(0, 0, 0, 0.5)',
        'vm-glow': '0 0 20px rgba(255, 107, 53, 0.15)',
      },
    },
  },
  plugins: [],
}

export default config
```

**Step 7: Criar PostCSS config**

Create: `vm-unified/postcss.config.js`

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 8: Criar index.html**

Create: `vm-unified/index.html`

```html
<!DOCTYPE html>
<html lang="en" class="dark">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vm-logo.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>VM Studio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  </head>
  <body class="bg-vm-bg text-vm-ink font-sans antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**Step 9: Criar entry point main.tsx**

Create: `vm-unified/src/main.tsx`

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app/App'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

**Step 10: Commit**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/
git commit -m "feat(vm-unified): setup project base with Vite + React + Tailwind"
```

---

## Task 2: Design System (UI Components)

**Files:**
- Create: `vm-unified/src/lib/utils.ts`
- Create: `vm-unified/src/components/ui/button.tsx`
- Create: `vm-unified/src/components/ui/card.tsx`
- Create: `vm-unified/src/components/ui/input.tsx`
- Create: `vm-unified/src/components/ui/kbd.tsx`

**Step 1: Criar utils (cn helper)**

Create: `vm-unified/src/lib/utils.ts`

```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

**Step 2: Criar globals.css com variáveis CSS**

Create: `vm-unified/src/styles/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --vm-bg: #0F0F0F;
    --vm-surface: #1A1A1A;
    --vm-surface-elevated: #242424;
    --vm-border: #2A2A2A;
    --vm-ink: #F5F5F5;
    --vm-ink-muted: #8A8A8A;
    --vm-ink-subtle: #5A5A5A;
    --vm-primary: #FF6B35;
    --vm-primary-dim: rgba(255, 107, 53, 0.12);
    --vm-success: #4ADE80;
    --vm-warning: #FBBF24;
    --vm-error: #F87171;
    --vm-hover: rgba(255, 255, 255, 0.06);
    --vm-active: rgba(255, 255, 255, 0.1);
  }

  * {
    @apply border-vm-border;
  }

  html {
    @apply bg-vm-bg text-vm-ink;
  }
}

@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
}
```

**Step 3: Criar Button component**

Create: `vm-unified/src/components/ui/button.tsx`

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    const variants = {
      primary: 'bg-vm-primary text-white hover:opacity-90',
      secondary: 'bg-vm-surface-elevated text-vm-ink hover:bg-vm-hover',
      ghost: 'text-vm-ink-muted hover:text-vm-ink hover:bg-vm-hover',
      danger: 'bg-vm-error/10 text-vm-error hover:bg-vm-error/20',
    }

    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-base',
    }

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center rounded-vm-md font-medium transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-vm-primary/20',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
```

**Step 4: Criar Card component**

Create: `vm-unified/src/components/ui/card.tsx`

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-vm-lg bg-vm-surface border border-vm-border shadow-vm-sm',
      className
    )}
    {...props}
  />
))
Card.displayName = 'Card'

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('flex flex-col p-4', className)} {...props} />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('font-semibold text-vm-ink', className)}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('p-4 pt-0', className)} {...props} />
))
CardContent.displayName = 'CardContent'

export { Card, CardHeader, CardTitle, CardContent }
```

**Step 5: Criar Input component**

Create: `vm-unified/src/components/ui/input.tsx`

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-vm-md bg-vm-surface border border-vm-border',
          'px-3 py-2 text-sm text-vm-ink placeholder:text-vm-ink-subtle',
          'focus:outline-none focus:ring-2 focus:ring-vm-primary/20 focus:border-vm-primary/50',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'

export { Input }
```

**Step 6: Criar Kbd component**

Create: `vm-unified/src/components/ui/kbd.tsx`

```typescript
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface KbdProps extends React.HTMLAttributes<HTMLElement> {}

const Kbd = React.forwardRef<HTMLElement, KbdProps>(
  ({ className, ...props }, ref) => {
    return (
      <kbd
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center',
          'h-5 min-w-[20px] px-1 rounded text-[10px] font-mono font-medium',
          'bg-vm-surface-elevated text-vm-ink-muted border border-vm-border',
          className
        )}
        {...props}
      />
    )
  }
)
Kbd.displayName = 'Kbd'

export { Kbd }
```

**Step 7: Testar build**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-unified
npm run build 2>&1 | head -20
```

Expected: `dist/` criado sem erros

**Step 8: Commit**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/src/{components/ui,lib,styles}
git commit -m "feat(vm-unified): add design system components (Button, Card, Input, Kbd)"
```

---

## Task 3: Zustand Store Unificado

**Files:**
- Create: `vm-unified/src/types/index.ts`
- Create: `vm-unified/src/hooks/use-store.ts`

**Step 1: Criar types**

Create: `vm-unified/src/types/index.ts`

```typescript
// Hierarchy Types
export interface Brand {
  id: string
  name: string
  createdAt: string
  updatedAt: string
}

export interface Project {
  id: string
  brandId: string
  name: string
  createdAt: string
  updatedAt: string
}

export interface Thread {
  id: string
  projectId: string
  name: string
  createdAt: string
  updatedAt: string
}

export interface Run {
  id: string
  threadId: string
  status: 'queued' | 'running' | 'waiting_approval' | 'completed' | 'failed'
  currentStage: string | null
  stages: Stage[]
  createdAt: string
  updatedAt: string
}

export interface Stage {
  key: string
  name: string
  status: 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'skipped'
  startedAt?: string
  completedAt?: string
}

export interface Artifact {
  path: string
  name: string
  type: 'markdown' | 'json' | 'yaml' | 'text'
  stageKey: string
}

// UI Types
export type ViewMode = 'guided' | 'dev'

export interface Template {
  id: string
  name: string
  description: string
  category: string
}

export interface ChatState {
  request: string
  suggestions: Template[]
  isGenerating: boolean
}
```

**Step 2: Criar store**

Create: `vm-unified/src/hooks/use-store.ts`

```typescript
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Brand, Project, Thread, Run, Artifact, ViewMode, Template, ChatState } from '@/types'

interface VMState {
  // Hierarchy
  brands: Brand[]
  projects: Project[]
  threads: Thread[]
  runs: Run[]
  artifacts: Artifact[]

  // Selection
  activeBrandId: string | null
  activeProjectId: string | null
  activeThreadId: string | null
  activeRunId: string | null

  // UI State
  viewMode: ViewMode
  chat: ChatState

  // Actions - Hierarchy
  setBrands: (brands: Brand[]) => void
  setProjects: (projects: Project[]) => void
  setThreads: (threads: Thread[]) => void
  setRuns: (runs: Run[]) => void
  setArtifacts: (artifacts: Artifact[]) => void

  // Actions - Selection
  selectBrand: (brandId: string | null) => void
  selectProject: (projectId: string | null) => void
  selectThread: (threadId: string | null) => void
  selectRun: (runId: string | null) => void

  // Actions - UI
  setViewMode: (mode: ViewMode) => void
  toggleViewMode: () => void
  setChatRequest: (request: string) => void
  setChatSuggestions: (suggestions: Template[]) => void
  setChatGenerating: (isGenerating: boolean) => void

  // Computed
  getActiveBrand: () => Brand | undefined
  getActiveProject: () => Project | undefined
  getActiveThread: () => Thread | undefined
  getActiveRun: () => Run | undefined
  getActiveArtifacts: () => Artifact[]
}

export const useStore = create<VMState>()(
  devtools(
    (set, get) => ({
      // Initial State
      brands: [],
      projects: [],
      threads: [],
      runs: [],
      artifacts: [],

      activeBrandId: null,
      activeProjectId: null,
      activeThreadId: null,
      activeRunId: null,

      viewMode: 'guided',
      chat: {
        request: '',
        suggestions: [],
        isGenerating: false,
      },

      // Actions - Hierarchy
      setBrands: (brands) => set({ brands }),
      setProjects: (projects) => set({ projects }),
      setThreads: (threads) => set({ threads }),
      setRuns: (runs) => set({ runs }),
      setArtifacts: (artifacts) => set({ artifacts }),

      // Actions - Selection
      selectBrand: (brandId) => set({
        activeBrandId: brandId,
        activeProjectId: null,
        activeThreadId: null,
        activeRunId: null,
      }),

      selectProject: (projectId) => set({
        activeProjectId: projectId,
        activeThreadId: null,
        activeRunId: null,
      }),

      selectThread: (threadId) => set({
        activeThreadId: threadId,
        activeRunId: null,
      }),

      selectRun: (runId) => set({ activeRunId: runId }),

      // Actions - UI
      setViewMode: (mode) => set({ viewMode: mode }),

      toggleViewMode: () => set((state) => ({
        viewMode: state.viewMode === 'guided' ? 'dev' : 'guided'
      })),

      setChatRequest: (request) => set((state) => ({
        chat: { ...state.chat, request }
      })),

      setChatSuggestions: (suggestions) => set((state) => ({
        chat: { ...state.chat, suggestions }
      })),

      setChatGenerating: (isGenerating) => set((state) => ({
        chat: { ...state.chat, isGenerating }
      })),

      // Computed
      getActiveBrand: () => {
        const { brands, activeBrandId } = get()
        return brands.find(b => b.id === activeBrandId)
      },

      getActiveProject: () => {
        const { projects, activeProjectId } = get()
        return projects.find(p => p.id === activeProjectId)
      },

      getActiveThread: () => {
        const { threads, activeThreadId } = get()
        return threads.find(t => t.id === activeThreadId)
      },

      getActiveRun: () => {
        const { runs, activeRunId } = get()
        return runs.find(r => r.id === activeRunId)
      },

      getActiveArtifacts: () => {
        const { artifacts, activeRunId } = get()
        return artifacts.filter(a => a.runId === activeRunId)
      },
    }),
    { name: 'VMStore' }
  )
)
```

**Step 3: Commit**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/src/{types,hooks}
git commit -m "feat(vm-unified): add Zustand store with hierarchy and UI state"
```

---

## Task 4: Layout Shell (3 Colunas)

**Files:**
- Create: `vm-unified/src/components/layout/header.tsx`
- Create: `vm-unified/src/components/layout/mode-toggle.tsx`
- Create: `vm-unified/src/components/layout/navigation-panel.tsx`
- Create: `vm-unified/src/components/layout/command-rail.tsx`
- Create: `vm-unified/src/components/layout/workspace.tsx`
- Create: `vm-unified/src/app/App.tsx`

**Step 1: Criar Header**

Create: `vm-unified/src/components/layout/header.tsx`

```typescript
import { ChevronRight, Search } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { ModeToggle } from './mode-toggle'
import { cn } from '@/lib/utils'

export function Header() {
  const { activeBrandId, activeProjectId, activeThreadId, brands, projects, threads } = useStore()

  const activeBrand = brands.find(b => b.id === activeBrandId)
  const activeProject = projects.find(p => p.id === activeProjectId)
  const activeThread = threads.find(t => t.id === activeThreadId)

  return (
    <header className="h-14 border-b border-vm-border bg-vm-bg flex items-center px-4 shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-vm-md bg-vm-primary flex items-center justify-center">
          <span className="text-white font-bold text-sm">VM</span>
        </div>
        <span className="font-semibold text-vm-ink">Vibe Marketing</span>
      </div>

      {/* Breadcrumb */}
      <nav className="ml-8 flex items-center gap-1 text-sm">
        {activeBrand ? (
          <>
            <span className="text-vm-ink font-medium">{activeBrand.name}</span>
            {activeProject && (
              <>
                <ChevronRight className="w-4 h-4 text-vm-ink-subtle" />
                <span className="text-vm-ink">{activeProject.name}</span>
              </>
            )}
            {activeThread && (
              <>
                <ChevronRight className="w-4 h-4 text-vm-ink-subtle" />
                <span className="text-vm-primary">{activeThread.name}</span>
              </>
            )}
          </>
        ) : (
          <span className="text-vm-ink-subtle">No brand selected</span>
        )}
      </nav>

      {/* Right Actions */}
      <div className="ml-auto flex items-center gap-2">
        <button className="p-2 rounded-vm-md hover:bg-vm-hover transition-colors">
          <Search className="w-4 h-4 text-vm-ink-muted" />
        </button>
        <ModeToggle />
      </div>
    </header>
  )
}
```

**Step 2: Criar Mode Toggle**

Create: `vm-unified/src/components/layout/mode-toggle.tsx`

```typescript
import { Code, MessageSquare } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { cn } from '@/lib/utils'

export function ModeToggle() {
  const { viewMode, toggleViewMode } = useStore()

  return (
    <button
      onClick={toggleViewMode}
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-vm-md transition-colors',
        'bg-vm-surface border border-vm-border hover:bg-vm-surface-elevated'
      )}
      title={`Switch to ${viewMode === 'guided' ? 'Dev' : 'Guided'} mode (⌘D)`}
    >
      {viewMode === 'guided' ? (
        <>
          <MessageSquare className="w-4 h-4 text-vm-primary" />
          <span className="text-sm text-vm-ink">Guided</span>
        </>
      ) : (
        <>
          <Code className="w-4 h-4 text-vm-primary" />
          <span className="text-sm text-vm-ink">Dev</span>
        </>
      )}
    </button>
  )
}
```

**Step 3: Criar Navigation Panel (simplificado)**

Create: `vm-unified/src/components/layout/navigation-panel.tsx`

```typescript
import { ChevronDown, ChevronRight, Plus, MoreHorizontal } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { cn } from '@/lib/utils'

export function NavigationPanel() {
  const {
    brands,
    projects,
    threads,
    activeBrandId,
    activeProjectId,
    activeThreadId,
    selectBrand,
    selectProject,
    selectThread,
  } = useStore()

  const getBrandProjects = (brandId: string) =>
    projects.filter(p => p.brandId === brandId)

  const getProjectThreads = (projectId: string) =>
    threads.filter(t => t.projectId === projectId)

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium text-vm-ink-subtle uppercase tracking-wider">
          Brands
        </span>
      </div>

      <div className="space-y-1">
        {brands.map((brand) => {
          const isActive = brand.id === activeBrandId
          const brandProjects = getBrandProjects(brand.id)

          return (
            <div key={brand.id} className="group">
              <button
                onClick={() => selectBrand(isActive ? null : brand.id)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded-vm-md transition-colors',
                  isActive ? 'bg-vm-primary-dim text-vm-primary' : 'hover:bg-vm-hover'
                )}
              >
                {isActive ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-vm-ink-subtle" />
                )}
                <span className="text-sm font-medium flex-1 text-left">{brand.name}</span>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-vm-hover rounded transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="w-3.5 h-3.5" />
                </button>
              </button>

              {isActive && brandProjects.length > 0 && (
                <div className="ml-4 mt-0.5 space-y-0.5 border-l border-vm-border pl-2">
                  {brandProjects.map((project) => {
                    const isProjectActive = project.id === activeProjectId
                    const projectThreads = getProjectThreads(project.id)

                    return (
                      <div key={project.id}>
                        <button
                          onClick={() => selectProject(isProjectActive ? null : project.id)}
                          className={cn(
                            'w-full flex items-center gap-2 px-2 py-1.5 rounded-vm-md transition-colors',
                            isProjectActive ? 'text-vm-ink' : 'text-vm-ink-muted hover:text-vm-ink hover:bg-vm-hover'
                          )}
                        >
                          {isProjectActive ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                          )}
                          <span className="text-sm">{project.name}</span>
                        </button>

                        {isProjectActive && projectThreads.length > 0 && (
                          <div className="ml-4 mt-0.5 space-y-0.5">
                            {projectThreads.map((thread) => {
                              const isThreadActive = thread.id === activeThreadId
                              return (
                                <button
                                  key={thread.id}
                                  onClick={() => selectThread(thread.id)}
                                  className={cn(
                                    'w-full text-left px-2 py-1.5 rounded-vm-md text-sm transition-colors',
                                    isThreadActive
                                      ? 'bg-vm-primary-dim text-vm-primary'
                                      : 'text-vm-ink-muted hover:bg-vm-hover'
                                  )}
                                >
                                  {thread.name}
                                </button>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-vm-md border border-dashed border-vm-border text-sm text-vm-ink-muted hover:border-vm-primary hover:text-vm-primary transition-colors">
        <Plus className="w-4 h-4" />
        New Brand
      </button>
    </div>
  )
}
```

**Step 4: Criar Command Rail (simplificado)**

Create: `vm-unified/src/components/layout/command-rail.tsx`

```typescript
import { Command, Play, CheckCircle, RotateCcw, FileText } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { Kbd } from '@/components/ui/kbd'
import { cn } from '@/lib/utils'

export function CommandRail() {
  const { runs, artifacts, activeRunId } = useStore()
  const activeRun = runs.find(r => r.id === activeRunId)
  const activeArtifacts = artifacts.filter(a => a.runId === activeRunId)

  return (
    <div className="h-full flex flex-col bg-vm-surface border-l border-vm-border">
      {/* Command Input */}
      <div className="p-3 border-b border-vm-border">
        <div className="flex items-center gap-2 px-3 py-2 rounded-vm-md bg-vm-bg border border-vm-border">
          <Command className="w-4 h-4 text-vm-ink-muted" />
          <input
            type="text"
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-sm text-vm-ink placeholder:text-vm-ink-subtle outline-none"
          />
          <Kbd>⌘K</Kbd>
        </div>
      </div>

      {/* Actions */}
      <div className="flex-1 overflow-y-auto p-2">
        {activeRun && (
          <>
            <Section title="Run Actions">
              <CommandItem icon={Play} label="Resume Workflow" shortcut="⌘R" />
              <CommandItem icon={CheckCircle} label="Approve Stage" shortcut="⌘A" />
              <CommandItem icon={RotateCcw} label="Retry Stage" />
            </Section>

            <Section title="Stage Status">
              {activeRun.stages?.map((stage) => (
                <div
                  key={stage.key}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm"
                >
                  <StatusDot status={stage.status} />
                  <span className="text-vm-ink-muted">{stage.name}</span>
                </div>
              ))}
            </Section>
          </>
        )}

        {activeArtifacts.length > 0 && (
          <Section title="Artifacts">
            {activeArtifacts.map((artifact) => (
              <CommandItem
                key={artifact.path}
                icon={FileText}
                label={artifact.name}
              />
            ))}
          </Section>
        )}

        {!activeRun && (
          <div className="px-2 py-8 text-center">
            <p className="text-sm text-vm-ink-subtle">No active run</p>
            <p className="text-xs text-vm-ink-subtle mt-1">
              Select a thread to view actions
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="px-2 py-1.5 text-xs font-medium text-vm-ink-subtle uppercase tracking-wider">
        {title}
      </div>
      <div className="mt-1 space-y-0.5">{children}</div>
    </div>
  )
}

function CommandItem({
  icon: Icon,
  label,
  shortcut,
  onClick,
}: {
  icon: React.ElementType
  label: string
  shortcut?: string
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 px-2 py-1.5 rounded-vm-md transition-colors group',
        'hover:bg-vm-hover text-left'
      )}
    >
      <Icon className="w-4 h-4 text-vm-ink-muted" />
      <span className="text-sm text-vm-ink">{label}</span>
      {shortcut && (
        <span className="ml-auto text-xs text-vm-ink-subtle opacity-0 group-hover:opacity-100 transition-opacity">
          {shortcut}
        </span>
      )}
    </button>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors = {
    pending: 'bg-vm-ink-subtle',
    running: 'bg-vm-primary animate-pulse',
    waiting_approval: 'bg-vm-warning',
    completed: 'bg-vm-success',
    failed: 'bg-vm-error',
    skipped: 'bg-vm-ink-subtle',
  }
  return <div className={cn('w-2 h-2 rounded-full', colors[status] || colors.pending)} />
}
```

**Step 5: Criar Workspace container**

Create: `vm-unified/src/components/layout/workspace.tsx`

```typescript
import { AnimatePresence, motion } from 'framer-motion'
import { useStore } from '@/hooks/use-store'

export function Workspace() {
  const { viewMode } = useStore()

  return (
    <div className="h-full overflow-auto p-4">
      <AnimatePresence mode="wait">
        {viewMode === 'guided' ? (
          <motion.div
            key="guided"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <GuidedMode />
          </motion.div>
        ) : (
          <motion.div
            key="dev"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <DevMode />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Placeholders - implementar nas próximas tasks
function GuidedMode() {
  const { chat, setChatRequest, setChatGenerating } = useStore()

  return (
    <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold text-vm-ink mb-2">
        What do you want to create?
      </h1>
      <p className="text-vm-ink-muted mb-8 text-center">
        Describe your goal and I&apos;ll suggest the best templates for your marketing workflow.
      </p>

      <div className="w-full">
        <div className="relative">
          <textarea
            value={chat.request}
            onChange={(e) => setChatRequest(e.target.value)}
            className="w-full h-32 p-4 rounded-vm-lg bg-vm-surface border border-vm-border text-vm-ink placeholder:text-vm-ink-subtle focus:outline-none focus:ring-2 focus:ring-vm-primary/20 resize-none"
            placeholder="e.g., Landing page for B2B consulting leads..."
          />
          <button
            onClick={() => setChatGenerating(true)}
            disabled={!chat.request.trim() || chat.isGenerating}
            className="absolute bottom-3 right-3 px-4 py-1.5 rounded-vm-md bg-vm-primary text-white text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {chat.isGenerating ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </div>
    </div>
  )
}

function DevMode() {
  const { getActiveThread, getActiveRun } = useStore()
  const thread = getActiveThread()
  const run = getActiveRun()

  if (!thread) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-vm-ink">No thread selected</p>
          <p className="text-vm-ink-muted text-sm mt-1">
            Select a thread from the navigation panel
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-3 rounded-vm-lg bg-vm-surface border border-vm-border">
          <p className="text-xs text-vm-ink-subtle uppercase tracking-wider">Thread</p>
          <p className="text-sm text-vm-ink font-medium mt-1">{thread.name}</p>
        </div>
        <div className="p-3 rounded-vm-lg bg-vm-surface border border-vm-border">
          <p className="text-xs text-vm-ink-subtle uppercase tracking-wider">Status</p>
          <p className="text-sm text-vm-success font-medium mt-1">
            {run?.status || 'No run'}
          </p>
        </div>
        <div className="p-3 rounded-vm-lg bg-vm-surface border border-vm-border">
          <p className="text-xs text-vm-ink-subtle uppercase tracking-wider">Stage</p>
          <p className="text-sm text-vm-ink font-medium mt-1">
            {run?.currentStage || '-'}
          </p>
        </div>
      </div>

      <div className="flex-1 rounded-vm-lg bg-vm-surface border border-vm-border p-4">
        <p className="text-vm-ink-muted text-center">
          DAG visualization coming soon...
        </p>
      </div>
    </div>
  )
}
```

**Step 6: Criar App.tsx principal**

Create: `vm-unified/src/app/App.tsx`

```typescript
import { Header } from '@/components/layout/header'
import { NavigationPanel } from '@/components/layout/navigation-panel'
import { Workspace } from '@/components/layout/workspace'
import { CommandRail } from '@/components/layout/command-rail'

function App() {
  return (
    <div className="h-screen flex flex-col bg-vm-bg">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-64 border-r border-vm-border bg-vm-bg shrink-0">
          <NavigationPanel />
        </aside>
        <main className="flex-1 min-w-0 bg-vm-bg">
          <Workspace />
        </main>
        <aside className="w-72 shrink-0">
          <CommandRail />
        </aside>
      </div>
    </div>
  )
}

export default App
```

**Step 7: Testar dev server**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-unified
npm run dev &
sleep 3
curl -s http://localhost:5173 | head -5
```

Expected: HTML com `<div id="root">` ou conteúdo React renderizado

**Step 8: Commit**

```bash
pkill -f "vite" 2>/dev/null || true
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/src/{components/layout,app}
git commit -m "feat(vm-unified): add 3-column layout shell with mode toggle"
```

---

## Task 5: Keyboard Shortcuts Hook

**Files:**
- Create: `vm-unified/src/hooks/use-keyboard.ts`

**Step 1: Criar hook de atalhos**

Create: `vm-unified/src/hooks/use-keyboard.ts`

```typescript
import { useEffect, useCallback } from 'react'
import { useStore } from './use-store'

export function useKeyboard() {
  const { toggleViewMode, selectBrand, selectProject, selectThread } = useStore()

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const { key, metaKey, ctrlKey } = event
    const mod = metaKey || ctrlKey

    // Mode toggle: ⌘D
    if (mod && key === 'd') {
      event.preventDefault()
      toggleViewMode()
      return
    }

    // Focus panels: ⌘1, ⌘2, ⌘3
    if (mod && key === '1') {
      event.preventDefault()
      document.querySelector('[data-panel="navigation"]')?.focus()
      return
    }

    if (mod && key === '2') {
      event.preventDefault()
      document.querySelector('[data-panel="workspace"]')?.focus()
      return
    }

    if (mod && key === '3') {
      event.preventDefault()
      document.querySelector('[data-panel="command"]')?.focus()
      return
    }

    // Escape: clear selection
    if (key === 'Escape') {
      selectBrand(null)
      return
    }

    // Help: ?
    if (key === '?' && !mod) {
      event.preventDefault()
      // TODO: Show keyboard shortcuts modal
      console.log('Show keyboard shortcuts')
    }
  }, [toggleViewMode, selectBrand])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
```

**Step 2: Integrar no App.tsx**

Modify: `vm-unified/src/app/App.tsx`

```typescript
import { Header } from '@/components/layout/header'
import { NavigationPanel } from '@/components/layout/navigation-panel'
import { Workspace } from '@/components/layout/workspace'
import { CommandRail } from '@/components/layout/command-rail'
import { useKeyboard } from '@/hooks/use-keyboard'

function App() {
  useKeyboard()

  return (
    <div className="h-screen flex flex-col bg-vm-bg">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-64 border-r border-vm-border bg-vm-bg shrink-0" data-panel="navigation">
          <NavigationPanel />
        </aside>
        <main className="flex-1 min-w-0 bg-vm-bg" data-panel="workspace">
          <Workspace />
        </main>
        <aside className="w-72 shrink-0" data-panel="command">
          <CommandRail />
        </aside>
      </div>
    </div>
  )
}

export default App
```

**Step 3: Commit**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/src/hooks/use-keyboard.ts 09-tools/web/vm-unified/src/app/App.tsx
git commit -m "feat(vm-unified): add keyboard shortcuts hook (⌘D, ⌘1/2/3, Esc)"
```

---

## Task 6: Mock Data para Demo

**Files:**
- Modify: `vm-unified/src/hooks/use-store.ts` (adicionar mock data)

**Step 1: Adicionar mock data ao store**

Modify: `vm-unified/src/hooks/use-store.ts`

Add after initial state definition:

```typescript
// Mock data for development
const mockBrands: Brand[] = [
  { id: 'brand-1', name: 'Acme Corp', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'brand-2', name: 'TechStart', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const mockProjects: Project[] = [
  { id: 'proj-1', brandId: 'brand-1', name: 'Q1 Launch', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'proj-2', brandId: 'brand-1', name: 'Product Hunt', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'proj-3', brandId: 'brand-2', name: 'Beta Campaign', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const mockThreads: Thread[] = [
  { id: 'thread-1', projectId: 'proj-1', name: 'Landing Page', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'thread-2', projectId: 'proj-1', name: 'Email Sequence', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'thread-3', projectId: 'proj-2', name: 'PH Launch', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const mockRuns: Run[] = [
  {
    id: 'run-1',
    threadId: 'thread-1',
    status: 'waiting_approval',
    currentStage: 'brand-voice',
    stages: [
      { key: 'research', name: 'Research', status: 'completed' },
      { key: 'brand-voice', name: 'Brand Voice', status: 'waiting_approval' },
      { key: 'positioning', name: 'Positioning', status: 'pending' },
      { key: 'keywords', name: 'Keywords', status: 'pending' },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
]

const mockArtifacts: Artifact[] = [
  { path: '/research/market-landscape.md', name: 'market-landscape.md', type: 'markdown', stageKey: 'research', runId: 'run-1' },
  { path: '/research/competitor-gaps.md', name: 'competitor-gaps.md', type: 'markdown', stageKey: 'research', runId: 'run-1' },
]
```

Then update initial state:

```typescript
// Initial State
brands: mockBrands,
projects: mockProjects,
threads: mockThreads,
runs: mockRuns,
artifacts: mockArtifacts,

activeBrandId: 'brand-1',
activeProjectId: 'proj-1',
activeThreadId: 'thread-1',
activeRunId: 'run-1',
```

Also need to update the Artifact type to include runId:

Modify: `vm-unified/src/types/index.ts`

```typescript
export interface Artifact {
  path: string
  name: string
  type: 'markdown' | 'json' | 'yaml' | 'text'
  stageKey: string
  runId: string  // Add this
}
```

**Step 2: Commit**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/src/{hooks/use-store.ts,types/index.ts}
git commit -m "feat(vm-unified): add mock data for development demo"
```

---

## Task 7: Final Build & Integração

**Files:**
- Modify: `vm-unified/vite.config.ts` (ajustar proxy e base)
- Create: README básico

**Step 1: Ajustar vite config para build de produção**

Modify: `vm-unified/vite.config.ts`

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? '/' : '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8766',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
}))
```

**Step 2: Criar README**

Create: `vm-unified/README.md`

```markdown
# VM Unified

Interface unificada do Vibe Marketing Studio — combinando Guided Mode e Dev Mode em uma experiência Raycast-style.

## Features

- **3-Column Layout**: Navigation | Workspace | Command Rail
- **Mode Toggle**: Alterne entre Guided (chat-first) e Dev (technical) modes
- **Raycast Aesthetic**: Dark mode, command palette, keyboard shortcuts
- **Keyboard Shortcuts**:
  - `⌘D`: Toggle mode
  - `⌘1/2/3`: Focus panels
  - `⌘K`: Command palette
  - `Esc`: Clear selection

## Development

```bash
npm install
npm run dev
```

Open http://localhost:5173

## Build

```bash
npm run build
```

Output in `dist/` directory.

## Integration

To integrate with the VM Web App backend, ensure the API is running on port 8766.
```

**Step 3: Build de produção**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-unified
npm run build 2>&1
```

Expected: Build completo sem erros, pasta `dist/` criada

**Step 4: Commit final**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/{vite.config.ts,README.md}
git add 09-tools/web/vm-unified/dist/.gitkeep 2>/dev/null || true
git commit -m "feat(vm-unified): production build config and README"
```

**Step 5: Tag da versão**

```bash
git tag -a vm-unified-v0.1.0 -m "VM Unified Interface v0.1.0 - Initial release"
```

---

## Resumo

Este plano cria a base da interface unificada com:

1. **Setup completo** (Vite + React + Tailwind + Zustand)
2. **Design system** (Button, Card, Input, Kbd)
3. **Store unificado** (hierarquia + UI state)
4. **Layout 3 colunas** (Navigation | Workspace | Command Rail)
5. **Mode toggle** (Guided ↔ Dev com animações)
6. **Keyboard shortcuts** (⌘D, ⌘1/2/3, Esc)
7. **Mock data** para demonstração

**Próximos passos (fora do escopo deste plano):**
- Conectar com API real do vm_webapp
- Implementar Guided Mode completo (chat, templates, deliverables)
- Implementar Dev Mode completo (DAG viewer, logs, JSON viewer)
- Resizable panels
- Command palette funcional
- Light mode toggle
