#!/usr/bin/env python3
"""最终修复 whitetulip / cachecache。whitetulip 用真店图+原始合集(非酒店);cachecache 再搜一次。"""
import json, os, subprocess
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
        nw = int(h * TARGET_RATIO); x=(w-nw)//2; box=(x,0,x+nw,h)
    else:
        nh = int(w / TARGET_RATIO); y=(h-nh)//2; box=(0,y,w,y+nh)
    im = im.crop(box)
    if max(im.size) > max_edge:
        s = max_edge/max(im.size); im = im.resize((int(im.size[0]*s), int(im.size[1]*s)), Image.LANCZOS)
    return im

def set_cafe(key, imgs, need=3):
    cafe_out = os.path.join(OUT_DIR, key)
    for f in os.listdir(cafe_out):
        try: os.remove(os.path.join(cafe_out, f))
        except: pass
    n = 0
    for im in imgs[:need]:
        if im is None: continue
        dst = os.path.join(cafe_out, f"img_{n+1}.jpg")
        im.save(dst, "JPEG", quality=88); n += 1
    return n

def main():
    data = json.load(open(DATA)); by_key = {c["key"]: c for c in data}

    # ---- whitetulip: 真店图(raw_strict) + 原始合集(raw 首轮) ----
    key = "whitetulip"
    real = [crop_to_916(Image.open(p).convert("RGB")) for p in list_images(os.path.join(RAW_DIR, key+"_strict"))]
    real = [x for x in real if x]
    supp_src = list_images(os.path.join(RAW_DIR, key))  # 首轮合集
    supp = []
    for p in supp_src:
        try: supp.append(crop_to_916(Image.open(p).convert("RGB")))
        except: pass
        if len(supp) >= 2: break
    imgs = real + supp
    n = set_cafe(key, imgs)
    print(f"whitetulip: 真店{len(real)} + 合集{len(supp)} -> 写入 {n} 张")

    # ---- cachecache: 再搜 ----
    key = "cachecache"
    cafe = by_key[key]
    queries = ["Cache Cache Bangkok", "曼谷 CacheCache 甜点", "曼谷 杏仁塔 法式 甜点", "曼谷 Song Wat 咖啡 甜点"]
    must = ["cachecache", "cache cache"]
    raw_cafe = os.path.join(RAW_DIR, key + "_final")
    os.makedirs(raw_cafe, exist_ok=True)
    seen=set(); matched=[]
    for q in queries:
        rc, out, err = run([OPENCLI, "xiaohongshu", "search", q, "--limit", "20", "-f", "json"])
        if rc != 0 or not out.strip(): continue
        try: notes = json.loads(out)
        except: continue
        for nn in notes:
            t = nn.get("title","").lower()
            if not any(m in t for m in must): continue
            u = nn.get("url")
            if u and u not in seen:
                seen.add(u); matched.append(nn)
    matched.sort(key=likes_of, reverse=True)
    print(f"cachecache 命中 {len(matched)} 条: " + " | ".join(nn.get('title','')[:18] for nn in matched[:4]))
    got = 0
    for nn in matched:
        if got >= 4: break
        rc, o, e = run([OPENCLI, "xiaohongshu", "download", nn.get("url"), "--output", raw_cafe])
        if rc != 0: continue
        got = len(list_images(raw_cafe))
    strict_imgs = []
    for p in list_images(raw_cafe):
        try: strict_imgs.append(crop_to_916(Image.open(p).convert("RGB")))
        except: pass
    if len(strict_imgs) < 3:
        # 回补首轮合集
        for p in list_images(os.path.join(RAW_DIR, key)):
            try:
                im = crop_to_916(Image.open(p).convert("RGB"))
                if im: strict_imgs.append(im)
            except: pass
            if len(strict_imgs) >= 3: break
    n = set_cafe(key, strict_imgs)
    print(f"cachecache: strict={len([1 for _ in list_images(raw_cafe)])} -> 写入 {n} 张")
    print("完成")

if __name__ == "__main__":
    main()
