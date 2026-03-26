"""
全市场股票扫描器
- 扫描全市场股票
- 排除ST、创业板、科创板、退市等股票
- 筛选出第二阶段（上升趋势）股票
- 扫描结果存入SQLite数据库
- 生成交易信号加入监测
"""
import asyncio
import time
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from loguru import logger
import httpx
import pandas as pd

from config import get_settings
from core.data_collector import DataCollector
from core.phase_analyzer import PhaseAnalyzer, StockPhase
from core.signal_generator import SignalGenerator
from models import get_scan_db, TradeSignal, SignalType


@dataclass
class StockFilter:
    """股票筛选条件"""
    exclude_st: bool = True          # 排除ST股票
    exclude_gem: bool = True         # 排除创业板 (300/301开头)
    exclude_star: bool = True        # 排除科创板 (688开头)
    exclude_bse: bool = True         # 排除北交所 (8/4开头)
    exclude_delisting: bool = True   # 排除退市整理期
    exclude_new: bool = True         # 排除次新股 (上市<60天)
    min_market_cap: float = 50       # 最小市值(亿)
    
    # 代码前缀过滤
    excluded_prefixes: tuple = ()
    
    def __post_init__(self):
        prefixes = []
        if self.exclude_gem:
            prefixes.extend(['300', '301'])  # 创业板
        if self.exclude_star:
            prefixes.append('688')            # 科创板
        if self.exclude_bse:
            prefixes.extend(['8', '4'])       # 北交所/新三板
        if self.exclude_delisting:
            prefixes.append('900')            # 退市整理
        self.excluded_prefixes = tuple(prefixes)


class StockScanner:
    """全市场股票扫描器"""
    
    def __init__(self, filter_config: Optional[StockFilter] = None):
        self.settings = get_settings()
        self.filter = filter_config or StockFilter()
        self.data_collector = DataCollector()
        self.phase_analyzer = PhaseAnalyzer()
        self.signal_generator = SignalGenerator()
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        await self.data_collector.client.aclose()
    
    # 预设股票池 - 沪深300成分股（部分）
    DEFAULT_STOCK_POOL = [
        {"code": "000001", "name": "平安银行"},
        {"code": "000002", "name": "万科A"},
        {"code": "000063", "name": "中兴通讯"},
        {"code": "000100", "name": "TCL科技"},
        {"code": "000333", "name": "美的集团"},
        {"code": "000538", "name": "云南白药"},
        {"code": "000568", "name": "泸州老窖"},
        {"code": "000596", "name": "古井贡酒"},
        {"code": "000625", "name": "长安汽车"},
        {"code": "000651", "name": "格力电器"},
        {"code": "000725", "name": "京东方A"},
        {"code": "000768", "name": "中航西飞"},
        {"code": "000858", "name": "五粮液"},
        {"code": "000895", "name": "双汇发展"},
        {"code": "000938", "name": "中材国际"},
        {"code": "001979", "name": "招商蛇口"},
        {"code": "002001", "name": "新和成"},
        {"code": "002007", "name": "华兰生物"},
        {"code": "002008", "name": "大族激光"},
        {"code": "002024", "name": "苏宁易购"},
        {"code": "002027", "name": "分众传媒"},
        {"code": "002049", "name": "紫光国微"},
        {"code": "002120", "name": "韵达股份"},
        {"code": "002142", "name": "宁波银行"},
        {"code": "002230", "name": "科大讯飞"},
        {"code": "002236", "name": "大华股份"},
        {"code": "002271", "name": "东方雨虹"},
        {"code": "002304", "name": "洋河股份"},
        {"code": "002311", "name": "海大集团"},
        {"code": "002352", "name": "顺丰控股"},
        {"code": "002371", "name": "北方华创"},
        {"code": "002415", "name": "海康威视"},
        {"code": "002460", "name": "赣锋锂业"},
        {"code": "002475", "name": "立讯精密"},
        {"code": "002493", "name": "荣盛石化"},
        {"code": "002555", "name": "三七互娱"},
        {"code": "002594", "name": "比亚迪"},
        {"code": "002601", "name": "龙佰集团"},
        {"code": "002648", "name": "卫星化学"},
        {"code": "002714", "name": "牧原股份"},
        {"code": "002812", "name": "恩捷股份"},
        {"code": "601398", "name": "工商银行"},
        {"code": "601288", "name": "农业银行"},
        {"code": "601988", "name": "中国银行"},
        {"code": "601939", "name": "建设银行"},
        {"code": "601628", "name": "中国人寿"},
        {"code": "601318", "name": "中国平安"},
        {"code": "600519", "name": "贵州茅台"},
        {"code": "600036", "name": "招商银行"},
        {"code": "600276", "name": "恒瑞医药"},
        {"code": "600309", "name": "万华化学"},
        {"code": "600585", "name": "海螺水泥"},
        {"code": "600690", "name": "海尔智家"},
        {"code": "600887", "name": "伊利股份"},
        {"code": "601888", "name": "中国中免"},
        {"code": "601012", "name": "隆基绿能"},
        {"code": "601166", "name": "兴业银行"},
        {"code": "601668", "name": "中国建筑"},
        {"code": "601857", "name": "中国石油"},
        {"code": "601088", "name": "中国神华"},
        {"code": "600028", "name": "中国石化"},
        {"code": "600900", "name": "长江电力"},
        {"code": "601728", "name": "中国电信"},
        {"code": "600050", "name": "中国联通"},
        {"code": "601186", "name": "中国铁建"},
        {"code": "601390", "name": "中国中铁"},
        {"code": "601800", "name": "中国交建"},
        {"code": "601618", "name": "中国中冶"},
        {"code": "601669", "name": "中国电建"},
        {"code": "601868", "name": "中国能建"},
        {"code": "601117", "name": "中国化学"},
        {"code": "601699", "name": "潞安环能"},
        {"code": "601225", "name": "陕西煤业"},
        {"code": "601898", "name": "中煤能源"},
        {"code": "601001", "name": "晋控煤业"},
        {"code": "600547", "name": "山东黄金"},
        {"code": "600489", "name": "中金黄金"},
        {"code": "601899", "name": "紫金矿业"},
        {"code": "600362", "name": "江西铜业"},
        {"code": "600111", "name": "北方稀土"},
        {"code": "600392", "name": "盛和资源"},
        {"code": "601600", "name": "中国铝业"},
        {"code": "603993", "name": "洛阳钼业"},
    ]

    async def get_all_stocks(self) -> List[Dict[str, str]]:
        """
        获取全市场股票列表
        通过 /api/codes 接口从TDX行情服务获取所有A股代码
        
        Returns:
            [{"code": "000001", "name": "平安银行", "exchange": "SZ"}, ...]
        """
        try:
            url = f"{self.settings.tdx_api_url}/api/codes"
            logger.info(f"正在从TDX服务获取全市场股票列表: {url}")
            
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") != 0:
                logger.error(f"API返回错误: {result.get('message')}")
                raise Exception(f"API错误: {result.get('message')}")
            
            # 解析数据 - 根据用户提供的代码格式
            data = result.get("data", {})
            codes_list = data.get("codes", []) if isinstance(data, dict) else data
            
            if not codes_list:
                logger.warning("API返回空股票列表，使用预设股票池")
                return self.DEFAULT_STOCK_POOL.copy()
            
            stocks = []
            for item in codes_list:
                if isinstance(item, dict) and item.get("code"):
                    code = item.get("code", "").strip()
                    name = item.get("name", "").strip()
                    exchange = item.get("exchange", "")
                    
                    # 过滤：只保留6位数字代码的A股
                    if code.isdigit() and len(code) == 6:
                        stocks.append({
                            "code": code,
                            "name": name,
                            "exchange": exchange,
                            "type": "stock"
                        })
            
            logger.info(f"成功获取 {len(stocks)} 只A股")
            return stocks
            
        except Exception as e:
            logger.error(f"获取全市场股票列表失败: {e}")
            logger.info("降级使用预设股票池")
            return self.DEFAULT_STOCK_POOL.copy()
    
    def is_valid_stock(self, stock: Dict[str, str]) -> bool:
        """
        检查股票是否符合筛选条件
        
        Args:
            stock: {"code": "000001", "name": "平安银行"}
            
        Returns:
            True表示符合要求，False表示被排除
        """
        code = stock.get("code", "")
        name = stock.get("name", "")
        
        if not code:
            return False
        
        # 排除ST股票
        if self.filter.exclude_st:
            if "ST" in name or "*ST" in name or "S" in name:
                logger.debug(f"排除ST股票: {code} {name}")
                return False
        
        # 排除特定板块（根据代码前缀）
        for prefix in self.filter.excluded_prefixes:
            if code.startswith(prefix):
                logger.debug(f"排除板块股票 {prefix}: {code} {name}")
                return False
        
        # 只保留A股（6位数字代码）
        if not (code.isdigit() and len(code) == 6):
            logger.debug(f"排除非A股: {code} {name}")
            return False
        
        # 只保留上海(60/68/90)和深圳(00/30)主板
        if not (code.startswith('6') or code.startswith('0') or code.startswith('3')):
            logger.debug(f"排除非主板: {code} {name}")
            return False
        
        return True
    
    async def scan_phase2_stocks(
        self,
        max_stocks: int = 0,
        batch_size: int = 10,
        save_to_db: bool = True,
        generate_signals: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[TradeSignal]]:
        """
        扫描全市场，找出第二阶段股票并生成交易信号
        
        Args:
            max_stocks: 最大返回股票数，0表示不限制
            batch_size: 并发处理批次大小
            save_to_db: 是否保存到数据库
            generate_signals: 是否生成交易信号
            
        Returns:
            (股票列表, 交易信号列表)
        """
        start_time = time.time()
        
        # 1. 获取全市场股票
        all_stocks = await self.get_all_stocks()
        logger.info(f"全市场共 {len(all_stocks)} 只股票")
        
        # 2. 筛选符合条件的股票
        valid_stocks = [s for s in all_stocks if self.is_valid_stock(s)]
        logger.info(f"筛选后剩余 {len(valid_stocks)} 只股票")
        
        # 3. 批量分析股票阶段
        phase2_stocks = []
        trade_signals = []
        
        # 统计各阶段数量
        phase_stats = {
            "PHASE_1_BOTTOM": 0,
            "PHASE_2_RISING": 0,
            "PHASE_3_TOP": 0,
            "PHASE_4_FALLING": 0,
            "UNKNOWN": 0,
            "ERROR": 0
        }
        
        # 分批处理，避免并发过多（优化批次大小）
        # 自动调整批次大小：最小20，最大50
        effective_batch_size = max(20, min(batch_size, 50))
        total_batches = (len(valid_stocks) - 1) // effective_batch_size + 1
        
        logger.info(f"开始批量分析，批次大小: {effective_batch_size}，总批次: {total_batches}")
        
        for i in range(0, len(valid_stocks), effective_batch_size):
            batch = valid_stocks[i:i + effective_batch_size]
            current_batch = i // effective_batch_size + 1
            logger.info(f"处理批次 {current_batch}/{total_batches}，本批次 {len(batch)} 只股票")

            # 更新进度
            if progress_callback:
                progress_callback({
                    "is_scanning": True,
                    "total_stocks": len(valid_stocks),
                    "processed_stocks": i,
                    "phase2_found": len(phase2_stocks),
                    "current_batch": current_batch,
                    "total_batches": total_batches,
                    "start_time": start_time,
                    "error": None
                })

            # 并发分析
            tasks = [self._analyze_single_stock(s, generate_signals) for s in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计本批次结果
            batch_phase2_count = 0
            for stock, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.warning(f"[{stock['code']}] 分析出错: {result}")
                    phase_stats["ERROR"] += 1
                    continue

                if result:
                    phase = result.get("phase")
                    if phase in phase_stats:
                        phase_stats[phase] += 1
                    else:
                        phase_stats["UNKNOWN"] += 1
                    
                    if phase == "PHASE_2_RISING":
                        batch_phase2_count += 1
                        stock_info = {
                            "code": result["code"],
                            "name": result["name"],
                            "phase": result["phase"],
                            "current_price": result["current_price"],
                            "ma30": result["ma30"],
                            "trend_strength": result["trend_strength"],
                            "volume_ratio": result["volume_ratio"],
                            "weeks_in_phase2": result["weeks_in_phase2"],
                            "breakout_confirmed": result["breakout_confirmed"]
                        }
                        phase2_stocks.append(stock_info)

                        # 收集交易信号
                        if generate_signals and result.get("signal"):
                            trade_signals.append(result["signal"])
                        
                    else:
                        logger.debug(f"[{stock['code']}] {result.get('name', '')} - 阶段: {phase}")
                else:
                    # 数据不足或分析失败
                    phase_stats["UNKNOWN"] += 1

            # 批次统计日志
            logger.info(
                f"批次 {current_batch}/{total_batches} 完成 - "
                f"本批次第二阶段: {batch_phase2_count} 只 | "
                f"累计第二阶段: {len(phase2_stocks)} 只 | "
                f"本批次错误: {phase_stats['ERROR']} 只"
            )

            # 达到上限时提前返回（max_stocks=0表示不限制）
            if max_stocks > 0 and len(phase2_stocks) >= max_stocks:
                logger.info(f"已达到最大数量 {max_stocks}，停止扫描")
                break

            if max_stocks > 0 and len(phase2_stocks) >= max_stocks:
                break

            # 批次间短暂延迟，避免请求过快
            await asyncio.sleep(0.1)  # 从0.5秒减少到0.1秒
        
        # 最终统计
        duration = int(time.time() - start_time)
        logger.info("=" * 80)
        logger.info(f"扫描完成统计:")
        logger.info(f"  总耗时: {duration} 秒")
        logger.info(f"  处理股票: {len(valid_stocks)} 只")
        logger.info(f"  阶段分布:")
        logger.info(f"    第一阶段(底部): {phase_stats['PHASE_1_BOTTOM']} 只")
        logger.info(f"    第二阶段(上升): {phase_stats['PHASE_2_RISING']} 只 ✓")
        logger.info(f"    第三阶段(顶部): {phase_stats['PHASE_3_TOP']} 只")
        logger.info(f"    第四阶段(下降): {phase_stats['PHASE_4_FALLING']} 只")
        logger.info(f"    未知/数据不足: {phase_stats['UNKNOWN']} 只")
        logger.info(f"    分析错误: {phase_stats['ERROR']} 只")
        logger.info(f"  生成交易信号: {len(trade_signals)} 个")
        logger.info("=" * 80)
        
        # 4. 保存到数据库
        if save_to_db and phase2_stocks:
            try:
                db = get_scan_db()
                statistics = {
                    'total_stocks': len(all_stocks),
                    'valid_stocks': len(valid_stocks)
                }
                filter_config = {
                    'exclude_st': self.filter.exclude_st,
                    'exclude_gem': self.filter.exclude_gem,
                    'exclude_star': self.filter.exclude_star,
                    'exclude_bse': self.filter.exclude_bse,
                    'excluded_prefixes': list(self.filter.excluded_prefixes)
                }
                # 即使没有找到第二阶段股票，也要保存扫描记录
                batch_id = db.save_scan_results(
                    phase2_stocks if phase2_stocks else [],  # 传入空列表
                    filter_config, 
                    statistics, 
                    duration
                )
                logger.info(f"扫描结果已保存到数据库，批次ID: {batch_id}")
                
                # 输出找到的第二阶段股票列表
                if phase2_stocks:
                    logger.info("=" * 80)
                    logger.info(f"第二阶段股票列表 ({len(phase2_stocks)} 只):")
                    for idx, stock in enumerate(phase2_stocks, 1):
                        logger.info(
                            f"  {idx}. {stock['code']} {stock['name']} - "
                            f"¥{stock['current_price']} | "
                            f"MA30: ¥{stock['ma30']} | "
                            f"强度: {stock['trend_strength']} | "
                            f"成交量: {stock['volume_ratio']}x | "
                            f"持续: {stock['weeks_in_phase2']}周"
                        )
                    logger.info("=" * 80)
            except Exception as e:
                logger.error(f"保存扫描结果到数据库失败: {e}")
        
        return phase2_stocks[:max_stocks if max_stocks > 0 else len(phase2_stocks)], trade_signals
    
    async def _analyze_single_stock(self, stock: Dict[str, str], generate_signal: bool = True) -> Optional[Dict]:
        """
        分析单只股票的阶段，可选生成交易信号
        
        Args:
            stock: {"code": "000001", "name": "平安银行"}
            generate_signal: 是否生成交易信号
            
        Returns:
            分析结果字典（包含signal字段），或None表示分析失败
        """
        code = stock.get("code", "")
        name = stock.get("name", "")
        
        try:
            logger.info(f"[{code}] 开始分析 {name}")
            
            # 获取周线数据
            df = await self.data_collector.get_weekly_data(code, weeks=150)
            if df is None or len(df) < 30:
                logger.warning(f"[{code}] 数据不足，需要至少30周数据，当前: {len(df) if df is not None else 0} 周")
                return None
            
            logger.info(f"[{code}] 获取数据成功，共 {len(df)} 周数据")
            
            # 分析阶段
            phase, metrics = self.phase_analyzer.analyze_phase(df)
            
            # 记录分析结果
            latest = df.iloc[-1]
            logger.info(
                f"[{code}] 阶段分析完成 - "
                f"阶段: {phase.name} | "
                f"价格: ¥{latest['close']:.2f} | "
                f"MA30: ¥{latest['ma30']:.2f if 'ma30' in latest else 'N/A'} | "
                f"均线方向: {metrics.ma30_direction} | "
                f"斜率: {metrics.ma30_slope:.4f} | "
                f"成交量比率: {metrics.volume_ratio:.2f}x"
            )
            
            # 只返回第二阶段股票详情
            if phase != StockPhase.PHASE_2_RISING:
                logger.debug(f"[{code}] 非第二阶段股票，跳过")
                return None
            
            logger.info(f"[{code}] ✓ 确认为第二阶段股票")
            
            # 构建结果
            result = {
                "code": code,
                "name": stock.get("name", ""),
                "phase": phase.name,
                "current_price": round(latest["close"], 2),
                "ma30": round(latest["ma30"], 2) if "ma30" in latest else None,
                "trend_strength": round(metrics.ma30_slope, 4),
                "volume_ratio": round(latest["volume"] / latest["volume_ma"], 2) if "volume_ma" in latest else 1.0,
                "weeks_in_phase2": self._count_weeks_in_phase2(df),
                "breakout_confirmed": metrics.breakout_confirmed
            }
            
            logger.info(
                f"[{code}] 第二阶段详情 - "
                f"价格/MA30: {latest['close']:.2f}/{latest['ma30']:.2f if 'ma30' in latest else 'N/A'} | "
                f"趋势强度: {metrics.ma30_slope:.4f} | "
                f"成交量: {metrics.volume_ratio:.2f}x | "
                f"突破确认: {'是' if metrics.breakout_confirmed else '否'} | "
                f"持续周数: {result['weeks_in_phase2']}"
            )
            
            # 生成交易信号
            if generate_signal:
                signals = self.signal_generator.generate_signals(code, name, df)
                if signals:
                    # 取第一个信号（通常是BUY或HOLD）
                    result["signal"] = signals[0]
                    logger.info(
                        f"[{code}] 生成交易信号 - "
                        f"类型: {signals[0].signal_type.value} | "
                        f"理由: {signals[0].reason}"
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"[{code}] 分析失败: {e}")
            return None
    
    def _count_weeks_in_phase2(self, df) -> int:
        """计算处于第二阶段的周数"""
        if len(df) < 30:
            return 0
        
        weeks = 0
        for i in range(len(df) - 1, -1, -1):
            row = df.iloc[i]
            if "ma30" in row and row["close"] > row["ma30"]:
                weeks += 1
            else:
                break
        return weeks
    
    async def get_market_statistics(self) -> Dict:
        """
        获取市场统计信息
        
        Returns:
            {
                "total_stocks": 5000,
                "valid_stocks": 3000,
                "phase1_count": 500,
                "phase2_count": 200,
                "phase3_count": 300,
                "phase4_count": 2000
            }
        """
        all_stocks = await self.get_all_stocks()
        valid_stocks = [s for s in all_stocks if self.is_valid_stock(s)]
        
        # 统计各阶段数量（采样分析）
        phase_counts = {
            "PHASE_1_BOTTOM": 0,
            "PHASE_2_RISING": 0,
            "PHASE_3_TOP": 0,
            "PHASE_4_FALLING": 0,
            "UNKNOWN": 0
        }
        
        # 随机采样100只进行统计
        sample_size = min(100, len(valid_stocks))
        import random
        sample = random.sample(valid_stocks, sample_size)
        
        for stock in sample:
            try:
                df = await self.data_collector.get_weekly_data(stock["code"], weeks=60)
                if df is not None and len(df) >= 30:
                    phase, _ = self.phase_analyzer.analyze_phase(df)
                    phase_counts[phase.name] = phase_counts.get(phase.name, 0) + 1
            except:
                pass
        
        # 按比例推算全市场
        ratio = len(valid_stocks) / sample_size if sample_size > 0 else 1
        
        return {
            "total_stocks": len(all_stocks),
            "valid_stocks": len(valid_stocks),
            "phase1_count": int(phase_counts["PHASE_1_BOTTOM"] * ratio),
            "phase2_count": int(phase_counts["PHASE_2_RISING"] * ratio),
            "phase3_count": int(phase_counts["PHASE_3_TOP"] * ratio),
            "phase4_count": int(phase_counts["PHASE_4_FALLING"] * ratio),
            "sample_size": sample_size
        }


# 便捷函数
async def scan_phase2_stocks(max_stocks: int = 0, generate_signals: bool = True) -> Tuple[List[Dict], List[TradeSignal]]:
    """扫描第二阶段股票（便捷函数）
    
    Args:
        max_stocks: 最大返回股票数，0表示不限制
        generate_signals: 是否生成交易信号
        
    Returns:
        (股票列表, 交易信号列表)
    """
    async with StockScanner() as scanner:
        return await scanner.scan_phase2_stocks(max_stocks=max_stocks, generate_signals=generate_signals)


async def test_scanner():
    """测试扫描器"""
    print("=" * 60)
    print("测试全市场股票扫描器")
    print("=" * 60)
    
    async with StockScanner() as scanner:
        # 1. 测试股票列表获取
        print("\n1. 获取股票列表...")
        stocks = await scanner.get_all_stocks()
        print(f"   全市场共 {len(stocks)} 只股票")
        
        # 2. 测试筛选
        print("\n2. 筛选股票...")
        valid_stocks = [s for s in stocks if scanner.is_valid_stock(s)]
        print(f"   符合条件的股票: {len(valid_stocks)} 只")
        
        # 显示部分被排除的股票
        excluded = []
        for s in stocks[:100]:
            if not scanner.is_valid_stock(s):
                excluded.append(f"{s['code']} {s['name']}")
        if excluded:
            print(f"   排除示例: {', '.join(excluded[:5])}")
        
        # 3. 测试第二阶段扫描
        print("\n3. 扫描第二阶段股票（前10只）...")
        phase2, signals = await scanner.scan_phase2_stocks(max_stocks=10, batch_size=5)
        print(f"\n   找到 {len(phase2)} 只第二阶段股票，生成 {len(signals)} 个交易信号:")
        for s in phase2:
            print(f"   ✓ {s['code']} {s['name']}: ¥{s['current_price']} (MA30: ¥{s['ma30']}, 强度: {s['trend_strength']})")
        if signals:
            print(f"\n   交易信号示例:")
            for sig in signals[:3]:
                print(f"   → {sig.stock_code}: {sig.signal_type.value} - {sig.reason[:50]}...")
        
        # 4. 市场统计
        print("\n4. 市场统计...")
        stats = await scanner.get_market_statistics()
        print(f"   全市场: {stats['total_stocks']} 只")
        print(f"   有效股: {stats['valid_stocks']} 只")
        print(f"   第一阶段(底部): ~{stats['phase1_count']} 只")
        print(f"   第二阶段(上升): ~{stats['phase2_count']} 只 ← 重点关注")
        print(f"   第三阶段(顶部): ~{stats['phase3_count']} 只")
        print(f"   第四阶段(下降): ~{stats['phase4_count']} 只")


if __name__ == "__main__":
    asyncio.run(test_scanner())
