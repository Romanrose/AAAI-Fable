# Concept-to-Fable Paper Reading Site

Astro Starlight site for reading papers related to Concept-to-Fable Synthesis.

## Features

- Four research pillars: knowledge graph, structure mapping, hierarchical generation, and educational evaluation.
- 25 paper pages with PDF links, grounded evidence notes, and research-oriented Q&A.
- Per-paper DeepSeek question box backed by a server-side API route.

## Local Development

```powershell
npm install
copy .env.example .env
npm run dev
```

Open `http://127.0.0.1:4321/`.

## DeepSeek API

Create `.env` locally or configure these variables in Vercel:

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

The API key is only read by `src/pages/api/ask-paper.ts`. Do not expose it in client-side code.

## Content Generation

Paper pages and the DeepSeek context file are generated from:

```powershell
node scripts\generate-content.cjs
```

This writes:

- `src/content/docs/papers/*.mdx`
- `src/content/docs/pillars/*.mdx`
- `src/data/paperContexts.json`

## Build

```powershell
npm run build
```

The project uses `@astrojs/vercel` with `output: 'server'` so the `/api/ask-paper` endpoint can call DeepSeek securely.
