#!/usr/bin/env python3
"""为 cafes_data.json 中 sample != true 的 32 家店抓取实拍图。
优先 Instagram（若已登录），否则回退小红书；下载后中心裁剪 9:16 -> 1080x1920 q80。
输出 html_assets/<key>/01.jpg,02.jpg,03.jpg 与 scripts/ig_fetch_manifest.json
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image

BASE = "/Users/shiduopili/WorkBuddy/2026-08-14-10-48-46/bangkok_cafe_xhs"
DATA = os.path.join(BASE, "scripts", "cafes_data.json")
ASSETS = os.path.join(BASE, "html_assets")
RAW = os.path.join(BASE, "images_raw32")
MANIFEST = os.path.join(BASE, "scripts", "ig_fetch_manifest.json")
LOG = "/tmp/ig_fetch.log"
OPENCLI = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin/opencli"
NODE_BIN = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin"

TARGET_W, TARGET_H = 1080, 1920
TARGET_RATIO = 9 / 16
SUPPORTED = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif')
FLAGSHIP = {"kif", "cachecache", "lacabra", "whitetulip", "tiramisu", "tobys", "shaloba", "arteasia"}
GENERIC = {"cafe", "coffee", "the", "and", "bkk", "bangkok", "bistro", "house", "dessert",
           "studio", "parlour", "parlor", "roasters", "brew", "bean", "tea", "friends"}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run(cmd, timeout=200):
    env = dict(os.environ)
    env["PATH"] = NODE_BIN + ":" + env.get("PATH", "")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return -9, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def sanitize(q):
    """去掉会让搜索接口返回空的特殊字符。"""
    q = q.replace("%", " ").replace("&", " ").replace("/", " ")
    q = re.sub(r"[（）()【】\[\]'\"]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def latin_name(name):
    """取名字里的拉丁主干（第一个 / 之前）。"""
    head = re.split(r"[/（(]", name)[0]
    head = re.sub(r"[^A-Za-z0-9'’.\s-]+", " ", head)
    return re.sub(r"\s+", " ", head).strip()


def cjk_name(name):
    m = re.findall(r"[\u4e00-\u9fff]{2,}", name)
    return m[0] if m else ""


def queries_for(cafe):
    """按优先级生成候选搜索词。"""
    out = []
    base = sanitize(cafe.get("search") or "")
    if base:
        out.append(base)
    lat = latin_name(cafe["name"])
    if lat:
        out.append(sanitize(f"曼谷 {lat}"))
        out.append(sanitize(f"{lat} 曼谷 咖啡"))
    cjk = cjk_name(cafe["name"])
    if cjk:
        out.append(sanitize(f"曼谷 {cjk} 咖啡"))
    # 去重保序
    seen, res = set(), []
    for q in out:
        if q and q not in seen:
            seen.add(q)
            res.append(q)
    return res


def tokens_for(cafe):
    toks = set()
    lat = latin_name(cafe["name"]).lower()
    for w in re.findall(r"[a-z0-9]{3,}", lat):
        if w not in GENERIC:
            toks.add(w)
    k = cafe["key"].lower()
    if k not in GENERIC:
        toks.add(k)
    cjk = cjk_name(cafe["name"])
    if cjk:
        toks.add(cjk)
    return toks


def score_note(note, toks):
    text = (note.get("title") or "").lower()
    s = 0.0
    hit = False
    for t in toks:
        if t and t in text:
            s += 4
            hit = True
    if "曼谷" in text or "bangkok" in text:
        s += 1.5
    if any(w in text for w in ("咖啡", "cafe", "café", "探店", "甜品", "抹茶", "brunch", "早午餐")):
        s += 0.8
    try:
        likes = int(str(note.get("likes", "0")).replace(",", "").replace("万", "0000"))
    except Exception:
        likes = 0
    s += min(likes / 800.0, 3.0)
    note["_hit"] = hit
    return s


def list_images(d):
    out = []
    for root, _, files in os.walk(d):
        for f in sorted(files):
            if f.lower().endswith(SUPPORTED):
                out.append(os.path.join(root, f))
    return out


def good_image(path):
    try:
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        return None
    if w < 500 and h < 500:
        return None
    if min(w, h) < 360:
        return None
    ar = w / h
    if ar > 2.6 or ar < 0.38:
        return None
    return (w, h)


def img_rank(path, size):
    """竖图优先，其次面积大的优先。"""
    w, h = size
    portrait = 0 if h >= w else 1
    return (portrait, -(w * h))


def crop_916(src, dst):
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        cur = w / h
        if cur > TARGET_RATIO:
            nw = int(round(h * TARGET_RATIO))
            x = (w - nw) // 2
            im = im.crop((x, 0, x + nw, h))
        else:
            nh = int(round(w / TARGET_RATIO))
            y = (h - nh) // 2
            im = im.crop((0, y, w, y + nh))
        im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        im.save(dst, "JPEG", quality=80, optimize=True)


def file_hash(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def ig_available():
    rc, out, err = run([OPENCLI, "instagram", "whoami", "-f", "json"], timeout=60)
    blob = (out or "") + (err or "")
    return '"ok": true' in blob or "ok: true" in blob


def xhs_search(q, limit=10):
    rc, out, err = run([OPENCLI, "xiaohongshu", "search", q, "--limit", str(limit), "-f", "json"], timeout=180)
    if rc != 0:
        return []
    txt = (out or "").strip()
    i = txt.find("[")
    if i < 0:
        return []
    try:
        data = json.loads(txt[i:])
        return data if isinstance(data, list) else []
    except Exception:
        return []


def fetch_cafe(cafe, use_ig):
    key = cafe["key"]
    name = cafe["name"]
    out_dir = os.path.join(ASSETS, key)
    raw_dir = os.path.join(RAW, key)
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    notes = []
    used_q = ""
    for q in queries_for(cafe):
        got = xhs_search(q, limit=10)
        log(f"    搜索「{q}」-> {len(got)} 条")
        if got:
            toks = tokens_for(cafe)
            for n in got:
                n["_score"] = score_note(n, toks)
            got.sort(key=lambda n: n.get("_score", 0), reverse=True)
            notes = got
            used_q = q
            # 有命中店名的笔记就够了，否则再试下一个词
            if any(n.get("_hit") for n in got[:5]):
                break
        time.sleep(1)

    if not notes:
        return {"name": name, "source": "none", "count": 0, "note": "搜索无结果"}

    hit_any = any(n.get("_hit") for n in notes[:5])
    top = " | ".join(f"{(n.get('title') or '')[:16]}({n.get('_score',0):.1f})" for n in notes[:3])
    log(f"    采用「{used_q}」 精确命中={hit_any} top: {top}")

    # 依次下载笔记，直到攒够候选图
    ordered = []
    seen_hash = set()
    for idx, n in enumerate(notes[:6], 1):
        url = n.get("url")
        if not url:
            continue
        sub = os.path.join(raw_dir, f"n{idx:02d}")
        os.makedirs(sub, exist_ok=True)
        rc, out, err = run([OPENCLI, "xiaohongshu", "download", url, "--output", sub], timeout=240)
        imgs = list_images(sub)
        if rc != 0 and not imgs:
            log(f"    笔记{idx} 下载失败: {(err or out)[:100]}")
            continue
        cand = []
        for p in imgs:
            size = good_image(p)
            if not size:
                continue
            try:
                hh = file_hash(p)
            except Exception:
                continue
            if hh in seen_hash:
                continue
            seen_hash.add(hh)
            cand.append((img_rank(p, size), p))
        cand.sort(key=lambda t: t[0])
        ordered.extend([p for _, p in cand])
        log(f"    笔记{idx}「{(n.get('title') or '')[:18]}」可用 {len(cand)} 张 (累计 {len(ordered)})")
        if len(ordered) >= 3:
            break
        time.sleep(1)

    if not ordered:
        return {"name": name, "source": "none", "count": 0, "note": "笔记无可用图片"}

    picked = ordered[:3]
    cnt = 0
    for i, p in enumerate(picked, 1):
        dst = os.path.join(out_dir, f"{i:02d}.jpg")
        try:
            crop_916(p, dst)
            cnt += 1
        except Exception as e:
            log(f"    裁剪失败 {os.path.basename(p)}: {e}")
    note = "" if hit_any else "宽松匹配(标题未含店名)"
    if cnt < 3:
        note = (note + f" 仅{cnt}张").strip()
    return {"name": name, "source": "xhs", "count": cnt, "note": note, "query": used_q}


def main():
    only = sys.argv[1:] or None
    data = json.load(open(DATA))
    todo = [c for c in data if not c.get("sample") and c["key"] not in FLAGSHIP]
    if only:
        todo = [c for c in todo if c["key"] in only]
    os.makedirs(RAW, exist_ok=True)

    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            manifest = json.load(open(MANIFEST))
        except Exception:
            manifest = {}

    use_ig = ig_available()
    log(f"===== 开始：{len(todo)} 家店，Instagram可用={use_ig}（不可用则全部走小红书）=====")

    for i, cafe in enumerate(todo, 1):
        key = cafe["key"]
        first = os.path.join(ASSETS, key, "01.jpg")
        if os.path.exists(first) and os.path.getsize(first) > 10000:
            log(f"[{i}/{len(todo)}] {key} 已有图片，跳过")
            manifest.setdefault(key, {"name": cafe["name"], "source": "existing",
                                      "count": len([f for f in os.listdir(os.path.join(ASSETS, key))
                                                    if f.endswith('.jpg')]), "note": "已存在"})
            continue
        log(f"[{i}/{len(todo)}] ===== {key} · {cafe['name']} =====")
        try:
            res = fetch_cafe(cafe, use_ig)
        except Exception as e:
            res = {"name": cafe["name"], "source": "none", "count": 0, "note": f"异常: {e}"}
        manifest[key] = res
        log(f"    -> {res['source']} {res['count']}张 {res.get('note','')}")
        json.dump(manifest, open(MANIFEST, "w"), ensure_ascii=False, indent=2)

    ok = sum(1 for v in manifest.values() if v.get("count", 0) >= 3)
    part = sum(1 for v in manifest.values() if 0 < v.get("count", 0) < 3)
    fail = [k for k, v in manifest.items() if v.get("count", 0) == 0]
    log(f"===== 完成：3张={ok} 部分={part} 失败={len(fail)} {fail} =====")


if __name__ == "__main__":
    main()
