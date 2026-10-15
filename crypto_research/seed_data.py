import sys
sys.path.insert(0, r"C:\Users\P52S\DoubaoWork\chats\2026-09-25\new-chat\twitter_monitor")
from db import save_tweets, save_price, save_event, init_db

init_db()

# ONDO tweets scraped from X.com search
ondo_tweets = [
    {"tweet_id": "ondo_1", "author": "Muhammad Uzair", "author_handle": "@Crypto_By_Uzair",
     "text": "Told You about $ONDO Pump Guys. Now It Hit $0.6089 level. Hope You Guys also Making the Profit. $ONDO Looking well on Weekly TF. $0.60 its next Target. Pump it Higher",
     "created_at": "2026-09-28T14:20:00Z", "likes": 180, "retweets": 127, "replies": 1, "views": "", "url": ""},
    {"tweet_id": "ondo_2", "author": "Rno", "author_handle": "@RnoLl2996761",
     "text": "ONDO feels like it's found its level for now, but the real action is over on NEAR. Whole ecosystem is quietly cooking, reminds me of SOL's vibes last cycle. The network effect is real when the base token moves.",
     "created_at": "2026-09-28T14:18:00Z", "likes": 1, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_3", "author": "beeran a pujari", "author_handle": "@PujariBeeran",
     "text": "GRID quietly cooking while everyone chases pumps. The BlackRock/Ondo thread into real product is the kind of partnership narrative that lasts. Still early.",
     "created_at": "2026-09-28T14:15:00Z", "likes": 1, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_4", "author": "Floki", "author_handle": "@CryptoFloki",
     "text": "Redemption shouldn't be the bottleneck (replying to @Capy_Research and @Ondo)",
     "created_at": "2026-09-28T14:14:00Z", "likes": 3, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_5", "author": "Dylan", "author_handle": "@zeramode30",
     "text": "If you had to choose a large cap to all in on between rn ondo, xlm, hbar, and avax which are you choosing?",
     "created_at": "2026-09-28T14:13:00Z", "likes": 10, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_6", "author": "Giannis Andreou", "author_handle": "@gandreou007",
     "text": "2028-2029 Crypto Price Predictions: $ONDO: $2.5 (along with BTC $180k, ETH $6000, SOL $430, NEAR $18)",
     "created_at": "2026-09-28T14:10:00Z", "likes": 373, "retweets": 3, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_7", "author": "Adams", "author_handle": "@ayomideadams024",
     "text": "Tokenization narrative waking up. $ONDO and $QNT",
     "created_at": "2026-09-28T14:08:00Z", "likes": 64, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_8", "author": "AMk.Crypto", "author_handle": "@leeky_k_crypt",
     "text": "BREAKING: ONDO ROLLS OUT MAJOR UPDATES ACROSS ITS PLATFORM. Last week, Ondo launched Intelligent Portfolios with BlackRock-developed strategies, packaged into single onchain tokens. It also expanded tokenized stock access through Alpaca's Instant Tokenization Network.",
     "created_at": "2026-09-28T14:07:00Z", "likes": 80, "retweets": 5, "replies": 4, "views": "", "url": ""},
    {"tweet_id": "ondo_9", "author": "wildly bullish", "author_handle": "@wildlybullish",
     "text": "突发：$ONDO 营销主管暗示 $ONDO 代币回购 (BREAKING: ONDO marketing chief hints at token buyback)",
     "created_at": "2026-09-27T18:00:00Z", "likes": 49, "retweets": 1, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "ondo_10", "author": "Ismael Manirumva", "author_handle": "@ismaelthetrader",
     "text": "This market correction gave us the fruitful chance of lower entry. Certain coins like $AVAX $ONDO $TRX $GRAM $XRP are fundamentally strong.",
     "created_at": "2026-09-28T14:12:00Z", "likes": 0, "retweets": 0, "replies": 0, "views": "", "url": ""},
]

# HYPE tweets scraped
hype_tweets = [
    {"tweet_id": "hype_1", "author": "Hao", "author_handle": "@DegenComeback",
     "text": "This should be the local bottom. Gut feeling tells me market makers are about to send $HYPE prices back up fast and furious to retest recent highs at $95.",
     "created_at": "2026-09-28T14:22:00Z", "likes": 2, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_2", "author": "Akshay", "author_handle": "@iiam_Akshay",
     "text": "$HYPE traders are facing a major market-structure change. Hyperliquid plans to lower its perpetual funding cap to 0.5% per hour with the next network upgrade. That directly affects how extreme funding can become during crowded trades.",
     "created_at": "2026-09-28T14:21:00Z", "likes": 30, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_3", "author": "GalleonCrypto", "author_handle": "@GalleonCrypto",
     "text": "What comes first for $HYPE? $80 or $100?",
     "created_at": "2026-09-28T14:20:00Z", "likes": 23, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_4", "author": "Giannis Andreou", "author_handle": "@gandreou007",
     "text": "COINBASE IS BLURRING THE LINE BETWEEN WALL STREET AND DEFI. Tokenized stocks can now be used as collateral for USDC loans through Aave V4. Coinbase users can borrow through Morpho using $HYPE and $ZEC as collateral directly inside the app.",
     "created_at": "2026-09-28T14:11:00Z", "likes": 302, "retweets": 2, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_5", "author": "SANPAL", "author_handle": "@SANPAL77",
     "text": "$HYPE Going as plan, $80 Per HYPE in coming days. $HYPE shorting here at CMP $91 and i will add more around $94. $80 Per $HYPE Is my next target. SL $97.8.",
     "created_at": "2026-09-28T14:09:00Z", "likes": 53, "retweets": 1, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_6", "author": "unfolded", "author_handle": "@cryptounfolded",
     "text": "Hyperliquid Leads as the top on-chain revenue generator of 2026, generating $429.04 million YTD",
     "created_at": "2026-09-28T14:00:00Z", "likes": 0, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_7", "author": "Shubham Bhandari", "author_handle": "@shubhamb126",
     "text": "Everyone is talking about $ZEC $QNT $HYPE. Can someone please pump $SOL 2x from current price",
     "created_at": "2026-09-28T14:08:00Z", "likes": 123, "retweets": 0, "replies": 0, "views": "", "url": ""},
    {"tweet_id": "hype_8", "author": "CRBot Signals", "author_handle": "@CRBOTSignals",
     "text": "$HYPE and Pump.fun doing most of the buyback heavy lifting is pretty telling. Real yield sounds great, but consistent cash flow is what makes it real.",
     "created_at": "2026-09-28T14:15:00Z", "likes": 10, "retweets": 0, "replies": 0, "views": "", "url": ""},
]

save_tweets("ONDO", ondo_tweets)
save_tweets("HYPE", hype_tweets)

# Price snapshots
save_price("ONDO", 0.6089, None, None)
save_price("HYPE", 88.74, -4.69, "$19.8B")

# Key events
save_event("ONDO", "partnership", "BlackRock智能投资组合发布",
           "Ondo与BlackRock合作推出基于贝莱德策略的链上智能投资组合代币",
           "CoinDesk/Foresight", "", "2026-09-24")
save_event("ONDO", "integration", "DTCC会员资格",
           "Ondo成为首个接入DTCC的RWA协议",
           "CoinMarketCap", "", "2026-09-17")
save_event("ONDO", "expansion", "通过Alpaca扩展代币化股票",
           "Ondo通过Alpaca Instant Tokenization Network扩展代币化股票接入",
           "X/@leeky_k_crypt", "", "2026-09-27")
save_event("ONDO", "ecosystem", "NEAR生态扩展",
           "Ondo在NEAR链上推出20个代币化美股和ETF",
           "MarketBeat", "", "2026-09-24")
save_event("HYPE", "integration", "Coinbase+Morpho抵押品",
           "Coinbase用户可直接用HYPE和ZEC作为抵押品在Morpho借贷",
           "X/@gandreou007", "", "2026-09-28")
save_event("HYPE", "tokenomics", "资金费率上限下调",
           "Hyperliquid计划在下一次网络升级中将永续资金费率上限降至0.5%/小时",
           "X/@iiam_Akshay", "", "2026-09-28")
save_event("HYPE", "buyback", "协议回购$45.8M",
           "Hyperliquid Strategies回购494,200枚HYPE",
           "CryptoNews", "", "2026-09-25")
save_event("HYPE", "listing", "上线Binance",
           "HYPE上线Binance，OI创纪录$18B",
           "e-bitcoin", "", "2026-09-24")
save_event("HYPE", "revenue", "2026 YTD链上收入第一",
           "Hyperliquid 2026年YTD收入$4.29亿，全链第一",
           "X/@cryptounfolded", "", "2026-09-28")

print("Done!")
