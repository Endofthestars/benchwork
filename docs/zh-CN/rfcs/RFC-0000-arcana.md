---
title: "RFC-0000：Benchwork 的 Arcana"
subtitle: 语言、哲学与设计总纲
document_id: BW-RFC-0000
version: 0.2
status: accepted
owner: Endofthestars
date: 2026-07-29
language: zh-CN
canonical: false
translation_key: BW-RFC-0000
translation_of: ../../en/rfcs/RFC-0000-arcana.md
source_version: 0.2
---

# RFC-0000：Benchwork 的 Arcana

[English](../../en/rfcs/RFC-0000-arcana.md) | [简体中文](RFC-0000-arcana.md)

> **严谨如仪式，证据皆留痕。**

## 序言

Benchwork 是一张面向计算型科研的工作台。研究者在这里提出问题、整理证据、形成主张、设计协议、实现系统、运行实验、解释结果，并据此作出下一步决定。每一项工作都具有来源、边界、版本和历史；每一次推进都能够被理解、复核和继续。

**Arcana** 是 Benchwork 的语言。它从实验室、炼金工艺、手稿、星图与精密仪器中汲取灵感，表达研究中的观察、提炼、塑形、试验、记录与承诺。

它的核心气质是：专注过程、尊重证据、自觉边界、慎重承诺、诚实记录失败与偏离、对未知保持开放，并长期坚持可复核性。

# 1. 工作台

工作台承载材料、器具、草图、测量、试验和记录。它允许探索，也要求秩序；它容纳创造，也保留痕迹。研究者可以暂时离开，再回到同一项工作；也可以邀请另一位研究者沿着已有记录继续推进。

研究沿着如下路径发展：

```text
想法 → 证据 → 主张 → 假设 → 协议 → 实现 → 实验 → 分析 → 审查 → 决定
```

这条路径可以循环、分支、暂停和回溯。每一次循环都产生新的证据，每一个分支都保留谱系，每一次决定都成为后续工作的起点。Benchwork 将研究理解为一项持续的 **Working**：一项被观察、被塑形、被检验，并能够被重新理解的工作。

# 2. Arcana 的语言

Arcana 由三层语言构成。

## 2.1 科学正典

科学正典描述研究本身的正式对象：Research Program、Claim、Evidence、Hypothesis、Protocol、Experiment、Run、Assessment、Issue、Decision、Deviation、Artifact 与 Receipt。

这些词用于 Schema、API、研究导出包、审计记录和正式方法文档。它们保持直接、稳定、可比较，使 Benchwork 能够与既有科研实践、统计工具和外部系统自然连接。

## 2.2 Arcana 机制

Arcana 机制描述 Benchwork 如何工作：Athanor、Chronicle、Ward、Sigil、Alembic、Sanctum、Crucible、Grimoire、Rite、Working、Circle 与 Seal。它们构成产品的运行时语言，出现在 CLI、终端、文档导航、扩展生态和架构图中。

## 2.3 能力语言

能力使用清晰、功能化、模型无关的名称，例如：

```text
bench.research.orchestrate       bench.evidence.discover
bench.evidence.synthesize        bench.evidence.verify
bench.hypothesis.frame           bench.hypothesis.challenge
bench.study.design               bench.study.audit
bench.code.inspect               bench.code.modify
bench.experiment.plan            bench.experiment.execute
bench.experiment.collect         bench.analysis.compute
bench.analysis.interpret         bench.decision.review
bench.decision.propose
```

Claude、Codex 与未来模型通过同一 Capability 契约参与工作。科学正典命名研究对象；Arcana 机制命名科研工艺；能力语言命名可执行动作。

# 3. Working 的哲学

## 3.1 研究留下痕迹

研究通过痕迹获得连续性。Claim 可追溯到 Evidence，Evidence 可追溯到来源、数据或 Run，Decision 可追溯到分析、审查、异议与授权。Benchwork 将连续性写入 Chronicle，并通过 Sigil 保持对象身份。

## 3.2 证据形成星座

证据散布于论文、代码、数据、实验结果与专家判断。Benchwork 将其组织为支持、反驳、限制、复现、扩展与未决的关联结构。单个来源提供观察，多项观察形成星座，帮助研究者理解问题的边界与方向。

## 3.3 协议塑造意图

Protocol 将研究意图塑造成可执行承诺：它连接 Claim、Hypothesis、数据、对照、测量、运行矩阵、分析计划和决策规则。Protocol 经 Seal 封存后获得稳定版本；后续变化通过 Deviation 进入 Chronicle。

## 3.4 计算与解释互补

Alembic 负责描述统计、效应量、不确定性、稳健性、资源使用和运行完整性。Agent 与研究者解释结果支持或限制了什么、有哪些竞争解释，以及下一项实验能带来什么信息。计算提供可重复的尺度，解释提供科学语境。

## 3.5 能力契约不随提供者更替

Capability 是 Benchwork 中稳定的能力单位。Claude、Codex、本地模型、远程模型与确定性执行器都可以实现它；调度由任务需求、工具、权限、预算、质量与用户策略决定。模型可以更替，Capability 契约、科研对象与 Chronicle 保持连续。

## 3.6 人类判断封存承诺

研究者拥有科研承诺的最终权威。Agent 帮助探索、整理、挑战、设计和解释；Athanor 验证结构与状态；Ward 检查权限和条件；研究者在方向、协议、正式实验和决定等关键节点确认。

## 3.7 失败是记录的一部分

失败 Run、负结果、取消任务、协议偏离与未解决 Issue 都属于研究历史。Chronicle 保存这些事件，使后续判断能理解一项工作为何继续、修复、转向或停止。失败成为信息，偏离成为上下文，停止成为有依据的科研决定。

## 3.8 研究经由谱系生长

Research Program 可以形成分支与谱系。一个方向可派生新问题，一个失败机制可转化为新假设，一个 PIVOT 可建立新 Program，同时保留与原工作的关系。科研是一棵持续生长的知识树。

# 4. 核心 Arcana

| 名称 | 标准含义 | 职责 |
|---|---|---|
| **Athanor** | 确定性核心炉 | 接收 Proposal，验证 Schema、引用、摘要、Gate 与授权条件；将获准的变化写入 Chronicle 并生成 Receipt。它负责一切规范状态迁移。 |
| **Chronicle** | 追加式科研事件账本 | 记录 Program、Claim、Evidence、Protocol、Run、Assessment 与 Decision；支持状态重建、历史回放、审计与比较。 |
| **Ward** | 保护层 | 在行动前给出权限、预算、租约、完整性与审批边界，并检查后置条件。 |
| **Sigil** | 稳定身份 | 连接内容摘要、来源、输入、输出、执行者、Policy 与 Receipt。 |
| **Alembic** | 确定性分析引擎 | 将 Run、测量和资源记录提炼为机器可读统计产物。 |
| **Sanctum** | Agent 隔离上下文 | 包含特定目标、可见材料、工具、预算和输出契约。 |
| **Crucible** | 可变工作区 | 在 Git worktree、容器、沙箱或远程目录中进行修改、调试、配置和试验。 |
| **Grimoire** | 版本化扩展来源 | 汇集 Rites、Capability Packs、各类 Adapter、Policy Packs、Schema Extensions、示例与 Benchmark。 |
| **Rite** | 版本化科研工作流 | 将目标、Capability、输入输出、Gate、Ward、人工审批点和停止条件组织成可复用过程。 |
| **Working** | 可恢复的 Rite 执行 | 绑定 Program、Rite 版本、输入、Policy、Provider 和 Task Graph，并记录状态、Receipt、失败、重试与检查点。 |
| **Circle** | 单任务边界 | 声明 Artifact、文件、网络、工具、执行权限、时间预算、费用预算和输出 Schema。 |
| **Seal** | 承诺冻结操作 | 为 Protocol、Analysis Plan、Decision 与对外导出包生成稳定版本和 Sigil。 |

# 5. Benchwork 的语法

```text
Grimoire 汇集可复用的 Rite；
Rite 被实例化为一次 Working；
Working 由一组 Task 推进；
每个 Task 都获得自己的 Circle；
Agent 在 Sanctum 中完成推理；
实现与实验在 Crucible 中演化；
Alembic 根据完整 Run 记录完成计算；
Ward 检查策略、权限和资源；
Athanor 接受规范状态变化；
Chronicle 保存已接受的事件；
Sigil 标识对象、产物与回执；
Seal 固定一个阶段的科研承诺。
```

# 6. 工作台命令

日常科研路径使用直接动词：

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

Arcana 操作表达 Benchwork 特有工艺：

```bash
bwork scry literature
bwork distill evidence
bwork invoke bench.evidence.verify
bwork seal protocol PT-001
bwork ward check
bwork trace claim CL-001
```

Scry 探索文献、代码与证据空间；Distill 将已检查材料整理为结构化 Proposal；Invoke 调用明确的 Capability；Seal 固定科研承诺；Ward 检查权限、预算、完整性与审批条件；Trace 重建对象、事件、Artifact 与 Decision 的谱系。

扩展生态也以对象命令进入日常实践：

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

# 7. Agent、Host 与 Provider

Benchwork 以 Capability 组织智能工作。Claude、Codex 和未来模型都可以作为研究者的交互入口，执行 `bench.research.orchestrate`，调用同一组 Capability，并通过统一输出契约将结果交还 Athanor。

Host 是研究者当前交互所在的环境；Provider 是实际执行 Capability 的模型或 Agent 后端；Capability 是稳定定义的科研动作。同一 Host 可调用不同 Provider，同一 Capability 可由多个 Provider 执行。

**Conductor** 是 `bench.research.orchestrate` 的产品称谓。它读取 Program 状态，理解研究者目标，形成 Task Proposal，调用 Capability，汇总 Working，并在需要科研承诺时邀请研究者确认。

| 能力领域 | Arcana 称谓 | Capability 范围 |
|---|---|---|
| 证据 | **Archivist** | `bench.evidence.*` |
| 方法 | **Adept** | `bench.hypothesis.*`、`bench.study.*` |
| 质询 | **Adversary** | 质询与审计 |
| 代码 | **Artificer** | `bench.code.*` |
| 执行 | **Hand** | `bench.experiment.*` |
| 完整性 | **Warden** | 策略与评估 |
| 维护 | **Keeper** | 配置与扩展 |

# 8. 声音与语调

Benchwork 的声音来自精密仪器、实验记录与冷静的研究伙伴：清楚、克制、稳定、有仪器感；能表达不确定性；重视对象、状态、来源和下一步；在关键科研承诺前呈现后果与上下文。

```text
BENCHWORK · ATHANOR
项目          /work/robust-memory
研究计划      RP-001
工作实例      WK-014
Rite          ml-computational-study@0.1.0
状态          WAITING_FOR_APPROVAL

Ward          需要审批：protocol.seal
对象          PT-003
Sigil         sha256:3d8b…9a21

下一步        审查协议并确认封存
```

Working 完成时：

```text
Working WK-014 已完成。
任务          7 项完成 · 1 项失败
Chronicle     已追加 12 个事件
Receipts      RC-031 … RC-042
决定          REVIEW_REQUIRED
下一步        科学审查
```

Benchwork 的语言应让研究者始终清楚：发生了什么、留下了什么、仍缺少什么，以及下一步由谁决定。

# 9. 视觉语言

视觉世界来自一间现代而古老的实验室：深色工作台、黄铜精密仪器、羊皮纸般的浅色阅读面、手稿边注、星图式关系网络、几何刻度、封蜡与印记，以及受控容器与可追溯路径。

| 名称 | 用途 | 示例 |
|---|---|---|
| Obsidian | 主背景 | `#111318` |
| Ash | 次级背景 | `#2C3038` |
| Parchment | 浅色阅读面 | `#F3EFE5` |
| Brass | 品牌强调 | `#B78A3B` |
| Lapis | 信息与链接 | `#4B5FA8` |
| Verdigris | 已验证与完成 | `#4F8A7B` |
| Cinnabar | 严重状态与停止状态 | `#B74A3D` |

矩形表示确定性组件，圆角矩形表示 Capability 或 Adapter，圆形表示 Gate 与 Approval Point，六边形表示 Artifact 或科研对象；实线箭头表示已提交状态流，虚线箭头表示 Proposal 与候选数据，双线边框表示 Sealed Object。设计服务于阅读、状态理解和谱系追踪。

# 10. Grimoires、Rites 与社区

Grimoire 与 Rite 构成开放生态。一个 Grimoire 可聚集领域研究方法、Capability、Provider Adapter、Policy、Schema、样例和 Benchmark，例如 `endofthestars/ml-research`。一个 Rite 描述可复用科研路径，例如 `ml-computational-study`、`paper-reproduction`、`benchmark-audit`、`systematic-evidence-map` 与 `ablation-study`。

贡献者以所有者、维护者、审查者、贡献者、安全联系人和 Rite 维护者等职责协作。社区栏目可以自然地使用“新 Rite”“Athanor 变更”“Chronicle 兼容性”“Ward 与安全说明”“Grimoire 更新”和“Seal 破坏性变更”等名称。

Arcana 为社区提供共同记忆，工程规范为社区提供共同节奏。工程活动仍保持可搜索与可自动化：

```text
feat(chronicle): add atomic append receipt
fix(ward): handle expired approval token
docs(arcana): refine seal semantics
```

# 11. 发布即章节

Benchwork 使用 SemVer 和 Schema Version 表达兼容性，使用代号表达项目历程。

| 里程碑 | 代号 | 主题 |
|---|---|---|
| M0 | **Foundation** | 仓库、规范与治理 |
| M1 | **Athanor** | 内核与 Chronicle |
| M2 | **Circle** | Capability 运行时与权限边界 |
| M3 | **Twin Gate** | 对称 Claude/Codex Host |
| M4 | **First Rite** | 首个计算型科研工作流 |
| M5 | **Alembic** | 确定性分析与评估闭环 |
| M6 | **Open Grimoire** | 扩展生态与公开 Alpha |

版本号回答“它与什么兼容”，代号回答“这一章在建设什么”。

# 12. Arcana 词典

| Arcana | 标准含义 | 核心表达 |
|---|---|---|
| **Benchwork** | 产品与科研工作台 | 研究在这里展开。 |
| **Arcana** | 产品语言与设计文化 | 科研工艺拥有共同语言。 |
| **Athanor** | 确定性核心 | 规范状态迁移拥有明确权威。 |
| **Chronicle** | 追加式事件账本 | 研究拥有记忆。 |
| **Ward** | Policy 与权限保护层 | 自动化拥有边界。 |
| **Sigil** | 身份、摘要与回执 | 产物拥有身份。 |
| **Alembic** | 确定性分析引擎 | 测量转化为分析。 |
| **Sanctum** | Agent 隔离上下文 | 推理拥有明确场所。 |
| **Crucible** | 可变实现与实验工作区 | 变化拥有接受检验的场所。 |
| **Grimoire** | 版本化扩展来源 | 可复用知识拥有归处。 |
| **Rite** | 版本化科研工作流 | 方法成为可复用路径。 |
| **Working** | 可恢复的 Rite 执行 | 研究沿着有记录的过程推进。 |
| **Circle** | 单任务权限与上下文边界 | 每项任务都有清晰边界。 |
| **Seal** | 科研承诺冻结操作 | 承诺获得稳定形式。 |

# 13. Arcana 的运行

一项典型的 Benchwork 工作如下：研究者创建 Research Program；Conductor 从固定版本的 Grimoire 中选择 Rite；Rite 创建 Working；Working 为证据发现开启 Circle；Agent 在 Sanctum 中推理；Athanor 接受已验证的 Evidence，并将相应事件写入 Chronicle；Protocol 经过塑形与 Seal；Artificer 在 Crucible 中开发实现；系统完整收集 Runs；Alembic 完成分析计算；审查者权衡证据与替代解释；研究者提交 Decision；Chronicle 保存完整谱系。

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

# 14. Benchwork 的承诺

好的科研工具应帮助研究者同时拥有三种能力：**看见**证据、假设、限制、失败、偏离与未决问题；**塑形**，将模糊意图转化为清晰的 Claim、Protocol、Experiment 和决策规则；**追溯**，从任何结论回到它的材料、过程、计算、解释与授权。

Arcana 将这些能力组织为一门工艺。Athanor 提供稳定核心；Chronicle 保存研究记忆；Ward 建立行动边界；Sigil 维持对象身份；Alembic 提供计算尺度；Sanctum 与 Circle 塑造上下文；Crucible 承载变化；Grimoire 保存可复用知识；Rite 描述方法；Working 推动研究；Seal 固定承诺。

> 研究是一项长期的 Working。每项 Working 都值得被认真观察、精确塑形、完整记录，并交由下一位研究者继续。

# 结语

Benchwork 的 Arcana 来自对科研工艺的热爱。它让工作台拥有名字，让过程拥有结构，让证据拥有关系，让对象拥有身份，让自动化拥有边界，让研究拥有记忆。

每一次 Scry 都扩展视野。每一次 Distill 都整理理解。每一次 Working 都推进研究。每一次 Seal 都固定承诺。每一条 Chronicle 记录都把今天的工作交给未来。
