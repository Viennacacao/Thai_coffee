# -*- coding: utf-8 -*-
import os, json, base64, glob, io, re
from PIL import Image

ROOT = "/Users/shiduopili/WorkBuddy/2026-08-14-10-48-46/bangkok_cafe_xhs"
ASSETS = os.path.join(ROOT, "html_assets")
HTML_OUT = os.path.join(ROOT, "html", "曼谷各国风咖啡甜品地图.html")

data = json.load(open(os.path.join(ROOT, "scripts", "cafes_data.json"), encoding="utf-8"))
by_key = {c["key"]: c for c in data}

# ---------- 母题 SVG（内联，零外部依赖）----------
MOTIF = {
    "jp": '<svg viewBox="0 0 120 120"><path d="M62 14 a46 46 0 1 1 -16 6" fill="none" stroke="var(--accent2)" stroke-width="7" stroke-linecap="round" opacity=".9"/></svg>',
    "fr": '<svg viewBox="0 0 80 80"><path d="M40 8 L48 32 L72 32 L52 48 L60 72 L40 56 L20 72 L28 48 L8 32 L32 32 Z" fill="none" stroke="var(--accent)" stroke-width="2.5" opacity=".8"/></svg>',
    "dk": '<svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="26" fill="none" stroke="var(--accent)" stroke-width="2.5" opacity=".7"/><circle cx="40" cy="40" r="4" fill="var(--accent)" opacity=".7"/></svg>',
    "kr": '<svg viewBox="0 0 80 80"><path d="M40 66 C12 46 18 20 40 26 C62 20 68 46 40 66 Z" fill="none" stroke="var(--accent)" stroke-width="2.5" opacity=".8"/></svg>',
    "it": '<svg viewBox="0 0 80 80"><path d="M40 12 C52 30 52 50 40 68 C28 50 28 30 40 12 Z" fill="none" stroke="var(--accent)" stroke-width="2.5" opacity=".8"/><line x1="40" y1="12" x2="40" y2="68" stroke="var(--accent)" stroke-width="2.5" opacity=".8"/></svg>',
    "au": '<svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="14" fill="none" stroke="var(--accent)" stroke-width="3"/><g stroke="var(--accent)" stroke-width="2.5">'+''.join(f'<line x1="40" y1="40" x2="{40+22*round(__import__("math").cos(a),3)}" y2="{40+22*round(__import__("math").sin(a),3)}"/>' for a in [i*3.14159/4 for i in range(8)])+'</g></svg>',
    "tr": '<svg viewBox="0 0 80 90"><path d="M14 80 V40 a26 26 0 0 1 52 0 V80" fill="none" stroke="var(--accent)" stroke-width="3"/><line x1="14" y1="80" x2="66" y2="80" stroke="var(--accent)" stroke-width="3"/></svg>',
    "th": '<svg viewBox="0 0 80 80"><path d="M40 64 C20 52 20 28 40 16 C60 28 60 52 40 64 Z M40 16 C40 30 40 44 40 64" fill="none" stroke="var(--accent)" stroke-width="2.5" opacity=".85"/></svg>',
    "dr": '<svg viewBox="0 0 80 80"><path d="M40 6 C44 30 50 36 74 40 C50 44 44 50 40 74 C36 50 30 44 6 40 C30 36 36 30 40 6 Z" fill="none" stroke="var(--accent)" stroke-width="2.5" opacity=".85"/><circle cx="40" cy="40" r="5" fill="var(--accent)" opacity=".6"/></svg>',
}

# ---------- 主题配置 ----------
THEMES = {
    "日式": dict(key="jp", flag="🇯🇵", accent="#B5651D", accent2="#C0392B", bg="#F7F3EC",
                 surface="#EFE7D8", ink="#2B2622", muted="#7A6F5E", line="#E2D7C4",
                 font_head="'Songti SC','Yu Mincho',serif", font_body="-apple-system,'PingFang SC',sans-serif",
                 radius="10px", vertical=True),
    "法式": dict(key="fr", flag="🇫🇷", accent="#C9A227", accent2="#7B2D3A", bg="#FBF6EA",
                 surface="#F3E9CE", ink="#3A3220", muted="#8C7C4E", line="#E8DDBB",
                 font_head="Georgia,'Songti SC',serif", font_body="Georgia,'Songti SC',serif",
                 radius="14px", vertical=False),
    "北欧": dict(key="dk", flag="🇩🇰", accent="#6B7A8F", accent2="#9AA7B4", bg="#F4F6F8",
                 surface="#E7ECF1", ink="#2C3640", muted="#6E7C8A", line="#D8E0E7",
                 font_head="'Helvetica Neue',Arial,sans-serif", font_body="'Helvetica Neue',Arial,sans-serif",
                 radius="4px", vertical=False),
    "韩式": dict(key="kr", flag="🇰🇷", accent="#D98BA0", accent2="#E9A7BC", bg="#FDF6F8",
                 surface="#F8E9EF", ink="#4A3340", muted="#A07C8C", line="#F0D9E2",
                 font_head="'PingFang SC',sans-serif", font_body="'PingFang SC',sans-serif",
                 radius="22px", vertical=False),
    "意式": dict(key="it", flag="🇮🇹", accent="#2E7D32", accent2="#B5651D", bg="#F4F8F2",
                 surface="#E4F0E2", ink="#26331F", muted="#5E7A55", line="#D7E8D3",
                 font_head="'PingFang SC',sans-serif", font_body="'PingFang SC',sans-serif",
                 radius="8px", vertical=False),
    "澳式": dict(key="au", flag="🇦🇺", accent="#E07A3F", accent2="#4A90A4", bg="#FDF6EF",
                 surface="#F8E7D8", ink="#3F2A1C", muted="#9A6A4C", line="#F0D9C6",
                 font_head="'PingFang SC',sans-serif", font_body="'PingFang SC',sans-serif",
                 radius="12px", vertical=False),
    "中东": dict(key="tr", flag="🇹🇷", accent="#C9A227", accent2="#8E5A3C", bg="#241B14",
                 surface="#2F241A", ink="#E8DCCB", muted="#B89B7E", line="#4A3A28",
                 font_head="Georgia,serif", font_body="'PingFang SC',sans-serif",
                 radius="10px", vertical=False),
    "泰式": dict(key="th", flag="🇹🇭", accent="#2A9D8F", accent2="#D4A017", bg="#F2FAF8",
                 surface="#DDF1EC", ink="#1F3A36", muted="#4E8A80", line="#C8E8E1",
                 font_head="'PingFang SC',sans-serif", font_body="'PingFang SC',sans-serif",
                 radius="12px", vertical=False),
    "梦幻": dict(key="dr", flag="🌿", accent="#9B5DE5", accent2="#F15BB5", bg="#FBF3FB",
                 surface="#F3E7F6", ink="#3A2A40", muted="#9A7CA8", line="#EBDDF2",
                 font_head="'PingFang SC',sans-serif", font_body="'PingFang SC',sans-serif",
                 radius="20px", vertical=False),
}

LEADS = {
    "日式": "脱鞋入座、原木与留白，一盏抹茶就能消磨整个下午。",
    "法式": "修车厂旁的别墅、金线与甜塔，把巴黎的优雅打包进热带。",
    "北欧": "白墙、原木、自然光，克制到极致的性冷淡美学。",
    "韩式": "粉彩、干花、奶油灯光，一秒掉进公主的早晨。",
    "意式": "像实验室一样的意式极简，每一杯都讲究配比与温度。",
    "澳式": "砖房、藤椅、早午餐，海风与 OOTD 的明快午后。",
    "中东": "古铜、拱门、铜壶煮咖啡，125 年古宅里的神秘东方。",
    "泰式": "彩窗、古木、热带绿意，泰西混血的当代艺术甜品。",
    "梦幻": "像掉进绘本里的一下午，粉紫、壁画、精致餐具，公主梦与奇幻感拉满。",
}
for _k, _v in LEADS.items():
    if _k in THEMES:
        THEMES[_k]["lead"] = _v
        THEMES[_k]["tagline"] = _v

# 章节顺序（含梦幻，40 家全覆盖）
CAT_ORDER = ["日式", "法式", "北欧", "韩式", "意式", "澳式", "中东", "泰式", "梦幻"]

# 每个风格的代表店（旗舰），渲染时排在最前并加「首推」标识
FLAGSHIPS = {"日式": "kif", "法式": "cachecache", "北欧": "lacabra", "韩式": "whitetulip",
             "意式": "tiramisu", "澳式": "tobys", "中东": "shaloba", "泰式": "arteasia", "梦幻": "sretsis"}

# 旗舰店的补充细节（其余店用 loc 解析 + 派生点评）
ENRICH = {
    "kif": {"hours": "每日 10:00–18:00", "transport": "BTS Phrom Phong 步行约 10 分 · Sukhumvit 31",
            "review": "曼谷最像东京下町的安静角落，自然光一照就是片；Matcha Latte 不甜不腻，刚刚好。"},
    "cachecache": {"hours": "10:00–18:00（周一、二休）", "transport": "Song Wat 巷内 · 河南岸咖啡动线 [D1]",
                  "review": "修车厂旁藏着一栋法式小墅，市井与欧陆的反差最出片；Émilie 塔的 kalamansi 酸香是记忆点。"},
    "lacabra": {"hours": "Talat Noi 店 17:00 关（建议上午）", "transport": "Talat Noi / Ari / Silom · 河南岸 [D1]",
                "review": "丹麦奥胡斯海外首店，水泥木头 daylight 极简，老店屋细节全留着，Flat White 标杆级。"},
    "whitetulip": {"hours": "周二–日 10:00–18:00（周一休）", "transport": "Rama 9",
                   "review": "满屋干花 + 窗边自然光，像掉进 Pinterest 公主世界；Tulip Cream Cake 颜值味道都在线。"},
    "tiramisu": {"hours": "营业时间以门店为准", "transport": "Sukhumvit",
                 "review": "只做提拉米苏的实验室，从 Classico 经典到 Coconut / Matcha / Durian 季节创意，甜品控朝圣。"},
    "tobys": {"hours": "各分店约 8:00–22:00（以门店为准）", "transport": "Sukhumvit 38 / Sala Daeng / Ploenchit",
              "review": "澳式早午餐砖房 + 藤椅，OOTD 圣地；Egg Mikado 亚洲风味班尼迪克蛋是一绝。"},
    "shaloba": {"hours": "8:30–17:00", "transport": "Dinso Rd 大秋千旁老城 · 老城 [D1 上午]",
                "review": "125 年古建筑，铜壶沙煮咖啡的过程本身就是视觉秀，古董酒店 + 中东神秘感拉满。"},
    "arteasia": {"hours": "营业时间以门店为准", "transport": "Song Wat（与 Cache Cache 同区）",
                 "review": "彩窗老建筑 + 古木 + 现代艺术 Tart Bar，泰西融合的 Golden Drops 椰子慕斯配「泰鱼子」很妙。"},
    "sretsis": {"hours": "营业时间以门店为准", "transport": "Asok",
                "review": "童话粉嫩奇幻风，壁画 + 精致餐具，是曼谷最有「公主梦下午茶」氛围的一家。"},
}

TAG_CLASS = {"✅": "tag-ok", "⚠️": "tag-warn", "🆕": "tag-new"}
TAG_TEXT = {"✅": "真实好评", "⚠️": "出片向", "🆕": "新晋"}


def b64(path, maxw=1000, q=72):
    try:
        im = Image.open(path).convert("RGB")
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def load_imgs(key, n=3):
    d = os.path.join(ASSETS, key)
    fs = sorted(glob.glob(os.path.join(d, "*.jpg")))
    out = []
    for f in fs[:n]:
        s = b64(f)
        if s:
            out.append(s)
    return out


def parse_loc(loc):
    """从 loc 字段尽量解析出 位置 / 价位 / 营业时间。"""
    pos, price, hours = loc.strip(), "以门店为准", "以门店为准"
    if "｜" in loc:
        p0, rest = loc.split("｜", 1)
        pos = p0.strip()
        rest = rest.strip()
        m = re.search(r'([\d,]+\s*[–-]\s*[\d,]+\s*฿|人均\s*[\d,–-]+\s*฿|[\d,]+\s*฿)', rest)
        if m:
            price = m.group(0).replace(" ", "")
        hm = re.search(r'[^，。]*?(?:休|关|营业|开放|每日|周一[^，。]*?休)[^，。]*', rest)
        if hm:
            hours = hm.group(0).strip().rstrip("，。")
    elif "休" in loc or "营业" in loc or re.search(r'\d{1,2}:\d{2}', loc):
        # 没有｜但含时间信息
        hm = re.search(r'[^，。]*?(?:休|关|营业|开放|每日|周一[^，。]*?休)[^，。]*', loc)
        if hm:
            hours = hm.group(0).strip().rstrip("，。")
    return pos, price, hours


def parse_loc_full(loc):
    pos, price, hours = parse_loc(loc)
    return pos, price, hours


def meta_row(k, v):
    return f'<div class="meta-row"><span class="k">{k}</span><span class="v">{v}</span></div>'


def make_review(c, e):
    if e.get("review"):
        return e["review"]
    sig0 = re.split(r"[、 ]", c["sig"])[0]
    return f"{c['style']}；来这里记得点「{sig0}」。"


sections_html = []
nav_html = []
sec_no = 0

for cat in CAT_ORDER:
    if cat not in THEMES:
        continue
    th = THEMES[cat]
    shops = [c for c in data if c["cat"] == cat]
    if not shops:
        continue
    sec_no += 1
    gid = f"sec-{th['key']}"

    # 旗舰排第一
    fs_key = FLAGSHIPS.get(cat)
    ordered = sorted(shops, key=lambda c: (0 if c["key"] == fs_key else 1, c["id"]))

    nav_html.append(
        f'<a class="pill" data-target="{gid}" data-accent="{th["accent"]}" '
        f'style="--p:{th["accent"]}"><span>{th["flag"]}</span>{cat}</a>'
    )

    # 竖排（仅日式）标题
    if th["vertical"]:
        title_block = f'''
        <div class="sec-title jp-title">
          <div class="jp-row">
            <div class="sec-flag">{th["flag"]}</div>
            <h2 class="vtitle">{cat}风</h2>
            <div class="sec-no">{sec_no:02d}</div>
          </div>
          <p class="sec-sub">{th["tagline"]}</p>
        </div>'''
    else:
        title_block = f'''
        <div class="sec-title">
          <div class="sec-flag">{th["flag"]}</div>
          <div>
            <h2>{cat}风</h2>
            <p class="sec-sub">{th["tagline"]}</p>
          </div>
          <div class="sec-no">{sec_no:02d}</div>
        </div>'''

    cards = ""
    for c in ordered:
        e = ENRICH.get(c["key"], {})
        imgs = load_imgs(c["key"], 3)
        pos, price, hours = parse_loc_full(c["loc"])
        review = make_review(c, e)
        transport = e.get("transport", pos)
        featured = (c["key"] == fs_key)
        ribbon = '<span class="ribbon">首推</span>' if featured else ""
        gal = "".join(f'<img class="shot" src="{s}" alt="{c["name"]}" loading="lazy">' for s in imgs)
        if not gal:
            gal = '<div class="no-gal">实拍图筹备中 · 稍后由 Instagram 探店图补入</div>'

        cards += f'''
        <article class="shop {'featured' if featured else ''}">
          {ribbon}
          <div class="shop-head">
            <span class="flag big">{c["flag"]}</span>
            <h3>{c["name"]}</h3>
            <span class="tag {TAG_CLASS[c["tag"]]}">{TAG_TEXT[c["tag"]]}</span>
            <span class="seal">{c["name"][:1]}</span>
          </div>
          <p class="review">“{review}”</p>
          <div class="body">
            <div class="meta">
              {meta_row("出片点", c["style"])}
              {meta_row("招牌推荐", c["sig"])}
              {meta_row("位置 / 交通", transport)}
              {meta_row("价位", price)}
              {meta_row("营业时间", e.get("hours", hours))}
            </div>
            <div class="gallery">{gal}</div>
          </div>
        </article>'''

    sec = f'''
    <section class="theme-sec" id="{gid}" data-theme="{th['key']}">
      <div class="sec-inner">
        <header class="sec-head">
          {title_block}
          <div class="motif">{MOTIF[th['key']]}</div>
          <p class="sec-lead">{th.get('lead','')}</p>
        </header>
        <div class="shops">{cards}</div>
      </div>
    </section>'''
    sections_html.append(sec)

sections_all = "\n".join(sections_html)
nav_all = "\n".join(nav_html)

CSS = """
:root{--active:#B5651D;--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;}
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{font-family:var(--sans);color:#222;background:#fff;line-height:1.7;}
#progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--active);z-index:200;transition:background .5s,width .1s;}
.hero{height:100vh;min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;
  background:radial-gradient(130% 120% at 50% 0%,#fff 0%,#f4ece2 55%,#e7d8c4 100%);padding:24px;position:relative;}
.hero .kicker{letter-spacing:.4em;font-size:13px;color:#9a7b54;text-transform:uppercase;margin-bottom:18px;}
.hero h1{font-family:"Songti SC",Georgia,serif;font-size:clamp(34px,7vw,74px);color:#2b2118;line-height:1.15;}
.hero .sub{margin-top:18px;font-size:clamp(15px,2.4vw,20px);color:#6b5640;max-width:640px;}
.hero .badges{margin-top:30px;display:flex;gap:12px;flex-wrap:wrap;justify-content:center;}
.hero .badge{border:1px solid #d8c4a8;background:rgba(255,255,255,.6);color:#7a5c38;padding:8px 16px;border-radius:999px;font-size:14px;}
.hero .scroll-tip{position:absolute;bottom:28px;left:50%;transform:translateX(-50%);color:#a98c64;font-size:13px;animation:bob 1.8s ease-in-out infinite;}
@keyframes bob{0%,100%{transform:translate(-50%,0);}50%{transform:translate(-50%,8px);}}
.nav{position:sticky;top:0;z-index:150;background:rgba(255,255,255,.92);backdrop-filter:blur(10px);
  border-bottom:1px solid #ece3d6;display:flex;gap:8px;padding:10px 14px;overflow-x:auto;}
.pill{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;text-decoration:none;color:#5a4a38;
  border:1px solid #e6dccb;border-radius:999px;padding:7px 14px;font-size:14px;white-space:nowrap;transition:.25s;background:#fff;}
.pill span{font-size:15px;}
.pill:hover{border-color:var(--p);}
.pill.active{background:var(--p);color:#fff;border-color:var(--p);transform:translateY(-1px);box-shadow:0 4px 14px rgba(0,0,0,.12);}
.intro{max-width:880px;margin:0 auto;padding:64px 24px 40px;text-align:center;}
.intro h2{font-family:"Songti SC",serif;font-size:28px;color:#2b2118;margin-bottom:18px;}
.intro p{color:#54483a;font-size:16px;margin-bottom:14px;}
.legend{display:flex;gap:18px;justify-content:center;flex-wrap:wrap;margin-top:22px;font-size:14px;color:#6b5640;}

/* ===== 主题章节（每主题局部变量） ===== */
.theme-sec{background:var(--bg);color:var(--ink);transition:background .6s;font-family:var(--font-body);}
[data-theme="jp"]{--bg:#F7F3EC;--surface:#EFE7D8;--ink:#2B2622;--muted:#7A6F5E;--line:#E2D7C4;--accent:#B5651D;--accent2:#C0392B;--font-head:"Songti SC","Yu Mincho",serif;--font-body:-apple-system,"PingFang SC",sans-serif;--radius:10px;}
[data-theme="fr"]{--bg:#FBF6EA;--surface:#F3E9CE;--ink:#3A3220;--muted:#8C7C4E;--line:#E8DDBB;--accent:#C9A227;--accent2:#7B2D3A;--font-head:Georgia,"Songti SC",serif;--font-body:Georgia,"Songti SC",serif;--radius:14px;}
[data-theme="dk"]{--bg:#F4F6F8;--surface:#E7ECF1;--ink:#2C3640;--muted:#6E7C8A;--line:#D8E0E7;--accent:#6B7A8F;--accent2:#9AA7B4;--font-head:"Helvetica Neue",Arial,sans-serif;--font-body:"Helvetica Neue",Arial,sans-serif;--radius:4px;}
[data-theme="kr"]{--bg:#FDF6F8;--surface:#F8E9EF;--ink:#4A3340;--muted:#A07C8C;--line:#F0D9E2;--accent:#D98BA0;--accent2:#E9A7BC;--font-head:"PingFang SC",sans-serif;--font-body:"PingFang SC",sans-serif;--radius:22px;}
[data-theme="it"]{--bg:#F4F8F2;--surface:#E4F0E2;--ink:#26331F;--muted:#5E7A55;--line:#D7E8D3;--accent:#2E7D32;--accent2:#B5651D;--font-head:"PingFang SC",sans-serif;--font-body:"PingFang SC",sans-serif;--radius:8px;}
[data-theme="au"]{--bg:#FDF6EF;--surface:#F8E7D8;--ink:#3F2A1C;--muted:#9A6A4C;--line:#F0D9C6;--accent:#E07A3F;--accent2:#4A90A4;--font-head:"PingFang SC",sans-serif;--font-body:"PingFang SC",sans-serif;--radius:12px;}
[data-theme="tr"]{--bg:#241B14;--surface:#2F241A;--ink:#E8DCCB;--muted:#B89B7E;--line:#4A3A28;--accent:#C9A227;--accent2:#8E5A3C;--font-head:Georgia,serif;--font-body:"PingFang SC",sans-serif;--radius:10px;}
[data-theme="th"]{--bg:#F2FAF8;--surface:#DDF1EC;--ink:#1F3A36;--muted:#4E8A80;--line:#C8E8E1;--accent:#2A9D8F;--accent2:#D4A017;--font-head:"PingFang SC",sans-serif;--font-body:"PingFang SC",sans-serif;--radius:12px;}
[data-theme="dr"]{--bg:#FBF3FB;--surface:#F3E7F6;--ink:#3A2A40;--muted:#9A7CA8;--line:#EBDDF2;--accent:#9B5DE5;--accent2:#F15BB5;--font-head:"PingFang SC",sans-serif;--font-body:"PingFang SC",sans-serif;--radius:20px;}

.sec-inner{max-width:1100px;margin:0 auto;padding:70px 24px;}
.sec-head{position:relative;display:grid;grid-template-columns:1fr auto;gap:18px 24px;align-items:center;
  border-bottom:2px solid var(--accent);padding-bottom:24px;margin-bottom:36px;}
.sec-title{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.sec-flag{font-size:34px;}
.sec-title h2{font-family:var(--font-head);font-size:36px;color:var(--ink);letter-spacing:.02em;}
.sec-sub{color:var(--muted);font-size:15px;margin-top:4px;}
.sec-no{font-family:var(--font-head);font-size:62px;font-weight:700;color:var(--accent);line-height:1;opacity:.85;}
.motif{width:84px;height:84px;opacity:.9;justify-self:end;align-self:start;}
.motif svg{width:100%;height:100%;}
.sec-lead{grid-column:1/-1;color:var(--muted);font-size:16px;max-width:760px;margin-top:4px;}

/* 日式竖排 */
.jp-title .jp-row{display:flex;align-items:center;gap:16px;}
.vtitle{writing-mode:vertical-rl;text-orientation:upright;font-family:var(--font-head);font-size:40px;
  letter-spacing:.15em;color:var(--ink);height:auto;}
.theme-sec[data-theme="jp"]{background:
  linear-gradient(0deg,rgba(0,0,0,.015),rgba(0,0,0,.015)),
  repeating-linear-gradient(90deg,#F7F3EC,#F7F3EC 22px,#F4EFE6 22px,#F4EFE6 24px);}
.theme-sec[data-theme="jp"] .shop{background:
  repeating-linear-gradient(0deg,rgba(0,0,0,.012),rgba(0,0,0,.012) 26px,transparent 26px,transparent 28px),var(--surface);}

.shops{display:flex;flex-direction:column;gap:34px;}
.shop{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:26px;box-shadow:0 10px 30px rgba(0,0,0,.05);}
.shop.featured{border-width:2px;border-color:var(--accent);box-shadow:0 14px 36px rgba(0,0,0,.1);}
.ribbon{position:absolute;top:-12px;left:22px;background:var(--accent);color:#fff;font-size:12px;
  font-weight:700;letter-spacing:.1em;padding:4px 12px;border-radius:999px;box-shadow:0 4px 12px rgba(0,0,0,.18);}
.theme-sec[data-theme="tr"] .shop.featured{border-color:var(--accent2);}
.theme-sec[data-theme="fr"] .shop{box-shadow:0 0 0 1px var(--accent) inset,0 12px 30px rgba(0,0,0,.06);}
.theme-sec[data-theme="tr"] .shop{border-color:var(--accent2);}
.shop-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px;position:relative;}
.flag{font-size:18px;}.flag.big{font-size:26px;}
.shop-head h3{font-family:var(--font-head);font-size:26px;color:var(--ink);}
.seal{margin-left:auto;width:40px;height:40px;display:flex;align-items:center;justify-content:center;
  background:var(--accent2);color:#fff;font-family:var(--font-head);font-size:20px;border-radius:6px;
  box-shadow:0 2px 8px rgba(0,0,0,.2);transform:rotate(-4deg);}
.theme-sec[data-theme="jp"] .seal{font-family:"Songti SC",serif;}
.tag{font-size:12px;padding:3px 10px;border-radius:999px;font-weight:600;}
.tag-ok{background:#E7F4E8;color:#2E7D32;}.tag-warn{background:#FFF3E0;color:#E07A3F;}.tag-new{background:#F0E9FB;color:#7B4FC0;}
.review{font-family:var(--font-head);font-size:18px;color:var(--ink);margin-bottom:20px;line-height:1.85;opacity:.92;}
.body{display:grid;grid-template-columns:1fr 1.05fr;gap:28px;}
.meta{display:flex;flex-direction:column;}
.meta-row{display:grid;grid-template-columns:84px 1fr;gap:12px;padding:11px 0;border-bottom:1px dashed var(--line);}
.meta-row .k{color:var(--accent);font-weight:700;font-size:14px;flex:0 0 84px;}
.meta-row .v{color:var(--ink);font-size:15px;}
.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;align-content:start;}
.shot{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:calc(var(--radius) - 2px);
  cursor:zoom-in;border:1px solid var(--line);background:#e9e3d8;transition:transform .25s,box-shadow .25s;}
.shot:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(0,0,0,.18);}
.no-gal{grid-column:1/-1;display:flex;align-items:center;justify-content:center;min-height:160px;
  border:1px dashed var(--line);border-radius:calc(var(--radius) - 2px);color:var(--muted);font-size:14px;
  background:rgba(255,255,255,.25);text-align:center;padding:18px;}

footer{background:#26201a;color:#cdbfae;text-align:center;padding:40px 24px;font-size:14px;line-height:1.9;}
footer a{color:#e6c9a0;}
#lightbox{position:fixed;inset:0;background:rgba(0,0,0,.9);display:none;align-items:center;justify-content:center;z-index:300;cursor:zoom-out;}
#lightbox img{max-width:92vw;max-height:92vh;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.5);}
@media(max-width:780px){
  .body{grid-template-columns:1fr;}
  .sec-head{grid-template-columns:1fr;}
  .sec-no{font-size:46px;}
  .motif{width:60px;height:60px;}
  .vtitle{font-size:30px;}
}
"""

JS = """
const root=document.documentElement;
const prog=document.getElementById('progress');
const pills=[...document.querySelectorAll('.pill')];
const sections=[...document.querySelectorAll('.theme-sec')];
function onScroll(){const h=document.documentElement;const max=h.scrollHeight-h.clientHeight;
  prog.style.width=(h.scrollTop/max*100)+'%';}
window.addEventListener('scroll',onScroll,{passive:true});onScroll();
const obs=new IntersectionObserver((es)=>{
  es.forEach(e=>{if(e.isIntersecting){
    const accent=getComputedStyle(e.target).getPropertyValue('--accent').trim();
    root.style.setProperty('--active',accent);
    pills.forEach(p=>p.classList.toggle('active',p.dataset.target===e.target.id));
  }});
},{rootMargin:'-45% 0px -45% 0px'});
sections.forEach(s=>obs.observe(s));
pills.forEach(p=>p.addEventListener('click',ev=>{ev.preventDefault();
  document.getElementById(p.dataset.target).scrollIntoView({behavior:'smooth'});}));
const lb=document.getElementById('lightbox');const lbimg=document.getElementById('lbimg');
document.querySelectorAll('.shot').forEach(im=>im.addEventListener('click',()=>{
  lbimg.src=im.src;lb.style.display='flex';}));
lb.addEventListener('click',()=>lb.style.display='none');
document.addEventListener('keydown',e=>{if(e.key==='Escape')lb.style.display='none';});
"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>曼谷各国风咖啡甜品地图 · 攻略博主精选</title>
<style>{CSS}</style>
</head>
<body>
<div id="progress"></div>

<header class="hero">
  <div class="kicker">Bangkok Cafe Guide</div>
  <h1>曼谷各国风<br>咖啡甜品地图</h1>
  <p class="sub">按美学风格挑一家对味的店——日式留白、法式甜点、北欧极简、韩系公主感……九个主题，四十家店，每家都值得专程去。</p>
  <div class="badges">
    <span class="badge">🇯🇵🇫🇷🇩🇰🇰🇷🇮🇹🇦🇺🇹🇷🇹🇭🌿 9 国风</span>
    <span class="badge">📸 实拍图</span>
    <span class="badge">✍️ 攻略博主出品</span>
  </div>
  <div class="scroll-tip">向下滚动，开启咖啡巡礼 ↓</div>
</header>

<nav class="nav" id="nav">
  <a class="pill" href="#top" style="--p:#9a7b54"><span>🏠</span>开篇</a>
  {nav_all}
</nav>

<main id="top">
  <section class="intro">
    <h2>写在前面：怎么用这份地图</h2>
    <p>曼谷的咖啡甜品店多到挑花眼，但真正「好拍又有风格」的，我按国家/美学分了类。你不用纠结「哪家最火」，先看自己是想拍<b>极简留白</b>还是<b>公主梦境</b>，对号入座。</p>
    <p>每一家都给了：<b>出片点</b>（为什么好拍）、<b>招牌推荐</b>（点什么不踩雷）、<b>位置交通</b>、<b>价位</b>、<b>营业时间</b>，还配了<b>实拍图</b>。图来自小红书 / Instagram 真实探店笔记，仅供风格参考。</p>
    <p>图例：<b>✅ 真实好评</b>／<b>⚠️ 出片向（味道见仁见智）</b>／<b>🆕 新晋待探</b>。顺路标注 [D1] 河南岸咖啡动线、[老城] 大秋千一带。「首推」为各风格的代表店。</p>
    <div class="legend"><i>✅ 多源真实好评</i><i>⚠️ 偏网红打卡</i><i>🆕 新晋/待自查</i></div>
  </section>

  {sections_all}
</main>

<footer>
  <p>📸 店内实拍图来源于小红书 / Instagram 用户探店笔记，版权归原作者所有，本页仅供风格参考与旅行攻略之用。</p>
  <p>全 40 家「各国风」清单已结构化存档，本版九大主题每家均含详版卡片，实拍图随 Instagram 探店图持续补齐。</p>
  <p>曼谷各国风咖啡甜品地图 · 攻略博主精选</p>
</footer>

<div id="lightbox"><img id="lbimg" src="" alt="放大查看"></div>
<script>{JS}</script>
</body>
</html>"""

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print("written:", HTML_OUT)
print("size MB:", round(os.path.getsize(HTML_OUT) / 1024 / 1024, 2))
