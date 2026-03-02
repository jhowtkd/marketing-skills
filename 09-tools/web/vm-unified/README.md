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
