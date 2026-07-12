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
			title: 'concept2fable',
			description: '从课程知识到可验证教学寓言的端到端研究流程。',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/Romanrose/AAAI-Fable' }],
			sidebar: [
				{
					label: 'concept2fable',
					items: [
						{ label: '项目总览', slug: '' },
						{ label: '当前实验方法', slug: 'methodology' },
						{ label: '01 · 图检索与证据', slug: 'pillars/retrieval-evidence' },
						{ label: '02 · 机制图', slug: 'pillars/mechanism-graph' },
						{ label: '03 · Copycat 候选竞争', slug: 'pillars/copycat-mapping-competition' },
						{ label: '04 · 寓言叙事', slug: 'pillars/fable-narrative' },
						{ label: '05 · 反向对齐与教育评测', slug: 'pillars/reverse-alignment-evaluation' },
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
