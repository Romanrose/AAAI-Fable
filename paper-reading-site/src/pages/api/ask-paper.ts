import type { APIRoute } from 'astro';
import paperContexts from '../../data/paperContexts.json';

export const prerender = false;

type PaperContext = {
	title: string;
	year: string;
	venue: string;
	pillar: string;
	url: string;
	contribution: string;
	relation: string;
	reading: string;
	borrow: string;
	limitation: string;
	transform: string;
	evidence: string[];
};

const contexts = paperContexts as Record<string, PaperContext>;

function json(data: unknown, status = 200) {
	return new Response(JSON.stringify(data), {
		status,
		headers: { 'Content-Type': 'application/json; charset=utf-8' },
	});
}

export const POST: APIRoute = async ({ request }) => {
	const apiKey = import.meta.env.DEEPSEEK_API_KEY;
	const model = import.meta.env.DEEPSEEK_MODEL || 'deepseek-v4-flash';
	const baseUrl = import.meta.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com';

	if (!apiKey) {
		return json({ error: '服务端还没有配置 DEEPSEEK_API_KEY。' }, 500);
	}

	let body: { paperSlug?: string; question?: string };
	try {
		body = await request.json();
	} catch {
		return json({ error: '请求体不是合法 JSON。' }, 400);
	}

	const paperSlug = String(body.paperSlug || '').trim();
	const question = String(body.question || '').trim();
	const paper = contexts[paperSlug];

	if (!paper) {
		return json({ error: '没有找到这篇论文的上下文。' }, 404);
	}
	if (question.length < 2) {
		return json({ error: '问题太短，请输入更明确的问题。' }, 400);
	}
	if (question.length > 1200) {
		return json({ error: '问题太长，请控制在 1200 字以内。' }, 400);
	}

	const context = [
		`论文：${paper.title}`,
		`年份/来源：${paper.year} · ${paper.venue}`,
		`所属支柱：${paper.pillar}`,
		`原文链接：${paper.url}`,
		`论文贡献：${paper.contribution}`,
		`与 Concept-to-Fable 的关系：${paper.relation}`,
		`推荐阅读部分：${paper.reading}`,
		`可借鉴点：${paper.borrow}`,
		`局限：${paper.limitation}`,
		`用于知识点转寓言的改造建议：${paper.transform}`,
		`原文依据定位：\n${paper.evidence.map((item) => `- ${item}`).join('\n')}`,
	].join('\n\n');

	const response = await fetch(`${baseUrl.replace(/\/$/, '')}/chat/completions`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${apiKey}`,
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			model,
			messages: [
				{
					role: 'system',
					content:
						'你是一个严谨的论文阅读助手，服务于 Concept-to-Fable Synthesis 研究。回答必须基于给定论文上下文，不要编造论文中没有的实验、数字或结论。若依据不足，请明确说明需要进一步查 PDF 页码。回答使用中文，结构清晰，给出具体建议。',
				},
				{
					role: 'user',
					content: `论文上下文如下：\n\n${context}\n\n用户问题：${question}`,
				},
			],
			temperature: 0.2,
			max_tokens: 1200,
		}),
	});

	const data = await response.json().catch(() => null);

	if (!response.ok) {
		return json({ error: data?.error?.message || `DeepSeek 请求失败：${response.status}` }, response.status);
	}

	const answer = data?.choices?.[0]?.message?.content;
	if (!answer) {
		return json({ error: 'DeepSeek 没有返回有效回答。' }, 502);
	}

	return json({ answer });
};
