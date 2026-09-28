"""claude_trading 历史数据库层 —— 建库/回填脚本包。

模块职责：
- ``ddl.sql``            完整 DDL（14 基表 + 5 视图 + 双列 FTS 索引），`ARCHITECTURE.md §2` 逐字落盘
- ``init_db.py``         执行 DDL、确保 FTS 扩展加载、打印各表行数（支持 --rebuild）
- ``etl_common.py``      连接 / 事务 / 批次 / ingest_file_log / 时间与 JSON 归一工具
- ``export_grams.py``    生成 body_grams（CJK 字符 bigram + 英文整词）
- ``load_daily_scan.py`` 载入 light + deep + source_status + coin_category_daily + content_archive
- ``load_macro.py``      载入 macro_snapshot + 3 张子表
- ``backfill_history.py``编排全流程 + 残缺日计算 + 数据写完后再建双列 FTS
"""
