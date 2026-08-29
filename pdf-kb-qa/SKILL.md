---
name: pdf-kb-qa
description: "Use when 问操作手册/图文PDF知识库问答(结合图示解答)或新手册入库/改版刷新"
version: 0.4.0
author: shujujiaohuan
license: MIT
---

# 图文 PDF 知识库问答(通用)

## Overview
把图文型 PDF(操作手册/用户指南)构建成可问答知识库:全文+截图视觉图说交错,agent 回答操作问题时**结合产品图示**。多文档并存,知识库小可整读,不用向量库。核心链路:pymupdf 抽截图 → glm-4v-flash(免费,通用端点)写图说 → 图文交错 md → 本机图片服务出图。

## 阶段路由
| 用户要做 | 执行路径 |
|---|---|
| 问手册操作问题(在哪/怎么操作) | 问答流程节 |
| 丢一份新 PDF 入库 | 新手册入库流程节 |
| 手册改版要刷新 | scripts 命令(增量,缓存不重复花钱) |
| 症状排查(图不显示/404/key报错) | 常见坑+references/deploy.md 故障表 |
| 交给别人/换机 | references/deploy.md 五步+验收 |

## 快速开始
```bash
pip install pymupdf                      # 唯一依赖
export VLM_API_KEY=xxx                   # 任意 OpenAI 兼容视觉模型 key(默认智谱免费 glm-4v-flash)
python scripts/build_kb.py "手册.pdf" --doc-id my-doc --name 显示名   # 入库
python scripts/build_kb.py --doctor      # 健康自检(服务/key/逐文档资产)
# 换厂商: --vlm-endpoint https://dashscope.aliyuncs.com/compatible-mode/v1 --vlm-model qwen-vl-plus
```

## 新手册入库流程
1. 选 doc-id:纯 ASCII、稳定可作 URL 段(如 cockpit-fill)
2. 一条命令入库(上例);产物 `<KB_ROOT>/<doc-id>/{<doc-id>.md, images/, captions.jsonl, meta.json}`
3. 验收:`--doctor` 全绿 + `--check` 预扫 → **人工优先抽检预警图**(图说错=知识库级污染)
4. 在目标聊天窗按通路矩阵发一张图实测

## 问答流程
1. 按问题域选 doc-id → 整读 `<KB_ROOT>/<doc-id>/<doc-id>.md`(小,可整读)
2. 定位:正文命中页码(页号在 `<!-- page:N -->` 注释锚点)→ 该页【图示】图说确认界面匹配
3. 按通路矩阵展示原图
4. 回答结构:结论先行 + 入口菜单路径 + 界面要素(对照图) + 手册页码引用 + 正文提到的坑

## 通路矩阵(本机聊天窗实测定版)
| 场景 | 通路 |
|---|---|
| Hermes 桌面窗 | `MEDIA:<KB_ROOT>/<doc-id>/images/pXX_xNN.png`(内联渲染) |
| 本机群窗(网页类) | `![图说](http://127.0.0.1:8377/<doc-id>/images/pXX_xNN.png)` |
| 跨设备(手机看群) | MEDIA 卡片 + 文字路径(127.0.0.1 跨设备无效,边界非 bug) |
| 服务疑似挂 | 探活该 URL;非 200 则 `python -m http.server 8377 --bind 127.0.0.1 --directory <KB_ROOT>` |

## 运行态约定(每台机器自己的,不进仓)
- `<KB_ROOT>`(默认 `C:\code\kb`,可 `--kb-root` 改):既是知识库根也是图片服务根,必须纯 ASCII
- kbserve.vbs 开机自启:模板在 `assets/kbserve.vbs`,改两处(python 绝对路径、--directory)后放 `shell:startup`
- API key:环境变量 `VLM_API_KEY`(或旧 `GLM_API_KEY`)或 `--env-file <你的.env>`;默认智谱通用端点+glm-4v-flash(coding 套餐端点拒收图片,错误1210);换厂商 `--vlm-endpoint`/`--vlm-model`(模型须支持图片输入)

## 常见坑
1. 群聊窗把 `::preview{...}` 当纯文本转义——群窗禁用该指令,走 8377 URL。
2. 中文路径的 MEDIA: 卡片可能不展开——展示一律用 ASCII 路径。
3. coding 套餐端点拒收图片(错误1210)——识图一律走通用端点 glm-4v-flash。
4. URL 必须带 doc-id 段(无 doc-id 的旧布局 404)。
5. 改脚本先改本仓再拷出部署,别两头各改各的;本机部署副本里的个人 key 回退属于配置边界,不算漂移。

## 迭代记录
- 0.4.0 多厂商:--vlm-endpoint/--vlm-model 切换任意 OpenAI 兼容视觉端点(阿里 qwen-vl-plus 等);key 放宽为 VLM_API_KEY(兼容 GLM_API_KEY);硬要求=模型支持图片输入。
- 0.3.0 流水线 v2:多文档并存+meta.json,URL 带 doc-id 段;由 picc-manual-qa 泛化更名;发布版清洗(脚本去机器路径,vbs 模板入 assets)。
- 0.2.0 --doctor/--env-file;md 页标改 `<!-- page:N -->` 注释锚点。
- 0.1.0 初版 picc-manual-qa,单手册,通路矩阵实测定版。
