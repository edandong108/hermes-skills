#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_kb.py v2 — 通用「图文PDF → agent图文知识库」流水线(不绑任何具体手册)

核心思想: 任意操作手册PDF → 抽产品截图 → 免费视觉模型写图说 → 生成可整读的图文md
布局约定(单一本体,无双副本):
  <KB_ROOT>\<doc-id>\            一个文档一个目录(doc-id 必须纯ASCII)
      <doc-id>.md                图文知识库(全文+图说+图片引用,头部带源PDF指纹)
      images/pXX_xNN.png         产品截图
      captions.jsonl             图说缓存(重跑不重复调API)
      meta.json                  源PDF路径/显示名(供 --rebuild-md 免传PDF)
  <KB_ROOT> 整体即图片服务根: URL = http://127.0.0.1:8377/<doc-id>/images/pXX_xNN.png

典型用法:
  新手册入库: python build_kb.py "D:\新手册.pdf" --doc-id new-system --name 新系统操作手册
  手册改版:   python build_kb.py "D:\新手册v2.pdf" --doc-id new-system      (增量,新图才调API)
  免API重组:  python build_kb.py --doc-id new-system --rebuild-md
  图说预扫:   python build_kb.py --doc-id new-system --check
  健康自检:   python build_kb.py --doctor          (服务+视觉通道+逐文档资产清点)

注意: 图说模型走智谱【通用端点】glm-4v-flash(免费);coding 套餐端点拒收图片(错误1210)。
"""
import argparse, base64, hashlib, json, os, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.error
import pymupdf

KB_ROOT    = r"C:\code\kb"
CAPTIONS   = "captions.jsonl"
META       = "meta.json"
GEN_EP     = "https://open.bigmodel.cn/api/paas/v4"   # 默认智谱;换厂商用 --vlm-endpoint
VLM_MODEL  = "glm-4v-flash"                      # 免费视觉模型;换厂商用 --vlm-model(须支持图片)
ENV_FALLBACK = None  # 不内置任何机器路径;用环境变量 VLM_API_KEY/GLM_API_KEY 或 --env-file 指定
PORT       = 8377
MIN_W, MIN_H, MAX_SIDE = 250, 150, 1800          # 过滤小图标 / caption 压边
SUSPICIOUS = ["无法确定", "无法辨认", "看不清", "不清楚", "可能是", "疑似"]

def load_key(env_file=None):
    k = os.environ.get("VLM_API_KEY") or os.environ.get("GLM_API_KEY")
    if k: return k
    path = env_file or ENV_FALLBACK
    if not path:
        print("[x] 缺 API key:设环境变量 VLM_API_KEY(或 GLM_API_KEY),或 --env-file 指向含它的 .env")
        return None
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and (line.startswith("VLM_API_KEY=") or line.startswith("GLM_API_KEY=")):
                return line.split("=", 1)[1]
    except FileNotFoundError:
        pass
    print(f"[x] 缺 API key:{path} 里没有 VLM_API_KEY/GLM_API_KEY")
    return None

def doc_dir(kb_root, doc_id):
    if not doc_id or not doc_id.isascii():
        sys.exit("[x] --doc-id 必须是纯 ASCII(它同时是目录名和URL段)")
    return os.path.join(kb_root, doc_id)

def pdf_fingerprint(path):
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    st = os.stat(path)
    return h[:16], st.st_size, datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")

def extract_images(doc, img_dir):
    os.makedirs(img_dir, exist_ok=True)
    kept, seen = [], set()
    for pno in range(doc.page_count):
        for img in doc[pno].get_images(full=True):
            xref = img[0]
            if xref in seen: continue
            seen.add(xref)
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n - pix.alpha > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                if pix.width < MIN_W or pix.height < MIN_H: continue
                fn = f"p{pno+1:02d}_x{xref}.png"
                pix.save(os.path.join(img_dir, fn))
                kept.append((fn, pno + 1))
            except Exception:
                pass
    return kept

def load_cache(d):
    cache = {}
    cp = os.path.join(d, CAPTIONS)
    if os.path.exists(cp):
        for line in open(cp, encoding="utf-8"):
            try:
                r = json.loads(line); cache[r["file"]] = r
            except Exception: pass
    return cache

def caption_one(fn, pno, page_ctx, doc_name, img_dir, key, endpoint, model):
    pix = pymupdf.Pixmap(os.path.join(img_dir, fn))
    if pix.n - pix.alpha > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    side = max(pix.width, pix.height)
    if side > MAX_SIDE:
        r = MAX_SIDE / side
        pix = pymupdf.Pixmap(pix, int(pix.width*r), int(pix.height*r))
    b64 = base64.b64encode(pix.tobytes("png")).decode()
    ctx = page_ctx.replace("\n", " ")[:500]
    prompt = (f"这是《{doc_name}》第{pno}页的插图。该页正文片段:「{ctx}」。"
              "请用3-6句话说明这张图:若是产品界面截图,说明在哪个菜单/页面、界面上的关键字段按钮选项、"
              "用户这步做什么;若是流程图,按顺序列出关键节点;若是表格,概括表头和用途。不要复述正文。")
    payload = {"model": model, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": prompt}]}], "max_tokens": 400, "temperature": 0.2}
    for attempt in range(3):
        req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions",
            json.dumps(payload).encode(),
            {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                out = json.loads(r.read())
                return {"file": fn, "page": pno,
                        "caption": out["choices"][0]["message"]["content"].strip()}
        except Exception as e:
            if attempt == 2:
                return {"file": fn, "page": pno, "caption": "", "error": str(e)[:120]}
            time.sleep(2 + attempt * 3)

def build_md(d, doc_id, doc_name, pdf_path, doc, cache, kept):
    fp, size, mtime = pdf_fingerprint(pdf_path)
    by_page = {}
    for fn, pno in kept:
        c = cache.get(fn, {}).get("caption", "")
        if c: by_page.setdefault(pno, []).append((fn, c))
    parts = [f"# {doc_name}(图文知识库版)",
        f"> doc-id:{doc_id} | 源文件:{os.path.basename(pdf_path)} | sha256:{fp} | 大小:{size//1024}KB | "
        f"源文件修改日:{mtime} | 抽取日期:{datetime.date.today()} | "
        f"图说模型:{VLM_MODEL}(免费) | 图:{len(kept)}张",
        f"> **图片说明由视觉模型生成,检索时先读说明定位,再展示原图给用户。"
        f"图片URL前缀: http://127.0.0.1:{PORT}/{doc_id}/images/ 。手册改版后重跑 build_kb.py 刷新。**\n"]
    for p in range(doc.page_count):
        pno = p + 1
        parts.append(f"\n<!-- page:{pno} -->\n")
        parts.append(doc[p].get_text("text").strip())
        for fn, c in by_page.get(pno, []):
            parts.append(f"\n**【图示 {fn}】**(视觉模型说明):{c}\n")
            parts.append(f"![]({('images/' + fn)})")
    out = os.path.join(d, f"{doc_id}.md")
    open(out, "w", encoding="utf-8").write("\n".join(parts))
    return out, len(kept)

def check(d):
    cp = os.path.join(d, CAPTIONS)
    if not os.path.exists(cp):
        sys.exit(f"[x] 无 {cp}")
    rows = [json.loads(l) for l in open(cp, encoding="utf-8") if l.strip()]
    bad = []
    for r in rows:
        c = r.get("caption", "")
        flags = []
        if r.get("error") or not c: flags.append("空/报错")
        if len(c) < 60: flags.append("过短")
        hits = [w for w in SUSPICIOUS if w in c]
        if hits: flags.append("措辞:" + ",".join(hits))
        if flags: bad.append((r["file"], r["page"], flags, c[:60]))
    print(f"[check] 共 {len(rows)} 条图说,预警 {len(bad)} 条(人工抽检优先看):")
    for fn, pno, flags, prev in bad:
        print(f"  {fn} (第{pno}页) [{';'.join(flags)}] {prev}...")

def doctor(kb_root, env_file):
    ok = True
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=3) as r:
            print(f"[OK] 图片服务 127.0.0.1:{PORT} 探活 {r.status}(根:{kb_root})")
    except Exception as e:
        ok = False
        print(f"[DOWN] 图片服务 127.0.0.1:{PORT} 不通({type(e).__name__})——图片展示退化为 MEDIA 路径卡片")
    key = load_key(env_file)
    if not key:
        ok = False
    else:
        try:
            payload = {"model": VLM_MODEL, "messages": [{"role": "user", "content": "回复OK"}], "max_tokens": 5}
            req = urllib.request.Request(GEN_EP + "/chat/completions", json.dumps(payload).encode(),
                                         {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                print("[OK] GLM_API_KEY 有效,", VLM_MODEL, "通用端点可用")
        except Exception as e:
            ok = False
            print(f"[DOWN] GLM 视觉通道异常: {str(e)[:120]}")
    n_docs = 0
    if os.path.isdir(kb_root):
        for sub in sorted(os.listdir(kb_root)):
            d = os.path.join(kb_root, sub)
            if not os.path.isdir(d) or sub.startswith(("_", ".")): continue
            n_img = len([f for f in os.listdir(os.path.join(d, "images")) if f.endswith(".png")]) if os.path.isdir(os.path.join(d, "images")) else 0
            caps = load_cache(d)
            n_cap = len([c for c in caps.values() if c.get("caption")])
            md_ok = os.path.exists(os.path.join(d, f"{sub}.md"))
            print(f"[{'OK' if md_ok and n_img else 'MISS'}] 文档 {sub}: {n_img} 图/{n_cap} 图说/md{'在' if md_ok else '缺'}")
            if not md_ok or n_img == 0: ok = False
            n_docs += 1
    if n_docs == 0:
        print(f"[MISS] {kb_root} 下还没有文档;新手册入库: python build_kb.py <pdf> --doc-id <ascii-id> --name <显示名>")
        ok = False
    print("[doctor] 结论:", "全部健康" if ok else "存在故障项,见上")
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(description="通用图文PDF知识库流水线")
    ap.add_argument("pdf", nargs="?", help="源手册 PDF 路径(新入库/改版必填)")
    ap.add_argument("--doc-id", help="文档ASCII标识=目录名=URL段(必填,除非 --doctor)")
    ap.add_argument("--name", help="显示名(默认取PDF文件名)")
    ap.add_argument("--kb-root", default=KB_ROOT, help=f"知识库根目录(默认 {KB_ROOT},即图片服务根)")
    ap.add_argument("--rebuild-md", action="store_true", help="只重组 md,不调 API(PDF路径读 meta.json)")
    ap.add_argument("--check", action="store_true", help="图说质量预扫")
    ap.add_argument("--doctor", action="store_true", help="整套资产健康自检")
    ap.add_argument("--env-file", default=None, help="API key 所在 .env(含 VLM_API_KEY 或 GLM_API_KEY=...)")
    ap.add_argument("--vlm-endpoint", default=GEN_EP, help=f"OpenAI 兼容视觉端点(默认智谱 {GEN_EP})")
    ap.add_argument("--vlm-model", default=VLM_MODEL, help=f"视觉模型名,须支持图片输入(默认 {VLM_MODEL};如 qwen-vl-plus/deepseek-vl 等)")
    args = ap.parse_args()

    if args.doctor: return doctor(args.kb_root, args.env_file)
    if not args.doc_id: ap.error("需要 --doc-id(ASCII,作目录名和URL段)")
    d = doc_dir(args.kb_root, args.doc_id)
    meta_path = os.path.join(d, META)
    meta = {}
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))

    if args.check: return check(d)

    if args.pdf:
        pdf = args.pdf
    elif args.rebuild_md and meta.get("pdf"):
        pdf = meta["pdf"]
    else:
        ap.error("请给源 PDF 路径(或该文档已有 meta.json 后用 --rebuild-md)")
    doc_name = args.name or meta.get("name") or os.path.splitext(os.path.basename(pdf))[0]

    doc = pymupdf.open(pdf)
    kept = extract_images(doc, os.path.join(d, "images"))
    cache = load_cache(d)
    todo = [(fn, pno) for fn, pno in kept if fn not in cache or not cache[fn].get("caption")]
    print(f"[1/3] {args.doc_id} 图片就绪 {len(kept)} 张,待补图说 {len(todo)} 张(缓存 {len(cache)})")

    if todo and not args.rebuild_md:
        key = load_key(args.env_file)
        if not key: return 1
        page_text = {p+1: doc[p].get_text("text").strip() for p in range(doc.page_count)}
        with ThreadPoolExecutor(max_workers=4) as ex:
            for res in ex.map(lambda t: caption_one(t[0], t[1], page_text.get(t[1], ""), doc_name,
                                                    os.path.join(d, "images"), key, args.vlm_endpoint, args.vlm_model), todo):
                cache[res["file"]] = res
                with open(os.path.join(d, CAPTIONS), "a", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")
        ok = sum(1 for r in todo if cache[r[0]].get("caption"))
        print(f"[2/3] 图说完成 {ok}/{len(todo)}")

    json.dump({"pdf": os.path.abspath(pdf), "name": doc_name},
              open(meta_path, "w", encoding="utf-8"), ensure_ascii=False)
    out, n = build_md(d, args.doc_id, doc_name, pdf, doc, cache, kept)
    print(f"[3/3] 已写入 {out} ({n} 张图;图片URL前缀 http://127.0.0.1:{PORT}/{args.doc_id}/images/)")

if __name__ == "__main__":
    sys.exit(main())
