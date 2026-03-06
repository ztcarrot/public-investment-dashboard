#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
短债基金筛选模块

使用 akshare API 获取基金数据，按年化收益率和最大回撤筛选短债基金。
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# 尝试导入 akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    logger.info("akshare 库可用")
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("akshare 库不可用，基金筛选功能将无法使用")


def get_all_funds() -> Optional[pd.DataFrame]:
    """
    获取所有基金列表

    Returns:
        基金列表 DataFrame，包含列：基金代码、基金简称、基金类型、成立日期等
        如果获取失败返回 None
    """
    if not AKSHARE_AVAILABLE:
        logger.error("akshare 不可用，无法获取基金列表")
        return None

    try:
        logger.info("正在获取所有基金列表...")
        funds_df = ak.fund_name_em()
        logger.info(f"成功获取 {len(funds_df)} 只基金")
        return funds_df
    except Exception as e:
        logger.error(f"获取基金列表失败: {e}")
        return None


def filter_short_bond_funds(
    funds_df: pd.DataFrame,
    min_years: int = 5
) -> pd.DataFrame:
    """
    筛选短债基金

    筛选条件：
    1. 基金简称包含"短债"
    2. 成立日期距今 >= min_years 年

    Args:
        funds_df: 基金列表 DataFrame
        min_years: 最小成立年限

    Returns:
        筛选后的短债基金 DataFrame
    """
    if funds_df is None or funds_df.empty:
        return pd.DataFrame()

    # 确保有必需的列
    required_cols = ['基金代码', '基金简称', '成立日期']
    missing_cols = [col for col in required_cols if col not in funds_df.columns]
    if missing_cols:
        logger.error(f"基金数据缺少必需的列: {missing_cols}")
        return pd.DataFrame()

    # 筛选名称包含"短债"的基金
    filtered = funds_df[funds_df['基金简称'].str.contains('短债', na=False)].copy()

    # 转换成立日期
    try:
        filtered['成立日期'] = pd.to_datetime(filtered['成立日期'])
    except Exception as e:
        logger.error(f"转换成立日期失败: {e}")
        return pd.DataFrame()

    # 筛选成立年限
    cutoff_date = datetime.now() - timedelta(days=min_years * 365)
    filtered = filtered[filtered['成立日期'] <= cutoff_date].copy()

    logger.info(f"筛选出 {len(filtered)} 只短债基金（成立≥{min_years}年）")
    return filtered


def get_fund_nav_history(fund_code: str) -> Optional[pd.DataFrame]:
    """
    获取基金历史净值数据

    Args:
        fund_code: 基金代码

    Returns:
        历史净值 DataFrame，包含列：日期、净值
        如果获取失败返回 None
    """
    if not AKSHARE_AVAILABLE:
        return None

    try:
        # 使用东方财富接口获取历史净值
        nav_df = ak.fund_open_fund_info_em(
            fund=fund_code,
            indicator="单位净值走势"
        )

        if nav_df is None or nav_df.empty:
            logger.warning(f"基金 {fund_code} 无净值数据")
            return None

        # 确保有净值列
        if '净值日期' not in nav_df.columns or '单位净值' not in nav_df.columns:
            logger.warning(f"基金 {fund_code} 数据格式不符合预期")
            return None

        # 重命名列并排序
        nav_df = nav_df[['净值日期', '单位净值']].copy()
        nav_df.columns = ['日期', '净值']
        nav_df['日期'] = pd.to_datetime(nav_df['日期'])
        nav_df = nav_df.sort_values('日期').reset_index(drop=True)

        return nav_df

    except Exception as e:
        logger.warning(f"获取基金 {fund_code} 净值数据失败: {e}")
        return None


def calculate_annual_return(nav_data: pd.DataFrame) -> float:
    """
    计算年化收益率

    公式: 年化收益率 = (当前净值 / 初始净值) ^ (365 / 运营天数) - 1

    Args:
        nav_data: 净值数据 DataFrame，包含列：日期、净值

    Returns:
        年化收益率（百分比），如果计算失败返回 0.0
    """
    try:
        if nav_data is None or len(nav_data) < 2:
            return 0.0

        # 获取初始和最终净值
        initial_nav = nav_data.iloc[0]['净值']
        final_nav = nav_data.iloc[-1]['净值']

        if initial_nav <= 0 or final_nav <= 0:
            return 0.0

        # 计算运营天数
        initial_date = nav_data.iloc[0]['日期']
        final_date = nav_data.iloc[-1]['日期']
        days = (final_date - initial_date).days

        if days <= 0:
            return 0.0

        # 计算年化收益率
        total_return = final_nav / initial_nav
        annual_return = (total_return ** (365 / days) - 1) * 100

        return round(annual_return, 2)

    except Exception as e:
        logger.warning(f"计算年化收益率失败: {e}")
        return 0.0


def calculate_max_drawdown(nav_data: pd.DataFrame) -> float:
    """
    计算最大回撤

    公式: 回撤 = (峰值 - 当前值) / 峰值

    Args:
        nav_data: 净值数据 DataFrame，包含列：日期、净值

    Returns:
        最大回撤（负百分比），如果计算失败返回 0.0
    """
    try:
        if nav_data is None or len(nav_data) < 2:
            return 0.0

        # 计算累计最高净值
        nav_values = nav_data['净值'].values
        cummax = np.maximum.accumulate(nav_values)

        # 计算回撤
        drawdown = (nav_values - cummax) / cummax * 100

        # 最大回撤
        max_dd = np.min(drawdown)

        return round(max_dd, 2)

    except Exception as e:
        logger.warning(f"计算最大回撤失败: {e}")
        return 0.0


def screen_funds(
    progress_callback=None,
    top_n_annual: int = 100,
    top_n_drawdown: int = 30
) -> Optional[Dict]:
    """
    执行完整的基金筛选流程

    筛选步骤：
    1. 获取所有基金
    2. 筛选短债基金（名称包含"短债"，成立≥5年）
    3. 计算年化收益率和最大回撤
    4. 按年化收益率选前 N 只
    5. 按最大回撤选前 M 只

    Args:
        progress_callback: 进度回调函数，签名为 (current, total, fund_info)
        top_n_annual: 按年化收益率筛选的前 N 只
        top_n_drawdown: 按最大回撤筛选的前 M 只

    Returns:
        筛选结果字典，格式：
        {
            "total_funds": int,
            "screened_funds": List[Dict]
        }
        如果失败返回 None
    """
    if not AKSHARE_AVAILABLE:
        logger.error("akshare 不可用，无法进行基金筛选")
        return None

    # 步骤1: 获取所有基金
    all_funds = get_all_funds()
    if all_funds is None:
        return None

    # 步骤2: 筛选短债基金
    short_bond_funds = filter_short_bond_funds(all_funds, min_years=5)

    if short_bond_funds.empty:
        logger.warning("未找到符合条件的短债基金")
        return {
            "total_funds": 0,
            "screened_funds": []
        }

    total_count = len(short_bond_funds)
    logger.info(f"开始处理 {total_count} 只短债基金...")

    # 步骤3: 计算指标（并行处理）
    results = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        # 提交所有任务
        future_to_fund = {}
        for idx, fund_row in short_bond_funds.iterrows():
            fund_code = fund_row['基金代码']
            future = executor.submit(
                process_single_fund,
                fund_row,
                idx,
                total_count,
                progress_callback
            )
            future_to_fund[future] = fund_code

        # 收集结果
        for future in as_completed(future_to_fund):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                fund_code = future_to_fund[future]
                logger.warning(f"处理基金 {fund_code} 时出错: {e}")

    if not results:
        logger.warning("没有成功处理任何基金")
        return None

    # 转换为 DataFrame
    results_df = pd.DataFrame(results)

    # 步骤4: 按年化收益率选前 N 只
    top_annual = results_df.nlargest(top_n_annual, '年化收益率')

    # 步骤5: 按最大回撤选前 M 只
    top_drawdown = top_annual.nsmallest(top_n_drawdown, '最大回撤')

    # 转换为列表
    screened_funds = top_drawdown.to_dict('records')

    logger.info(f"筛选完成：从 {total_count} 只中筛选出 {len(screened_funds)} 只")

    return {
        "total_funds": total_count,
        "screened_funds": screened_funds
    }


def process_single_fund(
    fund_row: pd.Series,
    idx: int,
    total: int,
    progress_callback=None
) -> Optional[Dict]:
    """
    处理单只基金：获取净值、计算指标

    Args:
        fund_row: 基金数据行
        idx: 当前索引
        total: 总数
        progress_callback: 进度回调函数

    Returns:
        基金数据字典，包含计算后的指标
    """
    fund_code = fund_row['基金代码']
    fund_name = fund_row['基金简称']

    try:
        # 更新进度
        if progress_callback:
            progress_callback(idx, total, {'代码': fund_code, '名称': fund_name})

        # 获取历史净值
        nav_data = get_fund_nav_history(fund_code)

        if nav_data is None or nav_data.empty:
            logger.debug(f"基金 {fund_code} 无净值数据，跳过")
            return None

        # 计算指标
        annual_return = calculate_annual_return(nav_data)
        max_drawdown = calculate_max_drawdown(nav_data)

        # 构建结果
        result = {
            '基金代码': fund_code,
            '基金简称': fund_name,
            '基金类型': fund_row.get('基金类型', ''),
            '成立日期': pd.to_datetime(fund_row['成立日期']).strftime('%Y-%m-%d'),
            '年化收益率': annual_return,
            '最大回撤': max_drawdown,
        }

        # 尝试添加其他信息
        if '基金规模' in fund_row:
            result['基金规模'] = fund_row.get('基金规模', '')

        if '基金经理' in fund_row:
            result['基金经理'] = fund_row.get('基金经理', '')

        if '基金公司' in fund_row:
            result['基金公司'] = fund_row.get('基金公司', '')

        return result

    except Exception as e:
        logger.warning(f"处理基金 {fund_code} 失败: {e}")
        return None
