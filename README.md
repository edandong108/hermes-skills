# Hermes Skills 集合

个人沉淀的可复用 Agent 技能（SKILL.md），用于把方法论固化成 AI 可执行的流程。

## 技能列表

### 1. `project-xray` — 企业级项目改造方法论

接手/改造陌生企业级项目的「先透视、后动手」流程，四个阶段：

| 阶段 | 内容 |
|------|------|
| 第一阶段 | 画三张图：架构图（系统级）、模块图（代码级）、依赖图（生态级） |
| 第二阶段 | 梳理 REST 接口清单 + 数据模型（含卡片式 ER 图） |
| 第三阶段 | 梳理代码风格 / 规范 / 约束（存量约定优先） |
| 第四阶段 | 测试摸底：摸核心链路，把「覆盖率目标」反转成「关键路径兜底目标」 |

核心思想来源：Michael Feathers《Working Effectively with Legacy Code》的存量约定优先原则、AGENTS.md/CLAUDE.md 规则文件形态、静态分析可执行配置。

### 2. `test_creator` — 测试用例生成专家

从需求文档（PRD/原型/流程图/接口文档）生成企业级测试用例与自动化脚本。

- 覆盖：功能/接口/权限/性能/安全(OWASP)/兼容性/易用性/移动端/AI算法/数据迁移/灰度发布
- 自动化脚本：Pytest / Selenium / Playwright / Cypress / Postman / Appium
- 三重质量护栏：需求载荷检查（没需求不脑补）→ PRD 质量审查（blocking/warning/info 分级）→ 缺失不编造（标 `[待确认]`）
- 核心链路识别：P0/P1 聚焦核心业务链路，边角功能降级，避免几百条平铺

### 3. `pdf-kb-qa` — 图文 PDF 知识库问答

把图文型 PDF（操作手册/用户指南）构建成 agent 可问答的图文知识库：pymupdf 抽截图 → 免费视觉模型（glm-4v-flash 通用端点）写图说 → 图文交错 md（小到可整读，不用向量库）→ 本机图片服务按聊天窗类型出图。

- 多文档并存：`--doc-id` 一条命令入库新手册（驾驶舱填报、客户系统手册均可）
- 运维闭环：`--doctor` 健康自检 / `--check` 可疑图说预扫 / `--rebuild-md` 零成本重组 / captions 缓存不重复调 API
- 换机部署：`references/deploy.md` 五步+验收；`assets/kbserve.vbs` 自启模板

## 安装使用

### Hermes Agent

把技能文件夹放到 skills 目录：

```bash
# project-xray
cp -r project-xray ~/AppData/Local/hermes/skills/software-development/

# test_creator
cp -r test_creator ~/AppData/Local/hermes/skills/software-development/
```

### 其他 Agent（Cursor / Claude Code / 通用）

直接引用对应文件夹下的 `SKILL.md`，或将内容作为项目规则文件（CLAUDE.md / .cursorrules）使用。

## 目录结构

```
hermes-skills/
├── project-xray/
│   └── SKILL.md          # 企业级项目改造方法论
├── test_creator/
│   └── SKILL.md          # 测试用例生成专家
└── README.md
```

## 迭代记录

- `project-xray` 目前 v0.5.0：四阶段已成形，第四阶段 Step 2-4 待补全。
- `test_creator` 由 test-case-generator 演化而来，吸收了两个源头的方法论精华。

## 许可

MIT License
