# Concept2Fable Paper Reading Site

独立的 Astro Starlight 阅读站，用于维护 Concept2Fable 相关的知识图谱、结构映射、Copycat、故事生成和教育评价论文。它不参与 Python 实验的运行，也不修改 `data/derived/` 中的实验产物。

当前站点包含 46 篇论文页面、46 份 PDF 和 5 个研究支柱页面；每篇论文可提供服务端 DeepSeek 问答。

## 在 MacBook 或其他新设备上启动

```bash
cd doc/paper-reading-site
npm install
cp .env.example .env             # Windows PowerShell: Copy-Item .env.example .env
npm run dev
```

打开 <http://127.0.0.1:4321/>。`node_modules/`、`dist/`、`.astro/` 和 `.vercel/` 是可再生本机构建目录，已由本目录 `.gitignore` 排除；`public/papers/` 和内容源文件应与仓库同步。

## DeepSeek 配置

在本目录 `.env` 或 Vercel 环境变量中设置：

```env
DEEPSEEK_API_KEY=replace-me
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

密钥仅由 `src/pages/api/ask-paper.ts` 在服务端读取，不能提交或暴露给客户端。

## 内容生成与构建

```bash
node scripts/generate-content.cjs
npm run build
```

内容生成会更新：

- `src/content/docs/papers/*.mdx`
- `src/content/docs/pillars/*.mdx`
- `src/data/paperContexts.json`

项目使用 `@astrojs/vercel` 和 `output: 'server'`，以安全运行 `/api/ask-paper`。
