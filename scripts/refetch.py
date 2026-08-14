#!/usr/bin/env python3
"""精准补抓：只对命中率低的店，要求标题必须含店名关键词才下载，替换 images_916/<key>。"""
import json, os, re, subprocess, sys
from PIL import Image

BASE = "/Users/shiduopili/WorkBuddy/2026-08-14-10-48-46/bangkok_cafe_xhs"
DATA = os.path.join(BASE, "scripts", "cafes_data.json")
RAW_DIR = os.path.join(BASE, "images_raw")
OUT_DIR = os.path.join(BASE, "images_916")
OPENCLI = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin/opencli"
NODE_BIN = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin"
TARGET_RATIO = 9 / 16
SUPPORTED = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif', '.heic')

# 需要补抓的店 + 标题必须含的词 + 额外城市限定（可选）
STRICT = {
    "kif":        {"must": ["kif"], "city": []},
    "cachecache": {"must": ["cache cache", "cachecache"], "city": []},
    "whitetulip": {"must": ["tulip", "white tulip"], "city": []},
    "shaloba":    {"must": ["shaloba"], "city": []},
    "tiramisu":   {"must": ["tiramisu"], "city": ["曼谷", "bangkok", "bkk", "泰国", "thai"]},
}

def run(cmd):
    env = dict(os.environ); env["PATH"] = NODE_BIN + ":" + env.get("PATH", "")
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout, p.stderr

def list_images(d):
    out = []
    for root, _, files in os.walk(d):
        for f in sorted(files):
            if f.lower().endswith(SUPPORTED):
                out.append(os.path.join(root, f))
    return out

def likes_of(n):
    try: return int(str(n.get("likes","0")).replace(",",""))
    except: return 0

def crop_to_916(im, max_edge=1600):
    w, h = im.size
    cur = w / h
    if cur > TARGET_RATIO:
        nw = int(h * TARGET_RATIO); x = (w-nw)//2; box=(x,0,x+nw,h)
    else:
        nh = int(w / TARGET_RATIO); y=(h-nh)//2; box=(0,y,w,y+nh)
    im = im.crop(box)
    if max(im.size) > max_edge:
        s = max_edge/max(im.size); im = im.resize((int(im.size[0]*s), int(im.size[1]*s)), Image.LANCZOS)
    return im

def main():
    data = json.load(open(DATA))
    by_key = {c["key"]: c for c in data}
    for key, rule in STRICT.items():
        cafe = by_key[key]
        print(f"\n===== 补抓 [{key}] {cafe['name']} =====")
        raw_cafe = os.path.join(RAW_DIR, key + "_strict")
        os.makedirs(raw_cafe, exist_ok=True)
        rc, out, err = run([OPENCLI, "xiaohongshu", "search", cafe["search"], "--limit", "20", "-f", "json"])
        notes = []
        if rc == 0 and out.strip():
            try: notes = json.loads(out)
            except Exception as e: print("  JSON err", e)
        # 过滤：标题必须含 must 之一，且（若设城市）含 city 之一
        matched = []
        for n in notes:
            t = n.get("title","").lower()
            if not any(m in t for m in rule["must"]):
                continue
            if rule["city"] and not any(c in t for c in rule["city"]):
                continue
            matched.append(n)
        matched.sort(key=likes_of, reverse=True)
        print(f"  命中 {len(matched)} 条: " + " | ".join(n.get("title","")[:22] for n in matched[:4]))
        if not matched:
            print("  ! 无严格命中，保留原图")
            continue
        got = 0
        for n in matched:
            if got >= 4: break
            rc, o, e = run([OPENCLI, "xiaohongshu", "download", n.get("url"), "--output", raw_cafe])
            if rc != 0:
                print(f"  download 失败: {e[:100]}"); continue
            got = len(list_images(raw_cafe))
            print(f"  + 「{n.get('title','')[:20]}」共 {got} 张")
        if got == 0:
            print("  ! 下载为空，保留原图"); continue
        # 重新裁并覆盖 images_916/<key>
        cafe_out = os.path.join(OUT_DIR, key)
        for f in os.listdir(cafe_out):
            try: os.remove(os.path.join(cafe_out, f))
            except: pass
        n = 0
        for p in list_images(raw_cafe):
            try:
                im = Image.open(p).convert("RGB"); im = crop_to_916(im)
                if im is None: continue
                base = os.path.splitext(os.path.basename(p))[0]
                dst = os.path.join(cafe_out, f"{base}.jpg"); i=1
                while os.path.exists(dst): dst = os.path.join(cafe_out, f"{base}_{i}.jpg"); i+=1
                im.save(dst, "JPEG", quality=88); n+=1
            except Exception as ex: print("  跳过", p, ex)
        print(f"  ✓ 重裁 {n} 张 -> {cafe_out}")
    print("\n补抓完成")

if __name__ == "__main__":
    main()
