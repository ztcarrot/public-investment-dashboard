#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金表现分析页面

从用户资产配置中读取基金，分析不同时间段的收益率和夏普比率。
"""

import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def fund_performance_page():
    """渲染基金表现分析页面"""
    st.title("📈 我的基金表现分析")

    from utils.fund_performance import analyze_user_funds
    from utils.fund_cache import fund_cache_manager

    # 顶部说明
    st.info("""
    💡 **基金表现分析**：从你的资产配置中读取所有基金，分析不同时间段的收益率和夏普比率。

    分析时间段：近1年、近3年、近5年、近10年、成立至今
    """)

    st.markdown("---")

    # 加载缓存数据
    cache_age = fund_cache_manager.get_cache_age_days()
    cache_data = fund_cache_manager.load()

    # 顶部控制栏
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("🔄 刷新数据", use_container_width=True):
            fund_cache_manager.clear()
            st.rerun()

    with col2:
        if cache_age >= 0:
            st.info(f"📅 缓存时间: {cache_age} 天前")
        else:
            st.info("📅 暂无缓存")

    with col3:
        if st.button("🏠 返回首页", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.session_state.page_selection = 0
            st.rerun()

    st.markdown("---")

    # 检查缓存是否过期
    is_expired = fund_cache_manager.is_expired(days=7)
    has_data = cache_data is not None and not is_expired

    if has_data:
        # 使用缓存数据
        funds = cache_data.get('funds', [])
        total_funds = cache_data.get('total_funds', 0)
        analyzed_funds = cache_data.get('analyzed_funds', 0)

        st.success(f"✅ 使用缓存数据：成功分析 {analyzed_funds} 只基金（共 {total_funds} 只）")

        # 展示分析结果
        _display_fund_performance(funds)

    else:
        # 重新获取数据
        st.info("🔄 正在分析你的基金表现...")

        # 创建进度条
        progress_bar = st.progress(0, text="正在获取基金数据...")
        status_text = st.empty()

        def update_progress(current, total, fund_info):
            """更新进度"""
            if total > 0:
                progress = min((current + 1) / total, 1.0)
                progress_bar.progress(progress, text=f"正在分析基金... ({current + 1}/{total})")

            if fund_info:
                status_text.text(f"📊 正在处理: {fund_info.get('名称', '')} ({fund_info.get('代码', '')})")
            else:
                status_text.empty()

        try:
            # 执行分析
            result = analyze_user_funds(progress_callback=update_progress)

            if result:
                # 保存到缓存
                fund_cache_manager.save(result)

                # 清空进度条
                progress_bar.empty()
                status_text.empty()

                # 展示结果
                funds = result.get('funds', [])
                total_funds = result.get('total_funds', 0)
                analyzed_funds = result.get('analyzed_funds', 0)

                st.success(f"✅ 分析完成：成功分析 {analyzed_funds} 只基金（共 {total_funds} 只）")

                # 展示分析结果
                _display_fund_performance(funds)
            else:
                progress_bar.empty()
                status_text.empty()
                st.error("❌ 分析失败，请检查配置文件中的基金是否正确")

        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            logger.error(f"基金分析失败: {e}")
            st.error(f"❌ 发生错误: {str(e)}")


def _display_fund_performance(funds: list):
    """
    展示基金表现分析结果

    Args:
        funds: 基金列表
    """
    if not funds:
        st.warning("⚠️ 没有找到基金数据")
        return

    # 转换为 DataFrame
    df = pd.DataFrame(funds)

    # 格式化显示
    display_df = df.copy()

    # 格式化收益率列
    for period in ['近1年', '近3年', '近5年', '近10年', '成立至今']:
        col = f'{period}收益率'
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) and x != 0 else "0.00%"
            )

    # 格式化最大回撤
    if '最大回撤' in display_df.columns:
        display_df['最大回撤'] = display_df['最大回撤'].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
        )

    # 格式化夏普比率
    for period in ['1年', '3年', '5年']:
        col = f'夏普比率{period}'
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
            )

    # 选择要显示的列
    display_cols = ['基金代码', '基金名称', '近1年收益率', '近3年收益率', '近5年收益率', '近10年收益率', '成立至今收益率', '最大回撤', '夏普比率1年', '夏普比率3年', '夏普比率5年']

    # 只显示存在的列
    display_cols = [col for col in display_cols if col in display_df.columns]

    st.markdown("### 📊 基金表现详情")
    st.dataframe(
        display_df[display_cols],
        use_container_width=True,
        hide_index=True
    )

    # 统计信息
    with st.expander("📈 统计摘要"):
        # 收益率统计（按时间段）
        periods = ['近1年', '近3年', '近5年', '近10年', '成立至今']

        for period in periods:
            col_name = f'{period}收益率'
            if col_name in df.columns:
                # 过滤掉 0 值（数据不足的情况）
                valid_returns = df[df[col_name] != 0][col_name]

                if len(valid_returns) > 0:
                    avg_return = valid_returns.mean()
                    max_return = valid_returns.max()
                    min_return = valid_returns.min()

                    st.markdown(f"**{period}收益率**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("平均", f"{avg_return:+.2f}%")
                    col2.metric("最高", f"{max_return:+.2f}%")
                    col3.metric("最低", f"{min_return:+.2f}%")
                    st.markdown("---")

        # 最大回撤统计
        if '最大回撤' in df.columns:
            avg_drawdown = df['最大回撤'].mean()
            max_drawdown = df['最大回撤'].min()  # 最小值 = 最大回撤
            min_drawdown = df['最大回撤'].max()  # 最大值 = 最小回撤

            st.markdown("**最大回撤**")
            col1, col2, col3 = st.columns(3)
            col1.metric("平均", f"{avg_drawdown:.2f}%")
            col2.metric("最差（最大）", f"{max_drawdown:.2f}%")
            col3.metric("最好（最小）", f"{min_drawdown:.2f}%")
            st.markdown("---")

        # 夏普比率统计
        sharpe_periods = ['1年', '3年', '5年']
        for period in sharpe_periods:
            col_name = f'夏普比率{period}'
            if col_name in df.columns:
                # 过滤掉 0 值
                valid_sharpe = df[df[col_name] != 0][col_name]

                if len(valid_sharpe) > 0:
                    avg_sharpe = valid_sharpe.mean()
                    max_sharpe = valid_sharpe.max()
                    min_sharpe = valid_sharpe.min()

                    st.markdown(f"**夏普比率（{period}）**")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("平均", f"{avg_sharpe:.2f}")
                    col2.metric("最高", f"{max_sharpe:.2f}")
                    col3.metric("最低", f"{min_sharpe:.2f}")
                    st.markdown("---")
