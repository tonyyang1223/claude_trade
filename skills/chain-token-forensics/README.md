# chain-token-forensics 技能

可复用的链上代币取证分析技能：`链 + 地址/符号` → 8 维评分 + 决策护栏 + 双格式报告。
对应设计：`docs/chain_token_analysis/skill_design.md`（契约 / DAG / 配置 / 迁移全在此）。

## 目录
```
skills/chain-token-forensics/
  SKILL.md     技能声明与调用协议（agent 一键加载）
  README.md    本说明
```

## 引擎入口
| 入口 | 用法 | 场景 |
|------|------|------|
| 仓库 CLI | `python scripts/chain/analyze_token.py --chain <链> --address <0x…> --format html,md,json` | 开发/本仓库 |
| 稳定 API | `from chain_engine import analyze, render`（`pip install .` 后任意项目可用） | 跨项目脚本 |
| 控制台命令 | `chain-forensic --chain bnb --address …`（安装后注册） | 一键 |
| 策略覆盖 | `--config config/chain/meme_strict.yaml` | 调权重/护栏/阈值 |

## 安装（跨项目复用）
```bash
cd <claude_trading 仓库>
python -m pip install .          # 打包 src/chain + chain_engine 为可安装引擎
# 之后任意目录:
chain-forensic --chain bnb --address 0x9212cf1f9f4a9c69bb010146ba5b0725169d4444 --format md,html
```

> 注：Windows 沙箱环境 wheel 构建的回收站删除可能受阻（SAFE_DELETE_FAIL_CLOSED），
> 属环境限制而非配置问题；在普通终端 / CI 执行即可。

## 配置
- `config/chain/default.yaml`：全量默认（与代码内嵌一致，文档化用途）
- `config/chain/meme_strict.yaml`：示例覆盖（更保守护栏 + Meme 权重调整）
- 规则：类别权重必须提供完整 8 维且和为 1（加载期校验）；decision.bands 覆盖需全量

## 测试
```bash
python -m pytest tests/chain -q        # 38 项：配置契约/红旗 schema/决策护栏/golden/渲染/GoPlus 解析
python -m pytest tests/chain -q -k network   # live 冒烟（标记 network，需联网）
```
