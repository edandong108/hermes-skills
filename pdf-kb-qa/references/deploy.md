# 换机部署(把本技能+知识库交给别人)

原则:**方法论是资产,配置是每个人自己的**——交付前确认正文无对方机器不存在的绝对路径(占位符 <KB_ROOT>/<doc-id> 除外,配置节集中改)。

## 交付物
1. `<KB_ROOT>` 整目录:build_kb.py + 各 <doc-id>/ 子目录(图文 md / images/ / captions.jsonl 图说缓存 / meta.json)
2. 本 skill 目录(data-engineering/pdf-kb-qa,含 references/deploy.md)

## 步骤
1. 复制 <KB_ROOT> 到对方机器(路径必须纯 ASCII,服务根=知识库根)
2. 装 Python 3.10+,`pip install pymupdf`
3. 配置 API key:环境变量 `VLM_API_KEY`(或旧 `GLM_API_KEY`),或验收时 `python build_kb.py --doctor --env-file <对方.env>`。默认智谱通用端点+glm-4v-flash(免费);换任意 OpenAI 兼容厂商加 `--vlm-endpoint`/`--vlm-model`(模型必须支持图片输入——key 对但端点拒图,就是当初 coding 套餐报 1210 的教训)
4. 写 kbserve.vbs 放入 `shell:startup`(Win+R 输 shell:startup)。模板=本机 `C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\kbserve.vbs`,改两处:python 绝对路径(对方任意存在的 python.exe)、--directory <KB_ROOT>。自带 8377 端口探测防重复
5. 双击 vbs 一次立即拉起(不等重启),然后跑下方验收

## 对方没现成知识库时
`python build_kb.py "对方手册.pdf" --doc-id <ascii-id> --name 显示名` 从零建第一本文档库;后续新手册同样一条命令入库。

## 验收(必跑,全绿才算交付)
- [ ] `python build_kb.py --doctor` → 全部健康(逐文档清点:服务探活200/GLM视觉通道/图+图说+md)
- [ ] 在对方**实际使用的聊天窗**问一个操作问题,按通路矩阵选路后图能显示
- [ ] 重启机器后 `--doctor` 仍全部健康(自启生效)

## 对方聊天窗类型 → 通路选择
- Hermes 桌面窗 → MEDIA: ASCII 路径卡片(内联渲染)
- 本机网页/群窗 → markdown 引 8377 URL(带 doc-id 段)
- 跨设备(手机看群) → MEDIA: 卡片 + 文字路径(127.0.0.1 跨设备无效,这是边界不是 bug)
- 不确定对方窗型 → 先发 8377 URL 再发卡片,让用户回一句哪个能看到

## 常见部署故障
| 现象 | 根因 | 处置 |
|---|---|---|
| 群窗图挂了显示裂图 | 8377 没跑(重启后 vbs 未生效/python路径错) | `--doctor` 定位→看 vbs 两处路径→手动拉起 |
| URL 404 | 旧布局无 doc-id 段,或 doc-id 拼错 | 核对 `http://127.0.0.1:8377/<doc-id>/images/xx.png` |
| vbs 双击无反应 | python 路径不存在,脚本静默退出 | 核对 vbs 内 py 变量 |
| 图说生成报 1210 | 模型/端点不支持图片输入(如 coding 套餐端点) | 默认走智谱通用端点 glm-4v-flash;换厂商确认视觉模型+--vlm-endpoint |
| 手机上看不了 127.0.0.1 图 | loopback 只对本机有效 | 改发 MEDIA: 卡片+文字路径 |
| --doctor 报 key 无效 | --env-file 未指向含 VLM_API_KEY/GLM_API_KEY 的 .env | 确认环境变量或 --env-file 路径 |
