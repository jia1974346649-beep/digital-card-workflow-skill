# 数字名片产品：从研究到交付的 Skill

![从产品目标到可验证交付](assets/process-overview.svg)

一个由真实项目经验提炼、重新撰写的 **AI 协作产品工作法作品集**。从最初的参考产品研究和需求拆解，经过角色设计、界面方案、原生分享、兼容升级、验证与文档，沉淀为可复用的 Codex skill。

**我的职责：** 主导业务目标、需求取舍、角色流程、界面方案选择与体验反馈，推动迭代优先级、隐私边界和交付要求。AI 协助研究、方案细化、代码实现与修改、排错、自动化检查和文档整理；工程成果采用 AI 协作模式完成。

**实践规模：** 原业务工程前后端源文件合计约 **5 万行**。这是原项目的匿名规模摘要，本仓库公开方法、模板和演示材料。详细统计口径与分工见 [项目规模与职责](#项目规模与职责)。

**公开范围：** 方法论、匿名复盘、原创通用示意图、模板和全新演示脚本。这里没有原公司的源码、Logo、人物、资料、聊天截图或部署信息；画面均为重新制作的示意。

## 快速开始：安装到自己的 Codex

### 1. 复制安装指令

在自己的 **Codex 聊天输入框**粘贴并发送下面整段内容。代码块右上角的复制按钮可直接复制：

```text
请用 $skill-installer 安装下面的 Codex Skill：
https://github.com/jia1974346649-beep/digital-card-workflow-skill/tree/main/skills/card-product-workflow
```

安装器会下载完整的 `card-product-workflow` 文件夹，包含指令、参考资料、模板和检查脚本。安装成功后，在下一条消息中使用；如果还没有识别到，重启 Codex 再试。

### 2. 复制使用示例

在 Codex 中打开自己的项目，然后发送：

```text
使用 $card-product-workflow。
我要做一个数字名片产品，请先整理需求，
划分员工、管理员、总管理员和访客的权限，
再给出首版范围、开发步骤和验证计划。
先完成规划，等我确认后再开始实现。
```

安装后可用名称为 `card-product-workflow`，显示名称为“名片产品全流程”。也可以描述具体问题，让 Codex 按这套工作法推进。

### 3. 准备自己的项目资料

提供目标用户、平台、已有代码和本次要完成的事情即可。现有项目可以直接从研究、开发、修复或交付中的任意阶段开始。

安装得到的是可复用的产品工作法、参考资料和模板。完整的名片应用需要在自己的项目中开发；微信、云服务、数据库与发布操作需要使用者自己的账号、配置和授权。运行本仓库提供的 Python 校验脚本时才需要准备 Python。

安装与技能发现机制见 [OpenAI 官方 Skill 说明](https://developers.openai.com/codex/skills)。

## 项目规模与职责

### 实践范围

项目围绕企业数字名片场景开展迭代，涉及员工、管理员、总管理员与访客的任务和权限，以及名片编辑、展示配置、分享与再次转发、咨询留资、图文视频内容、头像审核、云同步和失败恢复。

本作品展示从产品研究、需求拆解、体验反馈到实现协作和文档整理的过程，并将其中可复用的经验提炼为 Skill。

### 匿名工程规模

以下为 **2026-10-22 本地原业务工程**的汇总统计；不包含原业务源码或逐文件清单。

| 统计范围 | 物理行数，约 | 口径 |
| --- | ---: | --- |
| 当前入口关联的小程序前端 | 3.6 万 | 页面与共享模块，按静态依赖关联统计 |
| 云端服务源文件 | 1.4 万 | 扣除迁移运行器与证明脚本 |
| **前后端源文件合计** | **5 万** | **非空行约 4.75 万，仍包含注释** |
| 数据库脚本，另列 | 1.8 万 | 累计建表和升级脚本，包含历史替换定义 |
| 测试源文件，另列 | 5 万 | 前后端测试文件量，不是通过的测试项数 |

物理行数包含注释和空行。前后端主体统计已排除第三方依赖、构建产物、同步副本、未注册旧页面及其他平台目录；数据库脚本和测试文件单列，不纳入上述主体合计。

这些数字描述原工程规模，**不代表本仓库公开代码量、本人逐行手写量或全部在线执行的代码量**。原业务工程与内部运行记录未公开，本仓库不能独立复现原工程的统计；静态文件统计也不证明当前正式部署或全部设备验收完成。

### 本人与 AI 的协作分工

| 参与方式 | 主要工作 |
| --- | --- |
| 本人主导 | 提出业务目标与使用场景，确定需求和优先级，选择界面方案，反馈实际体验问题，提出隐私和交付要求 |
| AI 协作 | 辅助研究与任务拆解，生成和修改代码，分析故障，编写自动化检查、流程说明与文档 |
| 协作产出 | 在本人确定的公开范围内，与 AI 协作整理匿名案例、角色流程、交付模板和可安装 Skill |

## 可展示的能力与材料

| 能力方向 | 项目中的实践 | 本仓库可查看的材料 |
| --- | --- | --- |
| 产品研究与需求拆解 | 将参考产品能力转化为用户任务、范围取舍和分阶段工作项 | [研究到交付](docs/research-to-delivery.md) · [需求拆解示例](examples/discovery-brief.md) |
| 角色与业务流程分析 | 梳理员工、管理员、总管理员和访客的操作边界，以及资料、咨询和分享的归属 | [角色与数据边界](skills/card-product-workflow/references/roles-and-data.md) · [通用架构图](assets/role-and-state-map.svg) |
| 体验判断与迭代推进 | 围绕阅读字号、长字段、原生输入和媒体编辑体验提出反馈并推进修正 | [界面与可读性](skills/card-product-workflow/references/ui-and-readability.md) · [匿名项目案例](docs/case-study.md) |
| AI 协作与交付组织 | 将实际问题拆为实现与验证任务，区分构建、上传、原生环境验证和真实收件等证据 | [验证与发布方法](skills/card-product-workflow/references/verification-and-release.md) · [证据矩阵](skills/card-product-workflow/assets/templates/evidence-matrix.md) |
| 知识复用与公开材料整理 | 按身份组织使用说明，保留验证边界，以匿名案例和通用示意图沉淀可复用资源 | [角色手册大纲](skills/card-product-workflow/assets/templates/role-guide-outline.md) · [Skill 入口](skills/card-product-workflow/SKILL.md) · [公开边界](docs/publication-boundary.md) |

能力说明以本仓库可查阅的实践材料为依据；工程规模与验证结果按各自口径呈现。

## 从哪里看

| 想了解的内容 | 入口 |
| --- | --- |
| 最初如何从一个大目标拆出产品范围 | [产品研究到交付](docs/research-to-delivery.md) |
| 真实迭代中做了哪些判断、犯过哪些错 | [匿名项目案例](docs/case-study.md) |
| 了解项目规模、本人职责和能力实践 | [项目规模与职责](#项目规模与职责) · [可展示的能力与材料](#可展示的能力与材料) |
| 安装并使用这套工作法 | [快速开始](#快速开始安装到自己的-codex) · [Skill 主入口](skills/card-product-workflow/SKILL.md) |
| 看作品展示图与流程卡片 | [静态作品页](index.html) · [流程总览](assets/process-overview.svg) |
| 理解本人、团队与访客之间的关系 | [通用架构图](assets/role-and-state-map.svg) |
| 看目标如何转成可验证的工作项 | [需求拆解示例](examples/discovery-brief.md) |
| 查看公开内容的边界与检查方法 | [发布边界](docs/publication-boundary.md) |

静态作品页没有后端、登录、统计脚本或真实二维码。可下载后直接打开 `index.html`；GitHub 中可先浏览 README 与 SVG 图。

## 这套 Skill 解决什么

- **需求太大：** 将参考产品拆成用户任务、独立设计、外部依赖和暂不实现的能力，维护早期原型与当前产品的边界。
- **身份太多：** 明确员工、管理员、所有者与访客各自可读、可写和可分享的资料。
- **分享状态混淆：** 区分请求成功、实际收件、头像审核、公开投影与再次转发，不靠自动重发掩盖不确定结果。
- **改版破坏旧数据：** 保留旧咨询原文，让新字段、编辑草稿与现有记录和平共存。
- **验证说得过满：** 将单测、浏览器、原生模拟器、真实设备、实际收件和平台版本核对分别记录。
- **交付说明落后：** 按角色组织手册，在相应动作旁说明设备差异，保留截图真实来源。

## 更多使用示例与手动安装

### 研究与需求拆解

```text
使用 $card-product-workflow。
我想做一个数字名片产品，先研究参考产品的公开能力，
再为员工、管理员和访客收敛首个业务闭环。
请给需求矩阵、角色边界和验证计划，不要复制品牌素材。
```

### 修复已有项目

```text
使用 $card-product-workflow。
访客再次打开名片时偶尔看不到资料。
请先复现并画出读取、缓存和权限状态，再做针对性修复；
区分浏览器、模拟器与真实设备证据，别自动重复分享。
```

### 更新三种身份的使用说明

```text
使用 $card-product-workflow。
请根据当前项目的实际功能和版本证据，
分别更新员工、管理员和总管理员的使用流程。
排版整齐，标清截图来源；未验证的步骤明确标注。
```

### 手动安装

也可以下载本仓库，解压后将 `skills/card-product-workflow` **整个文件夹**复制到以下一个位置：

| 使用范围 | 复制后的目录 |
| --- | --- |
| 自己的所有项目 | `~/.agents/skills/card-product-workflow/` |
| 仅当前项目 | `<项目根目录>/.agents/skills/card-product-workflow/` |

`~` 表示用户主目录；如果当前 Codex 环境配置了其他技能目录，以该环境实际识别的位置为准。保留 `references/`、`assets/`、`scripts/` 和 `agents/` 等随附目录，确保目标目录中直接包含 `SKILL.md`。

复制完成后，在下一条消息中调用 `$card-product-workflow`；如果未识别到，重启 Codex。已有同名技能时，先核对已有内容和来源，再决定是否替换。

## 可直接复用的材料

- [研究目标卡](skills/card-product-workflow/assets/templates/discovery-brief.md)
- [需求与角色矩阵](skills/card-product-workflow/assets/templates/requirements-and-roles.md)
- [验证证据矩阵](skills/card-product-workflow/assets/templates/evidence-matrix.md)
- [版本交付回执](skills/card-product-workflow/assets/templates/release-receipt.md)
- [三种身份手册大纲](skills/card-product-workflow/assets/templates/role-guide-outline.md)

## 本地检查

仅需 Python 标准库和 Git；skill 格式校验可使用创建 skill 时的验证工具。

```bash
python -m unittest discover -s tests -v
python skills/card-product-workflow/scripts/check_evidence.py examples/partial-evidence.json
python scripts/audit_public_package.py --root . --manifest publication-manifest.json --git-history
```

证据示例会返回“尚未具备真实发布条件”，这是刻意保留的演示结果。检查工具校验的是结构和证据范围，不替代实际测试，也不保证发现所有敏感内容。

本仓库的可展示成果是 **可执行的方法、状态模型、复盘与交付模板**；不以未核实的上线状态、用户量、收入或性能数字作为宣传。

## 内容归属

仅展示独立撰写的方法论与演示材料。未在这里发布原业务产品或授权其素材。仓库目前未额外指定开源许可，公开展示与产品源码开源是不同的事情，见 [内容说明](NOTICE.md)。
