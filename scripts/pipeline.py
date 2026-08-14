#!/usr/bin/env python3
"""小红书探店实拍图管线：search -> download -> crop 9:16 -> 清单。
只处理 cafes_data.json 中 sample=true 的 8 家店。
"""
import json, os, re, subprocess, sys, time
from PIL import Image

BASE = "/Users/shiduopili/WorkBuddy/2026-08-14-10-48-46/bangkok_cafe_xhs"
DATA = os.path.join(BASE, "scripts", "cafes_data.json")
RAW_DIR = os.path.join(BASE, "images_raw")
OUT_DIR = os.path.join(BASE, "images_916")
OPENCLI = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin/opencli"
NODE_BIN = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin"
TARGET_RATIO = 9 / 16
SUPPORTED = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif', '.heic')

def run(cmd):
    env = dict(os.environ)
    env["PATH"] = NODE_BIN + ":" + env.get("PATH", "")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout, p.stderr

def normalize(s):
    s = s.lower().strip()
    s = re.sub(r'[\s\-_/&]+', '', s)
    return s

def match_tokens(cafe):
    toks = set()
    toks.add(cafe["key"].lower())
    name = cafe["name"]
    toks.add(normalize(name))
    # 名字里去掉修饰词的主要词（取 >=3 字母词）
    for w in re.findall(r'[A-Za-z]{3,}', name.lower()):
        toks.add(w)
    toks.discard('cafe'); toks.discard('coffee'); toks.discard('the')
    return toks

def score_note(note, toks):
    title = note.get("title", "").lower()
    s = 0
    for t in toks:
        if t and t in title:
            s += 3
    likes = 0
    try:
        likes = int(str(note.get("likes", "0")).replace(",", ""))
    except: pass
    s += min(likes / 1000.0, 3)
    return s

def list_images(d):
    out = []
    for root, _, files in os.walk(d):
        for f in sorted(files):
            if f.lower().endswith(SUPPORTED):
                out.append(os.path.join(root, f))
    return out

def crop_to_916(im, max_edge=1600):
    w, h = im.size
    if w <= 0 or h <= 0:
        return None
    cur = w / h
    if cur > TARGET_RATIO:
        new_w = int(h * TARGET_RATIO)
        x = (w - new_w) // 2
        box = (x, 0, x + new_w, h)
    else:
        new_h = int(w / TARGET_RATIO)
        y = (h - new_h) // 2
        box = (0, y, w, y + new_h)
    im = im.crop(box)
    if max(im.size) > max_edge:
        scale = max_edge / max(im.size)
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    return im

def count_imgs(d):
    return len(list_images(d))

def main():
    data = json.load(open(DATA))
    sample = [c for c in data if c.get("sample")]
    print(f"样张店数: {len(sample)}")
    manifest = {}
    for cafe in sample:
        key = cafe["key"]
        name = cafe["name"]
        print(f"\n===== [{key}] {name} =====")
        raw_cafe = os.path.join(RAW_DIR, key)
        os.makedirs(raw_cafe, exist_ok=True)
        # 1) search
        rc, out, err = run([OPENCLI, "xiaohongshu", "search", cafe["search"], "--limit", "8", "-f", "json"])
        notes = []
        if rc == 0 and out.strip():
            try:
                notes = json.loads(out)
            except Exception as e:
                print(f"  search JSON 解析失败: {e}")
        if not notes:
            print(f"  ! 未搜到笔记，跳过")
            manifest[key] = {"name": name, "images": []}
            continue
        toks = match_tokens(cafe)
        for n in notes:
            n["_score"] = score_note(n, toks)
        notes.sort(key=lambda n: n.get("_score", 0), reverse=True)
        print(f"  搜到 {len(notes)} 条，top3 标题: " + " | ".join(f'{n.get("title","")[:18]}({n["_score"]:.1f})' for n in notes[:3]))
        # 2) download 直到 >=3
        got = 0
        used = 0
        for n in notes:
            if got >= 3:
                break
            url = n.get("url")
            if not url:
                continue
            used += 1
            rc, out, err = run([OPENCLI, "xiaohongshu", "download", url, "--output", raw_cafe])
            if rc != 0:
                print(f"  download 失败({used}): {err[:120]}")
                continue
            got = count_imgs(raw_cafe)
            print(f"  + 笔记{used}「{n.get('title','')[:20]}」下载后共 {got} 张")
            if got >= 3:
                break
        # 3) crop 9:16
        cafe_out = os.path.join(OUT_DIR, key)
        os.makedirs(cafe_out, exist_ok=True)
        raws = list_images(raw_cafe)
        cropped = 0
        for p in raws:
            try:
                im = Image.open(p).convert("RGB")
                im = crop_to_916(im)
                if im is None:
                    continue
                base = os.path.splitext(os.path.basename(p))[0]
                dst = os.path.join(cafe_out, f"{base}.jpg")
                i = 1
                while os.path.exists(dst):
                    dst = os.path.join(cafe_out, f"{base}_{i}.jpg"); i += 1
                im.save(dst, "JPEG", quality=88)
                cropped += 1
            except Exception as e:
                print(f"  跳过 {p}: {e}")
        imgs = sorted(os.listdir(cafe_out))
        # 取前 3 张作为该店代表图
        rep = imgs[:3]
        print(f"  裁好 {cropped} 张，代表图 {len(rep)} 张 -> {cafe_out}")
        manifest[key] = {"name": name, "raw": got, "cropped": cropped, "images": rep}
    json.dump(manifest, open(os.path.join(BASE, "xhs_manifest.json"), "w"), ensure_ascii=False, indent=2)
    print("\n===== 完成，manifest 已写 =====")
    for k, v in manifest.items():
        print(f"  {k}: {v['cropped']}裁/{v['raw']}原 -> 代表{v['images']}")

if __name__ == "__main__":
    main()
