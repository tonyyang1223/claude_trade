"""生成HTML工作台，内嵌数据"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

data_js = json.dumps(data, ensure_ascii=False)

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Crypto 投研工作台</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0e17; color:#e0e6ed; font-family:'Segoe UI',system-ui,sans-serif; font-size:13px; }}
.header {{ background:#111827; padding:12px 20px; border-bottom:1px solid #1f2937; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:100; }}
.header h1 {{ font-size:18px; color:#f0b90b; }}
.header .stats {{ color:#6b7280; font-size:12px; }}
.container {{ display:flex; height:calc(100vh - 53px); }}
.sidebar {{ width:420px; border-right:1px solid #1f2937; overflow-y:auto; }}
.main {{ flex:1; overflow-y:auto; padding:20px; }}
.search-bar {{ padding:10px; background:#111827; position:sticky; top:0; }}
.search-bar input {{ width:100%; padding:8px 12px; background:#0a0e17; border:1px solid #1f2937; border-radius:6px; color:#e0e6ed; font-size:13px; }}
.project-item {{ padding:10px 14px; border-bottom:1px solid #1a2332; cursor:pointer; display:flex; justify-content:space-between; align-items:center; transition:background .15s; }}
.project-item:hover {{ background:#1a2332; }}
.project-item.active {{ background:#1e3a5f; border-left:3px solid #f0b90b; }}
.project-item .sym {{ font-weight:600; color:#f0b90b; }}
.project-item .name {{ color:#6b7280; font-size:11px; }}
.project-item .price {{ text-align:right; }}
.up {{ color:#0ecb81; }}
.down {{ color:#f6465d; }}
.tag {{ display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px; margin-left:4px; }}
.tag-hot {{ background:#f6465d22; color:#f6465d; }}
.tag-new {{ background:#0ecb8122; color:#0ecb81; }}
.detail-header {{ background:#111827; border-radius:8px; padding:20px; margin-bottom:16px; }}
.detail-header h2 {{ font-size:24px; color:#fff; }}
.detail-header .price-big {{ font-size:32px; font-weight:700; margin:8px 0; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:12px; margin:16px 0; }}
.card {{ background:#111827; border-radius:8px; padding:14px; }}
.card .label {{ color:#6b7280; font-size:11px; text-transform:uppercase; }}
.card .value {{ font-size:18px; font-weight:600; margin-top:4px; }}
.section-title {{ font-size:16px; font-weight:600; margin:20px 0 10px; color:#f0b90b; border-bottom:1px solid #1f2937; padding-bottom:6px; }}
.event-item {{ background:#111827; border-left:3px solid #f0b90b; padding:10px 14px; margin-bottom:8px; border-radius:0 6px 6px 0; }}
.event-item .date {{ color:#6b7280; font-size:11px; }}
.tweet-item {{ background:#111827; padding:12px; margin-bottom:8px; border-radius:6px; }}
.tweet-item .author {{ color:#f0b90b; font-weight:600; }}
.tweet-item .text {{ margin-top:4px; line-height:1.5; }}
.tweet-item .meta {{ color:#6b7280; font-size:11px; margin-top:6px; }}
.badge {{ padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.badge-bull {{ background:#0ecb8122; color:#0ecb81; }}
.badge-bear {{ background:#f6465d22; color:#f6465d; }}
.filter-btns {{ display:flex; gap:6px; padding:8px 10px; }}
.filter-btns button {{ background:#1f2937; border:none; color:#9ca3af; padding:4px 10px; border-radius:4px; cursor:pointer; font-size:11px; }}
.filter-btns button.active {{ background:#f0b90b; color:#000; }}
</style>
</head>
<body>
<div class="header">
  <h1>Crypto 投研工作台</h1>
  <div class="stats">前100项目 | 更新: 2026-09-28 | <span id="count"></span></div>
</div>
<div class="container">
  <div class="sidebar">
    <div class="search-bar"><input type="text" id="search" placeholder="搜索项目名称或symbol..."></div>
    <div class="filter-btns">
      <button class="active" data-f="all">全部</button>
      <button data-f="up24">24h涨</button>
      <button data-f="down24">24h跌</button>
      <button data-f="ath">距ATH&gt;50%</button>
    </div>
    <div id="project-list"></div>
  </div>
  <div class="main" id="detail">
    <div style="text-align:center; color:#6b7280; margin-top:100px;">
      <p style="font-size:48px;">📊</p>
      <p style="margin-top:12px;">从左侧选择项目查看详情</p>
    </div>
  </div>
</div>
<script>
const DATA = {data_js};
let currentFilter = 'all';

document.getElementById('count').textContent = DATA.projects.length + ' projects';

function renderList() {{
  const q = document.getElementById('search').value.toLowerCase();
  let list = DATA.projects.filter(p => 
    p.symbol.toLowerCase().includes(q) || p.name.toLowerCase().includes(q)
  );
  if (currentFilter === 'up24') list = list.filter(p => p.chg24h > 0);
  if (currentFilter === 'down24') list = list.filter(p => p.chg24h < 0);
  if (currentFilter === 'ath') list = list.filter(p => p.ath && p.price && (p.price/p.ath-1) < -0.5);
  
  const el = document.getElementById('project-list');
  el.innerHTML = list.map(p => {{
    const chg = p.chg24h || 0;
    const cls = chg >= 0 ? 'up' : 'down';
    const pct = p.ath && p.price ? ((p.price/p.ath-1)*100).toFixed(1) : 0;
    return `<div class="project-item" onclick="showDetail('${{p.symbol}}')">
      <div><div class="sym">${{p.symbol}}</div><div class="name">${{p.name}}</div></div>
      <div class="price"><div class="${{cls}}">${{chg>=0?'+':''}}${{chg.toFixed(1)}}%</div><div class="name">$${{p.price?.toFixed(p.price>100?2:4)}}</div></div>
    </div>`;
  }}).join('');
}}

function showDetail(sym) {{
  const p = DATA.projects.find(x => x.symbol === sym);
  if (!p) return;
  const chg = p.chg24h || 0;
  const cls = chg >= 0 ? 'up' : 'down';
  const athPct = p.ath && p.price ? ((p.price/p.ath-1)*100).toFixed(1) : 'N/A';
  const mcapB = p.mcap ? (p.mcap/1e9).toFixed(1) : 'N/A';
  
  const events = DATA.events.filter(e => e.project === sym);
  const tweets = DATA.tweets.filter(t => t.project === sym);
  
  document.getElementById('detail').innerHTML = `
    <div class="detail-header">
      <h2>${{p.name}} (${{p.symbol}})</h2>
      <div class="price-big ${{cls}}">$${{p.price?.toFixed(p.price>100?2:4)}} <span style="font-size:16px">(${{chg>=0?'+':''}}${{chg.toFixed(2)}}% 24h)</span></div>
      <div style="color:#6b7280">市值 $${{mcapB}}B | 7d: ${{p.chg7d?.toFixed(1)}}% | 30d: ${{p.chg30d?.toFixed(1)}}%</div>
    </div>
    
    <div class="grid">
      <div class="card"><div class="label">ATH</div><div class="value">$${{p.ath?.toFixed(2)}}</div></div>
      <div class="card"><div class="label">距ATH</div><div class="value ${{parseFloat(athPct)<-50?'down':''}}">${{athPct}}%</div></div>
      <div class="card"><div class="label">24h成交量</div><div class="value">$${{p.vol?(p.vol/1e6).toFixed(0)+'M':'N/A'}}</div></div>
      <div class="card"><div class="label">FDV</div><div class="value">$${{p.fdv?(p.fdv/1e9).toFixed(1)+'B':'N/A'}}</div></div>
      <div class="card"><div class="label">流通量</div><div class="value">${{p.circ?(p.circ/1e6).toFixed(1)+'M':'N/A'}}</div></div>
      <div class="card"><div class="label">事件/推文</div><div class="value">${{events.length}} / ${{tweets.length}}</div></div>
    </div>
    
    <div class="section-title">关键事件时间线 (${{events.length}})</div>
    ${{events.length ? events.map(e => `<div class="event-item">
      <div class="date">${{e.event_date}} | ${{e.event_type}}</div>
      <div style="margin-top:4px; font-weight:600">${{e.title}}</div>
      <div style="color:#9ca3af; margin-top:2px">${{e.description}}</div>
    </div>`).join('') : '<div style="color:#6b7280">暂无事件记录</div>'}}
    
    <div class="section-title">Twitter推文 (${{tweets.length}})</div>
    ${{tweets.length ? tweets.map(t => `<div class="tweet-item">
      <div class="author">@${{t.author_handle}}</div>
      <div class="text">${{t.text}}</div>
      <div class="meta">❤️ ${{t.likes}} | 🔁 ${{t.retweets}} | ${{t.created_at}}</div>
    </div>`).join('') : '<div style="color:#6b7280">暂无推文记录，待抓取</div>'}}
  `;
}}

document.getElementById('search').addEventListener('input', renderList);
document.querySelectorAll('.filter-btns button').forEach(b => {{
  b.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btns button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    currentFilter = b.dataset.f;
    renderList();
  }});
}});

renderList();
showDetail('BTC');
</script>
</body>
</html>'''

out = os.path.join(BASE, "投研工作台.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"HTML written to {out}")
