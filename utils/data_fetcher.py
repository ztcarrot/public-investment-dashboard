#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据抓取模块
"""

import requests
import pandas as pd
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# 尝试导入 akshare，如果不可用则设置为 None
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("akshare 库可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("akshare 库不可用，债券数据将使用备用方法")


class DataFetcher:
    """数据抓取器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_fund_historical_from_eastmoney(self, fund_code: str, start_date: str, end_date: str) -> List[Dict]:
        """
        从东方财富获取基金历史净值

        Args:
            fund_code: 基金代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            历史数据列表
        """
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"获取基金 {fund_code} 数据失败: HTTP {response.status_code}")
                return []

            content = response.text

            # 提取净值数据
            # 优先使用单位净值（NetWorthTrend），而不是累计净值（Data_netWorthTrend）
            # 基金计算应该是：份额 × 单位净值
            patterns = [
                r'NetWorthTrend.*?\[\[(.*?)\]\]',      # 单位净值（优先）
                r'Data_netWorthTrend.*?\[\[(.*?)\]\]',  # 累计净值（备用）
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    data_str = match.group(1)
                    points = data_str.split('],[')

                    result = []
                    for point in points:
                        try:
                            point = point.replace('"', '').replace('[', '').replace(']', '')
                            values = point.split(',')

                            if len(values) >= 2:
                                timestamp = values[0].strip()
                                nav = values[1].strip()

                                if nav and float(nav) > 0:
                                    try:
                                        if len(timestamp) > 10:
                                            timestamp = timestamp[:10]

                                        date_obj = datetime.fromtimestamp(int(timestamp))
                                        date_str = date_obj.strftime('%Y-%m-%d')

                                        if start_date <= date_str <= end_date:
                                            result.append({
                                                '日期': date_str,
                                                '净值': float(nav)
                                            })
                                    except:
                                        continue

                        except Exception:
                            continue

                    if result:
                        logger.info(f"基金 {fund_code} 获取到 {len(result)} 条历史数据")
                        return result

            return []

        except Exception as e:
            logger.error(f"获取基金 {fund_code} 历史数据出错: {e}")
            return []

    def get_stock_historical_from_sina(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """
        从新浪财经获取股票历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            历史数据列表
        """
        try:
            if len(stock_code) != 6:
                return []

            # 判断市场
            if stock_code.startswith('5') or stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"

            url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen=1023"

            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"获取股票 {stock_code} 数据失败: HTTP {response.status_code}")
                return []

            content = response.text.strip()
            if not content or content == 'null':
                return []

            import json
            data = json.loads(content)

            result = []
            for item in data:
                date_str = item.get('day', '')
                close_price = item.get('close', 0)

                if start_date <= date_str <= end_date:
                    result.append({
                        '日期': date_str,
                        '净值': float(close_price)
                    })

            if result:
                logger.info(f"股票 {stock_code} 获取到 {len(result)} 条历史数据")

            return result

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 历史数据出错: {e}")
            return []

    def get_stock_historical_from_eastmoney(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        """
        从东方财富获取股票历史数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            历史数据列表
        """
        try:
            if len(stock_code) != 6:
                return []

            # 判断市场：5/6/11开头→上海市场(secid=1.xxx)，其他→深圳市场(secid=0.xxx)
            if stock_code.startswith('5') or stock_code.startswith('6') or stock_code.startswith('11'):
                secid = f"1.{stock_code}"
            else:
                secid = f"0.{stock_code}"

            # 东方财富K线API
            url = f"http://push2.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=0&beg={start_date.replace('-', '')}&end={end_date.replace('-', '')}"

            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"获取股票 {stock_code} 数据失败: HTTP {response.status_code}")
                return []

            import json
            data = response.json()

            if not data.get('data') or not data['data'].get('klines'):
                return []

            klines = data['data']['klines']
            result = []

            for kline in klines:
                # K线数据格式：日期,开盘,收盘,最高,最低,成交量...
                parts = kline.split(',')
                if len(parts) >= 3:
                    date_str = parts[0]
                    close_price = parts[2]  # 收盘价在第3个位置（索引2）

                    if close_price:
                        result.append({
                            '日期': date_str,
                            '净值': float(close_price)
                        })

            if result:
                logger.info(f"股票 {stock_code} 获取到 {len(result)} 条历史数据")

            return result

        except Exception as e:
            logger.error(f"获取股票 {stock_code} 历史数据出错: {e}")
            return []

    def get_bond_19789_historical(self, start_date: str, end_date: str) -> List[Dict]:
        """
        获取25特国06(19789)的历史数据

        使用专门的API接口获取特别国债数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            历史数据列表
        """
        try:
            # 方法1: 尝试使用东方财富的国债详情接口
            price = self.get_bond_19789_current_price()

            if price:
                # 生成历史数据，特别国债价格相对稳定
                # 使用较小的波动率，基于最新价格生成历史数据
                from datetime import timedelta

                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')

                result = []
                current_date = end

                # 特别国债年化收益率约2.5%-3.5%
                annual_return = 0.025

                # 从最新日期向前推算
                days_diff = 0
                while current_date >= start:
                    # 基于年化收益率计算历史价格（时间越早价格越低）
                    years_diff = days_diff / 365.0
                    calculated_price = price / ((1 + annual_return) ** years_diff)

                    result.append({
                        '日期': current_date.strftime('%Y-%m-%d'),
                        '净值': round(calculated_price, 4)
                    })

                    current_date -= timedelta(days=1)
                    days_diff += 1

                # 反转列表，使日期从早到晚
                result.reverse()
                logger.info(f"19789 生成 {len(result)} 条历史数据，最新价格: {price:.4f}")
                return result
            else:
                # 如果API失败，返回空列表
                logger.warning("19789 无法获取当前价格")
                return []

        except Exception as e:
            logger.error(f"获取19789历史数据出错: {e}")
            return []

    def get_bond_19789_current_price(self) -> Optional[float]:
        """
        获取25特国06(19789)的当前价格

        Returns:
            float: 当前价格，失败返回None
        """
        # 方法1: 尝试使用普通API接口
        price = self.get_bond_19789_from_api()
        if price:
            return price

        # 方法2: 使用固定价格作为备用（特别国债面值通常为100元）
        logger.warning("19789 所有API获取失败，使用固定价格 100.00")
        return 100.00

    def get_bond_19789_from_api(self) -> Optional[float]:
        """
        从东方财富API获取25特国06价格

        Returns:
            float: 价格，失败返回None
        """
        try:
            api_urls = [
                "http://push2.eastmoney.com/api/qt/stock/get?secid=1.019789&fields=f43,f44,f45,f46,f47,f48,f49,f50,f51,f52",
                "http://push2.eastmoney.com/api/qt/quotenp/get?secid=1.019789&fields=f43",
            ]

            for url in api_urls:
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('data') and data['data'].get('f43'):
                            raw_price = data['data']['f43']
                            # 债券价格判断：根据返回值大小决定除数
                            # 如果价格 > 100000，说明是毫元单位，除以1000
                            # 如果价格在 10000-100000 之间，可能是厘元单位，除以100
                            # 如果价格 < 10000，说明已经是元单位
                            if raw_price > 100000:
                                price = raw_price / 1000
                            elif raw_price > 10000:
                                price = raw_price / 100
                            else:
                                price = raw_price

                            # 检查价格合理性（债券通常在90-110元之间）
                            if 50 < price < 200:
                                logger.info(f"19789 从API获取价格: {price:.4f} (原始值: {raw_price})")
                                return price
                            else:
                                logger.warning(f"19789 API返回价格异常: {price:.4f} (原始值: {raw_price})，尝试其他方式")
                except Exception as e:
                    logger.debug(f"API调用失败: {e}")
                    continue

            return None

        except Exception as e:
            logger.error(f"获取19789价格出错: {e}")
            return None

    def get_bond_historical_from_akshare(self, bond_code: str, start_date: str, end_date: str) -> List[Dict]:
        """
        使用 akshare 获取债券历史数据

        根据债券类型选择不同的方法：
        1. 可转债（代码11/12开头）：使用精确的K线数据
        2. 其他债券：使用国债收益率曲线推算

        Args:
            bond_code: 债券代码（6位代码）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            历史数据列表
        """
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare 库不可用，无法使用 akshare 获取债券数据")
            return []

        try:
            # 标准化债券代码
            code = bond_code.zfill(6) if len(bond_code) < 6 else bond_code

            logger.info(f"使用 akshare 获取债券 {code} 的历史数据...")

            result = []

            # 判断是否为可转债（11或12开头，6位数字）
            # 11xxxx: 上海可转债
            # 12xxxx: 深圳可转债
            if len(code) == 6 and (code.startswith('11') or code.startswith('12')):
                logger.info(f"债券 {code} 识别为可转债，尝试获取精确K线数据...")
                result = self._get_convertible_bond_data(code, start_date, end_date)

            # 对于其他债券，使用国债收益率曲线推算
            if not result:
                logger.info(f"尝试使用国债收益率曲线推算价格...")
                result = self._get_bond_yield_curve_data(start_date, end_date)

            if not result:
                logger.warning(f"akshare 未能获取债券 {code} 的历史数据")

            return result

        except Exception as e:
            logger.error(f"使用 akshare 获取债券 {bond_code} 历史数据出错: {e}")
            return []

    def _get_convertible_bond_data(self, code: str, start_date: str, end_date: str) -> List[Dict]:
        """
        获取可转债的精确K线数据

        Args:
            code: 可转债代码（6位）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史数据列表
        """
        try:
            # 构造symbol：上海市场sh+代码，深圳市场sz+代码
            if code.startswith('11'):
                symbol = f"sh{code}"
            elif code.startswith('12'):
                symbol = f"sz{code}"
            else:
                # 默认使用上海市场
                symbol = f"sh{code}"

            # 获取可转债日线数据
            df = ak.bond_zh_hs_cov_daily(symbol=symbol)

            if df is not None and not df.empty:
                # 过滤日期范围
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

                # 转换为标准格式
                result = []
                for _, row in df.iterrows():
                    result.append({
                        '日期': row['date'],
                        '净值': float(row['close'])  # 使用收盘价
                    })

                if result:
                    logger.info(f"akshare 可转债 {symbol} 获取到 {len(result)} 条精确K线数据")
                    return result

            return []

        except Exception as e:
            logger.debug(f"akshare 获取可转债K线数据失败: {e}")
            return []

    def _get_bond_yield_curve_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        使用国债收益率曲线推算债券价格

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史数据列表
        """
        try:
            # 获取中国国债收益率
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            df = ak.bond_china_yield(start_date=start_date_str, end_date=end_date_str)

            if df is not None and not df.empty:
                # 筛选中债国债收益率曲线
                treasury_curve = df[df['曲线名称'] == '中债国债收益率曲线']

                if not treasury_curve.empty:
                    # 收益率数据转换为价格
                    result = []
                    for _, row in treasury_curve.iterrows():
                        date_str = str(row.get('日期', ''))
                        if not date_str or len(date_str) < 10:
                            continue

                        # 日期格式已经是 YYYY-MM-DD
                        date_formatted = date_str

                        # 使用10年期国债收益率推算价格
                        # 简化的价格计算：价格 ≈ 面值 * (1 - 收益率影响因子)
                        yield_10y = row.get('10年')
                        if yield_10y and pd.notna(yield_10y):
                            yield_rate = float(yield_10y) / 100  # 转换为小数
                            # 简化价格计算（实际应该使用更复杂的债券定价公式）
                            # 这里使用简单的反比关系：收益率越高，价格越低
                            # 以2%为基准收益率
                            price = 100.0 * (1 - (yield_rate - 0.02) * 3)
                            price = max(90, min(110, price))  # 限制在合理范围 90-110

                            result.append({
                                '日期': date_formatted,
                                '净值': round(price, 4)
                            })

                    if result:
                        logger.info(f"akshare 国债收益率曲线获取到 {len(result)} 条数据")
                        # 按日期排序
                        result.sort(key=lambda x: x['日期'])
                        return result

            return []

        except Exception as e:
            logger.debug(f"akshare 获取国债收益率数据失败: {e}")
            return []

    def fetch_asset_data(self, asset: Dict, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取单个资产的历史数据

        Args:
            asset: 资产配置字典
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            历史数据DataFrame
        """
        code = asset.get('代码')
        code_type = asset.get('代码类型', '基金')
        name = asset.get('名称')
        asset_type = asset.get('资产类别', '股票')
        shares_value = asset.get('初始份额')

        # 处理份额：统一使用份额
        if shares_value is not None and shares_value > 0:
            shares = float(shares_value)
        else:
            # 没有提供份额，默认为0
            shares = 0.0

        # 获取历史数据
        # 特殊处理19789（25特国06）：使用 akshare
        if code == '19789' or code == '019789':
            # 使用 akshare 获取数据
            logger.info(f"特殊国债 {code} 使用 akshare 获取数据...")
            history = self.get_bond_historical_from_akshare(code, start_date, end_date)
        elif code_type == '债券':
            # 债券类型：使用 akshare 获取数据
            logger.info(f"债券 {code} 使用 akshare 获取数据...")
            history = self.get_bond_historical_from_akshare(code, start_date, end_date)
        elif code_type == '场内ETF':
            # 所有场内ETF统一使用新浪API获取交易价格
            # ETF的交易价格比净值更准确反映市场价值
            history = self.get_stock_historical_from_sina(code, start_date, end_date)
        elif code_type == '基金':
            # 普通基金 → 东方财富基金API
            fetch_code = code.zfill(6) if len(code) < 6 else code
            history = self.get_fund_historical_from_eastmoney(fetch_code, start_date, end_date)
        elif code_type == '股票':
            # 股票 → 东方财富股票API
            history = self.get_stock_historical_from_eastmoney(code, start_date, end_date)
        else:
            # 默认使用东方财富基金API
            fetch_code = code.zfill(6) if len(code) < 6 else code
            history = self.get_fund_historical_from_eastmoney(fetch_code, start_date, end_date)

        if not history:
            logger.warning(f"未获取到 {code}({name}) 的数据")
            return pd.DataFrame()

        # 转换为DataFrame
        df = pd.DataFrame(history)

        # 特殊处理：基金类型日期增加一天
        # 基金净值通常在交易日收盘后公布，所以数据日期应该是下一个交易日
        if code_type == '基金':
            df['日期'] = pd.to_datetime(df['日期']) + timedelta(days=1)
            df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
            logger.info(f"基金 {code} 日期已增加一天")
        elif code == '005350' or code == '5350':
            # 兼容旧的短债基金特殊处理
            df['日期'] = pd.to_datetime(df['日期']) + timedelta(days=1)
            df['日期'] = df['日期'].dt.strftime('%Y-%m-%d')
            logger.info(f"短债基金 {code} 日期已增加一天")

        # 计算市值（使用份额）
        df['持有份额'] = shares
        df['当前市值'] = df['净值'] * shares

        # 添加其他信息
        df['代码'] = code
        df['名称'] = name
        df['代码类型'] = code_type
        df['资产类型'] = asset_type
        df['最新价格'] = df['净值']

        # 计算收益率
        if len(df) > 0:
            first_value = df['当前市值'].iloc[0]
            if first_value > 0:
                df['收益率'] = ((df['当前市值'] - first_value) / first_value * 100).round(2)
            else:
                df['收益率'] = 0
        else:
            df['收益率'] = 0

        return df[['日期', '代码', '名称', '代码类型', '资产类型', '最新价格', '持有份额', '当前市值', '收益率']]

    def fetch_all_assets_data(self, assets: List[Dict], start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取所有资产的历史数据

        Args:
            assets: 资产配置列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            所有历史数据DataFrame
        """
        all_data = []

        for asset in assets:
            logger.info(f"正在获取 {asset['代码']}({asset['名称']}) 的数据...")

            asset_df = self.fetch_asset_data(asset, start_date, end_date)

            if not asset_df.empty:
                logger.info(f"  ✅ {asset['代码']} 获取 {len(asset_df)} 条数据")
                all_data.append(asset_df)
            else:
                logger.warning(f"  ❌ {asset['代码']} 未获取到数据")

        logger.info(f"总共获取到 {len(all_data)} 个资产的数据")

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            result = result.sort_values(['日期', '代码'])

            # 检查合并后的数据
            unique_codes = result['代码'].nunique()
            logger.info(f"合并后共有 {unique_codes} 个不同的资产代码")
            logger.info(f"资产代码列表: {sorted(result['代码'].unique())}")
            logger.info(f"成功获取 {len(result)} 条历史数据")

            return result
        else:
            logger.warning("未获取到任何历史数据")
            return pd.DataFrame()

    def get_portfolio_summary(self, historical_data: pd.DataFrame) -> pd.DataFrame:
        """
        生成组合汇总数据

        Args:
            historical_data: 历史数据DataFrame

        Returns:
            组合汇总DataFrame
        """
        if historical_data.empty:
            return pd.DataFrame()

        # 按日期分组汇总
        grouped = historical_data.groupby('日期').agg({'当前市值': 'sum'}).reset_index()
        grouped.columns = ['日期', '总资产']

        # 按资产类型汇总
        for asset_type in ['股票', '黄金', '现金', '国债']:
            asset_df = historical_data[historical_data['资产类型'] == asset_type].groupby('日期').agg({'当前市值': 'sum'}).reset_index()
            asset_df.columns = ['日期', asset_type]
            grouped = grouped.merge(asset_df, on='日期', how='left')

        # 填充空值
        for asset_type in ['股票', '黄金', '现金', '国债']:
            if asset_type not in grouped.columns:
                grouped[asset_type] = 0
            grouped[asset_type] = grouped[asset_type].fillna(0)

        # 过滤非交易日：如果某天有任何资产类型的值为0，则认为是非交易日
        # 获取当天实际存在的资产类型（从原始数据中统计）
        asset_types_per_day = historical_data.groupby('日期')['资产类型'].nunique()
        total_asset_types = historical_data['资产类型'].nunique()

        # 只保留所有资产类型都有数据的日期（交易日）
        valid_dates = asset_types_per_day[asset_types_per_day == total_asset_types].index
        grouped = grouped[grouped['日期'].isin(valid_dates)]

        logger.info(f"过滤掉非交易日，从 {len(asset_types_per_day)} 天减少到 {len(grouped)} 个交易日")

        # 计算占比
        total_assets = grouped['总资产']
        for asset_type in ['股票', '黄金', '现金', '国债']:
            grouped[f'{asset_type}占比'] = (grouped[asset_type] / total_assets * 100).round(2)

        return grouped
