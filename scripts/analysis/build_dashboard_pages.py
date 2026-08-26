# -*- coding: utf-8 -*-
"""build_dashboard_pages.py — 生成多个静态 HTML 看板页面

输出到 reports/dashboard/:
  - index.html    导航首页 + 各维度速览
  - market.html   市场总览
  - sectors.html  板块分析
  - deep.html     币种深度研究
  - funds.html    资金与生态

每页独立, ECharts 用 CDN, 数据用 fetch 加载同目录 JSON。
所有页面用普通字符串 + .replace() 占位符, 避免 f-string 与 JS 大括号冲突。
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "reports", "dashboard")
ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"

CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#e6edf3;font-family:"Segoe UI","Microsoft YaHei",sans-serif;padding:20px;min-height:100vh}
a{text-decoration:none;color:inherit}
.nav{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;border-bottom:1px solid #30363d;padding-bottom:14px}
.nav a{padding:8px 16px;border:1px solid #30363d;border-radius:8px;font-size:14px;color:#8b949e;transition:.15s}
.nav a:hover{color:#e6edf3;border-color:#58a6ff}
.nav a.active{background:#1f6feb33;color:#58a6ff;border-color:#58a6ff}
h1{font-size:22px;margin-bottom:4px}
.sub{color:#8b949e;font-size:12px;margin-bottom:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 16px}
.card .label{color:#8b949e;font-size:12px;margin-bottom:6px}
.card .val{font-size:22px;font-weight:600}
.grid{display:grid;gap:16px;margin-bottom:16px}
.g2{grid-template-columns:repeat(auto-fit,minmax(480px,1fr))}
.chart{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px}
.chart h3{font-size:14px;color:#8b949e;margin-bottom:8px;font-weight:500}
.chart .box{height:360px}
.chart .box.tall{height:440px}
table{width:100%;border-collapse:collapse;font-size:13px;background:#161b22}
th{color:#8b949e;text-align:right;padding:8px 10px;border-bottom:1px solid #30363d;cursor:pointer;user-select:none;white-space:nowrap;position:sticky;top:0;background:#161b22}
th:first-child,td:first-child{text-align:left}
th:hover{color:#58a6ff}
td{padding:7px 10px;text-align:right;border-bottom:1px solid #21262d;white-space:nowrap}
tr:hover td{background:#1c2129}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;background:#30363d;color:#8b949e}
.up{color:#f6465d}.down{color:#2ebd85}
.loading{color:#8b949e;text-align:center;padding:40px}
.err{background:#f6465d;color:#fff;padding:12px;border-radius:8px;margin-bottom:12px}
.src-note{color:#8b949e;font-size:11px;margin-top:24px;border-top:1px solid #30363d;padding-top:10px;line-height:1.8}
.tbl-wrap{max-height:600px;overflow:auto}
.badge{font-size:11px;padding:2px 8px;border-radius:4px;background:#1f6feb33;color:#58a6ff;margin-left:8px}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px}"""

NAV = """<div class="nav">
<a href="index.html">首页</a>
<a href="market.html">市场总览</a>
<a href="sectors.html">板块分析</a>
<a href="deep.html">深度研究</a>
<a href="funds.html">资金与生态</a>
</div>"""

JSU = """const UP='#f6465d',DOWN='#2ebd85',TXT='#e6edf3',SUB='#8b949e',SPLIT='#30363d';
const charts=[];
function mk(id,opt){const el=document.getElementById(id);if(!el)return;const c=echarts.init(el);
opt.tooltip=opt.tooltip||{backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}};
opt.grid=Object.assign({left:50,right:30,top:30,bottom:50},opt.grid||{});
c.setOption(Object.assign({backgroundColor:'transparent',textStyle:{color:TXT}},opt));
charts.push(c);return c;}
window.addEventListener('resize',()=>charts.forEach(c=>c.resize()));
function fm(v){return v==null?'-':(Math.abs(v)>=1e12?(v/1e12).toFixed(2)+'T':Math.abs(v)>=1e9?(v/1e9).toFixed(1)+'B':Math.abs(v)>=1e6?(v/1e6).toFixed(1)+'M':v.toLocaleString());}
function fp(v){return v==null?'-':'$'+(Math.abs(v)>=1?v.toLocaleString(undefined,{maximumFractionDigits:Math.abs(v)>=100?0:4}):v.toFixed(6));}
function pct(v){return v==null?'-':(v>0?'+':'')+v.toFixed(2)+'%';}
function cls(v){return v>0?'up':(v<0?'down':'');}
function showErr(msg){document.body.insertAdjacentHTML('afterbegin','<div class="err">'+msg+'</div>');}
function loadJSON(url){return fetch(url).then(r=>{if(!r.ok)throw new Error(url+' '+r.status);return r.json();}).catch(e=>{showErr('加载 '+url+' 失败: '+e.message);throw e;});}
function hbar(id,items,color,valfmt){mk(id,{grid:{left:80,right:70},xAxis:{type:'value',axisLabel:{color:SUB},splitLine:{lineStyle:{color:'#21262d'}}},
yAxis:{type:'category',data:items.map(i=>i.sym).reverse(),axisLabel:{color:TXT}},
series:[{type:'bar',barWidth:'60%',data:items.map(i=>({value:i.v,itemStyle:{color:color}})).reverse(),
label:{show:true,position:'right',color:SUB,fontSize:10,formatter:p=>valfmt(p.value)}}]});}
function kpiCards(items){document.getElementById('kpis').innerHTML=items.map(x=>'<div class="card"><div class="label">'+x.l+'</div><div class="val '+(x.c||'')+'">'+x.v+'</div></div>').join('');}"""


def page_head(title, date, sub, active):
    nav = NAV
    if active:
        nav = nav.replace(f'href="{active}.html"', f'href="{active}.html" class="active"')
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<script src="{ECHARTS_CDN}"></script>
<style>{CSS}</style>
</head><body>
{nav}
<h1>{title} <span class="badge">{date}</span></h1>
<div class="sub">{sub}</div>"""


def page_foot(note=""):
    return f'<div class="src-note">{note}</div></body></html>' if note else '</body></html>'


# ============ 各页面 (用普通字符串, JS 大括号单写, 占位符替换) ============

INDEX_BODY = """<div class="kpis" id="kpis"><div class="loading">加载中...</div></div>
<div class="grid g2">
<div class="chart"><h3>市场速览 · 24h 涨跌分布</h3><div class="box" id="c_dist"></div></div>
<div class="chart"><h3>市值 TOP10</h3><div class="box" id="c_mcap"></div></div>
</div>
<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">
<div class="chart"><h3>板块分布</h3><div class="box" id="c_cat" style="height:320px"></div></div>
<div class="chart"><h3>稳定币供应量</h3><div class="box" id="c_stable" style="height:320px"></div></div>
<div class="chart"><h3>主流币两日价格变动</h3><div class="box" id="c_cmp" style="height:320px"></div></div>
</div>
<script>
__JSU__
Promise.all([loadJSON('index_data.json'),loadJSON('market.json'),loadJSON('sectors.json'),loadJSON('funds.json')]).then(([idx,mkt,sec,funds])=>{
kpiCards([
{l:'总市值',v:'$'+fm(idx.kpi.totalMcap)},
{l:'监控币种',v:idx.kpi.coinCnt},
{l:'平均 24h 涨跌',v:pct(idx.kpi.avgChg),c:cls(idx.kpi.avgChg)},
{l:'上涨 / 下跌',v:'<span class="up">'+idx.kpi.upCnt+'</span> / <span class="down">'+idx.kpi.downCnt+'</span>'},
{l:'深度研究币种',v:idx.kpi.deepStudied},
]);
mk('c_dist',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
xAxis:{type:'category',data:mkt.dist.labels,axisLabel:{color:SUB,rotate:45,fontSize:10}},
yAxis:{type:'value',name:'币数',nameTextStyle:{color:SUB},axisLabel:{color:SUB},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',barCategoryGap:'20%',data:mkt.dist.values.map((v,i)=>({value:v,itemStyle:{color:mkt.dist.labels[i].charAt(0)==='+'?UP:(mkt.dist.labels[i].charAt(0)==='0'?'#8b949e':DOWN)}}))}]});
const tm=mkt.topMcap.slice(0,10);
mk('c_mcap',{grid:{left:70,right:60},xAxis:{type:'value',axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
yAxis:{type:'category',data:tm.map(c=>c.sym).reverse(),axisLabel:{color:TXT}},
series:[{type:'bar',barWidth:'60%',data:tm.map(c=>({value:c.mcap,itemStyle:{color:'#58a6ff'}})).reverse(),
label:{show:true,position:'right',color:SUB,fontSize:10,formatter:p=>'$'+fm(p.value)}}]});
mk('c_cat',{tooltip:{trigger:'item',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
legend:{type:'scroll',orient:'vertical',right:5,top:10,bottom:10,textStyle:{color:SUB},pageTextStyle:{color:SUB}},
series:[{type:'pie',radius:['40%','70%'],center:['40%','50%'],data:sec.cats.map(c=>({name:c.cat,value:c.count})),
label:{color:SUB},itemStyle:{borderColor:'#0d1117',borderWidth:2}}]});
if(funds.stablecoins.length){
mk('c_stable',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT},formatter:p=>p[0].name+': $'+fm(p[0].value)},
xAxis:{type:'category',data:funds.stablecoins.slice(0,12).map(s=>s.symbol),axisLabel:{color:TXT,rotate:30,fontSize:10}},
yAxis:{type:'value',axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',data:funds.stablecoins.slice(0,12).map(s=>s.total_supply),itemStyle:{color:'#58a6ff'},barWidth:'50%',
label:{show:true,position:'top',color:SUB,fontSize:9,formatter:p=>'$'+fm(p.value)}}]});
}else document.getElementById('c_stable').innerHTML='<div class="loading">无稳定币数据</div>';
if(funds.dayCmp.length){
mk('c_cmp',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
xAxis:{type:'category',data:funds.dayCmp.map(x=>x.sym),axisLabel:{color:TXT,fontSize:10}},
yAxis:{type:'value',axisLabel:{color:SUB,formatter:v=>'$'+fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',barWidth:'55%',data:funds.dayCmp.map(x=>({value:x.cur,itemStyle:{color:x.pct>=0?UP:DOWN}})),
label:{show:true,position:'top',color:SUB,fontSize:9,formatter:p=>pct(funds.dayCmp[p.dataIndex].pct)}}]});
}else document.getElementById('c_cmp').innerHTML='<div class="loading">无对比数据</div>';
}).catch(e=>console.error(e));
</script>"""

MARKET_BODY = """<div class="kpis" id="kpis"><div class="loading">加载中...</div></div>
<div class="grid g2">
<div class="chart"><h3>24h 涨跌分布</h3><div class="box tall" id="c_dist"></div></div>
<div class="chart"><h3>24h 涨跌 vs 7d 涨跌 (成交额 Top120, 气泡=成交额)</h3><div class="box tall" id="c_scatter"></div></div>
<div class="chart"><h3>24h 涨幅榜 TOP15</h3><div class="box tall" id="c_gain"></div></div>
<div class="chart"><h3>24h 跌幅榜 TOP15</h3><div class="box tall" id="c_lose"></div></div>
<div class="chart"><h3>市值 TOP15</h3><div class="box tall" id="c_mcap"></div></div>
<div class="chart"><h3>24h 成交额 TOP15</h3><div class="box tall" id="c_vol"></div></div>
</div>
<script>
__JSU__
loadJSON('market.json').then(d=>{
kpiCards([
{l:'监控币种数',v:d.coinCnt},
{l:'上涨 / 下跌',v:'<span class="up">'+__UPCNT__+'</span> / <span class="down">'+__DOWNCNT__+'</span>'},
{l:'平均 24h 涨跌',v:pct(__AVGCHG__),c:cls(__AVGCHG__)},
{l:'总市值',v:'$'+fm(__TOTALMCAP__)},
]);
mk('c_dist',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
xAxis:{type:'category',data:d.dist.labels,axisLabel:{color:SUB,rotate:45,fontSize:10}},
yAxis:{type:'value',name:'币数',nameTextStyle:{color:SUB},axisLabel:{color:SUB},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',barCategoryGap:'20%',data:d.dist.values.map((v,i)=>({value:v,itemStyle:{color:d.dist.labels[i].charAt(0)==='+'?UP:(d.dist.labels[i].charAt(0)==='0'?'#8b949e':DOWN)}}))}]});
const sc=d.scatter;const vmax=Math.max(...sc.map(c=>c.vol||0))||1;
mk('c_scatter',{tooltip:{trigger:'item',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT},formatter:p=>p.data.name+'<br>24h: '+pct(p.data.value[0])+'<br>7d: '+pct(p.data.value[1])+'<br>成交额: $'+fm(p.data.value[2])},
grid:{left:50,right:120},
xAxis:{type:'value',name:'24h %',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:'{value}%'},splitLine:{lineStyle:{color:'#21262d'}}},
yAxis:{type:'value',name:'7d %',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:'{value}%'},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'scatter',data:sc.map(c=>({name:c.sym,value:[c.chg24,c.chg7d,c.vol]})),
symbolSize:v=>8+30*Math.sqrt((v[2]||0)/vmax),itemStyle:{color:p=>p.data.value[0]>=0?UP:DOWN,opacity:.75},
label:{show:true,formatter:p=>p.data.name,position:'top',color:SUB,fontSize:9},labelLayout:{hideOverlap:true}}]});
hbar('c_gain',d.gainers,UP,v=>pct(v));
hbar('c_lose',d.losers,DOWN,v=>pct(v));
hbar('c_mcap',d.topMcap,'#58a6ff',v=>'$'+fm(v));
hbar('c_vol',d.topVol,'#e2b03',v=>'$'+fm(v));
}).catch(e=>console.error(e));
</script>"""

SECTORS_BODY = """<div class="grid g2">
<div class="chart"><h3>各板块币数 与 平均24h涨跌 <span id="catDay"></span></h3><div class="box tall" id="c_cat"></div></div>
<div class="chart"><h3>各板块总市值</h3><div class="box tall" id="c_catmcap"></div></div>
</div>
<div class="chart"><h3>板块代表币 (各板块市值前3)</h3><div class="tbl-wrap"><table id="t_cat"><tr><td class="loading">加载中...</td></tr></table></div></div>
<script>
__JSU__
loadJSON('sectors.json').then(d=>{
document.getElementById('catDay').textContent='(数据日: '+d.catDay+')';
mk('c_cat',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
xAxis:{type:'category',data:d.cats.map(c=>c.cat),axisLabel:{color:SUB,rotate:20}},
yAxis:[{type:'value',name:'币数',nameTextStyle:{color:SUB},axisLabel:{color:SUB},splitLine:{lineStyle:{color:'#21262d'}}},
{type:'value',name:'平均涨跌%',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:'{value}%'},splitLine:{show:false}}],
series:[{type:'bar',data:d.cats.map(c=>c.count),itemStyle:{color:'#58a6ff'},barWidth:'45%'},
{type:'line',yAxisIndex:1,data:d.cats.map(c=>c.avg_chg),itemStyle:{color:'#e2b03'},lineStyle:{color:'#e2b03'},
symbolSize:6,label:{show:true,color:'#e2b03',fontSize:10,formatter:p=>pct(p.value)}}]});
mk('c_catmcap',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
xAxis:{type:'category',data:d.cats.map(c=>c.cat),axisLabel:{color:SUB,rotate:20}},
yAxis:{type:'value',axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
series:[{type:'bar',data:d.cats.map(c=>c.mcap),itemStyle:{color:'#a371f7'},barWidth:'45%',
label:{show:true,position:'top',color:SUB,fontSize:10,formatter:p=>'$'+fm(p.value)}}]});
const t=document.getElementById('t_cat');
t.innerHTML='<tr><th>板块</th><th>币种</th><th>排名</th><th>价格</th><th>市值</th><th>24h涨跌</th></tr>'+
d.catTop.map(c=>'<tr><td><span class="tag">'+c.cat+'</span></td><td>'+c.name+' ('+c.sym+')</td><td>'+(c.rank||'-')+'</td><td>'+fp(c.price)+'</td><td>'+(c.mcap?'$'+fm(c.mcap):'-')+'</td><td class="'+cls(c.chg24)+'">'+pct(c.chg24)+'</td></tr>').join('');
}).catch(e=>console.error(e));
</script>"""

DEEP_BODY = """<div class="grid g2">
<div class="chart"><h3>社区热度榜 TOP15 (社交提及数)</h3><div class="box tall" id="c_social"></div></div>
<div class="chart"><h3>Reddit 订阅数 TOP15</h3><div class="box tall" id="c_reddit"></div></div>
</div>
<div class="chart"><h3>深度研究币种明细 (可点击表头排序 · __DEEPCNT__ 币)</h3><div class="tbl-wrap"><table id="t_deep"><tr><td class="loading">加载中...</td></tr></table></div></div>
<script>
__JSU__
loadJSON('deep.json').then(d=>{
const byM=[...d.deep].sort((a,b)=>(b.mentions||0)-(a.mentions||0)).slice(0,15).filter(c=>c.mentions>0);
if(byM.length)hbar('c_social',byM.map(c=>({sym:c.sym,v:c.mentions})),'#f0883e',v=>v+'次');
else document.getElementById('c_social').innerHTML='<div class="loading">暂无社交提及数据</div>';
const byR=[...d.deep].sort((a,b)=>(b.reddit_sub||0)-(a.reddit_sub||0)).slice(0,15).filter(c=>c.reddit_sub>0);
if(byR.length)hbar('c_reddit',byR.map(c=>({sym:c.sym,v:c.reddit_sub})),'#ff7b72',v=>v.toLocaleString());
else document.getElementById('c_reddit').innerHTML='<div class="loading">暂无 Reddit 数据</div>';
const cols=[['rank','排名',1],['name','币种',0],['price','价格',1],['mcap','市值',1],['chg24','24h',1],
['mentions','提及',1],['upvotes','点赞',1],['reddit_sub','Reddit订阅',1],['cscore','社区分',1],['news','新闻',1],['bili','B站',1],['date','研究日',0]];
function render(rows){const t=document.getElementById('t_deep');
t.innerHTML='<tr>'+cols.map(c=>'<th data-k="'+c[0]+'" data-n="'+c[2]+'">'+c[1]+'</th>').join('')+'</tr>'+
rows.map(r=>'<tr><td>'+(r.rank||'-')+'</td><td>'+r.name+' <b style="color:#8b949e">'+r.sym+'</b></td><td>'+fp(r.price)+'</td><td>'+(r.mcap?'$'+fm(r.mcap):'-')+'</td><td class="'+cls(r.chg24)+'">'+pct(r.chg24)+'</td><td>'+(r.mentions||0)+'</td><td>'+(r.upvotes||0).toLocaleString()+'</td><td>'+(r.reddit_sub||0).toLocaleString()+'</td><td>'+(r.cscore==null?'-':r.cscore)+'</td><td>'+(r.news||0)+'</td><td>'+(r.bili||0)+'</td><td><span class="tag">'+(r.date||'').slice(5)+'</span></td></tr>').join('');
t.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k,num=th.dataset.n==='1';const asc=th.dataset.asc!=='1';
t.querySelectorAll('th').forEach(x=>x.dataset.asc='0');th.dataset.asc=asc?'1':'0';
const arr=[...d.deep].sort((a,b)=>{const av=a[k],bv=b[k];if(num)return ((bv||0)-(av||0))*(asc?-1:1);return String(bv).localeCompare(String(av))*(asc?-1:1);});
render(arr);});}
render(d.deep);
}).catch(e=>console.error(e));
</script>"""

FUNDS_BODY = """<div class="kpis" id="kpis"><div class="loading">加载中...</div></div>
<div class="grid g2">
<div class="chart"><h3>稳定币供应量 与 24h 增减</h3><div class="box tall" id="c_stable"></div></div>
<div class="chart"><h3>主流币价格两日对比</h3><div class="box tall" id="c_cmp"></div></div>
</div>
<script>
__JSU__
loadJSON('funds.json').then(d=>{
kpiCards([
{l:'Ethereum TVL',v:d.ethTvl?'$'+fm(d.ethTvl):'-'},
{l:'USDT 供应量',v:d.stablecoins.length?'$'+fm(d.stablecoins[0].total_supply):'-'},
{l:'BTC 仓库 Stars',v:d.github?d.github.stars.toLocaleString():'-'},
{l:'深度研究队列剩余',v:d.queueLen},
{l:'轻量监控总数',v:d.lightTotal},
]);
if(d.stablecoins.length){
const s=d.stablecoins;
mk('c_stable',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
xAxis:{type:'category',data:s.map(x=>x.symbol),axisLabel:{color:TXT,rotate:30,fontSize:10}},
yAxis:[{type:'value',name:'供应量',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{lineStyle:{color:'#21262d'}}},
{type:'value',name:'24h增减',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:v=>fm(v)},splitLine:{show:false}}],
series:[{type:'bar',data:s.map(x=>x.total_supply),itemStyle:{color:'#58a6ff'},barWidth:'45%',
label:{show:true,position:'top',color:SUB,fontSize:9,formatter:p=>'$'+fm(p.value)}},
{type:'scatter',yAxisIndex:1,data:s.map(x=>x.mint_change_24h),symbolSize:12,
itemStyle:{color:p=>p.value>=0?UP:DOWN},
label:{show:true,position:'right',color:SUB,fontSize:9,formatter:p=>(p.value>=0?'+':'')+'$'+fm(p.value)}}]});
}else document.getElementById('c_stable').innerHTML='<div class="loading">无稳定币数据</div>';
if(d.dayCmp.length){
mk('c_cmp',{tooltip:{trigger:'axis',backgroundColor:'#161b22',borderColor:SPLIT,textStyle:{color:TXT}},
legend:{data:[{name:'当前价'},{name:'前一日'}],textStyle:{color:SUB},top:5},
xAxis:{type:'category',data:d.dayCmp.map(x=>x.sym),axisLabel:{color:TXT}},
yAxis:{type:'value',name:'价格',nameTextStyle:{color:SUB},axisLabel:{color:SUB,formatter:v=>'$'+fm(v)},splitLine:{lineStyle:{color:'#21262d'}}}},
series:[{type:'bar',name:'当前价',barWidth:'50%',data:d.dayCmp.map(x=>({value:x.cur,itemStyle:{color:x.pct>=0?UP:DOWN}})),
label:{show:true,position:'top',color:SUB,fontSize:10,formatter:p=>'$'+fm(p.value)}},
{type:'scatter',name:'前一日',data:d.dayCmp.map(x=>x.prev),symbol:'diamond',symbolSize:10,itemStyle:{color:'#8b949e'}}]});
}else document.getElementById('c_cmp').innerHTML='<div class="loading">无对比数据</div>';
}).catch(e=>console.error(e));
</script>"""


def main():
    # 内嵌所有数据 (避免 fetch 跨路径问题)
    def load(name):
        with open(os.path.join(OUT_DIR, name), encoding="utf-8") as f:
            return f.read()

    meta = json.load(open(os.path.join(OUT_DIR, "meta.json"), encoding="utf-8"))
    kpi = json.load(open(os.path.join(OUT_DIR, "kpi.json"), encoding="utf-8"))
    date = meta["date"]
    deep_data = json.load(open(os.path.join(OUT_DIR, "deep.json"), encoding="utf-8"))
    deepcnt = len(deep_data["deep"])

    # 各页面所需的数据块 (内嵌, 替换 fetch)
    embed = {
        "INDEX_DATA": load("index_data.json"),
        "MARKET": load("market.json"),
        "SECTORS": load("sectors.json"),
        "DEEP": load("deep.json"),
        "FUNDS": load("funds.json"),
    }

    pages = [
        ("index.html", page_head("加密货币看板", date, "数据来源: 服务器定时采集 · 多维度可视化", "index") + INDEX_BODY + page_foot("首页展示各维度速览, 详细分析见各子页面。")),
        ("market.html", page_head("市场总览", date, "24h 涨跌分布 · 涨跌幅榜 · 市值/成交额排行 · 24h vs 7d 散点", "market") + MARKET_BODY + page_foot()),
        ("sectors.html", page_head("板块分析", date, "按板块聚合的币数 · 平均涨跌 · 总市值 · 代表币", "sectors") + SECTORS_BODY + page_foot("板块分类基于深度研究 category 字段, 自动选取近7天内覆盖币数最多的一天。")),
        ("deep.html", page_head("币种深度研究", date, "深度研究明细 · 社区热度榜 · Reddit 订阅榜 · 可排序表格", "deep") + DEEP_BODY + page_foot("服务器每10分钟深度研究1个币, 覆盖市场/资金费率/持仓量/稳定币流向/社交/Reddit/新闻/B站等12维度。")),
        ("funds.html", page_head("资金与生态", date, "稳定币供应量与24h增减 · Ethereum TVL · GitHub 仓库 · 主流币两日对比", "funds") + FUNDS_BODY + page_foot("稳定币来自深度研究 stablecoin_flows; TVL 来自 DefiLlama; GitHub 来自 bitcoin/bitcoin 仓库。")),
    ]
    for name, content in pages:
        content = content.replace("__JSU__", JSU)
        # 替换 KPI 占位符 (market.html)
        content = content.replace("__UPCNT__", str(kpi["upCnt"]))
        content = content.replace("__DOWNCNT__", str(kpi["downCnt"]))
        content = content.replace("__AVGCHG__", repr(kpi["avgChg"]))
        content = content.replace("__TOTALMCAP__", repr(kpi["totalMcap"]))
        content = content.replace("__DEEPCNT__", str(deepcnt))
        # 内嵌数据: 把 fetch('xxx.json') 替换为内嵌变量
        content = content.replace("loadJSON('index_data.json')", "Promise.resolve(JSON.parse('"+embed["INDEX_DATA"].replace("\\", "\\\\").replace("'", "\\'")+"'))")
        content = content.replace("loadJSON('market.json')", "Promise.resolve(JSON.parse('"+embed["MARKET"].replace("\\", "\\\\").replace("'", "\\'")+"'))")
        content = content.replace("loadJSON('sectors.json')", "Promise.resolve(JSON.parse('"+embed["SECTORS"].replace("\\", "\\\\").replace("'", "\\'")+"'))")
        content = content.replace("loadJSON('deep.json')", "Promise.resolve(JSON.parse('"+embed["DEEP"].replace("\\", "\\\\").replace("'", "\\'")+"'))")
        content = content.replace("loadJSON('funds.json')", "Promise.resolve(JSON.parse('"+embed["FUNDS"].replace("\\", "\\\\").replace("'", "\\'")+"'))")
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  {name}: {os.path.getsize(path)//1024} KB")
    print(f"\n看板页面已生成到 {OUT_DIR}/")
    print("打开 index.html 开始浏览 (需联网加载 ECharts CDN)")


if __name__ == "__main__":
    main()
