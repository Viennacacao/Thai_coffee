#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_maps.py —— Google 地图商家照片批量抓取（浏览器桥接内 fetch 转 base64，绕开被代理挡死的 CDN）

原理：
  1. opencli browser 打开 Google Maps 搜索页（商家照片 CDN 直连超时/代理 502，但 Chrome 网络栈通）
  2. 滚动触发懒加载，eval 提取 lh3.googleusercontent.com/gps-cs-s/... 照片 URL
  3. URL 尺寸参数改为 w1600 拿高清原图
  4. 浏览器内 fetch(URL) -> blob -> FileReader -> base64（异源 fetch 已验证可用）
  5. base64 解码 -> PIL 中心裁 9:16 -> 存 html_assets/<key>/NN.jpg

用法：
  python fetch_maps.py --keys nana roast          # 指定店铺
  python fetch_maps.py --all                       # 全部缺图店铺（<3 张的）
  python fetch_maps.py --session m                 # 指定 browser session（默认 m）
每店最多抓 N 张（默认 6，只保留前 3 张 9:16 成图）。
"""
import os, re, sys, json, time, base64, argparse, subprocess
from PIL import Image
from io import BytesIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "scripts", "cafes_data.json")
ASSETS = os.path.join(ROOT, "html_assets")

# Google Maps 精确搜索词覆盖（key -> 英文查询词，比店名更易命中商家页）
MAPS_QUERY = {
    "roast": "Roast Coffee EmQuartier Bangkok",
    "sulbing": "After You Dessert Cafe Bangkok",
    "kaizen": "Kaizen Coffee Bangkok",
    "sarnies": "Sarnies Bangkok",
    "shelly": "Shelly House Bangkok",
    "shatku": "Shatku Cafe Bistro Bangkok",
    "shakti": "Shakti Cafe Bistro Bangkok",
    "thongyoy": "Thongyoy Cafe Bangkok",
    "ruedemansri": "Rue De Mansri Bangkok",
    "wallflowers": "Wallflowers Cafe Bangkok",
    "bubbleforest": "Bubble in the Forest Bangkok",
    "sretsis": "Sretsis Parlour Bangkok",
    "gumps": "GUMP'S Ari Bangkok",
    "babyccino": "Babyccino Bangkok",
    "nana": "Nana Coffee Roasters Bangkok",
}

# 需要跳过搜索的店名片段（含括号注释/别名的，取主名）
def clean_name(name: str) -> str:
    n = name.split("（")[0].strip()          # 去掉中文括号注释
    n = n.split("(")[0].strip()              # 去掉英文括号注释
    n = n.split("/")[0].strip()              # 多店名取第一个（如 Sulbing / After You...）
    n = n.split("&")[0].strip() if n.lower().startswith("sarnies") else n  # Sarnies（& Friends）特殊
    return n

def run_cli(args, timeout=90):
    r = subprocess.run(["opencli"] + args, capture_output=True, text=True, timeout=timeout)
    out = r.stdout
    # 去掉 opencli 噪声行
    lines = [l for l in out.splitlines() if "UNDICI" not in l and "trace-warnings" not in l]
    return "\n".join(lines)

def open_maps(session, query):
    url = "https://www.google.com/maps/search/" + query.replace(" ", "+") + "+Bangkok"
    run_cli(["browser", session, "open", url], timeout=60)
    time.sleep(2.5)
    run_cli(["browser", session, "scroll", "down"], timeout=30)
    time.sleep(1.2)
    run_cli(["browser", session, "scroll", "down"], timeout=30)
    time.sleep(1.2)

def extract_urls(session):
    js = ("Array.from(document.images).map(i=>i.currentSrc||i.src)"
          ".filter(s=>/gps-cs-s/.test(s)).map(s=>s.split('=')[0])")
    out = run_cli(["browser", session, "eval", js], timeout=60)
    return list(dict.fromkeys(re.findall(r"https://[^\" ]+", out)))

def fetch_b64(session, url):
    js = (f"fetch('{url}').then(r=>r.blob()).then(b=>new Promise((res,rej)=>{{"
          f"const fr=new FileReader();fr.onload=()=>res(fr.result);fr.onerror=rej;"
          f"fr.readAsDataURL(b)}}))")
    out = run_cli(["browser", session, "eval", js], timeout=120)
    m = re.search(r"data:image/(jpeg|png);base64,([A-Za-z0-9+/=]+)", out)
    if not m:
        return None
    return base64.b64decode(m.group(2))

def save_916(data: bytes, dest: str, maxw=1080, q=82) -> bool:
    """中心裁 9:16 + resize，存 JPEG。返回是否成功。"""
    try:
        im = Image.open(BytesIO(data)).convert("RGB")
        w, h = im.size
        if h <= 0 or w <= 0:
            return False
        # 中心裁 9:16（竖版）：目标宽高比 w/h = 9/16 ≈ 0.5625
        target = 9 / 16
        if w / h > target:          # 太宽（横图）-> 裁左右
            nw = int(h * target)
            x = (w - nw) // 2
            im = im.crop((x, 0, x + nw, h))
        elif h / w > 16 / 9:        # 太高（竖长图）-> 裁上下
            nh = int(w * 16 / 9)
            y = (h - nh) // 2
            im = im.crop((0, y, w, y + nh))
        if im.width > maxw:
            im = im.resize((maxw, int(maxw * im.height / im.width)), Image.LANCZOS)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        im.save(dest, "JPEG", quality=q, optimize=True)
        return True
    except Exception as e:
        print(f"    !! 图片处理失败: {e}")
        return False

def fetch_shop(session, key, name, want=3, max_try=8):
    """为一家店抓图，返回成功张数。"""
    out_dir = os.path.join(ASSETS, key)
    os.makedirs(out_dir, exist_ok=True)
    existing = len([f for f in os.listdir(out_dir) if f.endswith(".jpg")])
    if existing >= want:
        print(f"[skip] {key} 已有 {existing} 张，跳过")
        return existing

    query = MAPS_QUERY.get(key, clean_name(name))
    print(f"[fetch] {key} | 搜索: {query}")
    try:
        open_maps(session, query)
    except Exception as e:
        print(f"    !! 打开 Maps 失败: {e}")
        return existing

    urls = extract_urls(session)
    print(f"    Maps 页抠到 {len(urls)} 张照片 URL")
    got = existing
    tried = 0
    for i, u in enumerate(urls):
        if got >= want or tried >= max_try:
            break
        tried += 1
        big = u + "=w1600-k-no"
        data = fetch_b64(session, big)
        if not data or len(data) < 20000:   # <20KB 视为失败/占位
            print(f"    - 图{i+1} 获取失败或过小，跳过")
            continue
        idx = got + 1
        dest = os.path.join(out_dir, f"{idx:02d}.jpg")
        if save_916(data, dest):
            print(f"    + 图{i+1} -> {dest} ({len(data)//1024}KB)")
            got += 1
        time.sleep(0.6)
    return got

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", nargs="*", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--session", default="m")
    ap.add_argument("--want", type=int, default=3)
    ap.add_argument("--max-try", type=int, default=8)
    args = ap.parse_args()

    cafes = json.load(open(DATA, encoding="utf-8"))
    if args.keys:
        targets = [(c["key"], c["name"]) for c in cafes if c["key"] in args.keys]
    elif args.all:
        targets = []
        for c in cafes:
            d = os.path.join(ASSETS, c["key"])
            n = len([f for f in os.listdir(d) if f.endswith(".jpg")]) if os.path.isdir(d) else 0
            if n < args.want:
                targets.append((c["key"], c["name"]))
    else:
        print("请指定 --keys 或 --all")
        sys.exit(1)

    print(f"目标 {len(targets)} 家店，每店要 {args.want} 张\n" + "=" * 50)
    summary = {}
    for key, name in targets:
        try:
            n = fetch_shop(args.session, key, name, want=args.want, max_try=args.max_try)
            summary[key] = n
        except Exception as e:
            print(f"[error] {key}: {e}")
            summary[key] = -1
    print("=" * 50)
    for k, n in summary.items():
        print(f"  {k:14s}: {n} 张")

if __name__ == "__main__":
    main()
