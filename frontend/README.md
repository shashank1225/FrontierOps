# FrontierOps Dashboard

The React and TypeScript control plane for FrontierOps. It reads the backend API and presents application inventory, evaluation quality, latency, cost, and release-gate decisions.

## Local development

Requires Node.js 22.13 or newer.

```bash
npm ci
npm run dev
```

The dashboard runs at `http://localhost:3000` and expects the API at `http://localhost:8000/api/v1`. Override the API with `NEXT_PUBLIC_API_URL` when needed.

## Quality checks

```bash
npm run lint
npm run typecheck
npm test
```

The frontend keeps transport contracts in `lib/api.ts`, orchestration in `components/dashboard.tsx`, and reusable presentation primitives under `components/ui/`.
