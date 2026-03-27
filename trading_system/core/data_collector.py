"""
股票数据获取模块 - 使用tdx-api
API地址: http://43.138.33.77:8080/
数据格式说明：
- 价格数据需要除以1000（原始值为0.001元）
- 返回格式: {'code': 0, 'message': 'success', 'data': {'Count': N, 'List': [...]}}
"""
import httpx
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger

from config import get_settings
from models.database import get_scan_db


class DataCollector:
    """股票数据收集器 - tdx-api版本"""
    
    # 价格缩放因子（tdx-api返回的价格是实际值的1000倍）
    PRICE_SCALE = 1000.0
    
    def __init__(self, base_url: str = None):
        self.settings = get_settings()
        self.base_url = (base_url or self.settings.tdx_api_url).rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
        self.db = get_scan_db() if self.settings.enable_kline_cache else None
    
    def _check_dataframe_has_nan(self, df: pd.DataFrame) -> bool:
        """
        检查DataFrame中是否存在NaN值
        
        Args:
            df: 要检查的DataFrame
            
        Returns:
            如果存在NaN返回True，否则返回False
        """
        if df is None:
            return True
        
        # 检查数值列是否有NaN
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isna().any():
                logger.warning(f"检测到NaN值在列 {col} 中")
                return True
        
        return False
    
    def _dataframe_to_cache_json(self, df: pd.DataFrame) -> str:
        """
        将DataFrame转换为可缓存的JSON字符串
        
        Args:
            df: 要转换的DataFrame
            
        Returns:
            JSON字符串
        """
        # 将日期转换为字符串
        df_copy = df.copy()
        # 检查date列是否为datetime类型
        if pd.api.types.is_datetime64_any_dtype(df_copy['date']):
            # 处理时区问题
            df_copy['date'] = df_copy['date'].dt.tz_localize(None) if df_copy['date'].dt.tz is not None else df_copy['date']
            df_copy['date'] = df_copy['date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # 如果已经是字符串，确保格式正确
            df_copy['date'] = pd.to_datetime(df_copy['date'], utc=True).dt.tz_localize(None).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 转换为字典列表
        records = df_copy.to_dict('records')
        return json.dumps(records, ensure_ascii=False)
    
    def _cache_json_to_dataframe(self, json_str: str) -> Optional[pd.DataFrame]:
        """
        将缓存的JSON字符串转换为DataFrame
        
        Args:
            json_str: JSON字符串
            
        Returns:
            DataFrame或None
        """
        try:
            records = json.loads(json_str)
            df = pd.DataFrame(records)
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            return df
        except Exception as e:
            logger.error(f"缓存JSON转换为DataFrame失败: {e}")
            return None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """发送HTTP请求"""
        try:
            url = f"{self.base_url}{endpoint}"
            logger.debug(f"请求: {url}, 参数: {params}")
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            # 检查返回码
            if result.get("code") != 0:
                logger.error(f"API返回错误: {result.get('message')}")
                return None
            
            return result.get("data")
        except Exception as e:
            logger.error(f"请求失败 {endpoint}: {e}")
            return None
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码 - tdx-api使用纯数字代码"""
        code = code.strip().upper()
        if code.startswith("SH") or code.startswith("SZ"):
            code = code[2:]
        elif code.startswith("sh") or code.startswith("sz"):
            code = code[2:]
        return code
    
    def _parse_kline_data(self, data: Dict) -> Optional[pd.DataFrame]:
        """解析K线数据"""
        try:
            if not data or "List" not in data:
                return None
            
            raw_list = data["List"]
            if not raw_list:
                return None
            
            # 转换为DataFrame
            df = pd.DataFrame(raw_list)
            
            # 标准化列名
            column_mapping = {
                "Time": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
                "Amount": "amount",
                "Last": "last",
            }
            
            df = df.rename(columns=column_mapping)
            
            # 检查必要列
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"数据缺少必要列: {missing_cols}")
                return None
            
            # 转换日期格式
            df["date"] = pd.to_datetime(df["date"])
            
            # 转换数值类型并处理价格缩放
            numeric_cols = ["open", "high", "low", "close"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce") / self.PRICE_SCALE
            
            # 成交量不需要缩放
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            
            # 处理成交额
            if "amount" in df.columns:
                df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
            else:
                df["amount"] = df["close"] * df["volume"]
            
            # 按日期排序
            df = df.sort_values("date").reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"解析K线数据失败: {e}")
            return None
    
    async def get_stock_list(self) -> List[Dict[str, str]]:
        """获取股票代码列表"""
        try:
            data = await self._request("/api/codes")
            if data and isinstance(data, list):
                return [{"code": item.get("code", ""), "name": item.get("name", "")} 
                        for item in data if item.get("code")]
            
            # 如果API返回空，使用默认股票池
            stock_codes = self.settings.get_stock_list()
            return [{"code": code, "name": ""} for code in stock_codes]
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
    
    async def get_kline_data(
        self, 
        code: str, 
        ktype: str = "day",
        limit: int = 500,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取K线数据（支持智能缓存）
        
        Args:
            code: 股票代码 (如: 000001)
            ktype: K线类型 (day=日线, week=周线, month=月线)
            limit: 获取条数
            use_cache: 是否使用缓存
        """
        normalized_code = self._normalize_code(code)
        
        # 尝试从缓存获取
        if use_cache and self.db and self.settings.enable_kline_cache:
            try:
                cached_json = self.db.get_kline_cache(normalized_code, ktype)
                if cached_json:
                    cached_df = self._cache_json_to_dataframe(cached_json)
                    if cached_df is not None and len(cached_df) > 0:
                        logger.debug(f"从缓存加载 {code} {ktype} 数据，共 {len(cached_df)} 条")
                        
                        # 检查缓存是否需要更新
                        should_update = False
                        update_reason = ""
                        
                        # 1. 检查缓存最新日期
                        last_date = cached_df.iloc[-1]['date']
                        today = datetime.now().date()
                        
                        # 获取实时行情
                        try:
                            quote = await self.get_realtime_quote(code)
                            if quote:
                                actual_close = quote.get('close', 0)
                                
                                # 检查日期是否过期（对于日线，如果不是今天则需要更新）
                                if ktype == "day":
                                    if last_date.date() < today:
                                        should_update = True
                                        update_reason = f"缓存数据日期过旧（{last_date.strftime('%Y-%m-%d')} < {today}）"
                                # 对于周线，如果本周有新交易日则需要更新
                                elif ktype == "week":
                                    last_week_end = last_date + timedelta(days=6 - last_date.weekday())
                                    if last_week_end.date() < today:
                                        should_update = True
                                        update_reason = f"周线数据需要更新（{last_week_end.strftime('%Y-%m-%d')} < {today}）"
                                
                                # 2. 检查价格差异（如果差异超过1%，需要更新）
                                if not should_update and actual_close > 0:
                                    cached_close = cached_df.iloc[-1]['close']
                                    price_diff_pct = abs(actual_close - cached_close) / cached_close * 100
                                    if price_diff_pct > 1.0:
                                        should_update = True
                                        update_reason = f"价格差异过大（{price_diff_pct:.2f}% > 1%）"
                                
                                # 如果需要更新，则重新获取数据
                                if should_update:
                                    logger.info(f"{code} {ktype} 缓存需要更新: {update_reason}")
                                    # 继续执行下面的API获取逻辑
                                else:
                                    # 只修正最后一根K线的价格
                                    if actual_close > 0:
                                        old_close = cached_df.iloc[-1]['close']
                                        cached_df.iloc[-1, cached_df.columns.get_loc('close')] = actual_close
                                        logger.debug(f"{code} 价格修正（缓存）: {old_close:.2f} -> {actual_close:.2f}")
                                    
                                    # 限制条数
                                    if limit and len(cached_df) > limit:
                                        cached_df = cached_df.tail(limit).reset_index(drop=True)
                                    
                                    return cached_df
                        except Exception as e:
                            logger.warning(f"获取{code}实时行情失败，使用缓存数据: {e}")
                            # 即使获取实时行情失败，也返回缓存数据
                            if limit and len(cached_df) > limit:
                                cached_df = cached_df.tail(limit).reset_index(drop=True)
                            return cached_df
            except Exception as e:
                logger.warning(f"读取缓存失败 {code} {ktype}: {e}")
        
        # 缓存未命中或缓存禁用，从API获取
        try:
            # 使用 /api/kline 接口
            params = {
                "code": normalized_code,
                "type": ktype,
            }
            
            # 调用tdx-api获取数据
            data = await self._request("/api/kline", params)
            
            if not data:
                logger.warning(f"获取{code}数据为空")
                return None
            
            # 解析数据
            df = self._parse_kline_data(data)
            
            if df is None or len(df) == 0:
                logger.warning(f"解析{code}数据失败")
                return None
            
            # 检查是否存在NaN值
            if self._check_dataframe_has_nan(df):
                logger.warning(f"{code} {ktype} 数据存在异常值（NaN），不缓存")
            else:
                # 保存到缓存
                if self.db and self.settings.enable_kline_cache:
                    try:
                        cache_json = self._dataframe_to_cache_json(df)
                        record_count = len(df)
                        self.db.save_kline_cache(
                            stock_code=normalized_code,
                            ktype=ktype,
                            data_json=cache_json,
                            record_count=record_count,
                            ttl_hours=self.settings.kline_cache_ttl
                        )
                    except Exception as e:
                        logger.warning(f"保存缓存失败 {code} {ktype}: {e}")
            
            # 限制条数
            if limit and len(df) > limit:
                df = df.tail(limit).reset_index(drop=True)
            
            # 获取实时行情修正最新价格（K线可能是复权价格）
            try:
                quote = await self.get_realtime_quote(code)
                if quote and len(df) > 0:
                    # 用实际交易价格替换最后一根K线的收盘价
                    actual_close = quote.get('close', 0)
                    if actual_close > 0:
                        old_close = df.iloc[-1]['close']
                        df.iloc[-1, df.columns.get_loc('close')] = actual_close
                        logger.info(f"{code} 价格修正: {old_close:.2f} -> {actual_close:.2f}")
            except Exception as e:
                logger.warning(f"修正{code}最新价格失败: {e}")
            
            logger.info(f"成功获取 {code} 的{ktype}K线数据，共 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败 {code}: {e}")
            return None
    
    async def get_weekly_data(
        self, 
        code: str, 
        weeks: int = 150
    ) -> Optional[pd.DataFrame]:
        """
        获取周线数据（用于30周均线计算）
        
        Args:
            code: 股票代码
            weeks: 获取周数（默认150周约3年数据）
        """
        try:
            df = await self.get_kline_data(
                code=code,
                ktype="week",
                limit=weeks
            )
            
            # 如果获取不到周线，从日线合成
            if df is None or len(df) < 30:
                logger.info(f"{code} 周线数据不足，尝试从日线合成")
                daily_df = await self.get_daily_data(code, days=weeks * 7)
                if daily_df is not None and len(daily_df) > 0:
                    df = self.resample_to_weekly(daily_df)
            
            return df
        except Exception as e:
            logger.error(f"获取周线数据失败 {code}: {e}")
            return None
    
    async def get_daily_data(
        self, 
        code: str, 
        days: int = 252
    ) -> Optional[pd.DataFrame]:
        """
        获取日线数据
        
        Args:
            code: 股票代码
            days: 获取天数（默认252个交易日约1年）
        """
        try:
            df = await self.get_kline_data(
                code=code,
                ktype="day",
                limit=days
            )
            return df
        except Exception as e:
            logger.error(f"获取日线数据失败 {code}: {e}")
            return None
    
    async def get_realtime_quote(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        try:
            params = {"code": self._normalize_code(code)}
            data = await self._request("/api/quote", params)
            
            if data and isinstance(data, list) and len(data) > 0:
                quote = data[0]
                # 解析价格数据
                k_data = quote.get("K", {})
                return {
                    "code": quote.get("Code"),
                    "open": k_data.get("Open", 0) / self.PRICE_SCALE,
                    "high": k_data.get("High", 0) / self.PRICE_SCALE,
                    "low": k_data.get("Low", 0) / self.PRICE_SCALE,
                    "close": k_data.get("Close", 0) / self.PRICE_SCALE,
                    "last": k_data.get("Last", 0) / self.PRICE_SCALE,
                    "volume": quote.get("TotalHand", 0),
                    "amount": quote.get("Amount", 0),
                }
            return None
        except Exception as e:
            logger.error(f"获取实时行情失败 {code}: {e}")
            return None
    
    async def get_batch_quotes(self, codes: List[str]) -> List[Dict]:
        """批量获取行情"""
        results = []
        for code in codes:
            quote = await self.get_realtime_quote(code)
            if quote:
                results.append(quote)
        return results
    
    async def get_index_data(self, index_code: str = "000001") -> Optional[pd.DataFrame]:
        """获取大盘指数数据"""
        return await self.get_weekly_data(index_code, weeks=150)
    
    async def search_stocks(self, keyword: str) -> List[Dict]:
        """搜索股票"""
        try:
            params = {"keyword": keyword}
            data = await self._request("/api/search", params)
            if data and isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"搜索股票失败: {e}")
            return []
    
    async def get_server_status(self) -> Dict:
        """获取服务器状态"""
        try:
            # 尝试调用一个简单接口来检查连接
            test_data = await self._request("/api/kline", {"code": "000001", "type": "day"})
            return {
                "connected": test_data is not None,
                "api_url": self.base_url
            }
        except Exception as e:
            logger.error(f"获取服务器状态失败: {e}")
            return {"connected": False, "error": str(e), "api_url": self.base_url}
    
    def resample_to_weekly(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        """
        将日线数据重采样为周线数据
        
        Args:
            daily_df: 日线DataFrame
        """
        try:
            if daily_df is None or len(daily_df) == 0:
                return daily_df
            
            df = daily_df.copy()
            df.set_index("date", inplace=True)
            
            # 按周重采样 (周五为周结束)
            weekly = df.resample("W-FRI").agg({
                "open": "first",
                "high": "max",
                "low": "min", 
                "close": "last",
                "volume": "sum",
                "amount": "sum"
            })
            
            # 删除没有交易的周
            weekly = weekly.dropna()
            
            # 重置索引
            weekly = weekly.reset_index()
            weekly.rename(columns={"index": "date"}, inplace=True)
            
            return weekly
            
        except Exception as e:
            logger.error(f"重采样到周线失败: {e}")
            return daily_df


# 同步包装函数（用于非异步环境）
import asyncio


def get_collector() -> DataCollector:
    """获取数据收集器实例"""
    return DataCollector()


async def fetch_stock_data(code: str, weeks: int = 150) -> Optional[pd.DataFrame]:
    """获取股票数据（便捷函数）"""
    async with DataCollector() as collector:
        return await collector.get_weekly_data(code, weeks)


# 测试函数
async def test_api():
    """测试API连接"""
    async with DataCollector() as collector:
        # 测试服务器状态
        print("测试服务器状态...")
        status = await collector.get_server_status()
        print(f"  连接状态: {'OK' if status.get('connected') else 'FAIL'}")
        
        # 测试搜索
        print("\n测试搜索股票...")
        search_results = await collector.search_stocks("平安")
        if search_results:
            print(f"  找到 {len(search_results)} 个结果")
            for item in search_results[:3]:
                print(f"    - {item.get('code')}: {item.get('name')}")
        else:
            print("  搜索无结果或API不支持")
        
        # 测试获取日线数据
        print("\n测试获取日线数据 (000001)...")
        df = await collector.get_daily_data("000001", days=10)
        if df is not None and len(df) > 0:
            print(f"  [OK] 获取到 {len(df)} 条日线数据")
            print(f"  最新: {df.iloc[-1]['date'].strftime('%Y-%m-%d')} 收盘: {df.iloc[-1]['close']:.2f}")
        else:
            print("  [FAIL] 获取失败")
        
        # 测试获取周线数据
        print("\n测试获取周线数据 (000001)...")
        weekly_df = await collector.get_weekly_data("000001", weeks=10)
        if weekly_df is not None and len(weekly_df) > 0:
            print(f"  [OK] 获取到 {len(weekly_df)} 条周线数据")
            print(f"  最新: {weekly_df.iloc[-1]['date'].strftime('%Y-%m-%d')} 收盘: {weekly_df.iloc[-1]['close']:.2f}")
        else:
            print("  [FAIL] 获取失败")
        
        # 测试实时行情
        print("\n测试获取实时行情 (000001)...")
        quote = await collector.get_realtime_quote("000001")
        if quote:
            print(f"  [OK] 当前价格: {quote['close']:.2f}, 成交量: {quote['volume']}")
        else:
            print("  [FAIL] 获取失败")
    
    print("\n测试完成!")


if __name__ == "__main__":
    # 运行测试
    print("="*50)
    print("测试 tdx-api 连接")
    print("="*50)
    asyncio.run(test_api())
