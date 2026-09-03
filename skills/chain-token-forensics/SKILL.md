---
name: chain-token-forensics
description: >-
  链上代币取证分析技能。用户给出「链（bnb/sol/robinhood）+ 合约地址或符号」、或要求判断
  rug/蜜罐/后门/安全风险时触发。执行 8 维评分（欺诈安全/趋势/动量/流动性健康/情绪/创新/
  类别/社区）+ 决策护栏，输出 HTML/Markdown/JSON 双格式报告与结构化红旗。禁止用于非加密请求。
agent_created: true
---

# 链上代币取证分析（chain-token-forensics）

引擎仓库：`claude_trading`（`src/chain`，设计见 `docs/chain_token_analysis/skill_design.md`）。

## 何时使用
- 用户输入形如「分析 bnb/sol/robinhood 上合约 0x… / 符号 XXX」或询问安全/rug/蜜罐/后门
- 需要对新发代币做欺诈、趋势、技术创新、类别的系统性研判并给出决策

## 前置
1. 引擎可用性（任选其一，在仓库根目录执行）：
   - 仓库内直接调：`python scripts/chain/analyze_token.py …`
   - 已安装包（跨项目）：`chain-forensic …`（`pip install .` 后获得）或
     `python -c "from chain_engine import analyze; …"`
2. 联网要求：分析需访问公共 RPC / DexScreener / GoPlus；离线请用 `--demo`

## 工作流
1. 解析输入 → chain（bnb/sol/robinhood）+ query（地址优先；符号需 DexScreener 覆盖）
2. 执行分析（自动完成：解析→抓取→身份回填→价格校验→分类定权→8维评分→决策护栏）
   - 仓库内：`python scripts/chain/analyze_token.py --chain <链> --address <0x…> --format html,md,json`
   - 可选策略覆盖：`--config config/chain/meme_strict.yaml`（更保守护栏 / 权重）
3. 读取 stdout 摘要：综合分 / 决策 / 仓位 / 红旗 `{level,code,msg}` / 缺失维度
4. 将输出路径回传用户；Markdown 摘要必须保留免责声明

## 输入参数
| 参数 | 说明 |
|------|------|
| --chain | bnb / sol / robinhood（必填）|
| --address / --symbol | 查询（地址优先）|
| --demo | 离线样例（不触网）|
| --config | 策略 YAML（权重/档位/护栏/阈值/词表覆盖）|
| --format | html / md / json / all |
| --rpc | 自定义 RPC（覆盖内置默认端点）|

## 输出契约
- 终端摘要：综合分 0-10、决策、风险、仓位、红旗清单、缺失维度
- 文件：`<sym>.html`（自包含深色报告）、`.md`（对话摘要）、`.json`（结构化 AnalysisResult+Decision，flags 为 `{level,code,msg}`）
- 元数据：`engine_version` / `fetched_at` / `sources_used` 随 JSON 输出

## 验收示例
```
python scripts/chain/analyze_token.py --chain bnb \
  --address 0x9212cf1f9f4a9c69bb010146ba5b0725169d4444 --format md,html,json
```
预期：5.7/10 左右 + 🟡 轻仓观察（合约层干净但 LP/持币与品牌风险需在结论中说明）。

## 注意事项
- 分析 ≠ 投资建议；所有输出必须带免责声明
- 字节码扫描结论可能因库函数内部调用而低估，需 GoPlus/浏览器交叉复核
- LP 锁仓/持币集中度「未知」时护栏自动收紧（只降不升），不要手动放宽
- 情绪维度(sentiment)在无社媒凭证时恒缺失 → 明确告知已排除加权
