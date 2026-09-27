# claude_trading 投研控制台

全栈加密货币量化投研控制台：FastAPI 后端（复用 `src/` 既有分析模块 + 读取本地 `daily_scan` 数据）+ React 前端（Vite + MUI + ECharts 深色科技风）。

> 视觉与交互为深色科技风，涨跌配色遵循国内惯例：**涨红 `#f6465d` / 跌绿 `#2ebd85`**。

## 目录结构

```
console/
├── backend/                     # FastAPI 后端
│   ├── main.py                  # 应用入口：CORS / 路由挂载 / 全局异常→信封
│   ├── core/
│   │   ├── config.py            # CORS、雷达权重、抓取超时等运行期配置
│   │   ├── envelope.py          # 统一响应信封 {code,message,data}
│   │   └── paths.py             # PROJECT_ROOT 注入 sys.path + 扫描日期解析
│   ├── data/
│   │   ├── loader.py            # daily_scan JSON 读取层（缺失/非法入参安全兜底）
│   │   └── schemas.py           # Pydantic 响应模型
│   ├── services/                # market / opportunity / token / chain / score / compare / macro / web_research
│   ├── routers/                 # meta / market / tokens / opportunity / compare / chain / scores / macro / research
│   ├── tests/                   # pytest（27 例）
│   ├── requirements.txt
│   └── run.sh
└── frontend/                    # Vite + React
    ├── src/
    │   ├── api/                 # axios 信封解包 + 端点常量
    │   ├── types/               # TS 类型（与后端 Pydantic 对应）
    │   ├── store/               # 全局状态（仅数据日期 date，持久化 localStorage）
    │   ├── layout/              # AppLayout + NavBar（导航 + 日期选择 + 底部强制免责声明）
    │   ├── components/          # common（Card/Loading/EmptyState/ErrorBoundary/PageHeader/RiskDisclaimer）+ charts（EChart/Radar/Bar/Kpi/HeatMap）
    │   └── pages/               # 6 个面板
    ├── vite.config.ts
    └── package.json
```

## 启动

### 后端

```bash
cd console/backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
# 或： bash run.sh
```

> 后端入口会把「项目根」(`claude_trading`) 注入 `sys.path`，从而 `import src` 复用既有算法，不在控制台重写核心逻辑。

### 前端

```bash
cd console/frontend
npm install
npm run dev          # Vite 默认 5173，/api 代理到 http://localhost:8000
```

打开 http://localhost:5173 即可访问 6 个面板：市场总览、百倍币雷达、币种档案、竞品对比、链上分析、评分与建议。

### 测试与构建

```bash
cd console/backend  && python -m pytest tests -q     # 27 passed
cd console/frontend && npm run typecheck && npm run build
```

## API 约定

- 统一响应信封 `{code, message, data}`；`code=0` 成功；数据缺失/分析失败返回 `data=空结构 + message`（HTTP 仍 200，**绝不 500**）。
- 日期参数 `?date=YYYY-MM-DD`；缺省或 `latest` → `data/reports/daily_scan/` 下字典序最大且含 `summary.json` 的目录（当前真实数据最新为 `2026-08-26`，共 9 个可用日期）。
  显式日期**不做存在性校验**（原样传递），非法或不存在时按「无数据」返回空结构，不会抛异常。
- 未匹配到任何路由时由框架返回 HTTP 404（`{"detail":"Not Found"}`），属预期的框架级行为，不套信封。
- 颜色（国内红涨绿跌）：涨 `#f6465d`、跌 `#2ebd85`、主蓝 `#58a6ff`、紫 `#a371f7`、背景 `#0d1117`、面板 `#161b22`、副文字 `#8b949e`。
  组件内禁止写裸 hex，一律引用 `src/theme.ts` 的 `COLORS`（唯一例外：`index.css` 的基础样式，CSS 无法读取 TS 常量）。
- 百倍币雷达启发式权重（初值，可调，`core/config.RADAR_WEIGHTS`）：`mcapScale 0.25 / growth 0.25 / narrative 0.20 / community 0.15 / onchain 0.15`。

## 端点一览（10 个）

| # | 方法 | 路径 | 入参 | data 主体 | 数据来源 |
|---|------|------|------|-----------|----------|
| E1 | GET | `/api/health` | — | `{status,version,dataDate}` | 本地（运维探活） |
| E2 | GET | `/api/meta` | — | `{date,scanTime,deepTotal,lightTotal,coinCnt,availableDates,weights}` | 本地 |
| E3 | GET | `/api/market/overview` | `?date=` | `{meta,kpi,distribution,gainers,losers,topByMcap,sectors}` | 本地 |
| E4 | GET | `/api/tokens/{id}` | `?date=` | `{basic,ath,athChg,narrative,social,news}` | 本地（离线基线） |
| E5 | GET | `/api/opportunity/radar` | `?date=&mcapMax=&sort=` | `{meta,rankings}` | 本地（启发式） |
| E6 | POST | `/api/comparison` | body `["btc","eth",...]`（2–5 个） | `{projects,matrix,winner,summary}` | `src.analysis.comparison`（触网） |
| E7 | GET | `/api/onchain` | `?chain=&query=&demo=` | `{chain,address,dims,total,decision,risk,position,triggers,missing,flags,disclaimer}` | `src.chain.orchestrator`（触网 / demo 离线） |
| E8 | GET | `/api/score/{id}` | — | `{coinId,scores,totalScore,rating,recommendation,riskLevel,advice}` | `src.analysis.scorer`+`advice`（触网） |
| E9 | GET | `/api/macro/btc-dominance` | — | `{currentDominance,trend,marketPhase,altcoinSeason,recommendation}` | `src.analysis.btc_dominance`（触网） |
| E10 | POST | `/api/tokens/{id}/research` | 无 body | `WebResearchResponse` | `src.research.web_research`（触网，25s 超时兜底） |

> 早期设计中的 `/api/sectors`（数据已在 overview.sectors 内）与 `/api/tokens` 列表端点（前端无消费者）已移除。

## 实测响应耗时（本机、受限网络）

面板首屏用的是纯本地点（< 1s）；分析类端点由用户点击触发，**耗时差异极大**，前端已按端点分别设置超时预算（`api/client.ts`）：

| 端点 | 实测 | 前端超时 |
|------|------|----------|
| overview / meta / tokens / radar | 0.01 – 0.2s | 60s |
| macro 冷启动 / 二次命中缓存 | 2.2s / 0.03s | 60s |
| onchain（真实链上地址） | ≈ 23s | 300s |
| score（单币 7 维） | ≈ 30s | 300s |
| comparison（2 币） | ≈ 149s | 300s |
| research | 25s 后按设计返回 503 兜底 | 60s |

> 分析类端点的耗时由 `src/` 内部对每个维度各发一轮网络请求（受限网络下带重试）决定，控制台不施加更短超时——否则会把「后端已成功」的请求在客户端判为失败。

## 运行时缓存

`src/data/cache.py` 的 `DataCache` 会在**当前工作目录**下建 `data/cache`。从 `console/backend` 启动后端时，抓取到的原始响应（GitHub commits/PRs、价格、链上统计等，单次分析可达数 MB）落在 `console/backend/data/cache/`，已在 `console/.gitignore` 中忽略——**请勿提交**。

缓存有效期由 `src` 决定（多数 24h）。这也是「重复调用同一评分/占比接口会明显变快」的原因（如 BTC 占比冷启动 2.2s → 命中缓存 0.03s）。

## 免责声明

前端每个页面底部均强制展示：「风险提示：以上仅为基于公开数据的整理，不构成任何投资建议」。评分/链上/宏观等涉及投资参考处另附各自 `disclaimer`（来自 `src/analysis/advice.DISCLAIMER` 等常量）。
