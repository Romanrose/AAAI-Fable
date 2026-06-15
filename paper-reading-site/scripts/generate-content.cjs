const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', 'src', 'content', 'docs');
const papersDir = path.join(root, 'papers');
const pillarsDir = path.join(root, 'pillars');

fs.mkdirSync(papersDir, { recursive: true });
fs.mkdirSync(pillarsDir, { recursive: true });

const pillarMeta = {
  知识图谱: {
    slug: 'knowledge-graph',
    title: '知识图谱：为寓言生成提供学科认知',
    description: '课程对齐、前置依赖、知识结构与教学顺序，是 Concept-to-Fable 的内容脊梁。',
    role: '让模型先理解课程知识结构，再决定寓言应该解释什么。',
    noun: '知识结构',
  },
  结构映射: {
    slug: 'structure-mapping',
    title: '结构映射：把知识逻辑变成故事逻辑',
    description: '从类比、隐喻、故事级对应到句子级对齐，保证寓言不是随意改写。',
    role: '把抽象知识结构稳定映射成寓言中的角色、冲突和情节。',
    noun: '映射机制',
  },
  层次化生成: {
    slug: 'hierarchical-generation',
    title: '层次化生成：先规划，再写作',
    description: '通过 story planning、controllable generation 和 KG-guided generation，降低故事跑偏风险。',
    role: '把生成过程拆成可控步骤，避免 LLM 直接写作时跑偏。',
    noun: '生成流程',
  },
  教育评价: {
    slug: 'educational-evaluation',
    title: '教育评价：不只流畅，还要可教',
    description: '教育准确性、映射忠实性、道德/寓言质量、分级阅读适配，是最终数据集的核心指标。',
    role: '判断生成的寓言是否真的可教、可信、适合目标学生。',
    noun: '评价标准',
  },
};

const papers = [
  ['hierarchical-neural-story-generation', 1, 'Hierarchical Neural Story Generation', '2018', 'ACL', '层次化生成', 'StoryGen-01-HierarchicalNeuralStoryGeneration-ACL-2018.pdf', 'https://aclanthology.org/P18-1082/', '提出分层故事生成思路，把故事创作拆成高层规划和低层文本生成。', '它支撑 Concept-to-Fable 中“先有知识逻辑和故事线，再扩写成寓言”的生成路线。', '重点看模型如何处理 prompt、storyline 与长文本生成之间的关系。', '借鉴“规划先行”的思想，把知识图谱中的概念链先转成寓言事件链。', '论文目标是开放故事生成，不保证教育概念的事实准确性或结构映射忠实性。', '需要把自由故事规划替换为受知识点、先修关系和映射说明约束的寓言规划。'],
  ['towards-controllable-story-generation', 2, 'Towards Controllable Story Generation', '2018', 'Workshop on Storytelling', '层次化生成', 'StoryGen-02-ControllableStoryGeneration-Workshop-2018.pdf', 'https://aclanthology.org/W18-1505/', '探索用事件、角色或主题控制故事生成。', '它说明寓言生成不能只依赖自然语言 prompt，而需要显式控制故事要素。', '重点看控制变量如何影响故事情节、角色和目标。', '可借鉴控制信号设计，把教学目标、寓意、概念关系作为生成条件。', '控制目标偏故事层面，没有覆盖学科知识点与情节之间的可解释对齐。', '需要把控制条件扩展为“概念-角色-关系-情节”的结构化约束。'],
  ['plan-and-write', 3, 'Plan-and-Write: Towards Better Automatic Storytelling', '2019', 'AAAI', '层次化生成', 'Method-01-PlanAndWrite-AAAI-2019.pdf', 'https://ojs.aaai.org/index.php/AAAI/article/view/4726', '提出先生成 storyline 再扩写故事的两阶段框架。', '这是 Concept-to-Fable 生成流程的核心技术参照：先把知识点逻辑规划成故事线。', '重点看 storyline 的形式、规划阶段和生成阶段如何衔接。', '可把 KG 路径或概念解释步骤转成 storyline，再让 LLM 扩写。', '原方法没有教育目标、年龄适配和映射忠实性约束。', '需要把 storyline 从关键词序列升级为带概念对齐字段的寓言骨架。'],
  ['controllable-plot-reward-shaping', 4, 'Controllable Neural Story Plot Generation via Reward Shaping', '2019', 'IJCAI', '层次化生成', 'StoryGen-03-ControllablePlotRewardShaping-IJCAI-2019.pdf', 'https://www.ijcai.org/proceedings/2019/829', '通过奖励塑形控制故事情节发展。', '它启发我们把教学约束转化为可优化的生成目标。', '重点看 reward 如何定义故事目标和情节偏好。', '可以把“覆盖概念关系”“不引入科学错误”“适合年级”设计成奖励或打分项。', '奖励主要服务情节控制，不直接处理课程知识和寓言映射。', '需要设计教育导向 reward，例如概念覆盖率、映射一致性和阅读难度。'],
  ['concept-extraction-prerequisite', 5, 'Concept Extraction and Prerequisite Relation Learning from Educational Data', '2019', 'AAAI', '知识图谱', 'Method-05-ConceptExtractionPrerequisite-AAAI-2019.pdf', 'https://ojs.aaai.org/index.php/AAAI/article/view/5033', '研究从教育数据中抽取概念并学习前置依赖关系。', '它直接支撑 Concept-to-Fable 的知识图谱构建：先知道讲哪个概念、依赖哪些前置知识。', '重点看概念抽取和 prerequisite relation 的建模方式。', '可用于从教材中自动抽取知识点和先修链，形成寓言生成输入。', '论文关注知识结构发现，不负责把知识结构转成故事。', '需要把抽取到的概念和先修关系转为寓言角色、冲突和解决路径。'],
  ['mooccube', 6, 'MOOCCube: A Large-scale Data Repository for NLP Applications in MOOCs', '2020', 'ACL', '知识图谱', 'KG-01-MOOCCube-ACL-2020.pdf', 'https://aclanthology.org/2020.acl-main.285/', '构建面向 MOOC 场景的大规模教育数据仓库。', '它展示了教育资源、概念和学习行为如何被组织成可计算资源。', '重点看数据 schema、概念资源和教育 NLP 应用方式。', '可借鉴数据组织方式，为小学知识点、教材段落和生成寓言建立统一索引。', 'MOOC 场景与小学全学科教材不同，且不面向寓言生成。', '需要转换到 K-12 课程标准，并补充寓言生成所需的映射与故事字段。'],
  ['automatic-story-generation-survey', 7, 'Automatic Story Generation: A Survey of Approaches', '2021', 'ACM Computing Surveys', '层次化生成', 'StoryGen-04-AutomaticStoryGenerationSurvey-ACMCSUR-2021.pdf', 'https://dl.acm.org/doi/10.1145/3453156', '系统综述自动故事生成方法。', '它提供故事生成技术谱系，帮助定位 Concept-to-Fable 不是普通故事生成，而是教育约束下的寓言生成。', '重点看规划式、神经式、受控式故事生成的比较。', '可用于 related work 中梳理从 general story generation 到 educational fable generation 的演化。', '综述覆盖面广，但没有深入处理知识图谱驱动和教育评价。', '需要将其中的生成方法按“是否支持知识约束和映射解释”重新分类。'],
  ['metaphor-generation-conceptual-mappings', 8, 'Metaphor Generation with Conceptual Mappings', '2021', 'ACL-IJCNLP', '结构映射', 'Method-02-MetaphorConceptualMappings-ACL-2021.pdf', 'https://aclanthology.org/2021.acl-long.524/', '研究基于概念映射生成隐喻表达。', '它支撑“知识概念到寓言世界”的跨域映射思想。', '重点看 source domain 与 target domain 的映射如何表达。', '可借鉴概念映射，把科学实体映射为寓言角色，把关系映射为互动。', '隐喻通常较短，不等同于有完整情节和教育目标的寓言。', '需要把短语级或句子级隐喻扩展为多事件寓言结构。'],
  ['moral-stories', 9, 'Moral Stories: Situated Reasoning about Norms, Intents, Actions, and their Consequences', '2021', 'EMNLP', '教育评价', 'Evaluation-01-MoralStories-EMNLP-2021.pdf', 'https://aclanthology.org/2021.emnlp-main.54/', '构建道德故事数据集，强调规范、意图、行动和结果。', '它帮助区分寓言中的“道德寓意”和 Concept-to-Fable 中的“知识寓意”。', '重点看故事如何连接情境、行为、后果和规范判断。', '可借鉴故事结构字段，为教育寓言加入情境、冲突、行动、结论。', '它关注道德推理，不关注科学概念解释和课程知识对齐。', '需要把 moral norm 替换为 learning objective，把行为后果映射为知识机制。'],
  ['controllable-text-generation-survey', 10, 'A Survey of Controllable Text Generation using Transformer-based Pre-trained Language Models', '2022', 'arXiv', '层次化生成', 'StoryGen-05-ControllableTextGenerationSurvey-arXiv-2022.pdf', 'https://arxiv.org/abs/2201.05337', '综述 Transformer 时代的可控文本生成方法。', '它支撑生成端控制策略选择，例如属性控制、规划控制和解码控制。', '重点看不同控制方法的输入形式、控制粒度和代价。', '可用于选择控制教学目标、年级难度、寓言风格的技术路线。', '综述不专门讨论故事结构和教育准确性。', '需要从通用可控生成中筛选适合长文本寓言和知识约束的方法。'],
  ['analogy-generation-llms', 11, 'Analogy Generation by Prompting Large Language Models: A Case Study of InstructGPT', '2022', 'INLG', '结构映射', 'Method-03-AnalogyGenerationLLMs-INLG-2022.pdf', 'https://aclanthology.org/2022.inlg-main.25/', '研究用 LLM prompt 生成类比。', 'Concept-to-Fable 本质上需要稳定生成“知识点到寓言情境”的类比。', '重点看 prompt 如何诱导类比，以及类比质量如何评估。', '可借鉴 prompt 设计，让模型提出候选寓言世界和角色映射。', '单纯 prompting 难以保证映射忠实性和教学准确性。', '需要加入 KG 约束、对齐检查和人工/模型评审环节。'],
  ['storal', 12, 'A Corpus for Understanding and Generating Moral Stories', '2022', 'NAACL', '教育评价', 'Evaluation-02-STORAL-NAACL-2022.pdf', 'https://aclanthology.org/2022.naacl-main.374/', '提供理解和生成道德故事的语料资源。', '它是构建寓言故事数据集时的重要参考，尤其是故事结构和寓意标注。', '重点看数据字段、任务定义和故事评价。', '可借鉴语料标注方式，为每个寓言标注情境、行为、结果和知识点。', '道德故事不等同于知识解释故事，缺少概念映射说明。', '需要把道德标签改造为知识概念、先修关系和解释步骤标签。'],
  ['storyanalogy', 13, 'STORYANALOGY: Deriving Story-level Analogies from Large Language Models', '2023', 'EMNLP', '结构映射', 'Core-05-STORYANALOGY-EMNLP-2023.pdf', 'https://aclanthology.org/2023.emnlp-main.706/', '研究从 LLM 中获得故事级类比。', '它是 Concept-to-Fable 的核心参照：寓言不是一句类比，而是故事级结构映射。', '重点看故事级 analogy 的构造、推理和评价。', '可借鉴故事级映射框架，用于说明每个知识步骤对应哪个情节。', '它不一定以课程知识和小学教学目标为输入。', '需要把 story analogy 约束到 KG 驱动的知识解释，并输出映射说明书。'],
  ['educational-material-to-kg', 14, 'Educational Material to Knowledge Graph Conversion', '2024', 'KaLLM Workshop', '知识图谱', 'Method-04-EducationalMaterial2KG-KaLLM-2024.pdf', 'https://aclanthology.org/2024.kallm-1.9/', '研究将教育材料转换为知识图谱。', '它直接服务“从教材到 KG”的前处理阶段。', '重点看教育文本如何被解析为实体、关系和图结构。', '可用于把教材章节转成 Concept-to-Fable 的输入图。', '转换后的 KG 不自动等价于可讲故事的结构。', '需要在 KG 上增加故事化字段，如角色候选、冲突类型和解释顺序。'],
  ['legalstories', 15, 'Leveraging Large Language Models for Learning Complex Legal Concepts through Storytelling', '2024', 'ACL', '教育评价', 'Core-01-LegalStories-ACL-2024.pdf', 'https://aclanthology.org/2024.acl-long.388/', '用 LLM 通过故事帮助学习复杂法律概念。', '它与 Concept-to-Fable 最接近：都使用故事解释复杂知识。', '重点看复杂概念如何被转化为故事，以及学习效果如何验证。', '可借鉴“复杂概念故事化”的任务叙事和用户评价设计。', '法律概念与小学全学科知识不同，且未必强调寓言式映射和 KG 驱动。', '需要把领域从法律扩展到 K-12，并把故事化进一步约束为寓言化。'],
  ['figurative-language-generation-survey', 16, 'A Survey on Automatic Generation of Figurative Language', '2024', 'ACM Computing Surveys', '结构映射', 'Figurative-01-FigurativeLanguageGenerationSurvey-ACMCSUR-2024.pdf', 'https://dl.acm.org/', '综述比喻、隐喻等修辞语言自动生成。', '寓言生成依赖修辞和跨域表达，这篇能提供语言层面的背景。', '重点看 figurative language 的类型、生成方法和评价。', '可用于说明 Concept-to-Fable 与 metaphor/analogy generation 的区别。', '修辞生成通常不要求完整教学闭环。', '需要把修辞表达与课程知识、故事结构和学习目标绑定。'],
  ['ss-gen', 17, 'SS-GEN: A Social Story Generation Framework with Large Language Models', '2025', 'AAAI', '层次化生成', 'Core-02-SSGEN-AAAI-2025.pdf', 'https://ojs.aaai.org/', '提出面向 social story 的 LLM 生成框架。', '它展示了特定用途故事生成如何定义约束、流程和评价。', '重点看框架如何组织输入、生成和质量控制。', '可借鉴任务化故事生成框架，把 social goal 替换为 learning objective。', 'social story 和 educational fable 的目标不同，不能直接迁移评价指标。', '需要换成知识准确性、映射忠实性和年级适配指标。'],
  ['scientific-concept-analogies', 18, 'Unlocking Scientific Concepts: How Effective Are LLM-Generated Analogies for Student Understanding and Classroom Practice?', '2025', 'CHI', '教育评价', 'Evaluation-04-ScientificConceptAnalogies-CHI-2025.pdf', 'https://dl.acm.org/', '研究 LLM 生成科学概念类比对学生理解和课堂实践的作用。', '它直接支撑 Concept-to-Fable 的教育有效性问题。', '重点看学生理解、教师实践和类比质量如何被评估。', '可借鉴教育场景评测，把寓言质量和学习效果连接起来。', '类比不一定是完整寓言，也未必有 KG 驱动。', '需要把单个 analogy 扩展为带情节、寓意和映射说明的寓言。'],
  ['multimodal-math-story-generation', 19, 'Multimodal Story Generation Using Generative AI for Contextualised Mathematics Education', '2025', 'AIED', '教育评价', 'Education-01-MultimodalMathStoryGeneration-AIED-2025.pdf', 'https://link.springer.com/', '研究生成式 AI 在数学教育中的情境化故事生成。', '它说明故事化知识解释可以服务具体学科教学。', '重点看数学概念如何被情境化，以及多模态元素如何支持理解。', '可借鉴数学教育场景中的故事任务设计和学生适配思路。', '数学故事不一定是寓言，也不覆盖全学科 KG。', '需要把情境化故事扩展为寓言结构，并加入跨学科知识图谱输入。'],
  ['kg-guided-storytelling', 20, 'Guiding Generative Storytelling with Knowledge Graphs', '2025', 'arXiv', '知识图谱', 'Core-04-KGGuidedStorytelling-arXiv-2025.pdf', 'https://arxiv.org/abs/2505.24803', '研究用知识图谱指导生成式故事创作。', '它正好连接 KG 和 storytelling，是 Concept-to-Fable 的关键技术桥梁。', '重点看 KG 如何影响故事内容、连贯性和可控性。', '可借鉴 KG-guided generation，把课程 KG 节点和边作为故事生成约束。', '普通 KG storytelling 不一定关注教育准确性和寓言映射。', '需要把 KG 从开放知识图谱换成课程图谱，并增加映射忠实性评估。'],
  ['analogy-annotators', 21, 'Can Language Models Serve as Analogy Annotators?', '2025', 'Findings of ACL', '结构映射', 'Evaluation-03-AnalogyAnnotators-ACLFindings-2025.pdf', 'https://aclanthology.org/', '评估语言模型能否作为类比标注者。', 'Concept-to-Fable 需要判断寓言映射是否合理，这篇提供自动评审启发。', '重点看 analogy annotation 的标准和模型可靠性。', '可借鉴让 LLM 辅助标注概念-故事对应关系。', 'LLM 标注存在偏差，不能完全替代专家和教师评估。', '需要设计多角色评审：知识专家、教师、模型共同检查映射。'],
  ['llm-story-generation-survey', 22, 'A Survey on LLMs for Story Generation', '2025', 'Findings of EMNLP', '层次化生成', 'StoryGen-06-LLMStoryGenerationSurvey-EMNLPFindings-2025.pdf', 'https://aclanthology.org/', '综述 LLM 时代故事生成方法和挑战。', '它帮助定位 LLM 在 Concept-to-Fable 中适合作为生成器，而不是唯一控制器。', '重点看 LLM story generation 的可控性、评价和一致性问题。', '可用于写 related work，说明为什么需要 KG 和显式映射来约束 LLM。', '综述本身不提供具体教育寓言数据集方案。', '需要把 LLM 故事生成问题转化为 KG-conditioned educational fable synthesis。'],
  ['synthetic-moral-fables', 23, 'TF1-EN-3M: Three Million Synthetic Moral Fables from Open Language Models', '2025', 'arXiv', '教育评价', 'Fable-01-SyntheticMoralFables-arXiv-2025.pdf', 'https://arxiv.org/abs/2504.20605', '构建大规模合成道德寓言数据。', '它说明大规模寓言数据集是可行的，但 Concept-to-Fable 更强调知识映射。', '重点看数据生成流程、过滤策略和寓言质量控制。', '可借鉴大规模生成和筛选 pipeline。', '道德寓言不是学科知识寓言，数据量大不等于教学准确。', '需要为每篇寓言加入知识点、概念链、映射说明和年级标签。'],
  ['k12-kgraph', 24, 'K12-KGraph: A Curriculum-Aligned Knowledge Graph for Benchmarking and Training Educational LLMs', '2026', 'arXiv', '知识图谱', 'Core-03-K12KGraph-arXiv-2026.pdf', 'https://arxiv.org/abs/2605.09635', '构建课程对齐的 K-12 知识图谱，用于教育 LLM 训练和评测。', '这是 Concept-to-Fable 的核心支柱：为寓言生成提供课程认知和知识结构。', '重点看 concept、skill、prerequisite 和 curriculum alignment 的定义。', '可直接作为小学全学科知识图谱构建和任务输入设计的参照。', 'KG 本身不解决故事化、寓言化和语言生成质量。', '需要在 K12-KGraph 之上增加“可寓言化”的结构映射层。'],
  ['classroom-ai', 25, 'Classroom AI: Large Language Models as Grade-Specific Teachers', '2026', 'npj Artificial Intelligence', '教育评价', 'Evaluation-05-ClassroomAI-npjAI-2026.pdf', 'https://www.nature.com/npjai/', '研究 LLM 作为分年级教师时的表现与适配。', '它支撑 Concept-to-Fable 的“因材施教”和年级阅读适配。', '重点看 grade-specific teaching、可读性和教学质量评价。', '可借鉴年级适配指标，为寓言生成设定小学 1-2、3-4、5-6 年级版本。', '它关注教师式回答，不一定生成寓言或映射说明。', '需要把教师回答标准转为寓言文本的可读性、解释性和知识准确性标准。'],
].map(([slug, order, title, year, venue, pillar, pdf, url, contribution, relation, reading, borrow, limitation, transform]) => ({ slug, order, title, year, venue, pillar, pdf, url, contribution, relation, reading, borrow, limitation, transform }));

function write(file, content) {
  fs.writeFileSync(file, content, 'utf8');
}

function yaml(s) {
  return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

write(path.join(root, 'index.mdx'), `---
title: 让知识活起来
description: AI 如何将枯燥教材幻化为动人寓言。
template: splash
---

# 让知识“活”起来：AI 如何将枯燥教材幻化为动人寓言？

你是否还记得小时候听过的《农夫与蛇》或《龟兔赛跑》？寓言之所以能跨越时间，是因为它能把抽象道理压缩进角色、冲突和结局里，让读者在故事中理解结构。

这个网站围绕一个研究构想展开：**Concept-to-Fable Synthesis**，即利用课程对齐知识图谱驱动，将小学全学科知识点系统性地转化为高质量、可解释、可评测的教学寓言故事数据集。

## 四个核心支柱

- **知识图谱**：用课程对齐的概念、技能、先修关系约束故事内容。
- **结构映射**：把知识点的实体、关系和因果链映射到寓言角色与情节。
- **层次化生成**：先规划故事线，再扩写成适合学生阅读的寓言。
- **教育评价**：评价故事是否准确、映射是否忠实、阅读难度是否匹配年级。

## 推荐阅读路径

1. 先读 [K12-KGraph](/papers/k12-kgraph/) 和 [Concept Extraction](/papers/concept-extraction-prerequisite/)，理解课程知识如何结构化。
2. 再读 [STORYANALOGY](/papers/storyanalogy/) 和 [Metaphor Generation](/papers/metaphor-generation-conceptual-mappings/)，理解知识到故事的跨域映射。
3. 然后读 [Plan-and-Write](/papers/plan-and-write/) 和 [KG-Guided Storytelling](/papers/kg-guided-storytelling/)，理解如何生成可控故事。
4. 最后读 [Classroom AI](/papers/classroom-ai/) 和 [Scientific Concept Analogies](/papers/scientific-concept-analogies/)，理解教育场景中的评价问题。

## 如何使用本站

每篇论文页面都不是普通摘要，而是一张围绕 Concept-to-Fable 的定向阅读卡。你会看到：这篇论文支撑哪一部分、能借鉴什么、有哪些局限，以及如果用到“知识点转寓言”需要怎样改造。
`);

for (const [name, meta] of Object.entries(pillarMeta)) {
  const related = papers
    .filter((p) => p.pillar === name)
    .map((p) => `- [${p.title}](/papers/${p.slug}/) (${p.year}, ${p.venue})`)
    .join('\n');
  write(path.join(pillarsDir, `${meta.slug}.mdx`), `---
title: ${meta.title}
description: ${meta.description}
---

# ${meta.title}

${meta.description}

这一支柱负责把研究构想中的关键风险前置处理：如果没有可靠的${meta.noun}，模型生成的寓言就容易变成流畅但不可控的故事。

## 在 Concept-to-Fable 中的作用

${meta.role}

## 相关论文

${related}
`);
}

for (const p of papers) {
  const meta = pillarMeta[p.pillar];
  write(path.join(papersDir, `${p.slug}.mdx`), `---
title: "${yaml(p.title)}"
description: "${p.year} ${p.venue} · ${p.pillar}"
sidebar:
  order: ${p.order}
---

# ${p.title}

**年份/来源**：${p.year} · ${p.venue}  
**所属支柱**：[${p.pillar}](/pillars/${meta.slug}/)  
**PDF**：[打开本地 PDF](/papers/${encodeURIComponent(p.pdf)})  
**原文链接**：[${p.url}](${p.url})

## 这篇论文在讲什么

${p.contribution}

## 与 Concept-to-Fable 的关系

${p.relation}

## 推荐阅读部分

${p.reading}

## 可借鉴点

${p.borrow}

## 局限与注意事项

${p.limitation}

## 研究导向 Q&A

### 1. 这篇论文解决的问题和 Concept-to-Fable 有什么关系？

${p.relation}

### 2. 它支撑四大支柱中的哪一部分？

它主要支撑 **${p.pillar}**。在 Concept-to-Fable 中，这一部分的任务是${meta.role}

### 3. 我们可以借鉴它的什么方法、数据或评测方式？

${p.borrow}

### 4. 它没有解决什么，因此我们的任务还有什么研究空间？

${p.limitation} 这也正是 Concept-to-Fable 可以继续推进的空间：把论文中的单点能力放进“课程 KG → 结构映射 → 寓言生成 → 教育评价”的完整链路里。

### 5. 如果把它用于“知识点转寓言”，需要怎样改造？

${p.transform}
`);
}

console.log(`Generated ${papers.length} paper pages.`);
