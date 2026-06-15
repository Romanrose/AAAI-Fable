const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', 'src', 'content', 'docs');
const papersDir = path.join(root, 'papers');
const pillarsDir = path.join(root, 'pillars');
const dataDir = path.join(__dirname, '..', 'src', 'data');

fs.mkdirSync(papersDir, { recursive: true });
fs.mkdirSync(pillarsDir, { recursive: true });
fs.mkdirSync(dataDir, { recursive: true });

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

const evidenceMap = {
  'hierarchical-neural-story-generation': [
    'Abstract 和 Introduction 将任务定义为基于 writing prompt 的长文本故事生成，强调长程依赖、主题一致性和提前规划。',
    '论文构建了约 300K prompt-story 数据集，并提出分层生成模型来改善 prompt 相关性。',
    'Evaluation 部分说明作者同时使用自动指标和人工评价，关注故事是否更连贯、更贴合 prompt。',
  ],
  'towards-controllable-story-generation': [
    '论文讨论如何让故事生成受给定事件、角色或目标约束，而不是完全开放式续写。',
    '核心价值在于把“控制变量”引入故事生成，这与教学寓言需要受教学目标约束高度相关。',
    '它没有处理课程知识或映射说明，因此只能作为可控生成思路，而不是完整教学寓言方案。',
  ],
  'plan-and-write': [
    'Abstract 中给出 Title、Storyline、Story 的三层示例，明确把故事生成拆成 storyline planning 和 surface realization。',
    '论文结论和实验说明，显式 storyline planning 能让生成故事更 diverse、coherent、on topic。',
    '它的 storyline 是从句子抽取关键词形成的中间计划，适合改造成“知识步骤到寓言事件”的骨架。',
  ],
  'controllable-plot-reward-shaping': [
    'Introduction 将任务定义为自动 plot generation，并强调给定目标结局下的情节控制。',
    'Evaluation 中报告 reward shaping 能显著提高生成 plot 达成目标的比例，说明目标导向控制是可行的。',
    '论文也承认事件表示不易做人类评价，这提醒 Concept-to-Fable 需要同时保留机器可检验结构和人类可读解释。',
  ],
  'concept-extraction-prerequisite': [
    'Abstract 明确指出 prerequisite relations 对教育应用关键，但自动抽取领域概念和先修关系很困难。',
    '论文提出先抽取高质量短语，再用 graph-based ranking 识别领域概念，并迭代学习 prerequisite relations。',
    'Evaluation 使用中文教材和人工标注评估概念抽取与先修关系学习，说明该方法适合教材知识结构化。',
  ],
  mooccube: [
    'Introduction 描述 MOOCCube 覆盖 700 多门课程、约 100K concepts、学生行为和外部资源。',
    '论文把课程、视频、概念、学生行为和关系组织成多维教育数据仓库，并展示 prerequisite discovery 作为应用。',
    'Conclusion 强调 MOOCCube 支持课程概念、学生活动和教育 NLP 应用，但它面向 MOOC 而不是小学寓言生成。',
  ],
  'automatic-story-generation-survey': [
    'Survey 将 automatic story generation 定义为选择事件或行动序列，使其满足故事标准并能被讲述。',
    'Introduction 指出故事长期用于娱乐、道德教育和儿童教育，提供了教学寓言的叙事合理性。',
    'Conclusion 强调故事生成需要考虑 author goal、角色、情节等复杂属性，支持把教学目标作为生成目标显式建模。',
  ],
  'metaphor-generation-conceptual-mappings': [
    'Abstract 说明论文用 conceptual metaphor theory 控制隐喻生成，并编码 cognitive domains 之间的 conceptual mappings。',
    '方法包含 CM-Lex 和 CM-BART，两者都围绕 source domain 与 target domain 的映射展开。',
    'Evaluation 同时看 metaphoricity 和 conceptual metaphor presence，说明只流畅不够，还要检查映射是否存在。',
  ],
  'moral-stories': [
    'Abstract 将数据集定义为 structured, branching narratives，覆盖 norms、intents、actions、consequences。',
    'Introduction 强调社会情境中的行为需要同时满足目标和规范约束，这可类比教学寓言中的知识目标与故事约束。',
    'Conclusion 指出模型常不能整合 normative constraints，提醒 Concept-to-Fable 也要防止模型忽略知识约束。',
  ],
  'controllable-text-generation-survey': [
    'Survey 将 controllable text generation 形式化为在约束条件下生成自然语言，约束可包含主题、关键词、风格、结构化数据等。',
    '文中举例 story generation 需要匹配 storyline 中关键元素及其顺序。',
    'Evaluation 部分区分人工、自动和半自动评价，支持 Concept-to-Fable 使用多维评价而不是单一指标。',
  ],
  'analogy-generation-llms': [
    'Abstract 定义两个任务：Analogous Concept Generation 和 Analogy Explanation Generation。',
    'Introduction 用 Bohr atom 与 solar system 说明类比依赖结构和关系相似性。',
    'Evaluation 指出 analogy explanation 更难，也更能测试模型的 analogical reasoning，这对寓言映射说明很关键。',
  ],
  storal: [
    'Abstract 将 STORAL 定义为中英文 human-written moral stories 数据集，并提出理解与生成任务。',
    '论文强调 moral story 需要理解 abstract concepts、inter-event discourse relations 和 value preference alignment。',
    'Evaluation 使用 BLEU、BERTScore 等自动指标并结合人工标注，说明寓言类数据集需要任务化评测。',
  ],
  storyanalogy: [
    'Abstract 说明 STORYANALOGY 是 24K story pairs 的大规模 story-level analogy corpus。',
    '论文基于扩展 Structure-Mapping Theory 标注两类相似性，并评估 story-level analogy identification 与 generation。',
    'Introduction 的病毒入侵细胞与盗贼闯入房屋例子，正是“科学机制到故事情境”的结构映射范式。',
  ],
  'educational-material-to-kg': [
    'Abstract 主张 digital educational content 应结构化为 knowledge graphs，以表达概念之间关系。',
    'Introduction 说明 KG 可支持知识导航、语义搜索、个性化学习和 LLM 集成。',
    '论文也指出教育 KG 存在标准化、互操作、数据完整性和规模化挑战，适合作为前处理参考。',
  ],
  legalstories: [
    'Abstract 将任务定义为用 LLM 生成 legal stories 和 comprehension questions，帮助非专家学习复杂法律概念。',
    '论文使用 expert-in-the-loop pipeline 构建 LEGAL STORIES 数据，并用故事与问题支持学习和测评。',
    'Evaluation 设计 randomized controlled trial，将故事学习与概念定义学习对比，直接启发 Concept-to-Fable 的教育有效性验证。',
  ],
  'figurative-language-generation-survey': [
    'Introduction 将 figurative language 解释为包含 metaphor 等多种修辞形式，可帮助表达难以可视化的抽象概念。',
    'Survey 覆盖 metaphor、simile、analogy、personification 等生成任务，为寓言语言层面的表达提供背景。',
    'Evaluation 部分强调自动评价和人工评价各有局限，提示寓言生成也需要人类对教育表达质量做最终把关。',
  ],
  'ss-gen': [
    'Abstract 指出 Social Stories 有严格约束，传统由专家撰写，成本高且多样性有限。',
    'SS-GEN 提出 constraint-driven strategy STAR SOW，用层次化 prompt 生成 social stories。',
    '论文包含质量评估标准和人类/GPT 评价，说明特定用途故事生成必须把领域约束前置进生成流程。',
  ],
  'scientific-concept-analogies': [
    '论文通过两阶段研究考察 LLM 生成教育类比对高中生和教师课堂实践的影响。',
    'Method 部分围绕 biology 和 physics 概念的 LLM-generated analogies，强调教育类比的有效性需要实证研究。',
    'Evaluation 包含学生测试、教师访谈和课堂 field study，并指出类比可能因信息缺失伤害理解。',
  ],
  'multimodal-math-story-generation': [
    'PDF 文本显示该 AIED 文件像 proceedings 合集，抽取结果混入多篇论文，需要人工复核具体目标论文页码。',
    '可确认其中相关内容关注 STEM 教育、学生参与、GenAI、故事化或多模态解释。',
    '因此当前页面只把它作为“数学教育情境化故事生成”的弱证据参考，后续应定位目标论文起止页再精修。',
  ],
  'kg-guided-storytelling': [
    'Abstract 指出 LLM story generation 面临 long-form coherence 和 user-friendly control 挑战。',
    '论文提出 KG-assisted storytelling pipeline，并通过 15 名参与者的 two-stage user study 评估 KG 编辑和故事生成。',
    'Discussion 提到 KG 难以表示内在情绪、心理成长等复杂状态，提示教学寓言 KG 也不能只建外部事件图。',
  ],
  'analogy-annotators': [
    'Abstract 说明论文评估 LLM 作为 story-level analogy annotators 的能力，并关注 base-target entity mapping。',
    'Method 提出 A3E 自动类比标注框架，基于 Structure Mapping Theory 和多阶段 prompting。',
    'Conclusion 报告 A3E 相比现有 LLM 标注有显著提升，但也指出英文场景和部署成本限制。',
  ],
  'llm-story-generation-survey': [
    'Abstract 建立 LLM story generation taxonomy，区分 independent story generation 和 author-assistance。',
    'Survey 比较方法、数据集、故事类型、评价方法和 LLM 使用方式，适合作为 LLM 故事生成 related work 总览。',
    'Conclusion 讨论 LLM-as-a-Judge 与 story-related aspects，如 relevance、coherence、empathy、surprise、engagement、complexity。',
  ],
  'synthetic-moral-fables': [
    'Abstract 说明 TF1-EN-3M 是三百万英语合成道德寓言数据集，由不超过 8B 的开源模型生成。',
    '论文使用 structured prompt template，编码 protagonist、trait、setting、conflict、resolution、moral 等寓言元素。',
    'Evaluation 使用多 LLM judge 评分 grammar、creativity、moral clarity、template adherence，并补充 diversity/readability 指标。',
  ],
  'k12-kgraph': [
    'Abstract/Introduction 明确提出 curriculum cognition，包括 prerequisite chains、concept taxonomies、experiment-concept links 和 pedagogical sequencing。',
    'K12-KGraph 覆盖数学、物理、化学、生物，并包含 Concept、Skill、Experiment、Exercise、Section、Chapter、Book 七类节点和九类关系。',
    '论文将每个 benchmark/training sample 追溯到 specific subgraph，使 difficulty、coverage、factual correctness 更可控。',
  ],
  'classroom-ai': [
    'Abstract 指出 LLM 难以为不同教育阶段学生提供 grade-appropriate responses。',
    '论文整合七个 readability metrics，并构建 grade-specific content generation 数据集。',
    'Evaluation 覆盖多个数据集和 208 名 human participants，报告年级对齐相较 prompt 方法提升 35.64 个百分点且保持准确性。',
  ],
};

function write(file, content) {
  fs.writeFileSync(file, content, 'utf8');
}

function yaml(s) {
  return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function pillarAdvice(p) {
  if (p.pillar === '知识图谱') {
    return {
      output: '把论文中的知识表示方法转化为 Concept-to-Fable 的输入 schema：概念节点、技能节点、先修关系、教材来源、年级、学科、解释目标，以及可生成寓言的候选关系链。',
      evidence: '优先检查它是否提供可复用的数据结构、概念抽取方法、先修关系定义或课程对齐方式。真正有价值的不是“用了 KG”这个标签，而是它能不能让每个寓言都有可追溯的知识依据。',
      action: '建议把它对应到你的 pipeline 第一步：教材或课程标准进入系统后，先生成一张可验证的小型知识子图，再进入寓言映射阶段。实现时不要一开始追求全学科大图，先选一个年级、一个学科、20-50 个知识点做 MVP。',
      risk: '主要风险是 KG 只停留在检索或索引层，不能直接保证故事解释正确。因此使用这类论文时，要额外设计“知识链是否被故事完整覆盖”的检查项。',
    };
  }
  if (p.pillar === '结构映射') {
    return {
      output: '把论文中的类比、隐喻或 story analogy 方法转化为 Concept-to-Fable 的映射说明书：知识实体对应哪个故事角色，知识关系对应哪个情节互动，因果链对应哪个故事转折。',
      evidence: '优先看它是否显式处理 source domain 与 target domain 的对应关系，以及是否能评价这种对应是否稳定。你的任务需要的不是漂亮比喻，而是可以逐句解释的结构映射。',
      action: '建议把它对应到 pipeline 第二步：先让系统产出候选寓言世界和映射表，再生成故事正文。每条故事句子最好能反查到一个知识点或关系，方便后续做人工审核和自动评价。',
      risk: '主要风险是 LLM 会生成听起来合理但结构错位的类比。使用这类论文时，要加入映射忠实性检查，尤其检查角色关系是否改变了原知识点的因果方向。',
    };
  }
  if (p.pillar === '层次化生成') {
    return {
      output: '把论文中的 planning、storyline、controllable generation 或 KG-guided generation 方法转化为两阶段甚至三阶段生成流程：知识链规划、寓言骨架规划、正文扩写与润色。',
      evidence: '优先看它如何避免长文本生成跑偏：是否有中间计划，是否有控制变量，是否能在生成前约束角色、事件、结局和风格。',
      action: '建议把它对应到 pipeline 第三步：不要直接 prompt LLM 写完整寓言，而是先生成“教学目标 → 故事线 → 分段正文”。这样你才能在每个阶段检查知识覆盖、情节连贯和语言难度。',
      risk: '主要风险是生成方法只优化故事流畅度，而没有保证教育准确性。因此使用这类论文时，要把教育约束放进规划阶段，而不是等故事写完后再补救。',
    };
  }
  return {
    output: '把论文中的评价标准、数据标注方式或课堂验证方法转化为 Concept-to-Fable 的质量控制表：知识准确性、映射忠实性、故事可读性、年级适配和教学有效性。',
    evidence: '优先看它如何定义“好”的教育文本或故事文本，以及评价是否只看语言质量，还是能真的测到学习理解、概念掌握和教师可用性。',
    action: '建议把它对应到 pipeline 第四步：每篇寓言生成后都输出评分和诊断，不只给总分，还要说明哪里可能科学不准确、哪里映射不充分、哪里对目标年级太难。',
    risk: '主要风险是评价指标过于通用，只能证明文本流畅，不能证明学生学会了。因此使用这类论文时，要把自动指标、教师审核和学生理解题结合起来。',
  };
}

function qaText(p, meta) {
  const advice = pillarAdvice(p);
  const evidence = evidenceMap[p.slug] || [
    '已根据 PDF 的题名、摘要、方法或实验部分进行初步定位；该条目后续仍建议补充更精确的页码和图表编号。',
  ];
  const evidenceBullets = evidence.map((item) => `- ${item}`).join('\n');
  return `### 1. 这篇论文解决的问题和 Concept-to-Fable 有什么关系？

**原文依据定位**：

${evidenceBullets}

**明确回答**：读完这篇论文后，可以把它理解为 Concept-to-Fable 的一个有证据支撑的模块来源。${p.relation} 更具体地说，它可以放在你的 Concept-to-Fable 流程中，帮助回答“从教材知识到可读寓言”链条里的一个关键问题：输入应该怎样被组织、中间结构应该怎样被约束、或者输出应该怎样被评价。

**对你的研究建议**：阅读这篇论文时，不要只记录它的摘要和模型名称，而要把它拆成三个可复用信息：第一，它假设的输入是什么；第二，它产生的中间表示或输出是什么；第三，它如何证明结果是好的。上面的依据定位已经给出这三类信息的初步来源。把这些内容填进你的系统表格后，就能判断它是直接可用、需要改造，还是只适合作为 related work 背景。

**落地判断**：如果这篇论文的方法能被改造成“知识点输入 → 可解释中间结构 → 寓言文本或评价结果”的一环，它就是核心参考；如果只能生成流畅文本但无法解释映射关系，就只能作为辅助参考。

### 2. 它支撑四大支柱中的哪一部分？

**明确回答**：它主要支撑 **${p.pillar}**。在 Concept-to-Fable 中，这一部分的任务是${meta.role}

**具体作用**：${advice.output}

**建议放置位置**：建议把这篇论文放在网站和论文写作中的“${p.pillar}”小节，而不是泛泛归入故事生成或教育 AI。放置理由不是标题相似，而是 PDF 中确实出现了与该支柱相关的方法、数据、任务定义或评价设计。这样读者能立刻看出它为你的任务解决了哪一类问题，也能看出你的四支柱框架不是事后拼接，而是有明确技术分工。

### 3. 我们可以借鉴它的什么方法、数据或评测方式？

**明确回答**：${p.borrow}

**可执行建议**：${advice.action}

**阅读时要记录的证据**：${advice.evidence} 当前页面已经列出 2-3 条从 PDF 中抽取并阅读后的依据。下一轮精修时，建议继续补充页码、图表编号或章节名，例如数据 schema、模型流程图、评价维度或实验设置。这样别人读你的站点时，不只是看到“可借鉴”，而是知道具体该翻论文哪一节。

### 4. 它没有解决什么，因此我们的任务还有什么研究空间？

**明确回答**：${p.limitation}

**研究空间**：这个判断来自论文自身的任务边界：它虽然提供了上面依据中的方法或数据，但没有完整覆盖“课程 KG → 结构映射 → 寓言生成 → 教育评价”的闭环。你的创新点不一定是重新发明它的方法，而是把它改造为一个面向教学寓言数据集的端到端任务定义，并要求每个生成故事都能说明“为什么这样讲是对的”。

**风险提醒**：${advice.risk} 写 related work 时建议明确说出这篇论文与你的边界：它解决了什么，你继承什么；它没解决什么，你补什么。这样可以减少 reviewer 觉得“只是换了个应用场景”的风险。

### 5. 如果把它用于“知识点转寓言”，需要怎样改造？

**明确回答**：${p.transform}

**改造方案**：建议按三个层次改造。第一，把输入改成课程知识点或 KG 子图，而不是普通主题或自由 prompt。第二，在生成前增加映射表，规定知识实体、关系、因果链分别对应哪些寓言角色、动作和结果。第三，在生成后增加检查器，分别检查科学准确性、映射忠实性、故事完整性和目标年级可读性。

**下一步建议**：如果这篇论文属于核心论文，可以进一步补一个小实验：选一个小学知识点，用它启发的方法生成一版寓言骨架，再人工标注“知识步骤—故事情节”的对应关系。这样它就不只是文献综述里的引用，而会变成你任务设计的实证支撑。对于目前依据定位还不够细的论文，下一步优先补页码、表格编号和原文术语，避免回答停留在二次概括。`;
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

import PaperAsk from '../../../components/PaperAsk.astro';

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

${qaText(p, meta)}

<PaperAsk slug="${p.slug}" title="${yaml(p.title)}" />
`);
}

const contexts = Object.fromEntries(
  papers.map((p) => [
    p.slug,
    {
      title: p.title,
      year: p.year,
      venue: p.venue,
      pillar: p.pillar,
      pdf: p.pdf,
      url: p.url,
      contribution: p.contribution,
      relation: p.relation,
      reading: p.reading,
      borrow: p.borrow,
      limitation: p.limitation,
      transform: p.transform,
      evidence: evidenceMap[p.slug] || [],
    },
  ]),
);
write(path.join(dataDir, 'paperContexts.json'), `${JSON.stringify(contexts, null, 2)}\n`);

console.log(`Generated ${papers.length} paper pages.`);
