#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短债基金筛选模块 - 简化版

使用预定义的短债基金列表，快速获取表现数据。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# 导入项目的 DataFetcher
from utils.data_fetcher import DataFetcher


# 预定义的短债基金列表（知名基金 + 配置文件中的基金）
SAMPLE_SHORT_BOND_FUNDS = [
    {"code": "005350", "name": "嘉实短债A"},
    {"code": "006986", "name": "华夏短债A"},
    {"code": "007286", "name": "南方短债A"},
    {"code": "006988", "name": "易方达安悦超短债A"},
    {"code": "006989", "name": "广发短债A"},
    {"code": "007334", "name": "招商短债A"},
    {"code": "007614", "name": "工银瑞信短债A"},
    {"code": "007898", "name": "中欧短债A"},
    {"code": "008086", "name": "汇添富短债A"},
    {"code": "008138", "name": "富国短债A"},
    {"code": "5350", "name": "短债基金（用户配置）"},  # 来自配置文件
]


def get_config_funds() -> List[Dict]:
    """
    从配置文件中获取短债基金

    Returns:
        短债基金列表
    """
    try:
        import os
        from utils.config_manager import parse_secrets_assets

        # 读取配置文件
        config_file = os.path.join(os.path.dirname(__file__).replace('utils', ''), '.streamlit', 'secrets.toml')

        if not os.path.exists(config_file):
            logger.debug("未找到 secrets.toml 配置文件")
            return []

        # 解析配置
        import toml
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = toml.load(f)

        assets = config_data.get('assets', [])
        parsed_assets = parse_secrets_assets(assets)

        # 筛选短债基金（代码类型为"债券"或"基金"，且资产类别为"现金"）
        short_bond_funds = []
        seen_codes = set()

        for asset in parsed_assets:
            code_type = asset.get('代码类型', '')
            asset_category = asset.get('资产类别', '')
            fund_name = asset.get('名称', '')
            fund_code = asset.get('代码', '')

            # 判断是否为短债基金
            is_bond_fund = (
                code_type in ['债券', '基金'] and
                asset_category == '现金' and
                '短债' in fund_name
            )

            if is_bond_fund and fund_code and fund_code not in seen_codes:
                short_bond_funds.append({
                    'code': fund_code,
                    'name': fund_name
                })
                seen_codes.add(fund_code)

        logger.info(f"从配置文件中找到 {len(short_bond_funds)} 只短债基金")
        return short_bond_funds

    except Exception as e:
        logger.warning(f"读取配置文件失败: {e}")
        return []


def get_fund_performance(fund_code: str, fund_name: str = "") -> Optional[Dict]:
    """
    获取单只基金的表现数据

    Args:
        fund_code: 基金代码
        fund_name: 基金名称

    Returns:
        基金表现数据字典
    """
    try:
        logger.debug(f"正在获取基金 {fund_code} 的数据...")

        # 使用项目的 DataFetcher 获取历史数据
        fetcher = DataFetcher()

        # 获取最近3年的数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365*3)).strftime('%Y-%m-%d')

        # 使用东方财富接口获取数据（更快）
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

        # 计算指标
        result = calculate_performance_metrics(nav_df, fund_code, fund_name)

        return result

    except Exception as e:
        logger.warning(f"获取基金 {fund_code} 数据失败: {e}")
        return None


def calculate_performance_metrics(nav_df: pd.DataFrame, fund_code: str, fund_name: str = "") -> Dict:
    """
    计算基金表现指标

    Args:
        nav_df: 净值数据 DataFrame
        fund_code: 基金代码
        fund_name: 基金名称

    Returns:
        表现指标字典
    """
    try:
        result = {
            '基金代码': fund_code,
            '基金名称': fund_name,
            '近1年收益率': 0.0,
            '近3年收益率': 0.0,
            '最大回撤': 0.0,
            '夏普比率': 0.0,
        }

        if len(nav_df) < 2:
            return result

        # 获取最新净值
        latest_nav = nav_df.iloc[-1]['净值']
        latest_date = nav_df.iloc[-1]['日期']

        # 计算近1年收益率
        one_year_ago = latest_date - pd.Timedelta(days=365)
        one_year_data = nav_df[nav_df['日期'] >= one_year_ago]

        if len(one_year_data) > 0:
            nav_1y_ago = one_year_data.iloc[0]['净值']
            if nav_1y_ago > 0:
                result['近1年收益率'] = round((latest_nav / nav_1y_ago - 1) * 100, 2)

        # 计算近3年收益率
        three_year_ago = latest_date - pd.Timedelta(days=365 * 3)
        three_year_data = nav_df[nav_df['日期'] >= three_year_ago]

        if len(three_year_data) > 0:
            nav_3y_ago = three_year_data.iloc[0]['净值']
            if nav_3y_ago > 0:
                result['近3年收益率'] = round((latest_nav / nav_3y_ago - 1) * 100, 2)

        # 计算最大回撤
        nav_values = nav_df['净值'].values
        cummax = np.maximum.accumulate(nav_values)
        drawdown = (nav_values - cummax) / cummax * 100
        result['最大回撤'] = round(np.min(drawdown), 2)

        # 计算夏普比率（简化版）
        if len(nav_df) > 30:
            returns = np.diff(nav_values) / nav_values[:-1] * 100
            avg_return = np.mean(returns)
            std_return = np.std(returns)

            if std_return > 0:
                # 假设无风险利率为 2%
                risk_free_rate = 2.0 / 252  # 日化
                sharpe = (avg_return - risk_free_rate) / std_return
                # 年化
                result['夏普比率'] = round(sharpe * np.sqrt(252), 2)

        return result

    except Exception as e:
        logger.warning(f"计算基金 {fund_code} 指标失败: {e}")
        return {
            '基金代码': fund_code,
            '基金名称': '',
            '近1年收益率': 0.0,
            '近3年收益率': 0.0,
            '最大回撤': 0.0,
            '夏普比率': 0.0,
        }


def screen_funds_simple(
    progress_callback=None,
    fund_list: List[Dict] = None
) -> Optional[Dict]:
    """
    执行简化的基金筛选流程

    Args:
        progress_callback: 进度回调函数
        fund_list: 基金列表，如果为 None 则使用默认的10个基金

    Returns:
        筛选结果字典
    """
    # 使用预定义的基金列表
    if fund_list is None:
        fund_list = SAMPLE_SHORT_BOND_FUNDS

    logger.info(f"开始处理 {len(fund_list)} 只短债基金...")

    results = []

    for idx, fund in enumerate(fund_list):
        fund_code = fund['code']
        fund_name = fund['name']

        # 更新进度
        if progress_callback:
            progress_callback(idx, len(fund_list), {'代码': fund_code, '名称': fund_name})

        # 获取基金数据
        performance = get_fund_performance(fund_code, fund_name)

        if performance:
            results.append(performance)

        logger.info(f"已处理 ({idx + 1}/{len(fund_list)}): {fund_name} ({fund_code})")

    if not results:
        logger.warning("没有成功处理任何基金")
        return None

    logger.info(f"筛选完成：成功获取 {len(results)} 只基金的数据")

    return {
        "total_funds": len(fund_list),
        "screened_funds": results
    }


def get_sample_funds() -> List[Dict]:
    """
    获取预定义的基金列表 + 配置文件中的短债基金

    Returns:
        基金列表（已去重）
    """
    # 从配置文件获取短债基金
    config_funds = get_config_funds()

    # 合并预定义基金和配置基金，去重
    seen_codes = {fund['code'] for fund in SAMPLE_SHORT_BOND_FUNDS}
    all_funds = SAMPLE_SHORT_BOND_FUNDS.copy()

    for fund in config_funds:
        if fund['code'] not in seen_codes:
            all_funds.append(fund)
            seen_codes.add(fund['code'])

    logger.info(f"基金列表总数: {len(all_funds)} (预定义: {len(SAMPLE_SHORT_BOND_FUNDS)}, 配置文件: {len(config_funds)})")

    return all_funds
