# claude_trading 投研控制台

全栈加密货币量化投研控制台：FastAPI 后端（复用 `src/` 既有分析模块 + 读取本地 `daily_scan` / `raw_server` 数据）+ React 前端（Vite + MUI + Tailwind + ECharts 深色科技风）。

## 目录结构

```
console/
├── backend/            # FastAPI 后端
│   ├── main.py         # 应用入口：CORS / 路由挂载 / 全局异常→信封
│   ├── config.py       # CORS、百倍币雷达权重等
│   ├── core/           # paths（项目根注入+最新日期解析）/ envelope / exceptions
│   ├── data/           # loader（daily_scan/parquet 读取）+ schemas（Pydantic）
│   ├── services/       # market / token / opportunity / chain / score / compare / macro / web_research / token_defi
│   ├── routers/        # meta / market / tokens / opportunity / compare / chain / scores / macro / research
│   └── requirements.txt
└── frontend/           # Vite + React
    ├── src/
    │   ├── api/        # axios 信封解包 + 端点
    │   ├── types/      # TS 类型（与后端 Pydantic 对应）
    │   ├── store/      # 全局状态（date / selectedTokens / themeMode）
    │   ├── layout/     # AppLayout + NavBar（顶部导航 + 底部强制免责声明）
    │   ├── components/ # common（玻璃卡片/Loading/Error/Disclaimer/PageHeader）+ charts（EChart/Radar/Bar/Kpi/HeatMap）
    │   └── pages/      # 6 个面板
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

> 后端入口会把「项目根」(`claude_trading`) 注入 `sys.path`，从而 `import src` 复用既有算法，严禁重写核心逻辑。

### 前端

```bash
cd console/frontend
npm install
npm run dev          # Vite 默认 5173，/api 代理到 http://localhost:8000
```

打开 http://localhost:5173 即可访问 6 个面板：市场总览、百倍币雷达、币种档案、竞品对比、链上分析、评分与建议。

## API 约定

- 统一响应信封 `{code, message, data}`；`code=0` 成功；数据缺失/分析失败返回 `data=空结构 + message`（HTTP 仍 200，**绝不 500**）。
- 日期参数 `?date=YYYY-MM-DD`；缺省或 `latest` → `data/reports/daily_scan/` 下字典序最大且含 `summary.json` 的目录（当前真实数据最新为 `2026-08-26`）。
- 颜色（国内红涨绿跌）：涨 `#f6465d`、跌 `#2ebd85`、主蓝 `#58a6ff`、紫 `#a371f7`、背景 `#0d1117`、面板 `#161b22`、副文字 `#8b949e`。
- 百倍币雷达启发式权重（初值，可调，`config.RADAR_WEIGHTS`）：`mcapScale 0.25 / growth 0.25 / narrative 0.20 / community 0.15 / onchain 0.15`。

## 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/meta` | 数据元信息（最新日期/可用日期/权重） |
| GET | `/api/market/overview` | 市场总览（KPI/分布/涨跌榜/市值榜/板块） |
| GET | `/api/sectors` | 板块统计 |
| GET | `/api/tokens` | 币种列表（支持 `q`/`limit`） |
| GET | `/api/tokens/{id}` | 币种档案（离线基线） |
| POST | `/api/tokens/{id}/research` | 实时网页研究（超时 25s，失败保留离线） |
| GET | `/api/opportunity/radar` | 百倍币机会雷达（支持 `mcapMax`/`sort`） |
| POST | `/api/comparison` | 竞品对比（body: 币种 ID 数组） |
| GET | `/api/onchain` | 链上分析（`chain`/`query`，支持 `demo`） |
| GET | `/api/score/{id}` | 综合评分与建议 |
| GET | `/api/macro/btc-dominance` | BTC 占比与市场规模判断 |

## 免责声明

前端每个页面底部均强制展示：「风险提示：以上仅为基于公开数据的整理，不构成任何投资建议」。评分/链上/宏观等涉及投资参考处另附各自 `disclaimer`。
