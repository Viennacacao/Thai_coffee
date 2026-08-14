#!/usr/bin/env python3
"""第四轮：精修 whitetulip/cachecache/tiramisu。
- whitetulip：用 white tulip 精确词；最终 = 真店图(images_raw/whitetulip_strict) + 回补原合集到 3 张。
- cachecache：搜「修车厂 法式」「Song Wat」特征 + cache 词；命中则用，否则回补。
- tiramisu：放宽城市，搜 tiramisu/提拉米苏 + 曼谷；命中则用，否则回补。
"""
import json, os, re, subprocess, shutil
from PIL import Image

BASE = "/Users/shiduopili/WorkBuddy/2026-08-14-10-48-46/bangkok_cafe_xhs"
DATA = os.path.join(BASE, "scripts", "cafes_data.json")
RAW_DIR = os.path.join(BASE, "images_raw")
OUT_DIR = os.path.join(BASE, "images_916")
BAK_DIR = os.path.join(BASE, "images_916_bak")
OPENCLI = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin/opencli"
NODE_BIN = "/Users/shiduopili/.workbuddy/binaries/node/versions/22.22.2/bin"
TARGET_RATIO = 9 / 16
SUPPORTED = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.avif', '.heic')

PLAN = {
    "cachecache": {"must": ["cache"], "queries": ["曼谷 修车厂 法式 甜点", "曼谷 Song Wat Cache Cache", "曼谷 Cache Cache 甜点"]},
    "tiramisu":   {"must": ["tiramisu", "提拉米苏"], "queries": ["曼谷 Tiramisu Lab", "THE TIRAMISÙ LAB 曼谷", "曼谷 提拉米苏实验室"]},
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
        nw = int(h * TARGET_RATIO); x=(w-nw)//2; box=(x,0,x+nw,h)
    else:
        nh = int(w / TARGET_RATIO); y=(h-nh)//2; box=(0,y,w,y+nh)
    im = im.crop(box)
    if max(im.size) > max_edge:
        s = max_edge/max(im.size); im = im.resize((int(im.size[0]*s), int(im.size[1]*s)), Image.LANCZOS)
    return im

def write_cafe(key, strict_list, backup_dir, need=3):
    """strict_list: 已裁好的 PIL images 列表；不足则从 backup_dir 回补。返回 (final_count, low_conf)"""
    cafe_out = os.path.join(OUT_DIR, key)
    for f in os.listdir(cafe_out):
        try: os.remove(os.path.join(cafe_out, f))
        except: pass
    n = 0; low = False
    for im in strict_list:
        if n >= need: break
        dst = os.path.join(cafe_out, f"strict_{n+1}.jpg")
        im.save(dst, "JPEG", quality=88); n += 1
    if n < need:
        low = True
        for f in sorted(os.listdir(backup_dir)):
            if n >= need: break
            src = os.path.join(backup_dir, f)
            dst = os.path.join(cafe_out, "bak_" + f)
            if os.path.exists(dst): continue
            try:
                im = Image.open(src).convert("RGB"); im = crop_to_916(im)
                im.save(dst, "JPEG", quality=88); n += 1
            except: pass
    return n, low

def main():
    data = json.load(open(DATA)); by_key = {c["key"]: c for c in data}
    # ---- whitetulip：精确 white tulip ----
    key = "whitetulip"
    print(f"\n===== 精修 [{key}] =====")
    raw_real = os.path.join(RAW_DIR, key + "_strict")      # 真店图(来自 refetch.py)
    raw_strict2 = os.path.join(RAW_DIR, key + "_strict2")  # 受污染的酒店图，弃用
    real_imgs = []
    for p in list_images(raw_real):
        try: real_imgs.append(crop_to_916(Image.open(p).convert("RGB")))
        except: pass
    print(f"  真店图: {len(real_imgs)} 张 (来自 {raw_real})")
    n, low = write_cafe(key, real_imgs, os.path.join(BAK_DIR, key))
    print(f"  ✓ whitetulip 共 {n} 张 (low_conf={low})")
    # ---- cachecache / tiramisu ----
    for key, plan in PLAN.items():
        cafe = by_key[key]
        print(f"\n===== 精修 [{key}] {cafe['name']} =====")
        raw_cafe = os.path.join(RAW_DIR, key + "_strict3")
        os.makedirs(raw_cafe, exist_ok=True)
        seen=set(); matched=[]
        for q in plan["queries"]:
            rc, out, err = run([OPENCLI, "xiaohongshu", "search", q, "--limit", "20", "-f", "json"])
            if rc != 0 or not out.strip(): continue
            try: notes = json.loads(out)
            except: continue
            for nn in notes:
                t = nn.get("title","").lower()
                if not any(m in t for m in plan["must"]): continue
                u = nn.get("url")
                if u and u not in seen:
                    seen.add(u); matched.append(nn)
        matched.sort(key=likes_of, reverse=True)
        print(f"  命中 {len(matched)} 条: " + " | ".join(nn.get('title','')[:20] for nn in matched[:4]))
        got = 0
        for nn in matched:
            if got >= 4: break
            rc, o, e = run([OPENCLI, "xiaohongshu", "download", nn.get("url"), "--output", raw_cafe])
            if rc != 0: continue
            got = len(list_images(raw_cafe))
            print(f"  +「{nn.get('title','')[:18]}」共 {got} 张")
        strict_imgs = []
        for p in list_images(raw_cafe):
            try: strict_imgs.append(crop_to_916(Image.open(p).convert("RGB")))
            except: pass
        n, low = write_cafe(key, strict_imgs, os.path.join(BAK_DIR, key))
        print(f"  ✓ {key} 共 {n} 张 (strict={len(strict_imgs)}, low_conf={low})")
    print("\n第四轮精修完成")

if __name__ == "__main__":
    main()
