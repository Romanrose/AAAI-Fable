const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', 'src', 'content', 'docs');
const papersDir = path.join(root, 'papers');
const pillarsDir = path.join(root, 'pillars');
const dataDir = path.join(__dirname, '..', 'src', 'data');

fs.mkdirSync(papersDir, { recursive: true });
fs.mkdirSync(pillarsDir, { recursive: true });
fs.mkdirSync(dataDir, { recursive: true });

const phaseMeta = {
  图检索与证据: {
    order: 1,
    slug: 'retrieval-evidence',
    title: '01 · 图检索与证据',
    description: '从课程概念出发，检索少量、相关、可引用且具有证据资格的图结构。',
    question: '这个概念应当依据哪些课程事实来讲？',
    input: 'ConceptSeed、年级与学科信息、课程知识图谱和教材来源。',
    method: '当前 M2NA V2 使用目标中心的自适应图检索：先排序并保留一跳证据，只有直连结构不足时才扩展最多八条两跳路径。课程章节桥接只在缺少核心直连关系时用于上下文，不能被引用为机制证据。检索包必须同时保存节点、边、路径、来源、相关性和检索决策。',
    output: '带证据引用、路径和资格标记的 RetrievalPackage。',
    gate: '目标概念已定位；核心证据可追溯；桥接边与机制证据已区分；上下文规模足以支持机制建模且不过载。',
    fallback: '证据不足时调整检索视角或扩展路径；噪声过多时重新排序和门控；不能用通用常识填补缺失的课程证据。',
    role: '为后续机制图提供可引用的课程事实，而不是直接提供故事素材。',
  },
  机制图: {
    order: 2,
    slug: 'mechanism-graph',
    title: '02 · 机制图',
    description: '把检索证据压缩为故事必须保留的条件、过程、作用、变化与结果。',
    question: '目标知识背后有哪些不可丢失、不可倒置的机制结构？',
    input: 'RetrievalPackage、目标概念和机制抽取约束。',
    method: 'M2NA 将证据组织为 MechanismRecord/MechanismGraph：节点表示必须保留的机制成分，有向边表示条件、作用、变化、因果或结果。结构经过严格 schema 校验和人工审核；桥接上下文不能冒充机制边。节点与边 ID 在进入映射后保持稳定，为候选映射和反向对齐提供共同坐标系。',
    output: '已验证并经人工批准的 MechanismGraph，以及证据引用和审核历史。',
    gate: '节点和边均有证据支持；边方向正确；must_preserve 结构明确；不存在无来源机制或未决审核。',
    fallback: '证据不支持时回到图检索；结构抽取错误时重新建图；未批准的机制图不得进入候选映射。',
    role: '固定寓言不能改变的深层知识结构。',
  },
  'Copycat 式候选映射竞争': {
    order: 3,
    slug: 'copycat-mapping-competition',
    title: '03 · Copycat 式候选映射竞争',
    description: '让多个故事域映射方案竞争，用结构覆盖和方向保持选择可验证的 Mapping Plan。',
    question: '怎样把机制角色转换为故事角色，同时不丢失关系结构？',
    input: '已批准的 MechanismGraph、检索上下文和禁用术语。',
    method: '当前主方法是 [LLM-Guided Copycat](/methodology/)：semantic scout 一次提出三个不同故事域的候选，每个候选必须映射全部机制节点和边。确定性验证检查 ID、覆盖、方向和术语泄漏；评分比较覆盖度、载体与关系多样性、叙事骨架和模板风险。元监控只在检测到重复或占位符时允许一次不改变深层结构的修订。标准映射和确定性 Copycat 保留为对照。',
    output: '全部候选及评分、修订轨迹和最终 Validated Mapping Plan。',
    gate: '节点/边全覆盖；所有边方向保持；无未知 ID；禁用术语不泄漏；最终胜者通过硬验证。',
    fallback: '单个候选失败则淘汰或受约束修订；三个候选全部失败则重新提出候选；机制本身有问题则回到机制图。',
    role: '把知识侧结构显式转换为故事侧结构，并保留可审计的候选竞争过程。',
  },
  寓言叙事: {
    order: 4,
    slug: 'fable-narrative',
    title: '04 · 寓言叙事',
    description: '在不改动机制和映射的前提下，将 Mapping Plan 实现为适龄、完整且具有寓言文体的故事。',
    question: '怎样把通过验证的映射计划写成真正可读、可控的教学寓言？',
    input: 'Validated Mapping Plan 的故事侧字段、禁用术语、目标年级和文体约束。',
    method: '生成器读取故事域、角色/物体、冲突、事件链、转折、解决状态及节点/边映射，不直接读取或改写机制事实。故事采用计划先行、正文实现、必要修订的分层流程；传统寓言特征用于约束短叙事、拟人化、行动—后果—寓意结构，多智能体与读者模型文献用于丰富叙事而不授权新增机制。每个概念—策略—候选的版本独立保存。',
    output: '寓言草稿、生成记录、修订版本和候选级审计文件。',
    gate: '正文覆盖映射计划；没有新造机制或术语泄漏；冲突—转折—解决完整；文体和年级要求可检查。',
    fallback: '表层遗漏或表达问题返回正文修订；若故事无法承载映射，则回到候选映射而不是强行润色。',
    role: '把已验证的故事结构实现为儿童可读的寓言文本。',
  },
  反向结构对齐与教育质量评测: {
    order: 5,
    slug: 'reverse-alignment-evaluation',
    title: '05 · 反向结构对齐与教育质量评测',
    description: '从成品故事反向重建结构，检查机制忠实性，并独立评价文体、适龄、公平性与学习价值。',
    question: '故事是否真的保留机制，而且能够安全、清楚地用于教学？',
    input: '寓言草稿、Mapping Plan、MechanismGraph、同批候选和目标学习者信息。',
    method: 'Aligner 从故事中寻找支持机制节点与边的保守证据，计算节点覆盖、边覆盖和方向准确度；规则与 Judge 评价知识忠实、映射清晰、可读性、模板化、泄漏和修订必要性；人工评审保存追加式历史。教育质量还需要年级适配、偏见审计、理解题和后续教师/学生研究，不能由 LLM 总分替代。',
    output: '反向对齐证据、质量分数、硬风险标记、修订建议、接受/修订/拒绝状态和批量报告。',
    gate: '结构可回查；方向正确；无硬泄漏；文体与适龄达到阈值；自动评价的边界被明确报告。',
    fallback: '按失败类型回到叙事、映射、机制图或检索阶段；失败样本和原始版本必须保留。',
    role: '决定样本能否进入数据集，并指出问题应返回哪一个上游阶段。',
  },
};

const phaseAssignments = {
  'hierarchical-neural-story-generation': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'towards-controllable-story-generation': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'plan-and-write': ['寓言叙事', ['机制图']],
  'controllable-plot-reward-shaping': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'concept-extraction-prerequisite': ['图检索与证据', ['机制图']],
  mooccube: ['图检索与证据', ['机制图']],
  'automatic-story-generation-survey': ['寓言叙事', ['机制图', '反向结构对齐与教育质量评测']],
  'metaphor-generation-conceptual-mappings': ['Copycat 式候选映射竞争', ['寓言叙事']],
  'moral-stories': ['机制图', ['寓言叙事', '反向结构对齐与教育质量评测']],
  'controllable-text-generation-survey': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'analogy-generation-llms': ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  storal: ['反向结构对齐与教育质量评测', ['机制图', '寓言叙事']],
  storyanalogy: ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  'educational-material-to-kg': ['图检索与证据', ['机制图']],
  legalstories: ['反向结构对齐与教育质量评测', ['寓言叙事']],
  'figurative-language-generation-survey': ['Copycat 式候选映射竞争', ['寓言叙事', '反向结构对齐与教育质量评测']],
  'ss-gen': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'scientific-concept-analogies': ['反向结构对齐与教育质量评测', ['Copycat 式候选映射竞争']],
  'multimodal-math-story-generation': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'kg-guided-storytelling': ['寓言叙事', ['图检索与证据', '机制图']],
  'analogy-annotators': ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  'llm-story-generation-survey': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'synthetic-moral-fables': ['反向结构对齐与教育质量评测', ['寓言叙事']],
  'k12-kgraph': ['图检索与证据', ['机制图', '反向结构对齐与教育质量评测']],
  'classroom-ai': ['反向结构对齐与教育质量评测', ['寓言叙事']],
  'teaching-through-analogies': ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  'enhanced-story-comprehension': ['机制图', ['反向结构对齐与教育质量评测']],
  morables: ['反向结构对齐与教育质量评测', ['寓言叙事']],
  'narrative-analogy-dimensions': ['Copycat 式候选映射竞争', ['机制图', '反向结构对齐与教育质量评测']],
  'biased-tales': ['反向结构对齐与教育质量评测', ['寓言叙事']],
  'fable-literary-genre': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'arnold-lobel-fable-features': ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'structural-similarity-figurative-language': ['Copycat 式候选映射竞争', ['寓言叙事']],
  'amar-kgqa': ['图检索与证据', ['机制图']],
  'story-of-thought': ['寓言叙事', ['Copycat 式候选映射竞争']],
  'copycat-mental-fluidity-part1': ['Copycat 式候选映射竞争', ['机制图']],
  'copycat-mental-fluidity-part2': ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  'copycat-mental-fluidity-part3': ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  'conceptual-slippage-copycat': ['Copycat 式候选映射竞争', ['机制图']],
  'copycat-reimplementation': ['Copycat 式候选映射竞争', []],
  'abstraction-analogy-ai': ['Copycat 式候选映射竞争', ['反向结构对齐与教育质量评测']],
  storybox: ['寓言叙事', ['反向结构对齐与教育质量评测']],
  'story-generation-reader-models': ['机制图', ['寓言叙事', '反向结构对齐与教育质量评测']],
  'commonsense-kg-axioms': ['机制图', ['图检索与证据', '寓言叙事']],
  'long-story-kg-literary-theory': ['寓言叙事', ['机制图', '反向结构对齐与教育质量评测']],
  creagentive: ['寓言叙事', ['机制图', '反向结构对齐与教育质量评测']],
};

const papers = [
  ['hierarchical-neural-story-generation', 1, 'Hierarchical Neural Story Generation', '2018', 'ACL', '层次化生成', 'StoryGen-01-HierarchicalNeuralStoryGeneration-ACL-2018.pdf', 'https://aclanthology.org/P18-1082/', '提出分层故事生成思路，把故事创作拆成高层规划和低层文本生成。', '它支撑 Concept-to-Fable 中“先有知识逻辑和故事线，再扩写成寓言”的生成路线。', '重点看模型如何处理 prompt、storyline 与长文本生成之间的关系。', '借鉴“规划先行”的思想，把知识图谱中的概念链先转成寓言事件链。', '论文目标是开放故事生成，不保证教育概念的事实准确性或结构映射忠实性。', '需要把自由故事规划替换为受知识点、先修关系和映射说明约束的寓言规划。'],
  ['towards-controllable-story-generation', 2, 'Towards Controllable Story Generation', '2018', 'Workshop on Storytelling', '层次化生成', 'StoryGen-02-ControllableStoryGeneration-Workshop-2018.pdf', 'https://aclanthology.org/W18-1505/', '探索用事件、角色或主题控制故事生成。', '它说明寓言生成不能只依赖自然语言 prompt，而需要显式控制故事要素。', '重点看控制变量如何影响故事情节、角色和目标。', '可借鉴控制信号设计，把教学目标、寓意、概念关系作为生成条件。', '控制目标偏故事层面，没有覆盖学科知识点与情节之间的可解释对齐。', '需要把控制条件扩展为“概念-角色-关系-情节”的结构化约束。'],
  ['plan-and-write', 3, 'Plan-and-Write: Towards Better Automatic Storytelling', '2019', 'AAAI', '层次化生成', 'Method-01-PlanAndWrite-AAAI-2019.pdf', 'https://ojs.aaai.org/index.php/AAAI/article/view/4726', '提出先生成 storyline 再扩写故事的两阶段框架。', '这是 Concept-to-Fable 生成流程的核心技术参照：先把知识点逻辑规划成故事线。', '重点看 storyline 的形式、规划阶段和生成阶段如何衔接。', '可把 KG 路径或概念解释步骤转成 storyline，再让 LLM 扩写。', '原方法没有教育目标、年龄适配和映射忠实性约束。', '需要把 storyline 从关键词序列升级为带概念对齐字段的寓言骨架。'],
  ['controllable-plot-reward-shaping', 4, 'Controllable Neural Story Plot Generation via Reward Shaping', '2019', 'IJCAI', '层次化生成', 'StoryGen-03-ControllablePlotRewardShaping-IJCAI-2019.pdf', 'https://www.ijcai.org/proceedings/2019/829', '通过奖励塑形控制故事情节发展。', '它启发我们把教学约束转化为可优化的生成目标。', '重点看 reward 如何定义故事目标和情节偏好。', '可以把“覆盖概念关系”“不引入科学错误”“适合年级”设计成奖励或打分项。', '奖励主要服务情节控制，不直接处理课程知识和寓言映射。', '需要设计教育导向 reward，例如概念覆盖率、映射一致性和阅读难度。'],
  ['concept-extraction-prerequisite', 5, 'Concept Extraction and Prerequisite Relation Learning from Educational Data', '2019', 'AAAI', '知识图谱', 'Method-05-ConceptExtractionPrerequisite-AAAI-2019.pdf', 'https://ojs.aaai.org/index.php/AAAI/article/view/5033', '研究从教育数据中抽取概念并学习前置依赖关系。', '它直接支撑 Concept-to-Fable 的知识图谱构建：先知道讲哪个概念、依赖哪些前置知识。', '重点看概念抽取和 prerequisite relation 的建模方式。', '可用于从教材中自动抽取知识点和先修链，形成寓言生成输入。', '论文关注知识结构发现，不负责把知识结构转成故事。', '需要把抽取到的概念和先修关系转为寓言角色、冲突和解决路径。'],
  ['mooccube', 6, 'MOOCCube: A Large-scale Data Repository for NLP Applications in MOOCs', '2020', 'ACL', '知识图谱', 'KG-01-MOOCCube-ACL-2020.pdf', 'https://aclanthology.org/2020.acl-main.285/', '构建面向 MOOC 场景的大规模教育数据仓库。', '它展示了教育资源、概念和学习行为如何被组织成可计算资源。', '重点看数据 schema、概念资源和教育 NLP 应用方式。', '可借鉴数据组织方式，为小学知识点、教材段落和生成寓言建立统一索引。', 'MOOC 场景与小学全学科教材不同，且不面向寓言生成。', '需要转换到 K-12 课程标准，并补充寓言生成所需的映射与故事字段。'],
  ['automatic-story-generation-survey', 7, 'Automatic Story Generation: A Survey of Approaches', '2021', 'ACM Computing Surveys', '层次化生成', 'StoryGen-04-AutomaticStoryGenerationSurvey-ACMCSUR-2021.pdf', 'https://dl.acm.org/doi/10.1145/3453156', '系统综述自动故事生成方法。', '它提供故事生成技术谱系，帮助定位 Concept-to-Fable 不是普通故事生成，而是教育约束下的寓言生成。', '重点看规划式、神经式、受控式故事生成的比较。', '可用于 related work 中梳理从 general story generation 到 educational fable generation 的演化。', '综述覆盖面广，但没有深入处理知识图谱驱动和教育评测。', '需要将其中的生成方法按“是否支持知识约束和映射解释”重新分类。'],
  ['metaphor-generation-conceptual-mappings', 8, 'Metaphor Generation with Conceptual Mappings', '2021', 'ACL-IJCNLP', '结构映射', 'Method-02-MetaphorConceptualMappings-ACL-2021.pdf', 'https://aclanthology.org/2021.acl-long.524/', '研究基于概念映射生成隐喻表达。', '它支撑“知识概念到寓言世界”的跨域映射思想。', '重点看 source domain 与 target domain 的映射如何表达。', '可借鉴概念映射，把科学实体映射为寓言角色，把关系映射为互动。', '隐喻通常较短，不等同于有完整情节和教育目标的寓言。', '需要把短语级或句子级隐喻扩展为多事件寓言结构。'],
  ['moral-stories', 9, 'Moral Stories: Situated Reasoning about Norms, Intents, Actions, and their Consequences', '2021', 'EMNLP', '评测', 'Evaluation-01-MoralStories-EMNLP-2021.pdf', 'https://aclanthology.org/2021.emnlp-main.54/', '构建道德故事数据集，强调规范、意图、行动和结果。', '它帮助区分寓言中的“道德寓意”和 Concept-to-Fable 中的“知识寓意”。', '重点看故事如何连接情境、行为、后果和规范判断。', '可借鉴故事结构字段，为教育寓言加入情境、冲突、行动、结论。', '它关注道德推理，不关注科学概念解释和课程知识对齐。', '需要把 moral norm 替换为 learning objective，把行为后果映射为知识机制。'],
  ['controllable-text-generation-survey', 10, 'A Survey of Controllable Text Generation using Transformer-based Pre-trained Language Models', '2022', 'arXiv', '层次化生成', 'StoryGen-05-ControllableTextGenerationSurvey-arXiv-2022.pdf', 'https://arxiv.org/abs/2201.05337', '综述 Transformer 时代的可控文本生成方法。', '它支撑生成端控制策略选择，例如属性控制、规划控制和解码控制。', '重点看不同控制方法的输入形式、控制粒度和代价。', '可用于选择控制教学目标、年级难度、寓言风格的技术路线。', '综述不专门讨论故事结构和教育准确性。', '需要从通用可控生成中筛选适合长文本寓言和知识约束的方法。'],
  ['analogy-generation-llms', 11, 'Analogy Generation by Prompting Large Language Models: A Case Study of InstructGPT', '2022', 'INLG', '结构映射', 'Method-03-AnalogyGenerationLLMs-INLG-2022.pdf', 'https://aclanthology.org/2022.inlg-main.25/', '研究用 LLM prompt 生成类比。', 'Concept-to-Fable 本质上需要稳定生成“知识点到寓言情境”的类比。', '重点看 prompt 如何诱导类比，以及类比质量如何评估。', '可借鉴 prompt 设计，让模型提出候选寓言世界和角色映射。', '单纯 prompting 难以保证映射忠实性和教学准确性。', '需要加入 KG 约束、对齐检查和人工/模型评审环节。'],
  ['storal', 12, 'A Corpus for Understanding and Generating Moral Stories', '2022', 'NAACL', '评测', 'Evaluation-02-STORAL-NAACL-2022.pdf', 'https://aclanthology.org/2022.naacl-main.374/', '提供理解和生成道德故事的语料资源。', '它是构建寓言故事数据集时的重要参考，尤其是故事结构和寓意标注。', '重点看数据字段、任务定义和故事评价。', '可借鉴语料标注方式，为每个寓言标注情境、行为、结果和知识点。', '道德故事不等同于知识解释故事，缺少概念映射说明。', '需要把道德标签改造为知识概念、先修关系和解释步骤标签。'],
  ['storyanalogy', 13, 'STORYANALOGY: Deriving Story-level Analogies from Large Language Models', '2023', 'EMNLP', '结构映射', 'Core-05-STORYANALOGY-EMNLP-2023.pdf', 'https://aclanthology.org/2023.emnlp-main.706/', '研究从 LLM 中获得故事级类比。', '它是 Concept-to-Fable 的核心参照：寓言不是一句类比，而是故事级结构映射。', '重点看故事级 analogy 的构造、推理和评价。', '可借鉴故事级映射框架，用于说明每个知识步骤对应哪个情节。', '它不一定以课程知识和小学教学目标为输入。', '需要把 story analogy 约束到 KG 驱动的知识解释，并输出映射说明书。'],
  ['educational-material-to-kg', 14, 'Educational Material to Knowledge Graph Conversion', '2024', 'KaLLM Workshop', '知识图谱', 'Method-04-EducationalMaterial2KG-KaLLM-2024.pdf', 'https://aclanthology.org/2024.kallm-1.9/', '研究将教育材料转换为知识图谱。', '它直接服务“从教材到 KG”的前处理阶段。', '重点看教育文本如何被解析为实体、关系和图结构。', '可用于把教材章节转成 Concept-to-Fable 的输入图。', '转换后的 KG 不自动等价于可讲故事的结构。', '需要在 KG 上增加故事化字段，如角色候选、冲突类型和解释顺序。'],
  ['legalstories', 15, 'Leveraging Large Language Models for Learning Complex Legal Concepts through Storytelling', '2024', 'ACL', '评测', 'Core-01-LegalStories-ACL-2024.pdf', 'https://aclanthology.org/2024.acl-long.388/', '用 LLM 通过故事帮助学习复杂法律概念。', '它与 Concept-to-Fable 最接近：都使用故事解释复杂知识。', '重点看复杂概念如何被转化为故事，以及学习效果如何验证。', '可借鉴“复杂概念故事化”的任务叙事和用户评价设计。', '法律概念与小学全学科知识不同，且未必强调寓言式映射和 KG 驱动。', '需要把领域从法律扩展到 K-12，并把故事化进一步约束为寓言化。'],
  ['figurative-language-generation-survey', 16, 'A Survey on Automatic Generation of Figurative Language', '2024', 'ACM Computing Surveys', '结构映射', 'Figurative-01-FigurativeLanguageGenerationSurvey-ACMCSUR-2024.pdf', 'https://dl.acm.org/', '综述比喻、隐喻等修辞语言自动生成。', '寓言生成依赖修辞和跨域表达，这篇能提供语言层面的背景。', '重点看 figurative language 的类型、生成方法和评价。', '可用于说明 Concept-to-Fable 与 metaphor/analogy generation 的区别。', '修辞生成通常不要求完整教学闭环。', '需要把修辞表达与课程知识、故事结构和学习目标绑定。'],
  ['ss-gen', 17, 'SS-GEN: A Social Story Generation Framework with Large Language Models', '2025', 'AAAI', '层次化生成', 'Core-02-SSGEN-AAAI-2025.pdf', 'https://ojs.aaai.org/', '提出面向 social story 的 LLM 生成框架。', '它展示了特定用途故事生成如何定义约束、流程和评价。', '重点看框架如何组织输入、生成和质量控制。', '可借鉴任务化故事生成框架，把 social goal 替换为 learning objective。', 'social story 和 educational fable 的目标不同，不能直接迁移评价指标。', '需要换成知识准确性、映射忠实性和年级适配指标。'],
  ['scientific-concept-analogies', 18, 'Unlocking Scientific Concepts: How Effective Are LLM-Generated Analogies for Student Understanding and Classroom Practice?', '2025', 'CHI', '评测', 'Evaluation-04-ScientificConceptAnalogies-CHI-2025.pdf', 'https://dl.acm.org/', '研究 LLM 生成科学概念类比对学生理解和课堂实践的作用。', '它直接支撑 Concept-to-Fable 的教育有效性问题。', '重点看学生理解、教师实践和类比质量如何被评估。', '可借鉴教育场景评测，把寓言质量和学习效果连接起来。', '类比不一定是完整寓言，也未必有 KG 驱动。', '需要把单个 analogy 扩展为带情节、寓意和映射说明的寓言。'],
  ['multimodal-math-story-generation', 19, 'Multimodal Story Generation Using Generative AI for Contextualised Mathematics Education', '2025', 'AIED', '评测', 'Education-01-MultimodalMathStoryGeneration-AIED-2025.pdf', 'https://link.springer.com/', '论文提出面向儿童数学问题的个性化多模态故事系统：Teacher、Planner、Writer 三个智能体依次求解、规划和写作，并结合图像生成与互动学习。', '它提供了“知识求解—故事规划—正文实现—迁移练习”的具体教育故事生成参照。', '重点看 PDF 第 452–457 页的 REACT/启发式学习依据、三智能体框架、60 个数学问题实验和七维评价。', '借鉴 Teacher/Planner/Writer 分工、逐步揭示答案、故事内应用题与跨情境迁移题。', '当前结果主要来自 Gemini 与 GPT-4o 的自动评判；同理心和参与度改善有限，惊喜度仍低，儿童与教师用户研究尚属未来工作。', '将数学求解计划替换为已审核 MechanismGraph 与 Mapping Plan，并用反向结构对齐和真实学习评测补足自动评分。'],
  ['kg-guided-storytelling', 20, 'Guiding Generative Storytelling with Knowledge Graphs', '2025', 'arXiv', '知识图谱', 'Core-04-KGGuidedStorytelling-arXiv-2025.pdf', 'https://arxiv.org/abs/2505.24803', '研究用知识图谱指导生成式故事创作。', '它正好连接 KG 和 storytelling，是 Concept-to-Fable 的关键技术桥梁。', '重点看 KG 如何影响故事内容、连贯性和可控性。', '可借鉴 KG-guided generation，把课程 KG 节点和边作为故事生成约束。', '普通 KG storytelling 不一定关注教育准确性和寓言映射。', '需要把 KG 从开放知识图谱换成课程图谱，并增加映射忠实性评估。'],
  ['analogy-annotators', 21, 'Can Language Models Serve as Analogy Annotators?', '2025', 'Findings of ACL', '结构映射', 'Evaluation-03-AnalogyAnnotators-ACLFindings-2025.pdf', 'https://aclanthology.org/', '评估语言模型能否作为类比标注者。', 'Concept-to-Fable 需要判断寓言映射是否合理，这篇提供自动评审启发。', '重点看 analogy annotation 的标准和模型可靠性。', '可借鉴让 LLM 辅助标注概念-故事对应关系。', 'LLM 标注存在偏差，不能完全替代专家和教师评估。', '需要设计多角色评审：知识专家、教师、模型共同检查映射。'],
  ['llm-story-generation-survey', 22, 'A Survey on LLMs for Story Generation', '2025', 'Findings of EMNLP', '层次化生成', 'StoryGen-06-LLMStoryGenerationSurvey-EMNLPFindings-2025.pdf', 'https://aclanthology.org/', '综述 LLM 时代故事生成方法和挑战。', '它帮助定位 LLM 在 Concept-to-Fable 中适合作为生成器，而不是唯一控制器。', '重点看 LLM story generation 的可控性、评价和一致性问题。', '可用于写 related work，说明为什么需要 KG 和显式映射来约束 LLM。', '综述本身不提供具体教育寓言数据集方案。', '需要把 LLM 故事生成问题转化为 KG-conditioned educational fable synthesis。'],
  ['synthetic-moral-fables', 23, 'TF1-EN-3M: Three Million Synthetic Moral Fables from Open Language Models', '2025', 'arXiv', '评测', 'Fable-01-SyntheticMoralFables-arXiv-2025.pdf', 'https://arxiv.org/abs/2504.20605', '构建大规模合成道德寓言数据。', '它说明大规模寓言数据集是可行的，但 Concept-to-Fable 更强调知识映射。', '重点看数据生成流程、过滤策略和寓言质量控制。', '可借鉴大规模生成和筛选 pipeline。', '道德寓言不是学科知识寓言，数据量大不等于教学准确。', '需要为每篇寓言加入知识点、概念链、映射说明和年级标签。'],
  ['k12-kgraph', 24, 'K12-KGraph: A Curriculum-Aligned Knowledge Graph for Benchmarking and Training Educational LLMs', '2026', 'arXiv', '知识图谱', 'Core-03-K12KGraph-arXiv-2026.pdf', 'https://arxiv.org/abs/2605.09635', '构建课程对齐的 K-12 知识图谱，用于教育 LLM 训练和评测。', '它主要支撑第一阶段的课程图检索与证据组织，并为第二阶段机制图提供课程认知结构。', '重点看 concept、skill、prerequisite 和 curriculum alignment 的定义。', '可直接作为小学全学科知识图谱构建和任务输入设计的参照。', 'KG 本身不解决故事化、寓言化和语言生成质量。', '需要在 K12-KGraph 之上增加“可寓言化”的结构映射层。'],
  ['classroom-ai', 25, 'Classroom AI: Large Language Models as Grade-Specific Teachers', '2026', 'npj Artificial Intelligence', '评测', 'Evaluation-05-ClassroomAI-npjAI-2026.pdf', 'https://www.nature.com/npjai/', '研究 LLM 作为分年级教师时的表现与适配。', '它支撑 Concept-to-Fable 的“因材施教”和年级阅读适配。', '重点看 grade-specific teaching、可读性和教学质量评价。', '可借鉴年级适配指标，为寓言生成设定小学 1-2、3-4、5-6 年级版本。', '它关注教师式回答，不一定生成寓言或映射说明。', '需要把教师回答标准转为寓言文本的可读性、解释性和知识准确性标准。'],
  ['teaching-through-analogies', 26, 'Teaching Through Analogies: A Modular Pipeline for Educational Analogy Generation', '2026', 'BEA', '结构映射', 'Education-02-TeachingThroughAnalogies-BEA-2026.pdf', '', '摘要提出由源域发现、子概念生成、解释生成和评价组成的模块化教育类比流程，并用结构映射理论分析阶段间影响。', '它直接支持把机制图拆成可对齐的子概念，再寻找寓言源域并生成映射解释。', '重点看 sub-concept grounding、开放/封闭源域检索和 LLM-as-a-judge 与人工排序的一致性。', '借鉴分阶段类比生成和子概念配对，把当前节点/边映射进一步组织为可评价的教育解释。', '论文生成教育类比而非完整寓言，且开放式源域生成仍明显弱于人类。', '在其四阶段之后增加寓言文体规划、故事生成和反向结构对齐。'],
  ['enhanced-story-comprehension', 27, 'Enhanced Story Comprehension for Large Language Models through Dynamic Document-Based Knowledge Graphs', '2022', 'AAAI', '评测', 'Evaluation-06-EnhancedStoryComprehension-AAAI-2022.pdf', '', '摘要用从故事动态抽取的知识图增强长篇故事问答和补全，并提出长文问答任务与更稳定的故事补全评价。', '它为完成寓言后的反向理解提供参照：先从故事重建事实图，再与原机制图比较。', '重点看动态文档知识图如何构造信息密集提示，以及故事问答和补全的评价设置。', '借鉴故事侧动态图作为反向对齐中间表示，减少只靠整体文本打分的不可解释性。', '论文关注长篇理解与上下文窗口，不直接检查教学机制是否保持。', '把动态故事图的实体/关系与 MechanismGraph 的节点/边做显式对齐。'],
  ['morables', 28, 'MORABLES: Moral Reasoning in LLMs with Fables', '2025', 'EMNLP', '评测', 'Fable-02-MORABLES-EMNLP-2025.pdf', '', '摘要构建经人工核验的寓言与短篇故事道德推理基准，用多选题、强干扰项和对抗变体测试深层寓意推断。', '它说明模型即使能回答阅读理解题，也可能依赖表面模式而不真正理解寓意。', '重点看 moral inference、多选干扰项、对抗改写和模型自相矛盾分析。', '借鉴“寓言—理解题—对抗题”设计，为生成寓言配套概念理解测试。', '道德推理不等于学科机制理解，且基准主要评价理解模型而非生成质量。', '把 moral choice 替换为机制判断、因果方向和迁移问题。'],
  ['narrative-analogy-dimensions', 29, 'Dimensions of Analogy in Narratives', '2022', 'IJCAI Workshop', '结构映射', 'Fable-03-NarrativesDimensionsAnalogy-IJCAIWorkshop-2022.pdf', '', '摘要提出叙事类比的六个维度，标注寓言语料并设计四类递增难度的类比推理任务。', '它为候选映射竞争提供比单一相似度更细的结构评价维度。', '重点看六维类比定义、寓言标注方案和语言模型/神经符号方法的有限表现。', '借鉴多维标注表检查角色、事件、因果和高阶关系是否共同保持。', '论文侧重叙事理解与类比评价，没有生成教育寓言的端到端流程。', '把六维类比标签接入候选评分和反向对齐报告。'],
  ['biased-tales', 30, 'Biased Tales: Cultural and Gender Stereotypes in LLM-Generated Children Stories', '2025', 'EMNLP', '评测', 'Fable-04-BiasedTales-EMNLP-2025.pdf', '', '摘要分析 LLM 儿童故事中由性别与文化身份触发的角色属性和主题偏差，并报告显著的外貌与文化刻板差异。', '它补足教育质量中的公平性和儿童叙事安全，不应只评价流畅度与结构覆盖。', '重点看受控提示、角色属性分析和不同文化/性别条件下的差异指标。', '增加角色能动性、职业/外貌分配、文化刻板印象和群体差异审计。', '研究对象是个性化睡前故事，并不直接处理学科知识忠实性。', '在不改变机制映射的前提下，对故事载体和语言实现增加偏见检查。'],
  ['fable-literary-genre', 31, 'La Fable En Tant Qu’un Genre Littéraire Et L’analyse De Fable', '2013', 'Turkish Studies', '寓言文体', 'Fable-05-FableLiteraryGenre-TurkishStudies-2013.pdf', '', '摘要将寓言界定为兼具教诲与娱乐功能的文学体裁，强调动物、拟人化行动、行为后果和儿童教育价值。', '它帮助明确输出为什么是寓言，而不只是带知识点的普通故事。', '重点看寓言定义、动物角色的功能、行为—结果—教训结构及儿童文学定位。', '把短叙事、拟人化、行动后果和明确但不过度说教的寓意转化为文体约束。', '文章以传统道德寓言为中心，没有讨论科学机制或自动生成。', '保留传统文体功能，同时将道德教训扩展为可回查的知识寓意。'],
  ['arnold-lobel-fable-features', 32, 'Arnold Lobel’s Fables and Traditional Fable Features', '1993', 'Children’s Folklore Review', '寓言文体', 'Fable-06-ArnoldLobelTraditionalFableFeatures-CFR-1993.pdf', '', '文章比较 Arnold Lobel 的文学寓言与传统寓言特征，讨论寓言作为民间叙事与文学创作之间的互文关系。', '它提醒文体规则不能被简化为“动物会说话”，还涉及短小形式、类型变体、传统母题和重述关系。', '重点看 fable set、传统母题、文学改写和民间/书面体裁边界。', '借鉴文体特征清单，区分必要结构、常见传统和可创新的表层实现。', '文章是文体个案研究，不提供计算模型或教育效果实验。', '把定性文体特征转成生成提示与人工评审表，而不把其误作硬科学规则。'],
  ['structural-similarity-figurative-language', 33, 'Structural Similarity in Figurative Language: A Preliminary Cognitive Analysis', '2023', 'Lingua', '结构映射', 'Fable-07-StructuralSimilarityFigurativeLanguage-Lingua-2023.pdf', '', '摘要区分实体结构与情境/事件结构相似性，并说明高层结构相似如何形成寓言、parable 与 allegory-like narrative。', '它为“知识机制—寓言情节”提供认知语言学解释：关键是关系结构而非表面对象相似。', '重点看不同抽象层级的结构相似、转喻参与和寓言式叙事例子。', '借鉴高层结构相似层级，解释为什么某个故事域能承载目标机制。', '文章是初步认知分析，没有自动候选生成或量化评价。', '把结构相似类型编码进候选理由和反向对齐标签。'],
  ['amar-kgqa', 34, 'Harnessing Large Language Models for Knowledge Graph Question Answering via Adaptive Multi-Aspect Retrieval-Augmentation', '2025', 'AAAI', '知识图谱', 'KG-02-Amar-KGQuestionAnswering-AAAI-2025.pdf', '', '摘要提出 Amar：联合检索实体、关系和子图，以自对齐减少多视角噪声，并用相关性门控选择真正有助于回答的知识。', '它直接启发图检索阶段不要把所有邻居无差别塞入上下文，而应对实体、关系和路径进行对齐与门控。', '重点看 multi-aspect retrieval、self-alignment、relevance gating 及其对 WebQSP/CWQ 的改善。', '借鉴多视角检索与软门控，为 RetrievalPackage 增加证据相关性和噪声抑制。', '论文解决通用 KGQA，不处理课程证据、机制抽取或寓言生成。', '把问题相关性改成教学概念相关性，并保留课程来源和机制证据资格。'],
  ['story-of-thought', 35, 'Story of Thought: Narrative Reasoning with Analogy and Metaphor', '2025', 'ACL', '层次化生成', 'Method-06-StoryOfThought-AnalogyAngle-ACL-2025.pdf', '', '摘要提出 Story of Thought，通过围绕问题构造带隐喻和类比的叙事来提升物理、化学和生物推理表现。', '它支持把叙事视为组织因果信息的推理中间层，而不只是最终展示格式。', '重点看叙事推理提示、类比/隐喻标注和在科学任务上的增益。', '借鉴“先构造解释叙事再求解”的思路，但将其置于已验证机制图之后。', '任务目标是提高问题求解准确率，不要求生成寓言或保持显式映射。', '让叙事生成受 Mapping Plan 约束，并用反向对齐验证类比没有改写机制。'],
  ['copycat-mental-fluidity-part1', 36, 'The Copycat Project: Mental Fluidity, Part I', '1995', 'Book excerpt', '结构映射', 'Method-07-CopycatProject-MentalFluidity-1995-Part1.pdf', '', '该材料是 Copycat 理论书籍的分卷节选，没有独立论文摘要；内容围绕角色优先的对应、概念光晕、概念滑动与多种相互竞争的类比压力。', '它是当前 Copycat-inspired 候选竞争与角色映射思想的理论来源。', '结合中文转换稿阅读 Seek-Whence/Copycat 类比谜题、对象一致性与结构角色冲突。', '借鉴“角色比对象字面身份更重要”和情境诱导概念滑动的原则。', '书籍讨论微领域认知架构，不能直接当作当前 LLM 方法的实验结果。', '将理论原则转成可验证的机制节点/边映射，并明确 MVP 与完整 Copycat 的差距。'],
  ['copycat-mental-fluidity-part2', 37, 'The Copycat Project: Mental Fluidity, Part II', '1995', 'Book excerpt', '结构映射', 'Method-07-CopycatProject-MentalFluidity-1995-Part2.pdf', '', '该分卷没有独立摘要，延续 Copycat 对 Slipnet、Workspace、Coderack、温度和并行微代理互动的系统说明。', '它为候选竞争、结构压力与元监控的架构解释提供背景。', '重点看概念网络、局部结构构建、代码元竞争和温度如何调节探索。', '借鉴多候选并行竞争、上下文敏感评分和不确定性反馈。', '当前项目并未实现完整 coderack、动态 slipnet 或非单调温度循环。', '只把已经落地的结构门控称为 Copycat-inspired，不夸大为完整复现。'],
  ['copycat-mental-fluidity-part3', 38, 'The Copycat Project: Mental Fluidity, Part III', '1995', 'Book excerpt', '结构映射', 'Method-07-CopycatProject-MentalFluidity-1995-Part3.pdf', '', '该分卷没有独立摘要，集中展示 Copycat 运行、类比选择的涌现过程及不同压力下的答案分布。', '它提示候选映射实验不仅应报告单个胜者，还应保存候选分布与选择轨迹。', '重点看具体运行案例、答案频率、温度变化和错误/意外类比。', '借鉴候选级审计、失败案例分析和策略间分布比较。', '字母串微领域的统计行为不能直接外推到开放域中文寓言。', '用多概念、多策略和人工评审验证候选竞争是否带来实际质量收益。'],
  ['conceptual-slippage-copycat', 39, 'Conceptual Slippage and Analogy-Making: A Report on the Copycat Project', '1988', 'Technical report', '结构映射', 'Method-08-ConceptualSlippage-Copycat-1988.pdf', '', '文章说明知觉与重叠、联想和情境敏感的概念系统如何产生概念滑动，并用 Copycat 字母串运行展示灵活类比。', '它为允许故事载体变化、同时保持关系角色提供最直接的理论依据。', '重点看 conceptual slippage、微领域问题和知觉机制与概念系统的互动。', '借鉴受限概念滑动：表层角色可变，必须保留的机制身份和方向不可变。', '微领域的灵活性来自完整认知架构，不能用一次 LLM 提示等同替代。', '将滑动范围写成显式允许/禁止约束，并保存每次映射决策。'],
  ['copycat-reimplementation', 40, 'A Reimplementation of the Copycat Project', '2018', 'arXiv', '结构映射', 'Method-09-CopycatReimplementation-arXiv-2018.pdf', '', '摘要报告用 DrRacket 重新解释和实现 Copycat，并讨论 Workspace、Coderack、Slipnet 等认知架构组件的实现收益与局限。', '它适合作为完整 Copycat 对照实现的工程参考。', '重点看函数抽象、命名/初始化、结构引用和三大组件如何对应原架构。', '借鉴可复现的模块边界，为确定性 Copycat 对照路线建立清楚接口。', '论文是工作中预印本，且实现质量与开放域适用性需要独立验证。', '只用于对照和架构检查，不把其字母串结果当作寓言映射效果证据。'],
  ['abstraction-analogy-ai', 41, 'Abstraction and Analogy-Making in Artificial Intelligence', '2021', 'arXiv', '结构映射', 'Method-10-AbstractionAnalogyAI-arXiv-2021.pdf', '', '摘要综述符号方法、深度学习和概率程序归纳在概念抽象与类比上的优势和局限，并提出挑战任务与评价方向。', '它帮助定位 concept2fable 的结构映射贡献：需要可量化、可迁移且不只依赖表面相似。', '重点看不同范式的比较，以及对人类式抽象/类比评测的建议。', '借鉴跨域泛化、系统性与可解释性作为映射方法的高级评价目标。', '综述指出现有系统距离人类类比仍远，不能据此宣称 LLM 已解决抽象。', '把主张限制在当前机制图和寓言域，并设计超出模板复用的挑战集。'],
  ['storybox', 42, 'StoryBox: Collaborative Multi-Agent Simulation for Hybrid Bottom-Up Long-Form Story Generation', '2026', 'AAAI', '层次化生成', 'StoryGen-07-StoryBox-AAAI-2026.pdf', '', '摘要提出混合自底向上的多智能体故事生成：角色在动态沙盒中互动产生涌现事件，再以顶层场景维持长篇方向。', '它为从固定寓言骨架到更自然角色互动提供生成端对照。', '重点看动态环境、角色行为、涌现事件和超过一万词的连贯性评价。', '借鉴受边界约束的角色互动来丰富情节，但不让涌现事件改变机制图。', '长篇开放故事目标与短篇教学寓言不同，涌现性也可能破坏知识忠实。', '把沙盒限制在 Mapping Plan 的事件状态和方向约束内，仅用于表层叙事多样化。'],
  ['story-generation-reader-models', 43, 'Guiding Neural Story Generation with Reader Models', '2021', 'arXiv', '层次化生成', 'StoryGen-09-GuidingStoryGeneration-ReaderModels-arXiv-2021.pdf', '', '摘要提出 StoRM：用知识图表示读者对故事世界的概念、实体和关系信念，指导故事保持连贯并达到目标世界状态。', '它连接了生成控制与读者理解，可用于显式建模学生读到每一步后应形成的概念状态。', '重点看 reader model KG、目标世界状态、情节合理性和 staying-on-topic 评价。', '借鉴读者状态作为叙事规划约束和教育理解检查的中间变量。', '模型面向一般神经故事生成，并不保证课程知识或寓言文体。', '把目标世界状态改成学习目标与机制理解状态，并接受人工/学生验证。'],
  ['commonsense-kg-axioms', 44, 'Generating Stories with Commonsense Knowledge Graphs and Axioms', '2021', 'CSKB', '知识图谱', 'StoryGen-10-CommonsenseKGAxioms-CSKB-2021.pdf', '', '摘要把常识公理与常识知识图结合，生成带常识解释的大规模故事，并用众包评价合理性与趣味性。', '它说明故事机制除了课程证据，还需要区分可补充的常识背景与不可改动的目标机制。', '重点看故事类型—公理对齐、知识图查询、大规模生成和解释性探测任务。', '借鉴“机制证据层/常识补全层”分层，避免常识替代课程事实。', '常识图可能含噪声和文化偏差，且故事公理不等同于学科机制。', '对常识只授予叙事辅助资格，不允许其作为机制边证据。'],
  ['long-story-kg-literary-theory', 45, 'Long Story Generation via Knowledge Graph and Literary Theory', '2025', 'arXiv', '层次化生成', 'StoryGen-11-LongStoryGeneration-KGLiteraryTheory-arXiv-2025.pdf', '', '摘要用多智能体、长短期记忆、文学叙事障碍框架和故事知识图缓解长篇生成的主题漂移与情节乏味。', '它为叙事阶段的记忆、障碍设计和写作—读者修订回路提供参考。', '重点看长短期记忆、主题障碍、故事知识图和多智能体反馈。', '借鉴受机制约束的障碍/转折生成与独立修订记录。', '面向数千词长篇故事，质量目标与短篇教学寓言不同。', '缩短到寓言尺度，只保留能增强因果可见性而不制造新机制的叙事障碍。'],
  ['creagentive', 46, 'CreAgentive: An Agent Workflow Driven Multi-Category Creative Generation Engine', '2025', 'arXiv', '层次化生成', 'StoryGen-12-CreAgentive-arXiv-2025.pdf', '', '摘要提出以知识图 Story Prototype 分离故事逻辑与文体实现，并用初始化、生成、写作三阶段多智能体工作流支持长篇多体裁创作。', '它与本项目“先固定结构、再实现文体”的分层思想高度一致。', '重点看 Story Prototype 三元组、长短期目标、多智能体对话和文体写作分离。', '借鉴结构原型与表层实现解耦，但用 Mapping Plan 取代开放式故事原型。', '论文强调长篇与多类型创作，没有教育知识保真和儿童评测。', '把其生成架构接入已验证映射之后，并以反向对齐和教育质量作为通过门槛。'],
].map(([slug, order, title, year, venue, legacyTheme, pdf, url, contribution, relation, reading, borrow, limitation, transform]) => {
  const assignment = phaseAssignments[slug];
  if (!assignment) throw new Error(`Missing five-phase assignment for ${slug}`);
  const [phase, secondaryPhases] = assignment;
  if (!phaseMeta[phase]) throw new Error(`Unknown primary phase ${phase} for ${slug}`);
  for (const secondary of secondaryPhases) {
    if (!phaseMeta[secondary]) throw new Error(`Unknown secondary phase ${secondary} for ${slug}`);
  }
  return {
    slug,
    order,
    title,
    year,
    venue,
    legacyTheme,
    phase,
    secondaryPhases,
    pdf,
    url,
    contribution,
    relation,
    reading,
    borrow,
    limitation,
    transform,
  };
});

const unregisteredAssignments = Object.keys(phaseAssignments).filter(
  (slug) => !papers.some((paper) => paper.slug === slug),
);
if (unregisteredAssignments.length) {
  throw new Error(`Assignments without paper entries: ${unregisteredAssignments.join(', ')}`);
}

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
    '目标论文位于所收录 AIED 2025 论文集的印刷页 452–457；系统以 REACT 情境学习和启发式学习为教育依据。',
    '故事文本由 Teacher、Planner、Writer 三个智能体分别负责逐步求解、情节规划和正文生成，并配合多模态与互动学习模块。',
    '作者在 60 个数学问题上用 Gemini 和 GPT-4o 评判七个维度；多智能体方案提高准确性、相关性、连贯性和复杂度，但同理心/参与度提升有限，惊喜度仍低。',
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

function phaseAdvice(p) {
  const adviceByPhase = {
    图检索与证据: {
      output: '把论文中的知识组织、实体/关系/路径检索、相关性排序或课程对齐方法转成 RetrievalPackage 的字段与检索决策。',
      evidence: '优先记录数据 schema、检索单位、相关性信号、噪声处理、证据来源和路径扩展规则。',
      action: '将可借鉴方法接入目标中心检索，但必须保留课程来源，并区分核心机制证据、桥接上下文和普通常识。',
      risk: '检索更多不等于证据更好；过大的图上下文会稀释目标关系，桥接边也可能被模型误当成机制事实。',
    },
    机制图: {
      output: '把论文中的实体—关系结构、因果/条件表示、事件状态或结构化故事 schema 转成 MechanismGraph 的节点、边和审核规则。',
      evidence: '优先记录哪些结构被视为事实、因果或状态变化，以及论文如何验证方向、完整性和可解释性。',
      action: '只吸收能够由 RetrievalPackage 证据支持的结构；为 must_preserve 节点/边保留稳定 ID，并在映射前完成人工审核。',
      risk: '故事图、常识图和课程机制图用途不同；不能把叙事上合理的关系直接升级为目标知识的机制边。',
    },
    'Copycat 式候选映射竞争': {
      output: '把论文中的类比、结构相似、概念滑动、候选生成或类比评价方法转成候选 Mapping Plan 与竞争信号。',
      evidence: '优先记录 source/target 对应、关系角色、候选多样性、结构覆盖、方向保持和类比评价的定义。',
      action: '让论文方法帮助提出或评价三个候选，但最终接受仍由机制节点/边硬验证、方向检查和可审计评分决定。',
      risk: '语义上漂亮的类比可能发生结构错位；当前 LLM-Guided Copycat 也不能被表述为完整 Copycat 认知架构。',
    },
    寓言叙事: {
      output: '把论文中的故事规划、受控生成、多智能体协作、寓言文体或读者模型方法转成 Mapping Plan 到正文的实现策略。',
      evidence: '优先记录中间计划、角色与事件控制、文体定义、长期一致性、修订机制和面向儿童的表达要求。',
      action: '所有创作方法只能在故事侧实现已验证映射；允许丰富冲突、转折和语言，不允许新增或倒置知识机制。',
      risk: '只优化连贯、趣味或篇幅可能掩盖知识偏移；动物拟人化也不是寓言成立的充分条件。',
    },
    反向结构对齐与教育质量评测: {
      output: '把论文中的类比标注、故事理解、数据集评价、可读性、偏见审计或学习实验转成反向对齐与教育质量指标。',
      evidence: '优先记录评价对象、人工标注、自动指标、理解题、对抗样本、用户研究和结论适用边界。',
      action: '将自动规则、Aligner、LLM Judge、人工审核和学生/教师研究分层报告，不用单一总分替代结构证据。',
      risk: '流畅度、LLM-as-a-judge 或故事偏好不能证明学生学会了；自动评价必须与结构回查和真实学习证据区分。',
    },
  };
  return adviceByPhase[p.phase];
}

function qaText(p, meta) {
  const advice = phaseAdvice(p);
  const evidence = evidenceMap[p.slug] || [
    `摘要或内容概述初读：${p.contribution}`,
    `建议重点定位：${p.reading}`,
  ];
  const evidenceBullets = evidence.map((item) => `- ${item}`).join('\n');
  return `### 1. 这篇论文解决的问题和 Concept-to-Fable 有什么关系？

**原文依据定位**：

${evidenceBullets}

**明确回答**：读完这篇论文后，可以把它理解为 Concept-to-Fable 的一个有证据支撑的模块来源。${p.relation} 更具体地说，它可以放在你的 Concept-to-Fable 流程中，帮助回答“从教材知识到可读寓言”链条里的一个关键问题：输入应该怎样被组织、中间结构应该怎样被约束、或者输出应该怎样被评价。

**对你的研究建议**：阅读这篇论文时，不要只记录它的摘要和模型名称，而要把它拆成三个可复用信息：第一，它假设的输入是什么；第二，它产生的中间表示或输出是什么；第三，它如何证明结果是好的。上面的依据定位已经给出这三类信息的初步来源。把这些内容填进你的系统表格后，就能判断它是直接可用、需要改造，还是只适合作为 related work 背景。

**落地判断**：如果这篇论文的方法能被改造成“知识点输入 → 可解释中间结构 → 寓言文本或评价结果”的一环，它就是核心参考；如果只能生成流畅文本但无法解释映射关系，就只能作为辅助参考。

### 2. 它在五阶段流程中的位置是什么？

**主要阶段**：**${p.phase}**。这一阶段的任务是：${meta.role}

**同时支撑**：${p.secondaryPhases.length ? p.secondaryPhases.map((phase) => `[${phase}](/pillars/${phaseMeta[phase].slug}/)`).join('、') : '无；当前仅作为主要阶段的直接参考。'}

**具体作用**：${advice.output}

**放置理由**：论文被归入“${p.phase}”不是因为标题相似，而是其摘要、方法、数据或评价设计能够直接改变该阶段的输入、中间表示、验证门槛或输出。

### 3. 我们可以借鉴它的什么方法、数据或评测方式？

**明确回答**：${p.borrow}

**可执行建议**：${advice.action}

**阅读时要记录的证据**：${advice.evidence} 当前页面已经列出 2-3 条从 PDF 中抽取并阅读后的依据。下一轮精修时，建议继续补充页码、图表编号或章节名，例如数据 schema、模型流程图、评价维度或实验设置。这样别人读你的站点时，不只是看到“可借鉴”，而是知道具体该翻论文哪一节。

### 4. 它没有解决什么，因此我们的任务还有什么研究空间？

**明确回答**：${p.limitation}

**研究空间**：这个判断来自论文自身的任务边界：它虽然提供了上面依据中的方法或数据，但没有完整覆盖“图检索与证据 → 机制图 → Copycat 式候选映射竞争 → 寓言叙事 → 反向结构对齐与教育质量评测”的闭环。项目的研究价值在于把可复用方法放进明确阶段，并要求每个样本都能解释“证据来自哪里、机制是什么、为什么这样映射、故事是否保持结构、教育质量如何验证”。

**风险提醒**：${advice.risk} 写 related work 时建议明确说出这篇论文与你的边界：它解决了什么，你继承什么；它没解决什么，你补什么。这样可以减少 reviewer 觉得“只是换了个应用场景”的风险。

### 5. 如果把它用于“知识点转寓言”，需要怎样改造？

**明确回答**：${p.transform}

**改造方案**：建议按三个层次改造。第一，把输入改成课程知识点或 KG 子图，而不是普通主题或自由 prompt。第二，在生成前增加映射表，规定知识实体、关系、因果链分别对应哪些寓言角色、动作和结果。第三，在生成后增加检查器，分别检查科学准确性、映射忠实性、故事完整性和目标年级可读性。

**下一步建议**：如果这篇论文属于核心论文，可以进一步补一个小实验：选一个小学知识点，用它启发的方法生成一版寓言骨架，再人工标注“知识步骤—故事情节”的对应关系。这样它就不只是文献综述里的引用，而会变成你任务设计的实证支撑。对于目前依据定位还不够细的论文，下一步优先补页码、表格编号和原文术语，避免回答停留在二次概括。`;
}

write(path.join(root, 'index.mdx'), `---
title: concept2fable
description: 从课程知识到可验证教学寓言的端到端研究流程。
template: splash
---

concept2fable 是一条面向教学寓言生成的可追溯流程：从课程知识中检索可引用的证据，显式建成机制图；让多个 Copycat 式映射候选竞争；再把胜出的映射计划写成寓言；最后从故事反向核对结构，并评估它是否真正适合教学。

它的目标不是把一个概念换成几只动物，而是为每篇寓言保留一条可检查的证据链：**它解释什么、为什么这样映射、故事是否保留了机制、学生是否可能从中学到正确内容。**

\`\`\`text
课程概念 / 教学目标
        ↓
图检索与证据 → 机制图 → Copycat 式候选映射竞争 → 寓言叙事
                                                      ↓
                         反向结构对齐与教育质量评测 ←┘
\`\`\`

## 当前流程

### [01 · 图检索与证据](/pillars/retrieval-evidence/)

**回答的问题：这个概念应当依据哪些课程事实来讲？**

系统从目标概念出发，在课程知识图中做目标中心的自适应检索：优先保留直接相关的节点和边，只有在直连结构不足时才扩展少量两跳路径。每条候选证据都保留来源、关系和检索决策，避免后续叙事只依赖无来源的通用常识。

**输入**：概念种子、年级/学科信息、课程图谱。  
**输出**：带证据来源的 \`RetrievalPackage\`。  
**下一步的约束**：桥接关系只用于理解上下文，不能被误写成机制证据。

完整阶段说明和全部适配文献见[图检索与证据](/pillars/retrieval-evidence/)，重点参考 [K12-KGraph](/papers/k12-kgraph/)、[Concept Extraction and Prerequisite Relation Learning](/papers/concept-extraction-prerequisite/) 与 [Amar](/papers/amar-kgqa/)。

### [02 · 机制图](/pillars/mechanism-graph/)

**回答的问题：知识背后必须保留的条件、过程、因果和结果是什么？**

检索到的证据不会直接被改写成故事。M2NA 先将其组织为 \`MechanismGraph\`：节点表示要保留的机制成分，带方向的边表示条件、作用、变化或因果关系。严格校验与人工审核发生在映射之前；只有已批准的机制图才能进入故事化阶段。

**输入**：\`RetrievalPackage\`。  
**输出**：已验证、可审核的 \`MechanismGraph\`。  
**守住的边界**：节点和边的身份不由下游生成器修改；未通过审核的机制不进入实验主流程。

这一层把“讲得像”与“讲得对”分开：故事可以有创造性，但不能自行发明或颠倒知识机制。完整输入、schema、审核门槛和适配文献见[机制图](/pillars/mechanism-graph/)。

### [03 · Copycat 式候选映射竞争](/pillars/copycat-mapping-competition/)

**回答的问题：怎样把机制逻辑转换为故事逻辑，同时不丢失结构？**

当前主方法为 [LLM-Guided Copycat](/methodology/)。它把 LLM 用作语义候选提出者，而不是最终裁判：对同一已审核机制图，\`semantic-scout/v1\` 一次提出 **3 个**不同故事域的映射计划；每个计划须为全部机制节点给出故事载体、为全部机制边给出有方向的故事关系。

候选随后经历确定性门控和排序：节点/边全覆盖、标识符合法、边方向保持、禁用术语不泄漏；再结合覆盖度、载体与关系多样性、叙事骨架和模板风险评分。若检测到重复载体、重复关系或序数占位符，元监控器最多做一次不改变深层结构的受约束修订。

**输入**：已批准的 \`MechanismGraph\` 与检索上下文。  
**输出**：\`Validated Mapping Plan\`，以及全部候选、评分和修订轨迹。  
**当前对比**：标准映射、确定性 Copycat 与 LLM-guided Copycat 各保留 3 个候选，便于比较。

这一步是“从概念到寓言”的核心，不等同于完整 Copycat 复现；当前 MVP 尚无动态 slipnet、coderack 和非单调温度反馈。阶段全貌见[Copycat 式候选映射竞争](/pillars/copycat-mapping-competition/)，实现细节见[当前实验方法](/methodology/)。

### [04 · 寓言叙事](/pillars/fable-narrative/)

**回答的问题：如何将通过验证的映射计划写成可读、可控的寓言？**

生成器只接收故事侧的映射字段和禁用术语，不直接改动机制图。它依据故事域、角色/物体、冲突、事件链、转折、解决状态，以及节点—载体和边—关系映射写出候选寓言；这使创作空间保留在叙事表达层，而不是机制事实层。

**输入**：通过验证的 \`Mapping Plan\`。  
**输出**：每个概念—策略—候选对应的寓言草稿及生成记录。  
**过程控制**：计划先行；需要修订时，修订与再判定均留下独立产物，不覆盖原候选。

这一阶段同时吸收“先规划、后写作”、可控生成、多智能体协作与传统寓言文体约束；完整方法边界和文献见[寓言叙事](/pillars/fable-narrative/)。

### [05 · 反向结构对齐与教育质量评测](/pillars/reverse-alignment-evaluation/)

**回答的问题：故事不仅好读，而且真的保留了机制并适合教学吗？**

评测不从“文笔优不优美”出发，而是从完成的寓言反向追问机制图：故事是否覆盖必须保留的节点和边？因果或条件方向有没有被倒置？是否泄漏学术术语、落入模板化表达，或只写出一个貌似相关的情节？对齐器与判定器都可查看机制图，用保守证据检查故事侧的主张。

教育质量则与结构保真并列：当前判定汇总知识忠实性、映射清晰度、可读性等信号，并结合规则检查、LLM 判定和人工复核。最终可比较三种映射策略的覆盖率、方向准确度、接受/修订/拒绝状态、泄漏风险与修订收益；关于学生学习效果的结论仍需要独立的课堂或用户研究，不能由自动指标代替。

**输入**：寓言草稿、映射计划、机制图与同批候选。  
**输出**：对齐证据、质量分数、硬性风险标记、修订建议和可汇总报告。  
**通过标准**：故事的结构对应应当可回查，教学质量应当被显式报告，而不是凭直觉宣布成功。

完整的结构回查、自动/人工评价边界和教育验证文献见[反向结构对齐与教育质量评测](/pillars/reverse-alignment-evaluation/)。

## 失败不会被最终文本掩盖

五个阶段不是一条只向前的流水线，而是带明确回退位置的闭环：

| 失败位置 | 典型问题 | 回退动作 |
|---|---|---|
| 图检索与证据 | 直连证据不足、噪声过多、桥接边被误当证据 | 调整检索视角与门控，重新生成 RetrievalPackage。 |
| 机制图 | 节点缺失、边方向错误、证据无法支持机制 | 返回机制构建与人工审核，不进入映射。 |
| 候选映射 | 覆盖不全、方向改变、术语泄漏、候选模板化 | 淘汰候选或做一次受约束修订；全部失败则重新提出候选。 |
| 寓言叙事 | 计划覆盖但正文漏写、情节引入新机制、文体不成立 | 返回正文修订；若表层无法修复，则回退到映射计划。 |
| 反向评测 | 结构无法回查、年级不适配、偏见风险或理解题失败 | 记录失败类型，按原因回到检索、机制、映射或叙事阶段。 |

因此，最终发布对象不是孤立的故事文本，而是“证据—机制—映射—故事—评价”的完整样本包。

## 论文证据地图

当前本地论文库共收录 **${papers.length} 个 PDF 条目**，所有条目都已进入网站，并按摘要或无摘要材料的内容概述重新归入流程：

- **[图检索与证据](/pillars/retrieval-evidence/)**：课程图、概念/先修抽取、多视角检索和证据门控。
- **[机制图](/pillars/mechanism-graph/)**：事实图、事件/状态结构、因果方向和人工审核。
- **[Copycat 式候选映射竞争](/pillars/copycat-mapping-competition/)**：结构映射、概念滑动、故事级类比、候选生成与筛选。
- **[寓言叙事](/pillars/fable-narrative/)**：规划写作、可控生成、多智能体、读者模型和寓言文体。
- **[反向结构对齐与教育质量评测](/pillars/reverse-alignment-evaluation/)**：结构回查、类比标注、故事理解、可读性、偏见与学习效果。

这里的分类表达“对 concept2fable 最直接的用途”，不表示论文只能用于一个阶段；跨阶段作用会在各自阅读页中单独说明。

## 运行闭环与可审计产物

concept2fable 不把中间推理藏在最终文本后面。一次运行至少保留以下可以复查的对象：

| 阶段 | 可审计产物 | 用途 |
|---|---|---|
| 图检索与证据 | 检索包、路径与证据引用 | 追溯“为什么选这些知识”。 |
| 机制图 | 机制节点、机制边、校验与人工审核记录 | 固定故事不可改变的深层结构。 |
| 候选竞争 | \`mapping_context.json\`、\`candidate_evaluations.json\`、\`selected_mapping_plan.json\`、\`run_result.json\` | 说明候选为何被接受、拒绝或修订。 |
| 寓言叙事 | 每个概念/策略/候选的故事草稿与版本 | 支持并列比较，而非只保留胜者。 |
| 反向评测 | 对齐证据、\`six_dim_eval.json\`、批量汇总报告与人工评审历史 | 解释故事是否保真、可教、可用。 |

## 用本站做什么

这里的论文页面是 concept2fable 每个阶段的**证据库**，不是脱离项目的文献清单。每页首先给出基于 PDF 摘要的初读；对 Copycat 书籍分卷等没有独立摘要的材料，则明确标注为内容概述。随后再说明它在流程中的位置、可复用的输入/中间表示/评测方法，以及它没有覆盖、需要本项目补上的边界。

若要先理解最关键的技术决策，请从[当前实验方法：LLM-Guided Copycat 结构映射](/methodology/)进入；若要按阶段查阅依据，直接使用左侧五阶段导航。
`);

for (const [name, meta] of Object.entries(phaseMeta)) {
  const primaryPapers = papers.filter((paper) => paper.phase === name);
  const supportingPapers = papers.filter((paper) => paper.secondaryPhases.includes(name));
  const primaryRows = primaryPapers
    .map((paper) => `| [${paper.title}](/papers/${paper.slug}/) | ${paper.year} · ${paper.venue} | ${paper.contribution} | ${paper.borrow} |`)
    .join('\n');
  const supportingRows = supportingPapers
    .map((paper) => `| [${paper.title}](/papers/${paper.slug}/) | ${paper.phase} | ${paper.borrow} |`)
    .join('\n');
  write(path.join(pillarsDir, `${meta.slug}.mdx`), `---
title: ${meta.title}
description: ${meta.description}
sidebar:
  order: ${meta.order}
---

${meta.description}

> 核心问题：**${meta.question}**

## 在完整流程中的位置

${meta.role}

**上游输入**：${meta.input}  
**当前实现**：${meta.method}  
**阶段产物**：${meta.output}

## 进入下一阶段的门槛

${meta.gate}

## 失败如何回退

${meta.fallback}

## 主要参考文献（${primaryPapers.length}）

这些论文直接定义或改变本阶段的方法、数据结构、验证门槛或输出。

| 论文 | 年份/来源 | 摘要初读：为什么相关 | 在本项目中的适配方式 |
|---|---|---|---|
${primaryRows}

## 跨阶段参考文献（${supportingPapers.length}）

这些论文的主要位置在其他阶段，但其方法或评价也为本阶段提供约束。

| 论文 | 主要阶段 | 对本阶段的可借鉴点 |
|---|---|---|
${supportingRows}

## 与相邻阶段的接口

- 本阶段只能消费上游已经通过门槛的产物。
- 本阶段产物必须保留稳定标识和审计信息，供下游与反向评测回查。
- 如果下游发现的问题属于本阶段责任，应按“失败如何回退”返回处理，而不是在最终文本中掩盖。
`);
}

for (const p of papers) {
  const meta = phaseMeta[p.phase];
  const sourceLine = p.url
    ? `**原文链接**：[${p.url}](${p.url})`
    : '**来源说明**：本地已收录全文；当前条目依据 PDF 摘要或内容概述整理。';
  write(path.join(papersDir, `${p.slug}.mdx`), `---
title: "${yaml(p.title)}"
description: "${p.year} ${p.venue} · ${p.phase}"
sidebar:
  order: ${p.order}
---

import PaperAsk from '../../../components/PaperAsk.astro';

**年份/来源**：${p.year} · ${p.venue}  
**主要流程阶段**：[${p.phase}](/pillars/${meta.slug}/)  
**同时支撑**：${p.secondaryPhases.length ? p.secondaryPhases.map((phase) => `[${phase}](/pillars/${phaseMeta[phase].slug}/)`).join('、') : '无'}  
**PDF**：[打开本地 PDF](/papers/${encodeURIComponent(p.pdf)})  
${sourceLine}

## 摘要 / 内容概述初读

${p.contribution}

## 在五阶段流程中的适配位置

${p.relation}

- **主要阶段**：${p.phase}——${meta.question}
- **具体适配**：${p.borrow}
- **跨阶段影响**：${p.secondaryPhases.length ? p.secondaryPhases.join('、') : '无；当前只作为主要阶段的直接证据。'}

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
      phase: p.phase,
      secondaryPhases: p.secondaryPhases,
      legacyTheme: p.legacyTheme,
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
