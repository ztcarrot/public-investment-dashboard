#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户基金表现分析模块

从用户资产配置中读取基金，计算不同时间段的收益率和夏普比率。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)

# 导入项目的 DataFetcher
from utils.data_fetcher import DataFetcher


def get_user_funds() -> List[Dict]:
    """
    从配置文件中获取用户的所有基金

    Returns:
        基金列表
    """
    try:
        from utils.config_manager import parse_secrets_assets

        # 读取配置文件
        config_file = os.path.join(os.path.dirname(__file__).replace('utils', ''), '.streamlit', 'secrets.toml')

        if not os.path.exists(config_file):
            logger.warning("未找到 secrets.toml 配置文件")
            return []

        # 解析配置
        import toml
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = toml.load(f)

        assets = config_data.get('assets', [])
        parsed_assets = parse_secrets_assets(assets)

        # 筛选基金（代码类型为"债券"或"基金"或"场内ETF"）
        funds = []
        for asset in parsed_assets:
            code_type = asset.get('代码类型', '')
            fund_name = asset.get('名称', '')
            fund_code = asset.get('代码', '')

            # 只包含基金类型资产
            if code_type in ['债券', '基金', '场内ETF']:
                # 补全代码到6位
                fund_code = fund_code.zfill(6)

                funds.append({
                    'code': fund_code,
                    'name': fund_name,
                    'type': code_type
                })

        logger.info(f"从配置文件中找到 {len(funds)} 只基金")
        return funds

    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return []


def calculate_period_return(nav_df: pd.DataFrame, period_days: int) -> float:
    """
    计算指定时间段的收益率

    Args:
        nav_df: 净值数据 DataFrame
        period_days: 时间段（天数）

    Returns:
        收益率（百分比）
    """
    try:
        if len(nav_df) < 2:
            return 0.0

        latest_nav = nav_df.iloc[-1]['净值']
        latest_date = nav_df.iloc[-1]['日期']

        # 计算起始日期
        start_date = latest_date - pd.Timedelta(days=period_days)

        # 找到最接近起始日期的数据
        period_data = nav_df[nav_df['日期'] >= start_date]

        if len(period_data) < 2:
            # 如果数据不足，使用最早的可用数据
            period_data = nav_df

        initial_nav = period_data.iloc[0]['净值']

        if initial_nav <= 0:
            return 0.0

        # 计算收益率
        return_rate = (latest_nav / initial_nav - 1) * 100

        return round(return_rate, 2)

    except Exception as e:
        logger.warning(f"计算{period_days}天收益率失败: {e}")
        return 0.0


def calculate_sharpe_ratio(nav_df: pd.DataFrame, period_days: int = None) -> float:
    """
    计算夏普比率

    Args:
        nav_df: 净值数据 DataFrame
        period_days: 时间段（天数），如果为 None 则使用全部数据

    Returns:
        夏普比率
    """
    try:
        if len(nav_df) < 30:  # 至少需要30个交易日
            return 0.0

        # 如果指定了时间段，只使用该时间段的数据
        if period_days:
            latest_date = nav_df.iloc[-1]['日期']
            start_date = latest_date - pd.Timedelta(days=period_days)
            nav_df = nav_df[nav_df['日期'] >= start_date]

        if len(nav_df) < 30:
            return 0.0

        nav_values = nav_df['净值'].values

        # 计算日收益率
        returns = np.diff(nav_values) / nav_values[:-1] * 100

        # 计算平均收益率和标准差
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # 假设无风险利率为 2%（年化），转换为日化
        risk_free_rate = 2.0 / 252

        # 计算夏普比率（日化）
        sharpe_daily = (avg_return - risk_free_rate) / std_return

        # 年化夏普比率
        sharpe_annual = sharpe_daily * np.sqrt(252)

        return round(sharpe_annual, 2)

    except Exception as e:
        logger.warning(f"计算夏普比率失败: {e}")
        return 0.0


def calculate_max_drawdown(nav_df: pd.DataFrame) -> float:
    """
    计算最大回撤

    Args:
        nav_df: 净值数据 DataFrame

    Returns:
        最大回撤（负百分比）
    """
    try:
        if len(nav_df) < 2:
            return 0.0

        nav_values = nav_df['净值'].values
        cummax = np.maximum.accumulate(nav_values)
        drawdown = (nav_values - cummax) / cummax * 100

        return round(np.min(drawdown), 2)

    except Exception as e:
        logger.warning(f"计算最大回撤失败: {e}")
        return 0.0


def analyze_fund_performance(fund_code: str, fund_name: str) -> Optional[Dict]:
    """
    分析单只基金的表现

    Args:
        fund_code: 基金代码
        fund_name: 基金名称

    Returns:
        基金表现数据字典
    """
    try:
        logger.debug(f"正在分析基金 {fund_code} ({fund_name})...")

        # 使用项目的 DataFetcher 获取历史数据
        fetcher = DataFetcher()

        # 获取最近10年的数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')

        # 使用东方财富接口获取数据
        historical_data = fetcher.get_fund_historical_from_eastmoney(
            fund_code,
            start_date,
            end_date
        )

        if not historical_data:
            logger.warning(f"基金 {fund_code} 无净值数据")
            return None

        # 转换为 DataFrame
        nav_df = pd.DataFrame(historical_data)

        if nav_df.empty:
            logger.warning(f"基金 {fund_code} 数据为空")
            return None

        # 确保日期是 datetime 类型
        nav_df['日期'] = pd.to_datetime(nav_df['日期'])
        nav_df = nav_df.sort_values('日期').reset_index(drop=True)

        # 计算各个时间段的收益率
        result = {
            '基金代码': fund_code,
            '基金名称': fund_name,
            '近1年收益率': calculate_period_return(nav_df, 365),
            '近3年收益率': calculate_period_return(nav_df, 365*3),
            '近5年收益率': calculate_period_return(nav_df, 365*5),
            '近10年收益率': calculate_period_return(nav_df, 365*10),
            '成立至今收益率': calculate_period_return(nav_df, 365*50),  # 假设最多50年
            '最大回撤': calculate_max_drawdown(nav_df),
            '夏普比率1年': calculate_sharpe_ratio(nav_df, 365),
            '夏普比率3年': calculate_sharpe_ratio(nav_df, 365*3),
            '夏普比率5年': calculate_sharpe_ratio(nav_df, 365*5),
        }

        # 计算总天数和年数
        days_count = (nav_df.iloc[-1]['日期'] - nav_df.iloc[0]['日期']).days
        years_count = days_count / 365.25

        result['数据天数'] = days_count
        result['数据年数'] = round(years_count, 1)

        logger.info(f"✅ 基金 {fund_code} 分析完成，数据跨度: {years_count:.1f}年")

        return result

    except Exception as e:
        logger.warning(f"分析基金 {fund_code} 失败: {e}")
        return None


def analyze_user_funds(
    progress_callback=None
) -> Optional[Dict]:
    """
    分析用户所有基金的表现

    Args:
        progress_callback: 进度回调函数

    Returns:
        分析结果字典
    """
    # 获取用户的基金列表
    funds = get_user_funds()

    if not funds:
        logger.warning("未找到用户配置的基金")
        return None

    logger.info(f"开始分析 {len(funds)} 只用户基金...")

    results = []

    for idx, fund in enumerate(funds):
        fund_code = fund['code']
        fund_name = fund['name']

        # 更新进度
        if progress_callback:
            progress_callback(idx, len(funds), {'代码': fund_code, '名称': fund_name})

        # 分析基金
        performance = analyze_fund_performance(fund_code, fund_name)

        if performance:
            results.append(performance)

    if not results:
        logger.warning("没有成功分析任何基金")
        return None

    logger.info(f"✅ 分析完成：成功获取 {len(results)} 只基金的数据")

    return {
        "total_funds": len(funds),
        "analyzed_funds": len(results),
        "funds": results
    }
