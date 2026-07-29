# Benchwork

[English](README.md) | [简体中文](README.zh-CN.md)

**面向智能体辅助计算科研的可审计工作台。**

Benchwork 将科研活动转化为明确、可审查的状态。智能体和工具可以提出工作
提案，但只有确定性的 Athanor 内核能够接受规范状态迁移。获准事件写入本地
追加式 Chronicle，并通过链式 SHA-256 Sigil 与 Receipt 留下记录。

> 项目状态：`0.2.0a3` 公开 Alpha。M0–M9 里程碑已经实现。

## 为什么需要 Benchwork

计算科研很少因为缺少一个聊天界面而失败。更常见的问题是研究意图、证据、
代码、运行、分析与决定逐渐脱节。Benchwork 为这些要素提供稳定身份和有记录
的生命周期：

```text
想法 → 证据 → 主张 → 假设 → 协议
     → 实现 → 实验 → 分析 → 审查 → 决定
```

系统明确区分两类工作：

- 研究者、智能体、Host 和工具产生的**提案**；
- 经 Athanor 验证并由 Chronicle 保存的**规范状态**。

对话仍然是有用的交互界面，但不会成为科研状态的事实来源。

## 当前已经实现

- **Athanor** 验证规范状态迁移并保证串行提交。
- **Chronicle** 使用追加式 JSONL 事件链和独立校验的 head 保存状态。
- **Sigil 与 Receipt** 使用 SHA-256 内容摘要绑定获准事件。
- **Research Program 与 Protocol** 支持受保护的
  `DRAFT → FROZEN` 生命周期。
- **Evidence、Claim 与 Hypothesis** 保存带来源的观察、验证检查、明确关系和
  可证伪预测。
- **Capability、Task Capsule、Circle 与 Ward** 在委派前约束工具、网络、
  时间与审批。
- **Codex 与 Claude Code Host** 生成对称、与 Provider 无关的任务提案。
- **Rite 与 Working** 固定工作流定义，并记录受 Protocol 约束的阶段迁移。
- **Experiment、Run 与 Alembic** 保留全部结果，并生成确定性的
  `result-bundle/1.1` 描述性聚合产物。
- **Assessment 与 Decision** 将解释绑定到 Result Bundle，并让最终科研承诺
  由人类 Seal 且可回放。
- **Artifact、Issue 与 Deviation** 保存内容寻址产物、可恢复的问题，以及不改写
  历史的 Protocol 封存后变更。
- **直动词与 Agent 交接** 创建经过 Ward 检查的 Task Proposal，并由 Athanor
  接纳绑定 Snapshot 与 Capability Contract 的 `agent-result/1.1` 输出。
- **Open Grimoire** 安装版本化、内容固定、仅数据的 Rite 包，不执行扩展代码。
- **版本化 JSON Schema** 定义科研对象、事件、任务、Run、Assessment、
  Decision 和 Result Bundle 的公共契约。

Benchwork 目前尚未提供规范远程智能体后端或自动实验执行。Alpha 阶段的
Grimoire 仅支持本地、仅数据安装；发布者签名和远程分发仍是后续工作。

## 完整性模型

检测到无效 Schema、断裂事件链、尾部截断、被修改的 Task Capsule、审批不匹配、
未注册 Rite 或无效 Working 迁移时，Benchwork 会拒绝继续。

当前完整性模型用于防止意外和可检测的漂移。SHA-256 Sigil 是内容摘要，不是
数字签名；它无法抵御能够同时替换完整 Chronicle、head 和所有 Receipt 的
恶意写入者。

完整边界参见
[Integrity Repair](docs/en/architecture/INTEGRITY_REPAIR.md)。

## 环境要求

- Python 3.11 或更高版本
- `pip`

## 安装

开发环境建议使用 editable 模式安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

安装过程会提供 `bwork` 命令，并安装运行时验证使用的版本化 JSON Schema。

## 快速开始

在允许 Benchwork 创建本地 `.benchwork/` 状态目录的位置执行：

```bash
bwork init

bwork program create robust-agent-memory \
  --title "可靠的智能体记忆" \
  --problem "测量长上下文条件下的检索可靠性。"

bwork evidence record EV-001 \
  --program RP-001 \
  --source "paper.json|sha256:0000000000000000000000000000000000000000000000000000000000000000" \
  --observation "既有工作报告了检索提升。" \
  --source-resolved \
  --content-inspected

bwork claim create CL-001 \
  --program RP-001 \
  --type empirical \
  --statement "处理方法可以提高检索表现。" \
  --evidence "EV-001|SUPPORTS"

bwork claim verify-relation CL-001 --evidence EV-001

bwork hypothesis create HY-001 \
  --program RP-001 \
  --claim CL-001 \
  --statement "处理方法提高注册检索指标。" \
  --prediction "平均指标高于基线平均值。"

bwork rq seal --program RP-001 \
  --statement "处理方法是否提高已注册检索指标？"

bwork protocol draft PT-001 \
  --program RP-001 \
  --title "记忆检索研究" \
  --analysis-plan "计算跨随机种子的效应量与不确定性。" \
  --study-mode confirmatory \
  --hypothesis HY-001 \
  --analysis-spec examples/basic-analysis-spec.json

bwork protocol seal PT-001

bwork working start computational-study@0.2.0 \
  --program RP-001 \
  --protocol PT-001

bwork artifact register AR-001 \
  --program RP-001 \
  --kind implementation \
  --location "artifact.json|sha256:<由-bwork-sigil-file-得到的摘要>" \
  --producer WK-001 \
  --input PT-001

bwork experiment create EX-001 \
  --program RP-001 \
  --protocol PT-001 \
  --hypothesis HY-001 \
  --question "处理方法是否提高已注册指标？"

bwork experiment transition EX-001 implemented
bwork experiment transition EX-001 pilot-started

bwork run record RUN-000 \
  --experiment EX-001 \
  --phase PILOT \
  --status COMPLETED \
  --include \
  --arm baseline \
  --seed 1 \
  --metric score=0.80

bwork run record RUN-001 \
  --experiment EX-001 \
  --phase PILOT \
  --status COMPLETED \
  --include \
  --arm treatment \
  --seed 1 \
  --metric score=0.82

bwork experiment transition EX-001 pilot-completed

bwork analyze --program RP-001 --protocol PT-001

bwork review RB-001 \
  --summary "注册结果支持该假设。" \
  --limitation "目前只有一组配对观察。" \
  --claim-finding "CL-001|SUPPORTED|观察方向与 Claim 一致。" \
  --hypothesis-finding "HY-001|SUPPORTED|预测得到满足。"

bwork decide \
  --program RP-001 \
  --outcome CONTINUE \
  --assessment AS-001 \
  --rationale "继续收集注册 Run。"

bwork status
bwork doctor
bwork trace CL-001
```

在新项目中，上述命令会建立从 `EV-001` 到已 Seal 的 `DE-001` 的完整追踪。
匹配的规范事件会让 `WK-001` 按固定退出契约推进到 `COMPLETED`。

操作完整性对象仍可与科学链并列记录：

```bash
bwork issue open IS-001 \
  --program RP-001 \
  --subject AR-001 \
  --severity HIGH \
  --title "环境元数据不完整" \
  --description "缺少一个依赖版本。"

bwork deviation record DV-001 \
  --protocol PT-001 \
  --kind UNPLANNED \
  --summary "Protocol 封存后补充环境元数据。" \
  --rationale "精确回放需要缺失的版本。" \
  --impact MINOR \
  --affected AR-001 \
  --affected IS-001

bwork issue resolve IS-001 \
  --resolution "在保留原始 Artifact 的前提下登记缺失版本。"
```

全零摘要只是在文档中使用的、语法有效的占位符。正式记录应使用对应 Artifact
的真实 SHA-256 摘要。

## Capability 与审批流程

Task Capsule 声明 Capability、输入 Sigil、允许使用的工具、网络访问和时间预算。
Ward 将这个 Circle 与本地 Capability 契约进行比较：

```text
任务请求
    ↓
Task Capsule + Circle
    ↓
Ward ── REJECTED
    ├── WAITING_FOR_APPROVAL → 人工审批 Receipt → PASS
    └── PASS
```

RFC 直动词复用同一边界：

```bash
bwork start "研究可恢复的智能体记忆"
bwork investigate --program RP-001
bwork design --program RP-001
bwork implement --program RP-001
bwork pilot --program RP-001
bwork run --program RP-001

bwork scry literature --program RP-001
bwork distill evidence --program RP-001
bwork invoke bench.hypothesis.challenge --program RP-001
```

`investigate` 与 `design` 通常通过只读契约；`implement`、`pilot` 和裸
`run` 会停在 `WAITING_FOR_APPROVAL`。这些命令只准备 Task Capsule，不会把
尚未发生的 Provider 工作报告为完成。Provider 返回 `agent-result/1.1` 文件后：

```bash
bwork task accept agent-result.json
bwork trace task TK-001
bwork chronicle verify
bwork sigil verify artifact.json
```

常用发现命令：

```bash
bwork capability list
bwork host list
bwork rite list
bwork grimoire list
bwork --help
```

## 命令地图

| 命令 | 用途 |
|---|---|
| `bwork init` | 初始化 Chronicle、Capability 契约、Rite 与 Grimoire |
| `bwork status` | 重建并输出规范状态 |
| `bwork doctor` | 验证 Chronicle 事件、Sigil、head 与 Receipt 链 |
| `bwork program` | 创建 Research Program |
| `bwork start` | 从研究目标启动 Research Program |
| `bwork investigate`、`design`、`implement`、`pilot`、`run` | 准备有边界的阶段 Task |
| `bwork scry`、`distill`、`invoke` | 准备 Arcana 或显式 Capability Task |
| `bwork seal` | 使用 RFC 直达形式 Seal Protocol |
| `bwork evidence` | 记录、验证和查看有来源的 Evidence |
| `bwork claim` | 创建 Claim 并显式验证 Evidence 关系 |
| `bwork hypothesis` | 创建和查看可证伪 Hypothesis |
| `bwork rq` | 显式封存 Research Question |
| `bwork protocol` | 起草并封存 Protocol |
| `bwork reproduction` | 将复现状态绑定到规范科研对象 |
| `bwork capability` | 查看已安装的 Capability 契约 |
| `bwork task` | 创建/查看 Task Capsule，并接纳 Agent Result |
| `bwork ward` | 根据策略评估 Task Capsule |
| `bwork approval` | 记录明确的人工审批 |
| `bwork host` | 创建 Codex 或 Claude Code Host 提案 |
| `bwork rite` | 查看固定版本的工作流定义 |
| `bwork grimoire` | 计算 Rite Sigil 并安装固定版本的本地 Grimoire |
| `bwork working` | 启动、查看和推进 Rite 执行 |
| `bwork experiment` | 创建绑定 Protocol 的 Experiment |
| `bwork run record` | 记录不可变 Run 及其分析纳入状态 |
| `bwork analyze` | 生成确定性的 Alembic Result Bundle |
| `bwork review` | 记录 Result Bundle Assessment |
| `bwork assessment` | 查看已完成的 Assessment |
| `bwork decide` | 由人类 Seal 科研 Decision |
| `bwork decision` | 查看已 Seal 的 Decision |
| `bwork artifact` | 登记和查看内容寻址 Artifact |
| `bwork issue` | 打开、解决和查看科研 Issue |
| `bwork deviation` | 记录和查看 Protocol 封存后的 Deviation |
| `bwork chronicle` | 输出或验证 Chronicle |
| `bwork sigil` | 输出对象/Receipt Sigil 或验证文件 |
| `bwork trace` | 查看一个对象对应的 Chronicle 事件 |

使用 `bwork <command> --help` 查看具体参数。

## 本地状态

`bwork init` 创建项目本地状态：

```text
.benchwork/
├── chronicle.jsonl
├── chronicle.head
├── chronicle.lock
├── capabilities.json
├── capabilities.lock
├── rites.json
├── grimoires.json
├── grimoires.lock
└── capsules/
```

Chronicle 是规范状态。Task Capsule 是不可变、可检查的提案；在获准状态迁移
引用它之前，它存储在规范账本之外。

## 文档

| 主题 | English | 简体中文 |
|---|---|---|
| 文档索引 | [English](docs/en/README.md) | [简体中文](docs/zh-CN/README.md) |
| Arcana 语言与设计 | [RFC-0000](docs/en/rfcs/RFC-0000-arcana.md) | [RFC-0000](docs/zh-CN/rfcs/RFC-0000-arcana.md) |
| Athanor 不变量 | [架构说明](docs/en/architecture/ATHANOR.md) | — |
| Circle 与 Ward | [架构说明](docs/en/architecture/CIRCLE.md) | — |
| Host 对称性 | [Twin Gate](docs/en/architecture/TWIN_GATE.md) | — |
| Working 生命周期 | [First Rite](docs/en/architecture/FIRST_RITE.md) | — |
| 分析边界 | [Alembic](docs/en/architecture/ALEMBIC.md) | — |
| 科研规范对象 | [Scientific Canon](docs/en/architecture/SCIENTIFIC_CANON.md) | — |
| 完整性与恢复 | [Integrity and Recovery](docs/en/architecture/INTEGRITY_RECOVERY.md) | — |
| 命令与 Agent 交接 | [Command Surface](docs/en/architecture/COMMAND_SURFACE.md) | — |
| 扩展边界 | [Open Grimoire](docs/en/architecture/OPEN_GRIMOIRE.md) | — |
| 本地化 | [规则](docs/LOCALIZATION.md) | — |

英文是文档的规范来源。翻译缺失时回退到英文页面，不在语言目录中复制未经翻译
的英文文档。

## 仓库结构

```text
src/benchwork/     Athanor 内核、CLI、Ward、Host、Rite 与 Grimoire
schemas/           公开的版本化 JSON Schema 契约
tests/             确定性单元测试与完整性测试
docs/en/           规范英文文档
docs/zh-CN/        简体中文翻译
hosts/             Host 集成指南
examples/          最小科研 Artifact 示例
```

## 开发

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

涉及规范状态迁移的改动，应根据情况补充回放、Schema 验证、完整性失败和并发
测试。文档改动应保持 locale 路径一致，并遵循
[本地化规则](docs/LOCALIZATION.md)。

## 许可证

Benchwork 采用 [MIT License](LICENSE)。
