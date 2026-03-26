# AGENTS.md

## 项目概述

**30周均线交易系统** 是基于史丹·温斯坦《笑傲牛熊：一条均线定乾坤》理论构建的量化交易系统。该系统通过30周均线阶段分析法，自动识别股票所处的四个阶段（底部/上升/顶部/下降），生成买入/卖出交易信号，并提供风险管理、智能提醒和AI分析功能。

### 核心特性

- **阶段分析引擎**：基于30周均线和成交量自动识别股票四阶段
- **交易信号生成**：自动检测买入/卖出信号，支持全市场扫描
- **风险管理模块**：止损位计算、仓位控制、金字塔加仓法
- **智能提醒系统**：支持钉钉/飞书webhook实时推送
- **AI分析集成**：调用OpenAI兼容大模型进行市场分析
- **Web管理后台**：基于React的可视化监控面板

### 技术栈

#### 后端 (trading_system/)
- **语言**: Python 3.9+
- **Web框架**: FastAPI 0.109.0 + Uvicorn
- **数据处理**: Pandas 2.1.4 + NumPy 1.26.3
- **HTTP客户端**: httpx 0.26.0 + requests 2.31.0
- **定时任务**: APScheduler 3.10.4
- **数据验证**: Pydantic 2.5.3
- **AI集成**: OpenAI 1.10.0
- **数据库**: SQLAlchemy 2.0.25 + aiosqlite 0.19.0
- **日志**: Loguru 0.7.2
- **数据源**: TDX API (http://43.138.33.77:8080)

#### 前端 (trading-dashboard/)
- **框架**: React 18.3.1 + TypeScript
- **构建工具**: Vite 5.4.10
- **样式**: 原生CSS + Tailwind CSS概念
- **动画**: Framer Motion
- **图标**: Lucide React

---

## 项目结构

```
stock_ma30/
├── trading_system/              # Python后端
│   ├── config/                  # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py          # 系统配置（环境变量管理）
│   ├── core/                    # 核心引擎
│   │   ├── __init__.py
│   │   ├── data_collector.py    # 数据获取（TDX API）
│   │   ├── phase_analyzer.py    # 30周均线阶段分析
│   │   ├── signal_generator.py  # 交易信号生成
│   │   ├── risk_manager.py      # 风险管理
│   │   └── stock_scanner.py     # 全市场股票扫描
│   ├── services/                # 服务层
│   │   ├── __init__.py
│   │   ├── notifier.py          # 钉钉/飞书通知
│   │   └── ai_analyzer.py       # AI分析服务
│   ├── scheduler/               # 定时任务
│   │   ├── __init__.py
│   │   └── task_scheduler.py    # 任务调度器
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   ├── database.py          # 数据库操作
│   │   └── schemas.py           # Pydantic模型定义
│   ├── tests/                   # 测试
│   │   ├── __init__.py
│   │   └── test_phase_analyzer.py
│   ├── main.py                  # 主入口 & API路由
│   ├── requirements.txt         # Python依赖
│   ├── .env.example             # 环境变量示例
│   └── README.md                # 后端文档
│
├── trading-dashboard/           # React前端
│   ├── src/
│   │   ├── components/          # React组件
│   │   │   ├── Dashboard.tsx    # 仪表盘
│   │   │   ├── Signals.tsx      # 信号列表
│   │   │   ├── StockDetail.tsx  # 股票详情
│   │   │   ├── Settings.tsx     # 设置
│   │   │   └── MarketScan.tsx   # 市场扫描
│   │   ├── api/
│   │   │   └── client.ts        # API客户端
│   │   ├── App.tsx              # 应用入口
│   │   ├── index.css            # 全局样式
│   │   └── main.tsx             # 主入口
│   ├── package.json             # Node依赖
│   ├── vite.config.ts           # Vite配置
│   └── tsconfig.json            # TypeScript配置
│
├── Dockerfile                   # Docker镜像构建
├── docker-compose.yml           # Docker Compose配置
├── nginx.conf                   # Nginx配置
├── API_接口文档.md              # TDX API文档
├── README.md                    # 项目说明
└── 一根均线定乾坤.txt           # 理论原文
```

---

## 构建和运行

### 环境要求

- Python 3.9+
- Node.js 18+
- (可选) Docker & Docker Compose

### 后端启动

```bash
cd trading_system

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 开发模式（自动重载）
python main.py --serve

# 生产模式
python main.py --serve --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd trading-dashboard

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

### Docker部署

```bash
# 构建前端
cd trading-dashboard
npm install
npm run build
cd ..

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 主要命令

#### 后端命令行工具

```bash
cd trading_system

# 执行完整分析（扫描股票池）
python main.py --run

# 分析单只股票
python main.py --stock 000001

# 启动API服务
python main.py --serve
```

#### 前端命令

```bash
cd trading-dashboard

# 开发服务器（端口3002）
npm run dev

# 构建（输出到dist/）
npm run build

# 代码检查
npm run lint

# 预览构建结果
npm run preview
```

---

## 开发规范

### Python后端

1. **异步优先**：所有I/O操作使用async/await模式
2. **类型提示**：使用Python类型注解，配合Pydantic进行数据验证
3. **日志规范**：使用Loguru记录日志，级别分为DEBUG/INFO/WARNING/ERROR
4. **配置管理**：通过环境变量和`.env`文件管理配置，使用Pydantic Settings
5. **API设计**：遵循RESTful规范，统一返回格式

### React前端

1. **TypeScript优先**：所有组件和逻辑使用TypeScript编写
2. **组件化设计**：将功能拆分为独立、可复用的组件
3. **状态管理**：使用React Hooks进行状态管理
4. **样式规范**：使用CSS类名遵循BEM命名规范
5. **错误处理**：所有API调用都需要try-catch错误处理

### 代码风格

- **Python**：遵循PEP 8规范，使用4空格缩进
- **TypeScript**：遵循ESLint配置，使用2空格缩进
- **命名约定**：
  - Python: 变量/函数使用snake_case，类使用PascalCase
  - TypeScript: 组件使用PascalCase，函数/变量使用camelCase

---

## 核心模块说明

### 1. DataCollector (core/data_collector.py)

数据获取模块，通过TDX API获取股票行情数据。

**主要功能**：
- 获取实时行情（五档买卖盘口）
- 获取K线数据（支持日/周/月等周期）
- 计算技术指标（30周均线、成交量比率等）

**关键方法**：
```python
async def get_kline_data(code: str, kline_type: str = 'day')
async def get_realtime_quote(code: str)
async def calculate_ma30_week(df: pd.DataFrame)
```

### 2. PhaseAnalyzer (core/phase_analyzer.py)

阶段分析引擎，基于30周均线判断股票所处阶段。

**四阶段定义**：
- `PHASE_1_BOTTOM`: 底部横盘（30周均线走平，股价震荡）
- `PHASE_2_RISING`: 上升趋势（股价突破，30周均线向上）
- `PHASE_3_TOP`: 顶部横盘（30周均线走平，波动加大）
- `PHASE_4_FALLING`: 下降趋势（30周均线向下，股价在均线下方）

**关键方法**：
```python
def analyze_phase(df: pd.DataFrame) -> StockPhase
def detect_breakout(df: pd.DataFrame) -> Tuple[bool, str]
def calculate_ma30_slope(df: pd.DataFrame) -> float
```

### 3. SignalGenerator (core/signal_generator.py)

交易信号生成器，根据阶段分析结果生成买卖信号。

**买入条件**：
- 股价放量突破第一阶段底部区间
- 30周均线开始向上倾斜
- 突破时成交量放大2倍以上
- 大盘处于上升趋势（可选）

**卖出条件**：
- 30周均线走平或向下
- 股价跌破30周均线且3周内无法站回
- 成交量异常放大但股价不涨

**关键方法**：
```python
def generate_buy_signal(result: AnalysisResult) -> Optional[TradeSignal]
def generate_sell_signal(result: AnalysisResult) -> Optional[TradeSignal]
def calculate_stop_loss(df: pd.DataFrame, buy_price: float) -> float
```

### 4. RiskManager (core/risk_manager.py)

风险管理模块，计算止损位和仓位大小。

**关键原则**：
- 单笔交易最大亏损不超过总资金的2-3%
- 止损位只能上移，不能下移
- 使用金字塔加仓法（首次建仓50%，盈利后加仓）

**关键方法**：
```python
def calculate_position_size(total_capital: float, stop_loss_price: float) -> float
def calculate_stop_loss_level(df: pd.DataFrame, buy_price: float) -> float
def update_trailing_stop(current_stop: float, new_price: float) -> float
```

### 5. StockScanner (core/stock_scanner.py)

全市场扫描器，批量扫描A股市场筛选第二阶段股票。

**性能优化**：
- 自动批次大小调整：20-50只/批
- 批次间延迟：0.1秒（优化前0.5秒）
- 支持进度回调，实时更新扫描进度

**过滤选项**：
- 排除ST股票
- 排除创业板（300/301）
- 排除科创板（688）
- 排除北交所（43/83/87）
- 排除退市整理期股票

**数据库保存**：
- 扫描结果自动保存到SQLite数据库
- 支持历史记录查询
- 即使没有找到第二阶段股票也会保存扫描记录

**关键方法**：
```python
async def scan_phase2_stocks(
    max_stocks: int = 0,
    batch_size: int = 10,
    save_to_db: bool = True,
    generate_signals: bool = True,
    progress_callback: Optional[callable] = None
) -> Tuple[List[Dict], List[TradeSignal]]
async def get_market_statistics() -> Dict
```

**扫描性能**：
- 优化前：3000只股票约2小时（10只/批，0.5秒延迟）
- 优化后：3000只股票约20-60分钟（20-50只/批，0.1秒延迟）
- 提速：约2-5倍

### 6. Notifier (services/notifier.py)

多渠道通知服务，支持钉钉和飞书webhook推送。

**支持渠道**：
- 钉钉机器人（支持签名验证）
- 飞书自定义机器人

**关键方法**：
```python
async def send_text(text: str, title: Optional[str] = None)
async def send_markdown(title: str, content: str)
async def send_trade_signal(signal: TradeSignal)
```

### 7. AIAnalyzer (services/ai_analyzer.py)

AI分析服务，调用OpenAI兼容大模型进行市场分析。

**分析内容**：
- 技术面分析
- 风险因素识别
- 交易建议生成

**关键方法**：
```python
async def analyze_stock(result: AnalysisResult, context: MarketContext)
async def generate_report(signals: List[TradeSignal])
```

---

## API接口文档

后端API基于FastAPI构建，启动后访问 http://localhost:8000/docs 查看交互式文档。

### 核心接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 系统信息 |
| `/health` | GET | 健康检查 |
| `/api/analyze/run` | POST | 执行完整分析任务 |
| `/api/analyze/stock/{code}` | GET/POST | 分析单只股票 |
| `/api/signals` | GET | 获取交易信号列表 |
| `/api/market/context` | GET | 获取市场环境 |
| `/api/ai/analyze/{code}` | POST | AI智能分析 |
| `/api/notify` | POST | 发送测试通知 |
| `/api/quote` | GET | 获取实时行情 |
| `/api/config` | GET | 获取系统配置 |
| `/api/market/scan` | GET | 全市场扫描 |
| `/api/market/statistics` | GET | 市场统计 |
| `/api/market/scan/history` | GET | 扫描历史记录 |
| `/api/market/scan/latest` | GET | 最新扫描结果 |
| `/api/market/scan/persistent` | GET | 持续第二阶段股票 |
| `/api/market/scan/progress` | GET | 扫描进度查询（实时） |

### API调用示例

```bash
# 获取系统信息
curl http://localhost:8000/

# 分析单只股票
curl http://localhost:8000/api/analyze/stock/000001

# 执行完整分析
curl -X POST http://localhost:8000/api/analyze/run

# 全市场扫描
curl "http://localhost:8000/api/market/scan?max_stocks=100&exclude_st=true"

# AI分析
curl -X POST http://localhost:8000/api/ai/analyze/000001
```

---

## 配置说明

### 环境变量 (.env)

```env
# 数据源配置
TDX_API_URL=http://43.138.33.77:8080

# 钉钉Webhook（可选）
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=xxx

# 飞书Webhook（可选）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# OpenAI配置（可选）
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 股票池配置
STOCK_POOL=000001,000002,000333,000858,002594,300750,600000,600519,601012,601318
INDEX_CODE=000001

# 风险控制
MAX_LOSS_PERCENT=2.0
STOP_LOSS_PERCENT=8.0

# 调度配置
SCHEDULE_DAY=5
SCHEDULE_TIME=15:30

# 系统配置
DATA_DIR=./data
LOG_LEVEL=INFO
```

---

## 测试

### Python后端测试

```bash
cd trading_system

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_phase_analyzer.py

# 运行并显示覆盖率
pytest --cov=core tests/
```

### 前端测试

当前项目未配置前端测试框架，建议后续添加：

```bash
cd trading-dashboard

# 安装测试依赖
npm install --save-dev @testing-library/react @testing-library/jest-dom vitest

# 运行测试
npm run test
```

---

## Docker部署

### 构建镜像

```bash
# 构建后端镜像
docker build -t trading-system .

# 或使用docker-compose构建
docker-compose build
```

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f trading-api
```

### 数据持久化

Docker部署时，以下目录会持久化：
- `./data/` - SQLite数据库文件
- `./logs/` - 系统日志文件

---

## 常见问题

### Q: 后端启动失败，提示端口被占用

A: 修改 `main.py` 中的默认端口，或使用命令行参数：
```bash
python main.py --serve --port 8001
```

### Q: 前端无法连接后端API

A: 检查 `trading-dashboard/src/api/client.ts` 中的API地址是否正确：
```typescript
const API_BASE_URL = 'http://localhost:8000';
```

### Q: 数据获取失败

A: 检查TDX API服务是否可用：
```bash
curl http://43.138.33.77:8080/api/quote?code=000001
```

### Q: 通知发送失败

A: 检查 `.env` 文件中的webhook地址和密钥是否正确，查看日志获取详细错误信息。

### Q: AI分析不工作

A: 确保已配置 `OPENAI_API_KEY`，并且API地址可访问。

### Q: 扫描速度很慢，需要2小时？

A: 这是正常现象，主要原因：
- 网络延迟：每批股票需要从TDX API获取数据
- 批次大小：优化前为10只/批，需处理300+批
- 批次延迟：每批之间有0.1-0.5秒延迟
- 数据量：全市场3000+只股票，每只需要150周K线数据

**解决方案**：
- 设置 `max_stocks` 参数限制扫描数量（如20-100只）
- 已优化批次大小到20-50只/批，提升2-5倍速度

### Q: 扫描结果刷新页面后消失？

A: 这通常是由于数据库保存失败导致的：
- 检查后端日志中是否有"保存扫描结果到数据库失败"错误
- 确认 `trading_system/data/scan_history.db` 文件存在且有写权限
- 现已修复：即使没有找到第二阶段股票也会保存扫描记录

### Q: 为什么扫描进度一直显示"正在扫描"？

A: 可能的原因：
- 扫描真的还在进行中（需要耐心等待1-3分钟）
- 浏览器控制台有JavaScript错误
- 后端服务崩溃或重启
- 进度轮询失败

**排查步骤**：
1. 打开浏览器控制台（F12）查看错误
2. 访问 `http://localhost:8000/api/market/scan/progress` 检查进度状态
3. 查看后端日志确认扫描是否在进行

### Q: 扫描完成后没有显示结果？

A: 可能的原因：
1. 没有找到第二阶段股票（正常现象）
2. API返回的数据格式有问题
3. 前端状态更新失败

**解决方案**：
- 检查后端日志确认扫描是否成功
- 查看浏览器控制台是否有错误
- 刷新页面后查看"历史记录"标签页

### Q: ma30 显示为null？

A: 这是数据问题，可能原因：
- 股票上市时间不足30周
- K线数据不完整
- 数据源没有提供足够的历史数据

**影响**：
- 无法准确判断30周均线方向
- 阶段分析可能不准确
- 建议观察一段时间后再分析

---

## 理论基础

本系统基于史丹·温斯坦《笑傲牛熊》中的**四阶段理论**：

### 四个阶段

1. **第一阶段（底部/冬天）**：
   - 30周均线走平或略微向下
   - 股价在均线上下震荡
   - 成交量萎缩
   - 策略：观察，不买入

2. **第二阶段（上升/春夏）**：
   - 股价放量突破底部区间
   - 30周均线开始向上
   - 成交量持续放大
   - 策略：买入并持有

3. **第三阶段（顶部/秋天）**：
   - 30周均线走平
   - 股价震荡，波动加大
   - 成交量不规则
   - 策略：考虑分批卖出

4. **第四阶段（下降/冬天）**：
   - 30周均线向下
   - 股价在均线下方运行
   - 策略：远离，不持有

### 交易纪律

- 不要试图抄底摸顶
- 只在第二阶段买入
- 单笔亏损不超过总资金2-3%
- 止损位只能上移，不能下移
- 不要与大势为敌

---

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 免责声明

**重要提示**：

1. 本系统仅供学习和研究使用，不构成任何投资建议
2. 股市有风险，投资需谨慎
3. 过往表现不代表未来收益
4. 请根据自身风险承受能力谨慎决策
5. 使用本系统产生的任何盈亏均由用户自行承担

---

## 许可证

MIT License

Copyright (c) 2024 30周均线交易系统

---

## 联系方式

- 项目地址：https://github.com/oficcejo/stock-ma30
- 理论视频：https://www.bilibili.com/video/BV1twFSzNE75

---

**最后更新**: 2026-03-25