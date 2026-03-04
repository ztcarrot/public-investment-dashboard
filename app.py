#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投资组合仪表盘 - 主应用
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging

from utils.data_fetcher import DataFetcher
from utils.config_manager import get_default_assets, parse_secrets_assets, validate_asset, calculate_shares_or_amount
from utils.local_storage import save_to_localstorage, load_from_localstorage
import json

# 配置日志
logger = logging.getLogger(__name__)


# 页面配置
st.set_page_config(
    page_title="投资组合仪表盘",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(ttl=3600)
def load_data(date_range="最近90天"):
    """加载或抓取数据"""
    assets = st.session_state.get('assets', [])

    if not assets:
        return None, None

    # 根据选择计算日期范围
    days_map = {
        "最近90天": 90,
        "最近180天": 180,
        "最近365天": 365
    }
    days = days_map.get(date_range, 90)

    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # 抓取数据
    fetcher = DataFetcher()

    with st.spinner(f"🔄 正在抓取最近{days}天数据..."):
        historical_data = fetcher.fetch_all_assets_data(assets, start_date, end_date)

    if historical_data.empty:
        return None, None

    # 生成组合数据
    portfolio_data = fetcher.get_portfolio_summary(historical_data)

    return historical_data, portfolio_data


def render_total_assets_chart(portfolio_data):
    """渲染总资产走势图"""
    if portfolio_data is None or portfolio_data.empty:
        return

    fig = go.Figure()

    # 添加总资产折线
    fig.add_trace(go.Scatter(
        x=portfolio_data['日期'],
        y=portfolio_data['总资产'],
        mode='lines+markers',
        name='总资产',
        line=dict(color='#d62728', width=3),
        marker=dict(size=6),
        hovertemplate='%{x}<br>总资产: ¥%{y:,.2f}<extra></extra>'
    ))

    # 添加趋势线
    if len(portfolio_data) > 1:
        import numpy as np
        x = list(range(len(portfolio_data)))
        y = portfolio_data['总资产'].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        trend_line = p(x)

        fig.add_trace(go.Scatter(
            x=portfolio_data['日期'],
            y=trend_line,
            mode='lines',
            name='趋势线',
            line=dict(color='gray', width=2, dash='dash'),
            hovertemplate='趋势: ¥%{y:,.2f}<extra></extra>'
        ))

    fig.update_layout(
        title="总资产走势",
        xaxis_title="日期",
        yaxis_title="总资产（元）",
        hovermode='x unified',
        template='plotly_white',
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)


def render_allocation_chart(portfolio_data):
    """渲染资产配置图"""
    if portfolio_data is None or portfolio_data.empty:
        return

    st.subheader("当前资产配置（最新一天）")

    # 创建子图 - 饼图
    fig_pie = make_subplots(
        rows=1, cols=2,
        subplot_titles=('资产金额分布', '资产占比分布'),
        specs=[[{'type': 'pie'}, {'type': 'pie'}]]
    )

    latest = portfolio_data.iloc[-1]

    # 资产金额饼图
    fig_pie.add_trace(
        go.Pie(
            labels=['股票', '黄金', '现金', '国债'],
            values=[latest['股票'], latest['黄金'], latest['现金'], latest['国债']],
            name="金额",
            textinfo='label+percent',
            texttemplate='%{label}<br>¥%{value:,.0f}<br>(%{percent})'
        ),
        row=1, col=1
    )

    # 资产占比饼图
    fig_pie.add_trace(
        go.Pie(
            labels=['股票', '黄金', '现金', '国债'],
            values=[latest['股票占比'], latest['黄金占比'], latest['现金占比'], latest['国债占比']],
            name="占比",
            textinfo='label+percent',
            texttemplate='%{label}<br>%{percent}'
        ),
        row=1, col=2
    )

    fig_pie.update_layout(
        template='plotly_white',
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    st.subheader("资产配置趋势")

    # 占比堆叠面积图
    fig_percentage = go.Figure()

    # 添加四个资产类型的占比线（堆叠面积图）
    for asset_type in ['国债', '现金', '黄金', '股票']:  # 按照从下到上的顺序
        fig_percentage.add_trace(go.Scatter(
            x=portfolio_data['日期'],
            y=portfolio_data[f'{asset_type}占比'],
            mode='lines',
            name=asset_type,
            stackgroup='one',  # 启用堆叠
            fill='tonexty',     # 填充到下一个轨迹
            line=dict(width=1),
            hovertemplate='%{x}<br>%{fullData.name}: %{y:.2f}%<extra></extra>'
        ))

    fig_percentage.update_layout(
        title="资产占比趋势（堆叠面积图）",
        xaxis_title="日期",
        yaxis_title="占比 (%)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        yaxis=dict(range=[0, 100])
    )

    st.plotly_chart(fig_percentage, use_container_width=True)

    # 显示第一个和最后一个占比数值
    st.caption("📊 占比变化：")
    first_row = portfolio_data.iloc[0]
    last_row = portfolio_data.iloc[-1]

    for asset_type in ['股票', '黄金', '现金', '国债']:
        first_val = first_row[f'{asset_type}占比']
        last_val = last_row[f'{asset_type}占比']
        change = last_val - first_val
        change_str = f"({change:+.2f}%)" if change != 0 else ""
        st.caption(f"  **{asset_type}**: {first_val:.2f}% → {last_val:.2f}% {change_str}")

    # 金额堆叠面积图
    fig_amount = go.Figure()

    # 添加四个资产类型的金额线（堆叠面积图）
    for asset_type in ['国债', '现金', '黄金', '股票']:  # 按照从下到上的顺序
        fig_amount.add_trace(go.Scatter(
            x=portfolio_data['日期'],
            y=portfolio_data[asset_type],
            mode='lines',
            name=asset_type,
            stackgroup='one',  # 启用堆叠
            fill='tonexty',     # 填充到下一个轨迹
            line=dict(width=1),
            hovertemplate='%{x}<br>%{fullData.name}: ¥%{y:,.2f}<extra></extra>'
        ))

    # 添加总资产线（虚线）
    fig_amount.add_trace(go.Scatter(
        x=portfolio_data['日期'],
        y=portfolio_data['总资产'],
        mode='lines',
        name='总资产',
        line=dict(color='black', width=2, dash='dash'),
        hovertemplate='%{x}<br>总资产: ¥%{y:,.2f}<extra></extra>'
    ))

    fig_amount.update_layout(
        title="资产金额趋势（堆叠面积图）",
        xaxis_title="日期",
        yaxis_title="金额（元）",
        hovermode='x unified',
        template='plotly_white',
        height=400
    )

    st.plotly_chart(fig_amount, use_container_width=True)


def render_asset_performance(historical_data):
    """渲染各标的收益表现（归一化）"""
    if historical_data is None or historical_data.empty:
        return

    # 按资产类型分组
    asset_types = historical_data['资产类型'].unique()

    for asset_type in asset_types:
        st.markdown(f"### {asset_type}类标的走势（归一化）")

        # 获取该资产类型的所有数据
        asset_data = historical_data[historical_data['资产类型'] == asset_type]

        # 按标的分组绘制折线图
        fig = go.Figure()

        for asset_name in asset_data['名称'].unique():
            asset_subset = asset_data[asset_data['名称'] == asset_name].copy()

            # 归一化：第一天设为100
            first_value = asset_subset['当前市值'].iloc[0]
            if first_value > 0:
                asset_subset['归一化值'] = (asset_subset['当前市值'] / first_value) * 100
            else:
                asset_subset['归一化值'] = 100

            # 保存原始值用于 hover 显示
            asset_subset['原始市值'] = asset_subset['当前市值']

            fig.add_trace(go.Scatter(
                x=asset_subset['日期'],
                y=asset_subset['归一化值'],
                mode='lines+markers',
                name=asset_name,
                line=dict(width=2),
                marker=dict(size=4),
                hovertemplate='%{x}<br>%{fullData.name}<br>归一化: %{y:.2f}<br>实际: ¥%{customdata[0]:,.2f}<extra></extra>',
                customdata=asset_subset[['原始市值']].values
            ))

        fig.update_layout(
            title=f"{asset_type}类标的走势（归一化，起点=100）",
            xaxis_title="日期",
            yaxis_title="相对值（起点=100）",
            hovermode='x unified',
            template='plotly_white',
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption("💡 归一化说明：所有标的起点设为100，便于比较相对走势")


def render_data_table(historical_data, portfolio_data):
    """渲染完整数据表格"""
    if historical_data is None or historical_data.empty:
        return

    st.subheader("📊 历史数据")

    # 按日期透视表格
    pivot_data = historical_data.pivot_table(
        index='日期',
        columns='名称',
        values='当前市值',
        aggfunc='sum'
    )

    st.dataframe(
        pivot_data.style.format('¥{:,.2f}'),
        use_container_width=True,
        height=400
    )

    st.markdown("---")

    st.subheader("📈 资产组合汇总")

    # 显示汇总数据
    display_df = portfolio_data.copy()
    display_df['日期'] = pd.to_datetime(display_df['日期']).dt.strftime('%Y-%m-%d')
    display_df['总资产'] = display_df['总资产'].apply(lambda x: f'¥{x:,.2f}')
    display_df['股票'] = display_df['股票'].apply(lambda x: f'¥{x:,.2f}')
    display_df['黄金'] = display_df['黄金'].apply(lambda x: f'¥{x:,.2f}')
    display_df['现金'] = display_df['现金'].apply(lambda x: f'¥{x:,.2f}')
    display_df['国债'] = display_df['国债'].apply(lambda x: f'¥{x:,.2f}')

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


def load_assets_config():
    """加载资产配置 - 按优先级"""
    # 1. 尝试从 LocalStorage 加载
    local_config = load_from_localstorage('investment_assets')
    if local_config and len(local_config) > 0:
        logger.info("从 LocalStorage 加载配置")
        return local_config

    # 2. 尝试从 secrets 加载
    if hasattr(st, 'secrets') and 'assets' in st.secrets:
        logger.info("从 secrets.toml 加载配置")
        return parse_secrets_assets(st.secrets['assets'])

    # 3. 使用默认配置
    logger.info("使用默认配置")
    return get_default_assets()


def main():
    """主函数"""

    st.title("📊 投资组合仪表盘")
    st.markdown("---")

    # 初始化session state
    if 'assets' not in st.session_state:
        st.session_state.assets = load_assets_config()

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # 初始化数字显示状态（默认隐藏）
    if 'show_numbers' not in st.session_state:
        st.session_state.show_numbers = False

    # 检查是否有配置
    assets = st.session_state.get('assets', [])

    if not assets:
        st.warning("⚠️ 尚未配置任何资产")
        st.info("💡 请在 Streamlit Secrets 中配置 `assets` 来使用此应用")
        return

    # 数据抓取按钮
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        st.info(f"📌 当前已配置 {len(assets)} 个资产")

    with col2:
        if st.button("🔄 刷新数据", type="primary"):
            st.cache_data.clear()
            st.rerun()

    with col3:
        # 日期范围选择
        date_range = st.selectbox(
            "数据范围",
            options=["最近90天", "最近180天", "最近365天"],
            index=0
        )

    with col4:
        # 眼睛按钮：切换显示/隐藏数字
        eye_icon = "👁️" if st.session_state.show_numbers else "🙈"
        if st.button(f"{eye_icon} {'隐藏' if st.session_state.show_numbers else '显示'}数字", key="toggle_numbers"):
            st.session_state.show_numbers = not st.session_state.show_numbers
            st.rerun()

    st.markdown("---")

    # 加载数据
    historical_data, portfolio_data = load_data(date_range)

    if historical_data is None or portfolio_data is None:
        st.error("❌ 数据加载失败，请检查网络连接或配置")
        return

    # 统计卡片（根据状态显示或隐藏）
    if st.session_state.show_numbers:
        latest = portfolio_data.iloc[-1]

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            # 显示最后一天相比前一天的变化
            if len(portfolio_data) >= 2:
                previous_value = portfolio_data['总资产'].iloc[-2]
                daily_change = ((latest['总资产'] - previous_value) / previous_value * 100)
                st.metric("总资产", f"¥{latest['总资产']:,.2f}", f"{daily_change:+.2f}%")
            else:
                st.metric("总资产", f"¥{latest['总资产']:,.2f}")

        with col2:
            if len(portfolio_data) >= 2:
                previous_stock = portfolio_data['股票'].iloc[-2]
                stock_change = ((latest['股票'] - previous_stock) / previous_stock * 100) if previous_stock > 0 else 0
                st.metric("股票占比", f"{latest['股票占比']:.2f}%", f"{stock_change:+.2f}%")
            else:
                st.metric("股票占比", f"{latest['股票占比']:.2f}%", f"¥{latest['股票']:,.2f}")

        with col3:
            if len(portfolio_data) >= 2:
                previous_gold = portfolio_data['黄金'].iloc[-2]
                gold_change = ((latest['黄金'] - previous_gold) / previous_gold * 100) if previous_gold > 0 else 0
                st.metric("黄金占比", f"{latest['黄金占比']:.2f}%", f"{gold_change:+.2f}%")
            else:
                st.metric("黄金占比", f"{latest['黄金占比']:.2f}%", f"¥{latest['黄金']:,.2f}")

        with col4:
            if len(portfolio_data) >= 2:
                previous_cash = portfolio_data['现金'].iloc[-2]
                cash_change = ((latest['现金'] - previous_cash) / previous_cash * 100) if previous_cash > 0 else 0
                st.metric("现金占比", f"{latest['现金占比']:.2f}%", f"{cash_change:+.2f}%")
            else:
                st.metric("现金占比", f"{latest['现金占比']:.2f}%", f"¥{latest['现金']:,.2f}")

        with col5:
            if len(portfolio_data) >= 2:
                previous_bond = portfolio_data['国债'].iloc[-2]
                bond_change = ((latest['国债'] - previous_bond) / previous_bond * 100) if previous_bond > 0 else 0
                st.metric("国债占比", f"{latest['国债占比']:.2f}%", f"{bond_change:+.2f}%")
            else:
                st.metric("国债占比", f"{latest['国债占比']:.2f}%", f"¥{latest['国债']:,.2f}")

        st.markdown("---")
    else:
        # 隐藏数字时显示提示
        st.info("💡 点击右上角的 🙈 按钮显示资产数据")

    # 图表
    tab1, tab2, tab3, tab4 = st.tabs(["📈 总资产走势", "🥧 资产配置", "📊 标的表现", "📋 数据表格"])

    with tab1:
        render_total_assets_chart(portfolio_data)

    with tab2:
        render_allocation_chart(portfolio_data)

    with tab3:
        render_asset_performance(historical_data)

    with tab4:
        render_data_table(historical_data, portfolio_data)


if __name__ == "__main__":
    main()
