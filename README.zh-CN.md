# Benchwork

[English](README.md) | [简体中文](README.zh-CN.md)

**面向智能体辅助计算科研的可审计工作台。**

Benchwork 将科研活动转化为明确、可审查的状态。智能体和工具可以提出工作
提案，但只有确定性的 Athanor 内核能够接受规范状态迁移。获准事件写入本地
追加式 Chronicle，并通过链式 SHA-256 Sigil 与 Receipt 留下记录。

> 项目状态：`0.1.0.dev0`。M0–M4 里程碑已经实现；M5
>（通过 Alembic 提供确定性分析）正在推进。

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
- **Capability、Task Capsule、Circle 与 Ward** 在委派前约束工具、网络、
  时间与审批。
- **Codex 与 Claude Code Host** 生成对称、与 Provider 无关的任务提案。
- **Rite 与 Working** 固定工作流定义，并记录受 Protocol 约束的阶段迁移。
- **版本化 JSON Schema** 定义科研对象、事件、任务、Run、Assessment、
  Decision 和 Result Bundle 的公共契约。

下一项活跃里程碑是 Alembic 的确定性 `result-bundle/1.0` 计算。Benchwork
目前尚未提供规范远程智能体后端、自动实验执行或公开的 Grimoire 扩展生态。

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

bwork protocol draft PT-001 \
  --program RP-001 \
  --title "记忆检索研究" \
  --analysis-plan "计算跨随机种子的效应量与不确定性。"

bwork protocol seal PT-001

bwork working start computational-study@0.1.0 \
  --program RP-001 \
  --protocol PT-001

bwork status
bwork doctor
bwork trace PT-001
```

在新项目中，上述命令会创建 `RP-001`、冻结 `PT-001`，并让 `WK-001`
从 `IMPLEMENTATION` 阶段开始。

每次 Working 迁移都必须提供固定 Rite 所要求的 Artifact：

```bash
bwork working advance WK-001 \
  --reason "实现已经审查。" \
  --artifact "implementation|artifact.json|sha256:0000000000000000000000000000000000000000000000000000000000000000"
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

常用发现命令：

```bash
bwork capability list
bwork host list
bwork rite list
bwork --help
```

## 命令地图

| 命令 | 用途 |
|---|---|
| `bwork init` | 初始化 Chronicle、Capability 契约与 Rite |
| `bwork status` | 重建并输出规范状态 |
| `bwork doctor` | 验证 Chronicle 事件、Sigil、head 与 Receipt 链 |
| `bwork program` | 创建 Research Program |
| `bwork protocol` | 起草并封存 Protocol |
| `bwork capability` | 查看已安装的 Capability 契约 |
| `bwork task` | 创建和查看有边界的 Task Capsule |
| `bwork ward` | 根据策略评估 Task Capsule |
| `bwork approval` | 记录明确的人工审批 |
| `bwork host` | 创建 Codex 或 Claude Code Host 提案 |
| `bwork rite` | 查看固定版本的工作流定义 |
| `bwork working` | 启动、查看和推进 Rite 执行 |
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
├── rites.json
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
| 本地化 | [规则](docs/LOCALIZATION.md) | — |

英文是文档的规范来源。翻译缺失时回退到英文页面，不在语言目录中复制未经翻译
的英文文档。

## 仓库结构

```text
src/benchwork/     Athanor 内核、CLI、Ward、Host 与 Rite
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
