---
title: "RFC-0000: The Arcana of Benchwork"
subtitle: Language, Philosophy, and Design Bible
document_id: BW-RFC-0000
version: 0.2
status: accepted
owner: Endofthestars
date: 2026-07-29
---

# RFC-0000: The Arcana of Benchwork

> **严谨如仪式，证据皆留痕。**  
> *Every working is observed, shaped, and traceable.*

---

## 序言

Benchwork 是一张面向计算型科研的工作台。

研究者在这里提出问题，整理证据，形成主张，设计协议，实现系统，运行实验，解释结果，并据此作出下一步决定。每一项工作都具有来源、边界、版本和历史；每一次推进都能够被理解、复核和继续。

**Arcana** 是 Benchwork 的语言。

它为长期科研工作赋予统一的秩序与意象，使抽象架构、日常命令、扩展生态和社区文化共享同一个世界。它从实验室、炼金工艺、手稿、星图与精密仪器中汲取灵感，表达研究中的观察、提炼、塑形、试验、记录与承诺。

Arcana 的核心气质是：

- 对过程的专注；
- 对证据的尊重；
- 对边界的自觉；
- 对承诺的慎重；
- 对失败与偏离的诚实记录；
- 对未知保持开放；
- 对可复核性保持长期耐心。

Benchwork 因而拥有一套既严谨、又有记忆点的产品语言。

---

# 1. The Bench

工作台是 Benchwork 的中心意象。

一张工作台承载材料、器具、草图、测量、试验和记录。它允许探索，也要求秩序；它容纳创造，也保留痕迹。研究者可以离开，再回到同一项工作；也可以邀请另一位研究者沿着已有记录继续推进。

在 Benchwork 中，一项研究沿着如下路径发展：

```text
Idea
→ Evidence
→ Claim
→ Hypothesis
→ Protocol
→ Implementation
→ Experiment
→ Analysis
→ Review
→ Decision
```

这条路径可以循环、分支、暂停和回溯。每一次循环都产生新的证据，每一个分支都保留谱系，每一次决定都成为后续工作的起点。

Benchwork 将研究理解为一种持续的 **Working**：

> 一项被观察、被塑形、被检验，并能够被重新理解的工作。

---

# 2. The Language of Arcana

Arcana 由三层语言共同构成。

## 2.1 Scientific Canon

**Scientific Canon** 描述研究本身的正式对象：

```text
Research Program
Claim
Evidence
Hypothesis
Protocol
Experiment
Run
Assessment
Issue
Decision
Deviation
Artifact
Receipt
```

这些词用于 Schema、API、研究导出包、审计记录和正式方法文档。它们保持直接、稳定、可比较，使 Benchwork 能够与现有科研实践、统计工具和外部系统自然连接。

## 2.2 Arcana Mechanics

**Arcana Mechanics** 描述 Benchwork 如何工作：

```text
Athanor
Chronicle
Ward
Sigil
Alembic
Sanctum
Crucible
Grimoire
Rite
Working
Circle
Seal
```

这些词共同构成产品的运行时语言。它们出现在 CLI、终端、文档导航、扩展生态和架构图中，并通过稳定关系形成一个完整世界。

## 2.3 Capability Language

**Capability Language** 描述系统可以完成的科研动作：

```text
bench.research.orchestrate
bench.evidence.discover
bench.evidence.synthesize
bench.evidence.verify
bench.hypothesis.frame
bench.hypothesis.challenge
bench.study.design
bench.study.audit
bench.code.inspect
bench.code.modify
bench.experiment.plan
bench.experiment.execute
bench.experiment.collect
bench.analysis.compute
bench.analysis.interpret
bench.decision.review
bench.decision.propose
```

Capability 使用清晰、功能化、模型无关的名称。Claude、Codex 与未来的模型通过同一 Capability 契约参与工作，使产品能力拥有长期稳定的接口。

三层语言彼此协作：

> Scientific Canon 命名研究对象；Arcana Mechanics 命名科研工艺；Capability Language 命名可执行动作。

---

# 3. The Philosophy of the Working

## 3.1 Research leaves a trace

研究通过痕迹获得连续性。

一个 Claim 可以追溯到 Evidence；一个 Evidence 可以追溯到来源位置、数据或 Run；一个 Decision 可以追溯到分析、审查、异议与授权。由此，研究工作能够跨越时间、模型、机器和协作者。

Benchwork 将这种连续性写入 Chronicle，并通过 Sigil 保持对象身份。

## 3.2 Evidence forms a constellation

证据常常分散在论文、代码、数据、实验结果与专家判断中。Benchwork 将这些材料组织为相互关联的结构：支持、反驳、限制、复现、扩展与未决。

证据的价值来自它在关系中的位置。单个来源提供一个观察，多项观察形成星座，星座帮助研究者理解问题的边界与方向。

## 3.3 Protocols shape intention

Protocol 将研究意图塑造成可执行承诺。

它连接 Claim、Hypothesis、数据、对照、测量、运行矩阵、分析计划和决策规则。Protocol 让“我们想知道什么”与“我们将如何知道”在实验开始之前相遇。

当 Protocol 被 Seal，它获得稳定版本。后续变化通过 Deviation 进入 Chronicle，使研究设计的演化保持可见。

## 3.4 Computation and interpretation are complementary crafts

Alembic 负责计算：描述统计、效应量、不确定性、稳健性、资源使用和运行完整性。

Agent 与研究者负责解释：结果支持了什么、限制了什么、还存在哪些竞争解释，以及下一项实验能够带来什么信息。

计算提供可重复的尺度，解释提供科学语境。两者共同构成评估。

## 3.5 Capabilities outlive providers

Capability 是 Benchwork 的稳定能力单位。

Claude、Codex、本地模型、远程模型与确定性执行器都可以成为 Capability 的实现者。调度由任务需求、工具、权限、预算、质量与用户策略共同决定。

模型可以更替，Capability 契约、科研对象和 Chronicle 保持连续。

## 3.6 Human judgment seals commitment

研究者拥有科研承诺的最终权威。

Agent 帮助探索、整理、挑战、设计和解释；Athanor 验证结构与状态；Ward 检查权限和条件；研究者在关键节点确认方向、协议、正式实验和决定。

这种协作使自动化获得速度，也使科研承诺保持责任归属。

## 3.7 Failure is part of the record

失败 Run、负结果、取消任务、协议偏离与未解决 Issue 都属于研究历史。

Chronicle 保存这些事件，使后续判断能够理解一项工作为何继续、修复、转向或停止。失败由此成为信息，偏离成为上下文，停止成为一种有依据的科研决定。

## 3.8 Research grows through lineage

Research Program 可以形成分支与谱系。

一个方向可以派生出新的问题，一个失败机制可以转化为新的假设，一个 PIVOT 可以建立新的 Program，同时保留与原工作的关系。

Benchwork 将科研看作一棵持续生长的知识树。分支保存选择，谱系保存理解。

---

# 4. The Core Arcana

## 4.1 Athanor

**Athanor** 是 Benchwork 的确定性核心炉。

它接收 Proposal，验证 Schema、引用、摘要、Gate 和授权条件，将被接受的变化写入 Chronicle，并生成 Receipt。Athanor 为长期科研工作提供稳定的状态边界。

> **Athanor owns canonical transitions.**

## 4.2 Chronicle

**Chronicle** 是追加式科研事件账本。

它记录 Program 的创建、Claim 的形成、Evidence 的验证、Protocol 的 Seal、Run 的状态、Assessment 的产生和 Decision 的提交。当前状态可以由 Chronicle 重建，历史也可以被回放、审计和比较。

> **Chronicle gives research a memory.**

## 4.3 Ward

**Ward** 是权限、预算、租约、完整性与审批的保护层。

每项任务在行动前获得明确边界，在行动后接受后置条件检查。Ward 让自动化拥有可理解的范围，让资源使用与关键操作保持透明。

> **Ward gives automation a boundary.**

## 4.4 Sigil

**Sigil** 是对象与产物的稳定身份。

它连接内容摘要、来源、输入、输出、执行者、Policy 与 Receipt，使研究者能够确认一个对象是什么、是否发生变化，以及它如何产生。

> **Sigil gives artifacts an identity.**

## 4.5 Alembic

**Alembic** 是确定性分析引擎。

它将 Run、测量与资源记录提炼为机器可读的统计产物。Alembic 为科学解释提供共同尺度，也为不同模型和研究者之间的审查提供一致输入。

> **Alembic turns measurements into analysis.**

## 4.6 Sanctum

**Sanctum** 是 Agent 任务的隔离上下文。

它包含特定目标、可见材料、工具、预算和输出契约。每个任务在自己的 Sanctum 中展开，从而获得清晰上下文与可复核边界。

> **Sanctum gives reasoning a place.**

## 4.7 Crucible

**Crucible** 是代码与实验实现的可变工作区。

修改、调试、配置和试验在这里发生。Crucible 可以由 Git worktree、容器、沙箱或远程目录实现，并通过 Artifact、Commit 与 Receipt 将成果带回长期科研记录。

> **Crucible gives change a place to be tested.**

## 4.8 Grimoire

**Grimoire** 是版本化扩展来源。

它汇集 Rites、Capability Packs、Host Adapters、Provider Adapters、Executor Adapters、Policy Packs、Schema Extensions、Examples 与 Benchmarks。每个 Grimoire 都拥有来源、版本、许可证、兼容范围与内容摘要。

> **Grimoire gathers reusable knowledge.**

## 4.9 Rite

**Rite** 是版本化科研工作流。

它将目标、Capability、输入输出、Gate、Ward、人工审批点和停止条件组织为可复用过程。一个 Rite 可以描述计算型研究、论文复现、Benchmark 审计、证据地图或消融研究。

> **Rite turns method into a reusable path.**

## 4.10 Working

**Working** 是一次可恢复的 Rite 执行。

它绑定特定 Research Program、Rite 版本、输入、Policy、Provider 和 Task Graph，并持续记录状态、Receipt、失败、重试与检查点。

> **Working is research in motion.**

## 4.11 Circle

**Circle** 是单个任务的权限与上下文边界。

它声明可见 Artifact、文件、网络、工具、执行权限、时间预算、费用预算和输出 Schema。Circle 让每个任务拥有与目标相称的能力范围。

> **Circle gives every task a defined horizon.**

## 4.12 Seal

**Seal** 是冻结科研承诺的操作。

Protocol、Analysis Plan、Decision 与对外导出包通过 Seal 获得稳定版本和 Sigil。Seal 使一个阶段的承诺清晰可引用，也为后续 Deviation 和新版本建立起点。

> **Seal gives commitment a form.**

---

# 5. The Grammar of Benchwork

Arcana 的词汇通过固定关系形成产品语法：

```text
A Grimoire contains Rites.
A Rite creates a Working.
A Working unfolds through Tasks.
Each Task receives a Circle.
An Agent reasons inside a Sanctum.
Implementation evolves inside a Crucible.
Alembic computes from recorded Runs.
Ward evaluates policy and permission.
Athanor accepts canonical transitions.
Chronicle records accepted events.
Sigils identify artifacts and receipts.
Seals stabilize scientific commitments.
```

中文表达为：

```text
Grimoire 汇集可复用的 Rite；
Rite 实例化为一次 Working；
Working 由一组 Task 推进；
每个 Task 都获得自己的 Circle；
Agent 在 Sanctum 中完成推理；
实现与实验在 Crucible 中演化；
Alembic 根据完整 Run 记录完成计算；
Ward 检查策略、权限和资源；
Athanor 接受规范状态变化；
Chronicle 保存被接受的事件；
Sigil 标识对象、产物与回执；
Seal 固定一个阶段的科研承诺。
```

这套语法使用户能够从命令、日志和文档中直观理解系统当前正在发生什么。

---

# 6. The Commands of the Bench

Benchwork 的命令语言分为两组。

## 6.1 The research path

日常科研路径使用直接、清晰的动词：

```bash
bwork init
bwork start
bwork investigate
bwork design
bwork implement
bwork pilot
bwork run
bwork analyze
bwork review
bwork decide
bwork resume
bwork status
bwork doctor
```

它们共同描述一项研究从开始到决定的主路径。

## 6.2 The Arcana operations

Arcana 命令表达 Benchwork 特有的工艺：

```bash
bwork scry literature
bwork distill evidence
bwork invoke bench.evidence.verify
bwork seal protocol PT-001
bwork ward check
bwork trace claim CL-001
```

- **Scry**：探索文献、代码与证据空间；
- **Distill**：将已检查材料整理为结构化 Proposal；
- **Invoke**：调用一个明确 Capability；
- **Seal**：固定科研承诺并生成 Receipt；
- **Ward**：检查权限、预算、完整性与审批条件；
- **Trace**：重建对象、事件、Artifact 与 Decision 的谱系。

## 6.3 The ecosystem

扩展与工作流使用一组相互关联的对象命令：

```bash
bwork grimoire add endofthestars/ml-research
bwork grimoire inspect endofthestars/ml-research

bwork rite search computational-study
bwork rite install ml-computational-study@0.1.0
bwork rite run ml-computational-study

bwork working list
bwork working inspect WK-014
bwork working resume WK-014

bwork chronicle show
bwork chronicle verify

bwork sigil show RC-031
bwork sigil verify artifact.json
```

这些命令让 Arcana 从品牌语言进入日常实践。

---

# 7. Agents, Hosts, and Providers

Benchwork 以 Capability 组织智能工作。

Claude、Codex 和未来模型都可以：

- 作为研究者的交互入口；
- 执行 `bench.research.orchestrate`；
- 调用同一组 Capability；
- 在权限与工具满足时完成文献、代码、实验和审查任务；
- 通过统一输出契约将结果交还 Athanor。

**Host** 表示研究者当前交互所在的环境。  
**Provider** 表示实际执行 Capability 的模型或 Agent 后端。  
**Capability** 表示 Benchwork 稳定定义的科研动作。

同一个 Host 可以调用不同 Provider；同一个 Capability 也可以由多个 Provider 执行。由此形成对称、开放、长期可替换的智能层。

## 7.1 Conductor

**Conductor** 是 `bench.research.orchestrate` 的产品称谓。

它读取 Program 状态，理解研究者目标，形成 Task Proposal，调用 Capability，汇总 Working，并在需要科研承诺时邀请研究者确认。

Conductor 的价值在于保持研究节奏：它帮助研究者看到当前问题、下一步动作、未决 Issue 与已有证据之间的关系。

## 7.2 Arcana titles

界面可以为能力组使用轻量称谓：

| 能力领域 | Arcana 称谓 | Capability 范围 |
|---|---|---|
| Evidence | **Archivist** | `bench.evidence.*` |
| Method | **Adept** | `bench.hypothesis.*`, `bench.study.*` |
| Challenge | **Adversary** | challenge 与 audit |
| Code | **Artificer** | `bench.code.*` |
| Execution | **Hand** | `bench.experiment.*` |
| Integrity | **Warden** | policy 与 assessment |
| Maintenance | **Keeper** | configuration 与 extensions |

这些称谓为界面增添性格；Capability ID 为系统提供稳定契约。

---

# 8. Voice and Tone

Benchwork 的声音来自精密仪器、实验记录与冷静的研究伙伴。

它具有以下特征：

- 清楚；
- 克制；
- 稳定；
- 有仪器感；
- 能够表达不确定性；
- 重视对象、状态、来源和下一步；
- 在关键科研承诺前呈现后果与上下文。

典型终端输出：

```text
BENCHWORK · ATHANOR
Project       /work/robust-memory
Program       RP-001
Working       WK-014
Rite          ml-computational-study@0.1.0
State         WAITING_FOR_APPROVAL

Ward          approval required: protocol.seal
Object        PT-003
Sigil         sha256:3d8b…9a21

Next action   review protocol and confirm seal
```

Working 完成时：

```text
Working WK-014 completed.
Tasks          7 completed · 1 failed
Chronicle      12 events appended
Receipts       RC-031 … RC-042
Decision       REVIEW_REQUIRED
Next action    scientific review
```

Benchwork 的语言让研究者始终知道：发生了什么、留下了什么、仍缺少什么，以及下一步由谁决定。

---

# 9. Visual Language

Benchwork 的视觉世界来自一间现代而古老的实验室：

- 深色工作台；
- 黄铜精密仪器；
- 羊皮纸般的浅色阅读面；
- 手稿边注；
- 星图式关系网络；
- 几何刻度；
- 封蜡与印记；
- 受控容器与可追溯路径。

建议色彩语义：

| 名称 | 用途 | 示例 |
|---|---|---|
| Obsidian | 主背景 | `#111318` |
| Ash | 次级背景 | `#2C3038` |
| Parchment | 浅色阅读面 | `#F3EFE5` |
| Brass | 品牌强调 | `#B78A3B` |
| Lapis | 信息与链接 | `#4B5FA8` |
| Verdigris | 已验证与完成 | `#4F8A7B` |
| Cinnabar | Critical 与 Stop | `#B74A3D` |

建议图示语法：

| 形状 | 含义 |
|---|---|
| 矩形 | 确定性组件 |
| 圆角矩形 | Capability 或 Adapter |
| 圆形 | Gate 与 Approval Point |
| 六边形 | Artifact 或科研对象 |
| 实线箭头 | 已提交状态流 |
| 虚线箭头 | Proposal 与候选数据 |
| 双线边框 | Sealed Object |

视觉设计服务于阅读、状态理解和谱系追踪。Arcana 通过细节与秩序建立气质。

---

# 10. Grimoires, Rites, and Community

Grimoire 与 Rite 构成 Benchwork 的开放生态。

一个 Grimoire 可以聚集特定领域的研究方法、Capability、Provider Adapter、Policy、Schema、样例和 Benchmark。例如：

```text
endofthestars/ml-research
open-lab/reproducibility
community/evidence-mapping
```

一个 Rite 描述可复用的科研路径。例如：

```text
ml-computational-study
paper-reproduction
benchmark-audit
systematic-evidence-map
ablation-study
```

贡献者围绕清晰职责协作：

```text
Owner
Maintainer
Reviewer
Contributor
Security Contact
Rite Maintainer
```

社区语言可以自然使用：

```text
New Rites
Changes in the Athanor
Chronicle Compatibility
Ward and Security Notes
Grimoire Updates
Breaking Seals
```

工程活动仍保持可搜索与可自动化：

```text
feat(chronicle): add atomic append receipt
fix(ward): handle expired approval token
docs(arcana): refine seal semantics
```

Arcana 为社区提供共同记忆，工程规范为社区提供共同节奏。

---

# 11. Releases as Chapters

Benchwork 使用 SemVer 和 Schema Version 表达兼容性，使用代号表达项目历程。

早期章节：

| 里程碑 | 代号 | 主题 |
|---|---|---|
| M0 | **Foundation** | 仓库、规范与治理 |
| M1 | **Athanor** | Kernel 与 Chronicle |
| M2 | **Circle** | Capability Runtime 与权限边界 |
| M3 | **Twin Gate** | 对称 Claude/Codex Host |
| M4 | **First Rite** | 首个计算型科研工作流 |
| M5 | **Alembic** | 确定性分析与评估闭环 |
| M6 | **Open Grimoire** | 扩展生态与公开 Alpha |

版本号回答“它与什么兼容”，代号回答“这一章在建设什么”。

---

# 12. The Arcana Lexicon

| Arcana | 标准含义 | 核心表达 |
|---|---|---|
| **Benchwork** | 产品与科研工作台 | Research has a place to unfold. |
| **Arcana** | 产品语言与设计文化 | The craft has a language. |
| **Athanor** | 确定性 Kernel | Canonical transitions have an authority. |
| **Chronicle** | 追加式事件账本 | Research has a memory. |
| **Ward** | Policy 与权限保护层 | Automation has a boundary. |
| **Sigil** | 身份、摘要与回执 | Artifacts have an identity. |
| **Alembic** | 确定性分析引擎 | Measurements become analysis. |
| **Sanctum** | Agent 隔离上下文 | Reasoning has a place. |
| **Crucible** | 可变实现与实验工作区 | Change has a place to be tested. |
| **Grimoire** | 版本化扩展来源 | Reusable knowledge has a home. |
| **Rite** | 版本化科研工作流 | Method becomes a reusable path. |
| **Working** | 一次可恢复的 Rite 执行 | Research moves through a recorded process. |
| **Circle** | 单任务权限与上下文边界 | Every task has a horizon. |
| **Seal** | 科研承诺冻结操作 | Commitment takes a stable form. |

---

# 13. The Arcana in Motion

一次典型的 Benchwork 工作如下：

```text
A researcher begins a Research Program.
The Conductor selects a Rite from a pinned Grimoire.
The Rite creates a Working.
The Working opens a Circle for evidence discovery.
An Agent reasons inside a Sanctum.
Athanor accepts verified Evidence events into Chronicle.
A Protocol is shaped and then Sealed.
An Artificer develops the implementation inside a Crucible.
Runs are collected in full.
Alembic computes the analysis.
Reviewers weigh the evidence and alternatives.
The researcher commits a Decision.
Chronicle preserves the complete lineage.
```

对应的用户体验：

```bash
bwork start "研究长上下文 Agent 的记忆检索可靠性"
bwork investigate
bwork design
bwork seal protocol PT-001
bwork implement
bwork pilot
bwork run
bwork analyze
bwork review
bwork decide
bwork trace decision DE-001
```

Arcana 让这条链路拥有一致的名字，也让研究者在任何时刻都能找到自己位于何处。

---

# 14. The Promise of Benchwork

Benchwork 相信，好的科研工具应当帮助研究者同时拥有三种能力：

1. **看见。**  
   看见证据、假设、限制、失败、偏离与未决问题。

2. **塑形。**  
   将模糊意图塑造成清晰 Claim、Protocol、Experiment 和 Decision Rule。

3. **追溯。**  
   从任何结论回到它的材料、过程、计算、解释与授权。

Arcana 将这三种能力组织为一门工艺。

Athanor 提供稳定核心；Chronicle 保存研究记忆；Ward 建立行动边界；Sigil维持对象身份；Alembic 提供计算尺度；Sanctum 与 Circle塑造上下文；Crucible承载变化；Grimoire保存可复用知识；Rite描述方法；Working推动研究；Seal固定承诺。

它们共同构成 Benchwork 的语言，也共同表达 Benchwork 对科研工作的理解：

> 研究是一项长期的 Working。  
> 每项 Working 都值得被认真观察、精确塑形、完整记录，并交给下一位研究者继续。

---

# 结语

> **严谨如仪式，证据皆留痕。**

Benchwork 的 Arcana 来自对科研工艺的热爱。

它让工作台拥有名字，让过程拥有结构，让证据拥有关系，让对象拥有身份，让自动化拥有边界，让研究拥有记忆。

每一次 Scry 都扩展视野。  
每一次 Distill 都整理理解。  
每一次 Working 都推进研究。  
每一次 Seal 都固定承诺。  
每一条 Chronicle 都把今天的工作交给未来。

**This is the Arcana of Benchwork.**
