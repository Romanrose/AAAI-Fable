// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import vercel from '@astrojs/vercel';

// https://astro.build/config
export default defineConfig({
	output: 'server',
	adapter: vercel(),
	integrations: [
		starlight({
			title: 'Concept-to-Fable',
			description: '一个围绕 Concept-to-Fable Synthesis 的论文阅读网站。',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/Romanrose/AAAI-Fable' }],
			sidebar: [
				{
					label: '研究导览',
					items: [
						{ label: '让知识活起来', slug: '' },
						{ label: '知识图谱', slug: 'pillars/knowledge-graph' },
						{ label: '结构映射', slug: 'pillars/structure-mapping' },
						{ label: '层次化生成', slug: 'pillars/hierarchical-generation' },
						{ label: '教育评价', slug: 'pillars/educational-evaluation' },
					],
				},
				{
					label: '论文库',
					items: [{ autogenerate: { directory: 'papers' } }],
				},
			],
		}),
	],
});
