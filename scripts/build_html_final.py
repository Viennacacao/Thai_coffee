# -*- coding: utf-8 -*-
import os, json, base64, glob

ROOT = "/Users/shiduopili/WorkBuddy/2026-08-14-10-48-46/bangkok_cafe_xhs"
ASSETS = os.path.join(ROOT, "html_assets")
HTML_OUT = os.path.join(ROOT, "html", "曼谷各国风咖啡甜品地图.html")

data = json.load(open(os.path.join(ROOT, "scripts", "cafes_data.json"), encoding="utf-8"))
by_key = {c["key"]: c for c in data}

# 主题皮肤：每个国家风格一套视觉语言
THEMES = {
    "日式": dict(key="jp", flag="🇯🇵", accent="#B5651D", bg="#FBF7F0", bg2="#F1E6D6",
                 ink="#3A2E22", muted="#8A7A66", line="#E6D7C4", font="serif",
                 sub="极简 · 昭和 · 枯山水",
                 lead="木色、纸感、安静的自然光——一秒切去东京下町的留白美学，随手一拍都干净。"),
    "法式": dict(key="fr", flag="🇫🇷", accent="#C9A227", bg="#FBF6EA", bg2="#F3E9CE",
                 ink="#3A3220", muted="#8C7C4E", line="#E8DDBB", font="serif",
                 sub="甜品 · 宫廷 · 左岸",
                 lead="奶油色与金线，欧陆咖啡馆的静谧与体面；甜点像艺术品，连包装都出片。"),
    "北欧": dict(key="dk", flag="🇩🇰", accent="#6B7A8F", bg="#F4F6F8", bg2="#E7ECF1",
                 ink="#2C3640", muted="#6E7C8A", line="#D8E0E7", font="sans",
                 sub="斯堪的纳维亚极简",
                 lead="水泥、原木、 daylight——把克制做到极致，空间本身就是主角。"),
    "韩式": dict(key="kr", flag="🇰🇷", accent="#D98BA0", bg="#FDF6F8", bg2="#F8E9EF",
                 ink="#4A3340", muted="#A07C8C", line="#F0D9E2", font="sans",
                 sub="极简 · 粉彩 · 公主感",
                 lead="奶油白调、满屋干花、窗边自然光，像掉进 Pinterest 里的粉色世界。"),
    "意式": dict(key="it", flag="🇮🇹", accent="#2E7D32", bg="#F4F8F2", bg2="#E4F0E2",
                 ink="#26331F", muted="#5E7A55", line="#D7E8D3", font="sans",
                 sub="甜品实验室",
                 lead="只为一种甜点而生，极简白调里把提拉米苏做到讲究。"),
    "澳式": dict(key="au", flag="🇦🇺", accent="#E07A3F", bg="#FDF6EF", bg2="#F8E7D8",
                 ink="#3F2A1C", muted="#9A6A4C", line="#F0D9C6", font="sans",
                 sub="早午餐 · Flat White",
                 lead="砖房、藤椅、大窗自然光，明亮通透的早午餐圣地，OOTD 随手出。"),
    "中东": dict(key="tr", flag="🇹🇷", accent="#8E5A3C", bg="#FBF4EE", bg2="#EFE0D4",
                 ink="#36241A", muted="#8A6A56", line="#E3CBB8", font="serif",
                 sub="异域 · 波西米亚",
                 lead="古铜、拱门、铜壶沙煮咖啡——125 年古建筑的神秘与优雅，过程即秀。"),
    "泰式": dict(key="th", flag="🇹🇭", accent="#2A9D8F", bg="#F2FAF8", bg2="#DDF1EC",
                 ink="#1F3A36", muted="#4E8A80", line="#C8E8E1", font="sans",
                 sub="复古 · 艺术 · 森林",
                 lead="鲜艳撞色、彩窗老建筑、独栋花园——新旧融合，热带又文艺。"),
}

FLAGSHIPS = ["kif", "cachecache", "lacabra", "whitetulip", "tiramisu", "tobys", "shaloba", "arteasia"]

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
}

TAG_CLASS = {"✅": "tag-ok", "⚠️": "tag-warn", "🆕": "tag-new"}
TAG_TEXT = {"✅": "真实好评", "⚠️": "出片向", "🆕": "新晋"}


def b64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def shop_images(key):
    d = os.path.join(ASSETS, key)
    fs = sorted(glob.glob(os.path.join(d, "*.jpg")))[:3]
    return [b64(f) for f in fs]


def meta_row(k, v):
    return f'<div class="meta-row"><span class="k">{k}</span><span class="v">{v}</span></div>'


sections_html = []
nav_html = []

for idx, key in enumerate(FLAGSHIPS, 1):
    c = by_key[key]
    th = THEMES[c["cat"]]
    e = ENRICH.get(key, {})
    imgs = shop_images(key)
    gid = f"sec-{th['key']}"
    # nav pill
    nav_html.append(
        f'<a class="pill" data-target="{gid}" data-accent="{th["accent"]}" '
        f'style="--p:{th["accent"]}"><span>{th["flag"]}</span>{c["cat"]}</a>'
    )
    # gallery
    gal = "".join(
        f'<img class="shot" src="{s}" alt="{c["name"]} 实拍" loading="lazy">' for s in imgs
    )
    # 加映
    others = [x for x in data if x["cat"] == c["cat"] and x["key"] != key][:3]
    more_cards = ""
    for o in others:
        more_cards += f'''
        <div class="more-card">
          <div class="more-head"><span class="flag">{o["flag"]}</span><b>{o["name"]}</b>
            <span class="tag {TAG_CLASS[o["tag"]]}">{TAG_TEXT[o["tag"]]}</span></div>
          <p><span class="mk">出片</span>{o["style"]}</p>
          <p><span class="mk">招牌</span>{o["sig"]}</p>
          <p><span class="mk">位置</span>{o["loc"]}</p>
        </div>'''
    more_block = ""
    if more_cards:
        more_block = f'''
        <div class="more">
          <h4 class="more-title">同场加映 · 更多{th["flag"]} {c["cat"]}风</h4>
          <div class="more-grid">{more_cards}</div>
        </div>'''

    sec = f'''
    <section class="theme-sec" id="{gid}" data-theme="{th["key"]}">
      <div class="sec-inner">
        <header class="sec-head">
          <div class="sec-no">{idx:02d}</div>
          <div class="sec-title">
            <div class="sec-flag">{th["flag"]}</div>
            <h2>{c["cat"]}风</h2>
            <p class="sec-sub">{th["sub"]}</p>
          </div>
          <p class="sec-lead">{th["lead"]}</p>
        </header>

        <article class="shop">
          <div class="shop-head">
            <span class="flag big">{c["flag"]}</span>
            <h3>{c["name"]}</h3>
            <span class="tag {TAG_CLASS[c["tag"]]}">{TAG_TEXT[c["tag"]]}</span>
          </div>
          <p class="review">“{e.get('review', c['style'])}”</p>
          <div class="body">
            <div class="meta">
              {meta_row("出片点", c["style"])}
              {meta_row("招牌推荐", c["sig"])}
              {meta_row("位置 / 交通", e.get("transport", c["loc"]))}
              {meta_row("价位", c["loc"].split("｜")[-1] if "｜" in c["loc"] else c["loc"])}
              {meta_row("营业时间", e.get("hours", "以门店为准"))}
            </div>
            <div class="gallery">{gal}</div>
          </div>
        </article>
        {more_block}
      </div>
    </section>'''
    sections_html.append(sec)

sections_all = "\n".join(sections_html)
nav_all = "\n".join(nav_html)

CSS = """
:root{--active:#B5651D;--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Hiragino Sans GB",sans-serif;--serif:"Songti SC","STSong",Georgia,"Times New Roman",serif;}
*{box-sizing:border-box;margin:0;padding:0;}
html{scroll-behavior:smooth;}
body{font-family:var(--sans);color:#222;background:#fff;line-height:1.7;}
#progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--active);z-index:200;transition:background .5s,width .1s;}
.hero{height:100vh;min-height:560px;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;
  background:radial-gradient(120% 120% at 50% 0%,#fff 0%,#f4ece2 55%,#e9dccb 100%);padding:24px;position:relative;}
.hero .kicker{letter-spacing:.4em;font-size:13px;color:#9a7b54;text-transform:uppercase;margin-bottom:18px;}
.hero h1{font-family:var(--serif);font-size:clamp(34px,7vw,72px);color:#2b2118;line-height:1.15;font-weight:700;}
.hero .sub{margin-top:18px;font-size:clamp(15px,2.4vw,20px);color:#6b5640;max-width:620px;}
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
.intro h2{font-family:var(--serif);font-size:28px;color:#2b2118;margin-bottom:18px;}
.intro p{color:#54483a;font-size:16px;margin-bottom:14px;}
.legend{display:flex;gap:18px;justify-content:center;flex-wrap:wrap;margin-top:22px;font-size:14px;color:#6b5640;}
.legend i{font-style:normal;}
.theme-sec{background:var(--bg);color:var(--ink);transition:background .6s;}
.sec-inner{max-width:1100px;margin:0 auto;padding:70px 24px;}
.sec-head{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;border-bottom:2px solid var(--accent);padding-bottom:26px;margin-bottom:38px;}
.sec-no{font-family:var(--serif);font-size:64px;font-weight:700;color:var(--accent);line-height:1;opacity:.9;}
.sec-title{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.sec-flag{font-size:34px;}
.sec-title h2{font-family:var(--font);font-size:34px;}
.sec-sub{width:100%;color:var(--muted);font-size:15px;letter-spacing:.05em;margin-top:2px;}
.sec-lead{grid-column:1/-1;color:var(--muted);font-size:16px;max-width:760px;margin-top:6px;}
.shop{background:var(--bg2);border:1px solid var(--line);border-radius:18px;padding:26px;box-shadow:0 10px 30px rgba(0,0,0,.04);}
.shop-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px;}
.flag{font-size:18px;}.flag.big{font-size:26px;}
.shop-head h3{font-family:var(--font);font-size:26px;color:var(--ink);}
.tag{font-size:12px;padding:3px 10px;border-radius:999px;font-weight:600;}
.tag-ok{background:#E7F4E8;color:#2E7D32;}.tag-warn{background:#FFF3E0;color:#E07A3F;}.tag-new{background:#F0E9FB;color:#7B4FC0;}
.review{font-family:var(--font);font-size:18px;color:var(--ink);margin-bottom:20px;line-height:1.8;opacity:.92;}
.body{display:grid;grid-template-columns:1fr 1.05fr;gap:28px;}
.meta{display:flex;flex-direction:column;gap:2px;}
.meta-row{display:grid;grid-template-columns:84px 1fr;gap:12px;padding:11px 0;border-bottom:1px dashed var(--line);}
.meta-row .k{color:var(--accent);font-weight:700;font-size:14px;flex:0 0 84px;}
.meta-row .v{color:var(--ink);font-size:15px;}
.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
.shot{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:12px;cursor:zoom-in;
  border:1px solid var(--line);transition:transform .25s,box-shadow .25s;background:#eee;}
.shot:hover{transform:translateY(-3px);box-shadow:0 10px 24px rgba(0,0,0,.18);}
.more{margin-top:34px;}
.more-title{font-family:var(--font);font-size:18px;color:var(--muted);margin-bottom:14px;}
.more-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;}
.more-card{background:var(--bg2);border:1px solid var(--line);border-radius:14px;padding:16px;font-size:14px;color:var(--ink);}
.more-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;}
.more-head b{font-size:16px;}
.more-card p{margin:4px 0;color:var(--ink);}
.more-card .mk{display:inline-block;color:var(--accent);font-weight:700;margin-right:6px;font-size:13px;}
footer{background:#26201a;color:#cdbfae;text-align:center;padding:40px 24px;font-size:14px;line-height:1.9;}
footer a{color:#e6c9a0;}
#lightbox{position:fixed;inset:0;background:rgba(0,0,0,.9);display:none;align-items:center;justify-content:center;z-index:300;cursor:zoom-out;}
#lightbox img{max-width:92vw;max-height:92vh;border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.5);}
@media(max-width:780px){
  .body{grid-template-columns:1fr;}
  .sec-head{grid-template-columns:1fr;}
  .sec-no{font-size:48px;}
  .intro{padding-top:44px;}
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
    const ac=e.target.getAttribute('data-theme');
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
  <p class="sub">按美学风格挑一家对味的店——日式留白、法式甜点、北欧极简、韩系公主感……拍照好看，也真好喝。</p>
  <div class="badges">
    <span class="badge">🇯🇵🇫🇷🇩🇰🇰🇷🇮🇹🇦🇺🇹🇷🇹🇭 8 国风</span>
    <span class="badge">📸 8 家实拍</span>
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
    <p>每家都给了：<b>出片点</b>（为什么好拍）、<b>招牌推荐</b>（点什么不踩雷）、<b>位置交通</b>、<b>价位</b>、<b>营业时间</b>，还配了<b>实拍图</b>。图都来自小红书真实探店笔记，仅供风格参考。</p>
    <p>图例：<b>✅ 真实好评</b>／<b>⚠️ 出片向（味道见仁见智）</b>／<b>🆕 新晋待探</b>。顺路标注 [D1] 河南岸咖啡动线、[老城] 大秋千一带。</p>
    <div class="legend">
      <i>✅ 多源真实好评</i><i>⚠️ 偏网红打卡</i><i>🆕 新晋/待自查</i>
    </div>
  </section>

  {sections_all}
</main>

<footer>
  <p>📸 店内实拍图来源于小红书用户探店笔记，版权归原作者所有，本页仅供风格参考与旅行攻略之用。</p>
  <p>全 40 家「各国风」清单已结构化存档，本版先放出 8 家旗舰实拍 + 同风格加映；解锁完整版请关注后续更新。</p>
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
