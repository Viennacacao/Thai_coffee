#!/usr/bin/env python3
"""第三轮精准补抓：用更准的搜索词，对 kif/cachecache/tiramisu/whitetulip 重抓；
命中标题含店名的笔记才下载；原图先备份，不足 3 张时回补并标 low_conf。"""
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
    "kif":        {"must": ["kif"], "city": [], "queries": ["曼谷 KIF 咖啡", "KIF BKK 曼谷", "KIF Coffee Roasters 曼谷"]},
    "cachecache": {"must": ["cache cache", "cachecache"], "city": [], "queries": ["曼谷 Cache Cache", "Cache Cache 曼谷 甜点", "曼谷 Cache Cache 法甜"]},
    "tiramisu":   {"must": ["tiramisu"], "city": ["曼谷","bangkok","bkk","泰国","thai"], "queries": ["曼谷 Tiramisu Lab", "THE TIRAMISÙ LAB 曼谷", "曼谷 提拉米苏实验室"]},
    "whitetulip": {"must": ["tulip", "white tulip"], "city": [], "queries": ["曼谷 White Tulip", "White Tulip 曼谷 Rama9", "怀特郁金香 曼谷咖啡"]},
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

def main():
    # 备份当前 images_916
    if os.path.exists(OUT_DIR):
        shutil.rmtree(BAK_DIR, ignore_errors=True)
        shutil.copytree(OUT_DIR, BAK_DIR)
        print(f"已备份原图到 {BAK_DIR}")
    data = json.load(open(DATA)); by_key = {c["key"]: c for c in data}
    for key, plan in PLAN.items():
        cafe = by_key[key]
        print(f"\n===== 补抓 [{key}] {cafe['name']} =====")
        raw_cafe = os.path.join(RAW_DIR, key + "_strict2")
        os.makedirs(raw_cafe, exist_ok=True)
        seen = set(); matched = []
        for q in plan["queries"]:
            rc, out, err = run([OPENCLI, "xiaohongshu", "search", q, "--limit", "20", "-f", "json"])
            if rc != 0 or not out.strip(): continue
            try: notes = json.loads(out)
            except: continue
            for n in notes:
                t = n.get("title","").lower()
                if not any(m in t for m in plan["must"]): continue
                if plan["city"] and not any(c in t for c in plan["city"]): continue
                u = n.get("url")
                if u and u not in seen:
                    seen.add(u); matched.append(n)
        matched.sort(key=likes_of, reverse=True)
        print(f"  跨词命中 {len(matched)} 条: " + " | ".join(n.get("title","")[:20] for n in matched[:5]))
        got = 0
        for n in matched:
            if got >= 4: break
            rc, o, e = run([OPENCLI, "xiaohongshu", "download", n.get("url"), "--output", raw_cafe])
            if rc != 0: continue
            got = len(list_images(raw_cafe))
            print(f"  +「{n.get('title','')[:18]}」共 {got} 张")
        # 裁并写回 images_916/<key>
        cafe_out = os.path.join(OUT_DIR, key)
        for f in os.listdir(cafe_out):
            try: os.remove(os.path.join(cafe_out, f))
            except: pass
        strict_imgs = list_images(raw_cafe)
        n = 0
        for p in strict_imgs:
            try:
                im = Image.open(p).convert("RGB"); im = crop_to_916(im)
                if im is None: continue
                base = os.path.splitext(os.path.basename(p))[0]
                dst = os.path.join(cafe_out, f"{base}.jpg"); i=1
                while os.path.exists(dst): dst = os.path.join(cafe_out, f"{base}_{i}.jpg"); i+=1
                im.save(dst, "JPEG", quality=88); n+=1
            except Exception as ex: print("  跳过", p, ex)
        low_conf = False
        if n < 3:
            # 回补：从备份里拿原图（非同名笔记，但仍是曼谷咖啡实拍）
            low_conf = True
            bak = os.path.join(BAK_DIR, key)
            for f in sorted(os.listdir(bak)):
                if n >= 3: break
                src = os.path.join(bak, f)
                dst = os.path.join(cafe_out, "bak_" + f)
                if not os.path.exists(dst):
                    try:
                        im = Image.open(src).convert("RGB"); im = crop_to_916(im)
                        im.save(dst, "JPEG", quality=88); n+=1
                    except: pass
        print(f"  ✓ 共 {n} 张 (strict={len(strict_imgs)}, low_conf={low_conf}) -> {cafe_out}")
    print("\n第三轮补抓完成")

if __name__ == "__main__":
    main()
