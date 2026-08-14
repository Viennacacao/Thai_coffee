#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_real.py — 为曼谷咖啡甜品地图抓取「真实、干净」的店铺照片。
策略（用户拍板）：优先店家官网/官方相册；无官网/无图再退到 Google 图片搜索（注：经实测
Google 图片缩略图经代理 502 不可下载，故仅作为「找官网」的发现手段，不作为取图像素来源）。

真实图片来源优先级：
  1) 官网：桥接渲染提取 <img>/data-src/背景图 + curl 抓 og:image（店家原图，最真实）
  2) 不足 3 张时：保留已有小红书图（不空白），不强行用低质源替换
全程：opencli browser 桥接（公开站无需登录）+ requests 直连下载 + PIL 裁 9:16。
"""
import os, re, sys, json, time, subprocess
from urllib.parse import urlparse, quote
import requests
from PIL import Image
from io import BytesIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "html_assets")
DATA = os.path.join(ROOT, "scripts", "cafes_data.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
OUT_W, OUT_H = 1080, 1920  # 9:16
SOCIAL = re.compile(r'facebook\.com|instagram\.com|twitter\.com|x\.com|tiktok\.com|tripadvisor\.com|wikipedia\.org|linkedin\.com|youtube\.com|pinterest\.|line\.me|foodpanda|grabfood', re.I)
BAD_IMG = re.compile(r'logo|icon|avatar|sprite|badge|placeholder|arrow|close|menu|btn|button|pixel|1x1|tracking|analytics|loading|spinner', re.I)

# ---------- opencli 桥接封装 ----------
def cli(args, timeout=90):
    try:
        r = subprocess.run(["opencli"] + args, capture_output=True, text=True, timeout=timeout)
        return r.stdout or ""
    except Exception as e:
        return f"ERR:{e}"

def eval_js(js, timeout=60):
    out = cli(["browser", "g", "eval", js], timeout=timeout)
    return parse_json_arr(out)

def parse_json_arr(out):
    out = out.strip()
    try:
        v = json.loads(out)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    return re.findall(r'https?://[^\s"\'\[\],]+', out)

def open_url(url, wait=2.0):
    cli(["browser", "g", "open", url], timeout=90)
    time.sleep(wait)

def scroll(n=6):
    for _ in range(n):
        cli(["browser", "g", "scroll", "down"], timeout=30)
        time.sleep(0.7)

# ---------- 官网发现 ----------
def google_links(query):
    open_url("https://www.google.com/search?q=" + quote(query), wait=2.0)
    links = eval_js("Array.from(document.querySelectorAll('a')).map(a=>a.href).filter(h=>/^https?:/.test(h)&&!/google\\.|gstatic\\.|youtube\\.|googleusercontent/.test(h))")
    return [l for l in links if isinstance(l, str) and l.startswith("http")]

def pick_official(name, links):
    toks = [t for t in re.findall(r'[a-z0-9]{4,}', name.lower()) if t not in ('cafe','coffee','bangkok','bangkokcafe')]
    cand = [l.split('?')[0] for l in links if not SOCIAL.search(l)]  # 去 Google 跟踪参数
    for l in cand:
        host = urlparse(l).netloc.lower().replace('www.', '')
        if any(t in host for t in toks):
            return l
    return cand[0] if cand else None

# ---------- 图片提取 ----------
BRIDGE_JS = r"""
(function(){
  var out=[];
  document.querySelectorAll('*').forEach(function(el){
    var st=el.getAttribute('style')||'';
    var m=st.match(/background-image:\s*url\((['"]?)([^)'"]+)\1\)/i);
    if(m) out.push(m[2]);
  });
  Array.from(document.images).forEach(function(i){
    var s=i.currentSrc||i.src||i.getAttribute('data-src')||i.getAttribute('data-lazy-src')||'';
    if(s) out.push(s);
    var ss=i.getAttribute('srcset')||'';
    ss.split(',').forEach(function(p){ var u=p.trim().split(' ')[0]; if(u&&/^https?:/.test(u)) out.push(u); });
  });
  var og=document.querySelector('meta[property="og:image"]'); if(og&&og.content) out.push(og.content);
  return out.filter(function(s){return /^https?:/.test(s)&&!/logo|icon/i.test(s);});
})()
"""

def site_imgs_bridge(url, retries=1):
    last=[]
    for attempt in range(retries+1):
        open_url(url, wait=3.0)
        scroll(6)
        imgs = eval_js(BRIDGE_JS)
        imgs = [u for u in imgs if isinstance(u, str) and not BAD_IMG.search(u.lower())]
        if len(imgs) >= 3:
            return dedupe(imgs)
        last = dedupe(imgs)
        time.sleep(1)
    return last

def site_imgs_curl(url):
    out=[]
    try:
        html = requests.get(url, headers={"User-Agent": UA}, timeout=30).text
        # og:image
        for m in re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I):
            out.append(m)
        # 直接 <img src>
        for m in re.findall(r'<img[^>]+src=["\'](https://[^"\']+\.(?:jpg|jpeg|png|webp))', html, re.I):
            if not BAD_IMG.search(m.lower()):
                out.append(m)
    except Exception:
        pass
    return dedupe(out)

def gimages_links(query):
    """仅用于「找官网」的发现；Google 图片缩略图经代理 502 不可下载，不取像素。"""
    open_url("https://www.google.com/search?tbm=isch&q=" + quote(query), wait=2.5)
    scroll(5)
    return google_links(query)  # 复用普通搜索链接抽取（图片搜索页也含站点链接）

def dedupe(lst):
    seen=set(); res=[]
    for u in lst:
        if u not in seen:
            seen.add(u); res.append(u)
    return res

# ---------- 下载 + 裁切 ----------
def download(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": "https://www.google.com/"}, timeout=35)
        if r.status_code == 200 and len(r.content) > 5000:
            return r.content
    except Exception:
        pass
    return None

def crop_916(data, path):
    try:
        im = Image.open(BytesIO(data)).convert("RGB")
        w, h = im.size
        if w < 200 or h < 200:
            return False
        scale = max(OUT_W / w, OUT_H / h)
        nw, nh = int(w * scale), int(h * scale)
        im = im.resize((nw, nh), Image.LANCZOS)
        left = (nw - OUT_W) // 2
        top = (nh - OUT_H) // 2
        im = im.crop((left, top, left + OUT_W, top + OUT_H))
        im.save(path, "JPEG", quality=82)
        return True
    except Exception:
        return False

# ---------- 单店流程 ----------
def existing_imgs(key):
    folder = os.path.join(ASSETS, key)
    if not os.path.isdir(folder):
        return []
    return sorted([f for f in os.listdir(folder) if f.endswith('.jpg')])

def process(key, name, force=False):
    have = existing_imgs(key)
    if not force and len(have) >= 3:
        print(f"  [skip] {key} 已有 {len(have)} 张")
        return len(have)

    print(f"== {key} ({name}) ==")
    found = []
    # 1) 官网发现
    links = google_links(f"{name} bangkok official website")
    official = pick_official(name, links)
    if official:
        print(f"   官网: {official}")
        found += site_imgs_bridge(official)
        print(f"   桥接图: {len(found)}")
        if len(found) < 3:
            found += site_imgs_curl(official)
            print(f"   +curl图: {len(found)}")
    # 2) 仍不足：Google 图片页找更多官网候选
    if len(found) < 3:
        more = gimages_links(f"{name} bangkok cafe")
        for u in more:
            if u in found: continue
            extra = site_imgs_bridge(u)
            found += extra
            if len(found) >= 6: break
        print(f"   追加候选后: {len(found)}")
    found = dedupe(found)

    # 3) 下载 + 裁切（尽量补到 3 张，已有的不覆盖，合并去重）
    folder = os.path.join(ASSETS, key)
    os.makedirs(folder, exist_ok=True)
    saved = 0
    used = set(have)
    for u in found:
        if len(used) >= 3: break
        data = download(u)
        if not data: continue
        # 避免重复已有图
        path = os.path.join(folder, f"0{len(used)+1}.jpg")
        if crop_916(data, path):
            used.add(path.name); saved += 1
            print(f"   存图: {u[:72]}")
    total = len(existing_imgs(key))
    print(f"   -> 现有 {total} 张")
    return total

# ---------- 主入口 ----------
def main():
    args = sys.argv[1:]
    force_all = "--all" in args
    keys_arg = [a for a in args if not a.startswith("--")]
    data = json.load(open(DATA, encoding="utf-8"))
    by_key = {c["key"]: c for c in data}
    if keys_arg:
        targets = [(k, by_key[k]["name"]) for k in keys_arg if k in by_key]
    else:
        targets = [(c["key"], c["name"]) for c in data]
    ok = 0
    for key, name in targets:
        try:
            n = process(key, name, force=force_all)
            if n >= 3: ok += 1
        except Exception as e:
            print(f"  [ERR] {key}: {e}")
    print(f"\n完成：满足>=3图的店铺 {ok}/{len(targets)}")

if __name__ == "__main__":
    main()
