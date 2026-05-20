# 数字货币投资研究项目

## 项目简介

本项目用于数字货币市场研究、分析和投资机会发现。整合学习资料、调研文档和自动化脚本，构建完整的数字货币研究体系。

## 目录结构

```
claude_trading/
├── config/                  # 配置文件
│   └── settings.example.yaml # 配置模板（复制为 settings.yaml 使用）
├── docs/                    # 学习资料与调研文档
│   ├── courses/             # 课程资料
│   ├── research/            # 调研报告
│   └── notes/               # 学习笔记
├── scripts/                 # 自动化脚本
│   ├── data_collection/     # 数据采集脚本
│   ├── analysis/            # 分析脚本
│   └── trading/             # 交易相关脚本
├── data/                    # 数据存储
│   ├── raw/                 # 原始数据
│   ├── processed/           # 处理后数据
│   └── cache/               # 缓存数据
├── notebooks/               # Jupyter 研究笔记本
├── src/                     # 核心代码模块
│   ├── data/                # 数据处理模块
│   ├── analysis/            # 分析模块
│   └── utils/               # 工具函数
└── requirements.txt         # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. 配置 API

```bash
cp config/settings.example.yaml config/settings.yaml
# 编辑 settings.yaml 填入你的 API 密钥
```

### 3. 开始研究

- 在 `docs/courses/` 放置课程资料
- 在 `docs/notes/` 记录学习笔记
- 在 `notebooks/` 进行交互式分析
- 在 `scripts/` 编写自动化脚本

## 研究方向

- [ ] 市场数据分析
- [ ] 技术指标研究
- [ ] 链上数据分析
- [ ] 量化策略开发
- [ ] 风险管理

## 注意事项

- API 密钥等敏感信息请勿提交到 Git
- 数据文件已通过 .gitignore 排除
- 建议先在测试网验证策略
