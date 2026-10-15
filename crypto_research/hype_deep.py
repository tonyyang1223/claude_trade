import sys
sys.path.insert(0, r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor")
from db import *

init_db()

# HYPE深度事件
events = [
    ("partnership", "Coinbase+Circle各质押50万HYPE", "Coinbase和Circle各质押50万HYPE（约$56M），可被slash，2026年8月26日开始计息，首次支付10月3日", "Hyperliquid Strategies", "", "2026-08-26", "重大机构采用"),
    ("buyback", "协议回购销毁4889万枚", "2024年12月至今累计销毁4889万HYPE（占总量4.89%），价值约$13亿。最近24h销毁34,280枚，均价$95.25", "DiarioBitcoin", "", "2026-09-24", "通缩机制"),
    ("listing", "上线Binance", "9月24日上线Binance，9月25日开放提币。推动ATH $97.96", "e-bitcoin", "", "2026-09-24", "流动性提升"),
    ("tokenomics", "资金费率上限下调", "Hyperliquid计划将永续资金费率上限降至0.5%/小时", "X/@iiam_Akshay", "", "2026-09-28", "结构优化"),
    ("revenue", "2026年9月毛收入$63.9M", "月度收入：9月$63.9M，8月$67.3M，7月$55.1M。Q2季度$169M。年化收入约$6.4-10亿", "Tokenomics.com", "", "2026-09-28", "链上收入第一"),
    ("integration", "Coinbase+Morpho抵押品", "Coinbase用户可直接用HYPE作为抵押品在Morpho借贷", "X/@gandreou007", "", "2026-09-28", "机构渠道"),
    ("integration", "Kraken通过Bitnomial开放永续", "Kraken旗下Payward计划通过Bitnomial向美国客户提供HYPE永续合约", "CryptoNews", "", "2026-09-16", "美国市场准入"),
    ("risk", "巨鲸抛售测试", "约$1亿巨鲸抛售，2006个钱包持仓变化。持有10+ HYPE的钱包减少6.3%", "AMBCrypto", "", "2026-09-28", "短期抛压"),
    ("risk", "$820M代币解锁", "9月6日解锁$820M，但大部分在团队/战略储备，实际抛压有限", "CryptoNews", "", "2026-09-06", "已消化"),
    ("competition", "竞争对手挑战", "Coinbase、Robinhood、Kraken在永续合约市场挑战Hyperliquid", "AInvest", "", "2026-09-20", "竞争加剧"),
    ("inflation", "净通缩-0.04%", "过去90天新增217万枚HYPE（团队/质押奖励），回购销毁225万枚，净通缩", "mrnasdog", "", "2026-09-26", "通缩"),
    ("milestone", "OI创纪录$18B", "Hyperliquid永续合约OI达$18B，超过之前$16.36B纪录", "e-bitcoin", "", "2026-09-24", "需求强劲"),
]

for e in events:
    save_event("HYPE", *e)

# 六维评分
scores = [
    ("叙事", 5, 0.25, "永续DEX龙头，真实收入，机构采用（Coinbase/Circle质押）"),
    ("技术", 5, 0.15, "自研L1链，秒级出块，订单簿DEX，无gas费，HIP-3允许自建市场"),
    ("代币经济", 4, 0.20, "总量10亿固定，4.89%已销毁，净通缩，但FDV/MCap=4.29（流通率仅23%）"),
    ("竞争", 4, 0.10, "永续DEX市占率第一，但Coinbase/Robinhood/Kraken在追赶"),
    ("风险", 3, 0.15, "巨鲸抛售压力，竞争加剧，流通率低导致解锁抛压"),
    ("市场动量", 5, 0.15, "OI $18B创纪录，上线Binance，2026 YTD收入$4.29亿全链第一"),
]
for s in scores:
    save_score("HYPE", *s)

# AI深度报告
save_report(
    "HYPE", "深度研究",
    # 看多
    "1. 真实收入：2026 YTD $4.29亿，年化$6.4-10亿，是链上收入最高的协议\n"
    "2. 通缩机制：累计销毁4889万枚（4.89%），月度回购$53-83M，净通缩\n"
    "3. 机构采用：Coinbase+Circle各质押50万HYPE（可slash），Coinbase+Morpho抵押品\n"
    "4. 流动性：上线Binance，OI $18B创纪录，Kraken美国市场准入\n"
    "5. 技术壁垒：自研L1+订单簿DEX，HIP-3允许第三方自建永续市场",
    # 看空
    "1. 流通率仅23%：FDV/MCap=4.29，未来解锁抛压大\n"
    "2. 竞争加剧：Coinbase/Robinhood/Kraken在永续合约市场直接竞争\n"
    "3. 巨鲸抛售：约$1亿抛压，10+ HYPE钱包减少6.3%\n"
    "4. 收入下降：从10月$124M降至9月$63.9M，下降近50%\n"
    "5. 监管风险：美国市场准入仍不确定",
    # 催化剂
    "1. 10月3日首次Coinbase/Circle质押收益支付\n"
    "2. 资金费率上限下调（下次升级）\n"
    "3. Kraken Bitnomial美国永续合约上线\n"
    "4. 月度回购持续销毁\n"
    "5. HIP-3新市场上线带来交易量",
    # 风险
    "1. 巨鲸持续抛售\n2. 主流CEX竞争挤压\n3. 收入下降趋势\n4. 监管不确定性",
    "看多（短期谨慎）",
    "短期$88-96区间，突破$98看$110-130；强支撑$80-82",
    "HYPE是目前crypto少有的'真实盈利'协议，收入+回购+机构采用三重驱动。但流通率低是最大隐忧，短期在$88-96震荡。"
)

print("HYPE深度数据已存入数据库")
