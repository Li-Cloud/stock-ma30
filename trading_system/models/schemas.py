"""
数据模型定义
"""
from enum import Enum
from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class StockPhase(Enum):
    """股票阶段枚举"""
    PHASE_1_BOTTOM = 1      # 第一阶段：底部横盘（冬天）
    PHASE_2_RISING = 2       # 第二阶段：上升趋势（春天/夏天）
    PHASE_3_TOP = 3          # 第三阶段：顶部横盘（秋天）
    PHASE_4_FALLING = 4      # 第四阶段：下降趋势（冬天）
    UNKNOWN = 0              # 未知阶段


class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"              # 买入信号
    SELL = "SELL"            # 卖出信号
    HOLD = "HOLD"            # 持有
    WATCH = "WATCH"          # 观察
    ADD_POSITION = "ADD_POSITION"  # 加仓信号


class StockData(BaseModel):
    """股票数据模型"""
    code: str                           # 股票代码
    name: str                           # 股票名称
    date: datetime                      # 日期
    open: float                         # 开盘价
    high: float                         # 最高价
    low: float                          # 最低价
    close: float                        # 收盘价
    volume: int                         # 成交量
    amount: float                       # 成交额
    ma30_week: Optional[float] = None   # 30周均线
    volume_ma: Optional[float] = None   # 成交量均线


class TradeSignal(BaseModel):
    """交易信号模型"""
    stock_code: str                     # 股票代码
    stock_name: str                     # 股票名称
    signal_type: SignalType             # 信号类型
    phase: StockPhase                   # 当前阶段
    current_price: float                # 当前价格
    ma30_week: float                    # 30周均线值
    volume_ratio: float                 # 成交量比率（当前/平均）
    index_trend: str                    # 大盘趋势
    reason: str                         # 信号原因
    stop_loss: Optional[float] = None   # 止损价
    take_profit: Optional[float] = None # 止盈价
    position_size: Optional[int] = None # 建议仓位（股数）
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_notification_text(self) -> str:
        """转换为通知文本"""
        emoji_map = {
            SignalType.BUY: "🟢",
            SignalType.SELL: "🔴", 
            SignalType.HOLD: "🟡",
            SignalType.WATCH: "👀",
            SignalType.ADD_POSITION: "📈"
        }
        
        phase_names = {
            StockPhase.PHASE_1_BOTTOM: "底部横盘",
            StockPhase.PHASE_2_RISING: "上升趋势",
            StockPhase.PHASE_3_TOP: "顶部横盘",
            StockPhase.PHASE_4_FALLING: "下降趋势"
        }
        
        text = f"""
{emoji_map.get(self.signal_type, "📊")} **交易信号提醒**

**股票**: {self.stock_name} ({self.stock_code})
**信号类型**: {self.signal_type.value}
**当前阶段**: {phase_names.get(self.phase, "未知")}
**当前价格**: ¥{self.current_price:.2f}
**30周均线**: ¥{self.ma30_week:.2f}
**成交量比**: {self.volume_ratio:.2f}倍
**大盘趋势**: {self.index_trend}

**信号原因**:
{self.reason}
"""
        if self.stop_loss:
            text += f"\n**止损价格**: ¥{self.stop_loss:.2f}"
        if self.take_profit:
            text += f"\n**止盈价格**: ¥{self.take_profit:.2f}"
        if self.position_size:
            text += f"\n**建议仓位**: {self.position_size}股"
            
        text += f"\n\n⏰ 生成时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return text


class PhaseMetrics(BaseModel):
    """阶段分析指标"""
    ma30_slope: float                   # 30周均线斜率
    ma30_direction: Literal["up", "down", "flat"]  # 均线方向
    price_to_ma_ratio: float            # 价格与均线比率
    consolidation_weeks: int            # 横盘周数
    breakout_confirmed: bool            # 突破确认
    volume_confirmation: bool           # 成交量确认


class AnalysisResult(BaseModel):
    """分析结果模型"""
    stock_code: str
    stock_name: str
    phase: StockPhase
    metrics: PhaseMetrics
    signals: List[TradeSignal]
    weekly_data: List[StockData]
    analysis_date: datetime = Field(default_factory=datetime.now)


class Position(BaseModel):
    """持仓模型"""
    stock_code: str
    stock_name: str
    entry_price: float                  # 入场价格
    entry_date: datetime                # 入场日期
    shares: int                         # 持股数量
    current_price: float                # 当前价格
    stop_loss: float                    # 止损价
    take_profit: Optional[float] = None # 止盈价
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.current_price * self.shares
    
    @property
    def profit_loss(self) -> float:
        """盈亏金额"""
        return (self.current_price - self.entry_price) * self.shares
    
    @property
    def profit_loss_percent(self) -> float:
        """盈亏比例"""
        return (self.current_price - self.entry_price) / self.entry_price * 100


class RiskConfig(BaseModel):
    """风险配置"""
    max_loss_percent: float = 2.0       # 单笔最大亏损比例
    stop_loss_percent: float = 8.0      # 止损比例
    max_positions: int = 10             # 最大持仓数量
    single_position_max: float = 20.0   # 单只股票最大仓位比例(%)


class MarketContext(BaseModel):
    """市场环境模型"""
    index_code: str                     # 指数代码
    index_name: str                     # 指数名称
    index_phase: StockPhase             # 指数阶段
    index_ma30: float                   # 指数30周均线
    market_sentiment: str               # 市场情绪
    risk_level: Literal["high", "medium", "low"] = "medium"


class AIAnalysisRequest(BaseModel):
    """AI分析请求"""
    stock_code: str
    stock_name: str
    analysis_result: AnalysisResult
    market_context: MarketContext
    question: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    """AI分析响应"""
    stock_code: str
    analysis_text: str
    recommendation: str
    confidence: float
    risk_factors: List[str]
    timestamp: datetime = Field(default_factory=datetime.now)
