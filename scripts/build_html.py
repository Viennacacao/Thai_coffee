#!/usr/bin/env python3
"""根据店家数据 + 实拍图清单生成 HTML 相册。

用法:
  python3 build_html.py --scope sample    # 仅 8 家样张
  python3 build_html.py --scope all       # 全部 40 家

依赖:
  scripts/cafes_data.json   店家元数据(全量)
  scripts/photos.json       { "<key>": ["images_916/xxx/1.jpg", ...], ... }  (相对工作区根)
输出:
  html/index.html
"""
import json, os, sys, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "scripts", "cafes_data.json")
PHOTOS = os.path.join(ROOT, "scripts", "photos.json")
OUT = os.path.join(ROOT, "html", "index.html")

def load():
    with open(DATA, encoding="utf-8") as f:
        cafes = json.load(f)
    photos = {}
    if os.path.exists(PHOTOS):
        with open(PHOTOS, encoding="utf-8") as f:
            photos = json.load(f)
    return cafes, photos

def slug(s):
    return s.replace('"', '').replace("'", "")

def card(c, imgs):
    accent = c.get("accent", "#888")
    flag = c.get("flag", "")
    name = c.get("name", "")
    tag = c.get("tag", "")
    cat = c.get("cat", "")
    style = c.get("style", "")
    sig = c.get("sig", "")
    loc = c.get("loc", "")
    if not imgs:
        img_html = ('<div class="img-row"><div class="img-cell empty">'
                    '<span>小红书图待抓取</span></div>'
                    '<div class="img-cell empty"><span>小红书图待抓取</span></div>'
                    '<div class="img-cell empty"><span>小红书图待抓取</span></div></div>')
    else:
        cells = []
        for p in imgs[:3]:
            rel = "../" + p
            cells.append(f'<div class="img-cell"><img loading="lazy" src="{rel}" alt="{slug(name)}"></div>')
        while len(cells) < 3:
            cells.append('<div class="img-cell empty"><span>—</span></div>')
        img_html = '<div class="img-row">' + "".join(cells) + '</div>'
    return f'''
    <section class="cafe" style="--accent:{accent}">
      <div class="accent"></div>
      <div class="body">
        <header class="cafe-head">
          <span class="flag">{flag}</span>
          <h2>{name}</h2>
          <span class="tag">{tag}</span>
          <span class="cat">{cat}</span>
        </header>
        <div class="meta">
          <p><span class="k">出片</span>{style}</p>
          <p><span class="k">招牌</span>{sig}</p>
          <p><span class="k">位置</span>{loc}</p>
        </div>
        {img_html}
      </div>
    </section>'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["sample", "all"], default="sample")
    args = ap.parse_args()

    cafes, photos = load()
    if args.scope == "sample":
        sel = [c for c in cafes if c.get("sample")]
    else:
        sel = cafes

    cards = []
    for c in sel:
        key = c["key"]
        imgs = photos.get(key, [])
        cards.append(card(c, imgs))
    cards_html = "\n".join(cards)

    title = "曼谷拍照咖啡/甜品店 · 小红书实拍" + ("（样张 8 家）" if args.scope == "sample" else "（全 40 家）")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI", Roboto, sans-serif;
    background:#f7f6f3; color:#2b2b2b; line-height:1.6; padding:24px 16px 64px;
  }}
  .top {{
    max-width:980px; margin:0 auto 28px; text-align:center;
  }}
  .top h1 {{ font-size:24px; letter-spacing:.5px; }}
  .top p {{ color:#888; font-size:13px; margin-top:6px; }}
  .wrap {{ max-width:980px; margin:0 auto; display:flex; flex-direction:column; gap:22px; }}
  .cafe {{
    display:flex; background:#fff; border-radius:16px; overflow:hidden;
    box-shadow:0 4px 18px rgba(0,0,0,.06);
  }}
  .accent {{ width:6px; flex:0 0 6px; background:var(--accent); }}
  .body {{ padding:18px 20px; flex:1; }}
  .cafe-head {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:10px; }}
  .cafe-head .flag {{ font-size:22px; }}
  .cafe-head h2 {{ font-size:19px; font-weight:700; }}
  .cafe-head .tag {{ font-size:13px; color:#c0392b; border:1px solid #f0c5bf; border-radius:6px; padding:1px 7px; }}
  .cafe-head .cat {{ font-size:12px; color:#fff; background:var(--accent); border-radius:6px; padding:2px 9px; }}
  .meta p {{ font-size:13.5px; color:#555; margin:3px 0; }}
  .meta .k {{
    display:inline-block; min-width:34px; color:#999; font-size:12px; margin-right:8px;
    border-right:1px solid #e8e8e8; padding-right:8px;
  }}
  .img-row {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:14px; }}
  .img-cell {{ aspect-ratio:9/16; background:#efefef; border-radius:10px; overflow:hidden; display:flex; align-items:center; justify-content:center; }}
  .img-cell img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .img-cell.empty {{ color:#bbb; font-size:12px; }}
  @media (max-width:560px) {{
    .img-row {{ grid-template-columns:repeat(3,1fr); gap:5px; }}
    .body {{ padding:14px; }}
    .cafe-head h2 {{ font-size:17px; }}
  }}
</style>
</head>
<body>
  <div class="top">
    <h1>{title}</h1>
    <p>图片来源：小红书实拍（agent-reach · OpenCLI）｜每家 3 张 · 9:16</p>
  </div>
  <div class="wrap">
    {cards_html}
  </div>
</body>
</html>'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ 已生成: {OUT}  ({len(sel)} 家)")

if __name__ == "__main__":
    main()
