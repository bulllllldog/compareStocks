# compareStocks 架构与使用方式分析

> 版本：v2.11.10 | 分析日期：2026-03-22

---

## 一、项目概览

compareStocks 是一个**本地优先的股票分析 Web 应用**，基于 Flask 构建，支持多股票收益率对比、投资组合构建、交易策略回测，以及与 Longbridge/IBKR 券商的实时数据集成。

---

## 二、目录结构

```
compareStocks/
├── main.py                          # 启动入口
├── config.toml                      # 主配置文件
├── requirements.txt                 # Python 依赖
├── app/                             # Flask 应用包
│   ├── __init__.py                  # App 工厂函数 create_app()
│   ├── web.py                       # 所有 HTTP 路由和页面渲染（2018行）
│   ├── market_data.py               # 价格历史获取与标准化
│   ├── comparisons.py               # 收益率对比逻辑
│   ├── date_constraints.py          # 交易日对齐处理
│   ├── logos.py                     # Logo 和 Quote 信息获取
│   ├── presentation.py              # 显示格式化辅助函数
│   ├── schemas.py                   # Dataclass 数据结构定义
│   ├── storage.py                   # Parquet 持久化层（537行）
│   ├── settings.py                  # 配置文件加载器
│   ├── config.py                    # 静态常量
│   ├── connectivity.py              # 远程服务可用性检查
│   ├── broker_market_data.py        # Longbridge/IBKR 集成
│   ├── broker_settings.py           # 券商凭证存储
│   ├── email_settings.py            # SMTP/Outlook OAuth 配置
│   ├── backtest_settings.py         # 回测执行模式持久化
│   └── web/
│       ├── static/
│       │   ├── assets/css/app.css   # 样式表
│       │   └── assets/js/           # 前端脚本
│       │       ├── app.js           # 主要交互逻辑
│       │       ├── chart.js         # 图表渲染
│       │       ├── backtest.js      # 回测页面逻辑
│       │       └── portfolio.js     # 组合页面逻辑
│       └── templates/               # Jinja2 HTML 模板
├── strategies/                      # 交易策略系统
│   ├── base.py                      # 策略基类与数据结构
│   ├── loader.py                    # 动态策略发现与注册
│   ├── backtest.py                  # 单标的回测引擎
│   └── algorithms/                  # 策略实现
│       ├── buy_and_hold.py          # 买入持有（基准）
│       ├── strategy_macd.py         # MACD 交叉策略
│       ├── strategy_supertrend_ai.py # 自适应 SuperTrend + K-Means
│       ├── strategy_knn_machine_learning.py # kNN 机器学习策略
│       └── strategy_lorentzian_classification.py # Lorentzian 分类策略
├── market_store/                    # 本地数据存储
│   ├── historical/                  # 按股票代码存放的 Parquet 文件
│   ├── profiles/                    # profiles.parquet（股票元数据）
│   ├── logos/                       # 缓存的 Logo PNG 文件
│   └── search/                      # 搜索结果缓存
├── settings_store/                  # 用户设置持久化
│   ├── smtp.json                    # 邮件和 OAuth 配置
│   └── brokers.json                 # 券商凭证
└── tests/
    └── test_backtest.py             # 回测指标单元测试
```

---

## 三、技术栈

| 层次 | 技术 |
|------|------|
| **Web 框架** | Flask 3.1.0 |
| **数据处理** | Pandas 2.2.3, PyArrow 19.0.1 |
| **金融数据** | yfinance 1.1.0（日线），Longbridge 4.0.3（分钟线）|
| **存储格式** | Apache Parquet（列式存储，高效压缩）|
| **前端** | Jinja2 模板 + 原生 JavaScript（无框架依赖）|
| **图表** | Chart.js |
| **邮件** | SMTP / Outlook OAuth 2.0 |
| **Python 版本** | 3.13+ |

---

## 四、架构模式

**SSR（服务端渲染）+ AJAX 混合架构**，遵循**服务层模式**：

```
┌─────────────┐     HTTP      ┌──────────────┐
│   Browser   │ ◄──────────► │   Flask      │
│  Jinja2 +   │              │  web.py      │
│  Vanilla JS │              └──────┬───────┘
└─────────────┘                     │
                         ┌──────────┴──────────┐
                         │    Service Layer     │
                    ┌────┴────┐  ┌────────────┐ ┌──────────┐
                    │market_  │  │comparisons │ │strategies│
                    │data.py  │  │.py         │ │/backtest │
                    └────┬────┘  └────────────┘ └──────────┘
                         │
                ┌────────┴────────┐
                │  storage.py     │  ← Parquet 持久化
                │  market_store/  │
                └─────────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
        yfinance    Longbridge    TradingView TA
```

---

## 五、核心模块职责

### `app/web.py` — HTTP 路由层

所有路由的入口，负责请求解析、参数验证、调用服务层、渲染模板。

**主要路由：**

| 路由 | 方法 | 功能 |
|------|------|------|
| `/compare` | GET | 多股票收益率对比 |
| `/portfolio` | GET | 投资组合构建 |
| `/backtest` | GET | 策略回测 |
| `/more/<section>` | GET | 扩展功能（总览、择时） |
| `/settings/<section>` | GET/POST | 设置管理 |
| `/api/symbol-search` | GET | 股票代码搜索（带缓存）|
| `/api/date-constraints` | GET | 交易日对齐计算 |
| `/api/trade-strategy-fields` | GET | 策略参数元数据 |
| `/api/settings/network-status` | GET | 远程服务连通性检查 |
| `/market-store/logos/<filename>` | GET | 本地 Logo 图片服务 |

---

### `app/market_data.py` — 市场数据服务

- `download_full_history(ticker)` — 通过 yfinance 获取全量历史，带重试
- `fetch_history(ticker, include_dividends)` — 返回缓存数据或触发获取
- `refresh_history_store(ticker)` — 手动从远端刷新

---

### `app/comparisons.py` — 收益率对比逻辑

1. `resolve_effective_period()` — 处理数据缺口时的时间段回退
2. `align_datasets_on_common_dates()` — 对多个数据集按交易日内连接
3. `build_series_payload()` — 计算归一化收益率（以起始收盘价为基准）

---

### `app/storage.py` — Parquet 持久化层

- 历史数据：`market_store/historical/{TICKER}.parquet`
- 股票元数据：`market_store/profiles/profiles.parquet`
- 搜索缓存：`market_store/search/search_cache.parquet`
- Logo 缓存：`market_store/logos/{TICKER}.png`
- 文件级 + 线程级双重锁（`fcntl` + `RLock`）

---

### `app/connectivity.py` — 远程服务健康检查

TTL 缓存的连通性探测，用于在离线/受限网络下自动降级：
- Yahoo Finance、EODHD、Google、icon.horse、TradingView TA

---

### `strategies/` — 策略插件系统

**策略基类（`base.py`）：**
```python
class BaseStrategy:
    def get_metadata() → StrategyMetadata
    def get_parameter_definitions() → tuple[StrategyParameterDefinition, ...]
    def compute_signals(dataset, params) → StrategySignalResult
```

**动态发现（`loader.py`）：**
自动扫描 `strategies/algorithms/` 目录，无需静态注册表。

**内置策略：**

| 策略 | 类型 | 说明 |
|------|------|------|
| Buy and Hold | 基准 | 首日买入，末日卖出 |
| MACD | 动量 | 快慢 EMA 交叉（默认 12/26/9）|
| SuperTrend AI | 趋势 | ATR 止损 + K-Means 自适应乘数 |
| kNN ML | 机器学习 | 7 个技术指标 + kNN(k=3) 投票 |
| Lorentzian | 机器学习 | 高级特征工程 + 概率加权信号 |

**回测引擎（`backtest.py`）：**
- 单标的多空回测
- 两种执行模式：`signal_close`（即时）/ `next_open`（次日开盘）
- 输出：净值曲线、交易记录、Sharpe 比率、最大回撤、胜率

---

## 六、数据流

### 对比页面数据流

```
GET /compare?ticker=MSFT&ticker=NVDA&period=1y
  │
  ├─ parse_requested_tickers()
  ├─ fetch_history() ─→ [local Parquet] 或 [yfinance]
  ├─ resolve_effective_period()
  ├─ align_datasets_on_common_dates()
  ├─ build_series_payload() ─→ 归一化收益率数组
  └─ render_template('compare.html', chart_data=...)
```

### 回测数据流

```
GET /backtest?ticker=QQQ&strategy=supertrend-ai&capital=10000
  │
  ├─ instantiate_strategy()  ← 动态加载
  ├─ fetch_history()
  ├─ compute_signals(params)
  ├─ run_single_ticker_backtest()
  └─ return JSON { summary, trades, chart }
```

### 状态管理

| 位置 | 内容 |
|------|------|
| URL Query Params | 选中股票、时间段、策略参数（可分享/书签）|
| Parquet 文件 | 历史 OHLCV 数据、股票元数据 |
| JSON 文件 | 邮件设置、券商凭证、回测模式 |
| 内存 TTL 缓存 | 远程服务连通状态、Logo URL |

---

## 七、配置系统

主配置文件 `config.toml` 分为以下节：

| 节 | 内容 |
|----|------|
| `[app]` | 应用名称、版本、调试模式 |
| `[server]` | 监听地址（默认 `0.0.0.0:8688`）|
| `[persistence]` | 数据存储目录路径 |
| `[defaults]` | 默认股票、时间段、权重、回测设置 |
| `[ui.labels]` | 100+ 个 UI 文本标签 |
| `[ui.theme]` | 颜色主题、圆角、阴影 |
| `[ui.chart]` | 图表渲染参数 |
| `[integrations.tradingview_ta]` | Screener 和 Exchange 默认值 |

---

## 八、启动与使用

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python main.py
```

默认访问地址：`http://127.0.0.1:8688`
（可在 `config.toml` 的 `[server]` 节修改 host/port）

### 主要功能入口

| 页面 | URL | 说明 |
|------|-----|------|
| 股票对比 | `/compare` | 选择 2-5 只股票，对比归一化收益率 |
| 投资组合 | `/portfolio` | 自定义权重构建组合，与 SPY/QQQ 对比 |
| 策略回测 | `/backtest` | 选择股票+策略，查看净值曲线和交易记录 |
| 扩展功能 | `/more/overview` | 市场总览、择时工具 |
| 系统设置 | `/settings/about` | 网络诊断、邮件、券商、数据管理 |

### 数据来源配置

- **日线数据（默认）：** 自动通过 yfinance 拉取，首次使用后本地缓存
- **分钟线数据：** 需在 `/settings/broker-access` 配置 Longbridge 凭证
- **手动刷新：** `/settings/local-market-store` → 选择股票 → 刷新

### 添加自定义策略

在 `strategies/algorithms/` 下新建文件，继承 `BaseStrategy`，实现以下方法：

```python
from strategies.base import BaseStrategy, StrategyMetadata, StrategySignalResult

class MyStrategy(BaseStrategy):
    def get_metadata(self) -> StrategyMetadata:
        return StrategyMetadata(id="my-strategy", name="My Strategy", ...)

    def get_parameter_definitions(self):
        return (...)

    def compute_signals(self, dataset, params) -> StrategySignalResult:
        # dataset: pandas DataFrame with OHLCV columns
        # 返回带 buy/sell 信号列的 DataFrame
        ...
```

系统启动时自动发现并注册，无需修改其他文件。

---

## 九、关键设计决策

1. **本地优先**：所有数据默认缓存在本地 Parquet 文件，网络不可用时仍可浏览历史数据
2. **无 JS 框架依赖**：前端使用原生 JavaScript，减少部署复杂度
3. **插件化策略**：策略通过文件系统自动发现，扩展无需改动核心代码
4. **双重锁机制**：文件级 + 线程级并发保护，保证数据一致性
5. **配置驱动 UI**：100+ 个 UI 标签通过 `config.toml` 集中管理，便于本地化
6. **TTL 缓存降级**：远程服务不可用时自动回退，不影响已缓存数据的使用
