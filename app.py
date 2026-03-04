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
from utils.local_storage import save_to_session, load_from_session
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


def calculate_change_percentages(portfolio_data, asset_name='总资产'):
    """计算不同时间段的涨跌幅"""
    if portfolio_data is None or portfolio_data.empty or len(portfolio_data) < 2:
        return None

    latest = portfolio_data[asset_name].iloc[-1]

    result = {
        'latest': latest,
        'daily_change': None,
        'weekly_change': None,
        'monthly_change': None,
        'total_change': None
    }

    # 日涨幅（相比前一天）
    if len(portfolio_data) >= 2:
        previous = portfolio_data[asset_name].iloc[-2]
        if previous > 0:
            result['daily_change'] = ((latest - previous) / previous * 100)

    # 周涨幅（相比7天前）
    if len(portfolio_data) >= 7:
        week_ago = portfolio_data[asset_name].iloc[-7]
        if week_ago > 0:
            result['weekly_change'] = ((latest - week_ago) / week_ago * 100)

    # 月涨幅（相比30天前）
    if len(portfolio_data) >= 30:
        month_ago = portfolio_data[asset_name].iloc[-30]
        if month_ago > 0:
            result['monthly_change'] = ((latest - month_ago) / month_ago * 100)

    # 总涨幅（相比第一天）
    if len(portfolio_data) >= 2:
        first = portfolio_data[asset_name].iloc[0]
        if first > 0:
            result['total_change'] = ((latest - first) / first * 100)

    return result


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


def render_config_manager():
    """渲染配置管理页面 - 使用表单编辑"""
    st.title("⚙️ 配置管理")
    st.markdown("---")

    # 操作按钮
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("➕ 添加资产", type="primary"):
            st.session_state.show_add_form = True
            st.session_state.editing_index = None
            st.rerun()

    with col2:
        if st.button("📤 导出配置", type="secondary"):
            assets = st.session_state.get('assets', [])
            if assets:
                json_data = json.dumps(assets, ensure_ascii=False, indent=2)
                st.download_button(
                    label="下载配置文件",
                    data=json_data,
                    file_name=f"investment_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

    with col3:
        uploaded_file = st.file_uploader(
            "📥 导入配置",
            type=['json'],
            label_visibility="collapsed",
            key="config_upload"
        )
        if uploaded_file is not None:
            try:
                json_data = json.load(uploaded_file)
                if isinstance(json_data, list):
                    valid_assets = []
                    for asset in json_data:
                        is_valid, error_msg = validate_asset(asset)
                        if is_valid:
                            valid_assets.append(asset)
                    if valid_assets:
                        st.session_state.assets = valid_assets
                        save_to_session('investment_assets', valid_assets)
                        # 清除缓存并跳转到首页
                        st.cache_data.clear()
                        st.session_state.current_page = 'dashboard'
                        st.success(f"✅ 成功导入 {len(valid_assets)} 个资产配置")
                        st.rerun()
                    else:
                        st.error("❌ 导入的配置中没有有效的资产")
                else:
                    st.error("❌ 配置文件格式错误：应为资产列表")
            except Exception as e:
                st.error(f"❌ 导入配置失败: {str(e)}")

    with col4:
        if st.button("🔄 使用默认配置", type="secondary"):
            if 'confirm_reset' not in st.session_state:
                st.session_state.confirm_reset = False

            if not st.session_state.confirm_reset:
                st.warning("⚠️ 将切换到默认的4个资产配置，当前配置将被覆盖")
                if st.button("确认切换", key="confirm_reset_btn"):
                    st.session_state.confirm_reset = True
                    st.rerun()
            else:
                default_assets = get_default_assets()
                st.session_state.assets = default_assets
                save_to_session('investment_assets', default_assets)
                st.session_state.confirm_reset = False
                # 清除缓存并跳转到首页
                st.cache_data.clear()
                st.session_state.current_page = 'dashboard'
                st.success("✅ 已切换到默认配置（4个资产）")
                st.rerun()

    st.markdown("---")

    # 添加/编辑资产表单
    if st.session_state.get('show_add_form', False):
        st.subheader("📝 添加/编辑资产")

        # 金额计算器（在表单外面）
        if st.session_state.get('show_calculator', False):
            st.markdown("---")
            st.markdown("### 💰 金额计算器")
            st.caption("输入您想要投资的金额，系统会根据当前价格自动计算份额")

            # 重新获取价格（如果还没有）
            if not st.session_state.get('calc_price_fetched', False):
                calc_code = st.session_state.get('calc_code', '')
                calc_code_type = st.session_state.get('calc_code_type', '')

                if calc_code and len(calc_code) == 6:
                    with st.spinner(f"正在获取 {calc_code} 的当前价格..."):
                        try:
                            fetcher = DataFetcher()
                            from datetime import datetime, timedelta
                            end = datetime.now().strftime('%Y-%m-%d')
                            start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

                            temp_asset = {
                                '代码': calc_code,
                                '代码类型': calc_code_type,
                                '初始份额': 1.0
                            }
                            history = fetcher.fetch_asset_data(temp_asset, start, end)
                            if not history.empty and '净值' in history.columns:
                                st.session_state.calc_price = history['净值'].iloc[-1]
                                st.session_state.calc_price_fetched = True
                        except Exception as e:
                            st.error(f"❌ 无法获取价格: {str(e)}")
                            if st.button("🔄 重试"):
                                st.session_state.calc_price_fetched = False
                                st.rerun()

            if st.session_state.get('calc_price_fetched', False) and not st.session_state.get('calc_price', None):
                st.warning("⚠️ 请先返回表单输入有效的代码")
                if st.button("🔙 返回表单"):
                    st.session_state.show_calculator = False
                    st.rerun()

            if st.session_state.get('calc_price', None):
                calc_amount = st.number_input(
                    "投资金额（元）*",
                    min_value=0.0,
                    step=1000.0,
                    value=10000.0,
                    format="%.2f",
                    help="输入您想投资的金额"
                )

                if calc_amount > 0:
                    current_price = st.session_state.calc_price
                    calculated_shares = calc_amount / current_price
                    st.info(f"💵 投资金额: ¥{calc_amount:,.2f} | 当前价格: ¥{current_price:.4f} | **计算份额: {calculated_shares:,.2f} 份**")

                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ 确认使用", use_container_width=True):
                            st.session_state.calc_result_shares = calculated_shares
                            st.session_state.show_calculator = False
                            st.success("✅ 份额已计算，请返回表单查看")
                            st.rerun()
                    with col_cancel:
                        if st.button("❌ 取消", use_container_width=True):
                            st.session_state.show_calculator = False
                            st.rerun()
                else:
                    st.warning("⚠️ 请输入有效的金额")

            if st.button("🔙 返回表单"):
                st.session_state.show_calculator = False
                st.rerun()

            st.markdown("---")

        # 表单
        editing_index = st.session_state.get('editing_index')
        is_edit = editing_index is not None

        if is_edit:
            assets = st.session_state.get('assets', [])
            current_asset = assets[editing_index]
            st.info(f"✏️ 正在编辑：{current_asset.get('名称', '未知')}")
        else:
            current_asset = {}

        with st.form(key="asset_form"):
            col_form1, col_form2 = st.columns(2)

            with col_form1:
                code = st.text_input(
                    "代码 *",
                    value=current_asset.get('代码', ''),
                    help="6位代码，如：511130"
                ).strip()

                name = st.text_input(
                    "名称 *",
                    value=current_asset.get('名称', ''),
                    help="资产名称"
                ).strip()

                code_type = st.selectbox(
                    "代码类型 *",
                    options=['场内ETF', '基金', '股票', '债券'],
                    index=['场内ETF', '基金', '股票', '债券'].index(current_asset.get('代码类型', '场内ETF')),
                    help="选择代码类型",
                    key="form_code_type"
                )

                # 保存到session_state供计算器使用
                if code:
                    st.session_state.temp_code = code
                if name:
                    st.session_state.temp_name = name
                st.session_state.temp_code_type = code_type

            with col_form2:
                asset_category = st.selectbox(
                    "资产类别 *",
                    options=['国债', '股票', '黄金', '现金'],
                    index=['国债', '股票', '黄金', '现金'].index(current_asset.get('资产类别', '股票')),
                    help="选择资产类别",
                    key="form_asset_category"
                )

                # 保存到session_state供计算器使用
                st.session_state.temp_asset_category = asset_category

                # 持有份额输入
                st.markdown("**持有信息**")
                st.caption("输入持有份额，或使用表单下方的「💰 金额计算器」按钮")

                # 获取当前价格（用于显示）
                current_price = None
                if code and len(code) == 6:
                    if 'current_price_cache' not in st.session_state:
                        st.session_state.current_price_cache = {}

                    cache_key = f"{code}_{code_type}"
                    if cache_key not in st.session_state.current_price_cache:
                        with st.spinner(f"正在获取 {code} 的当前价格..."):
                            try:
                                fetcher = DataFetcher()
                                from datetime import datetime, timedelta
                                end = datetime.now().strftime('%Y-%m-%d')
                                start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

                                temp_asset = {
                                    '代码': code,
                                    '代码类型': code_type,
                                    '初始份额': 1.0
                                }
                                history = fetcher.fetch_asset_data(temp_asset, start, end)
                                if not history.empty and '净值' in history.columns:
                                    current_price = history['净值'].iloc[-1]
                                    st.session_state.current_price_cache[cache_key] = current_price
                            except Exception as e:
                                st.warning(f"⚠️ 无法获取价格: {str(e)}")
                    else:
                        current_price = st.session_state.current_price_cache.get(cache_key)

                # 显示金额计算器入口提示
                st.markdown("**持有份额**")
                st.caption("输入持有份额，或使用表单下方的「💰 金额计算器」按钮")

                default_shares = current_asset.get('初始份额', 0)
                # 如果通过计算器计算了份额，使用计算的结果
                if st.session_state.get('calc_result_shares'):
                    default_shares = st.session_state.calc_result_shares
                    del st.session_state.calc_result_shares

                shares = st.number_input(
                    "持有份额 *",
                    min_value=0.0,
                    step=100.0,
                    value=float(default_shares) if default_shares else 0.0,
                    format="%.2f",
                    help="输入持有份额",
                    key="form_shares"
                )

                # 显示当前价格信息
                if current_price:
                    if shares and shares > 0:
                        estimated_value = current_price * shares
                        st.info(f"💰 当前价格: ¥{current_price:.4f} | 预估市值: ¥{estimated_value:,.2f}")
                    else:
                        st.info(f"💰 当前价格: ¥{current_price:.4f}")
                else:
                    st.caption("💡 输入代码后自动获取当前价格")

            col_submit1, col_submit2, col_submit3 = st.columns(3)

            with col_submit1:
                submit = st.form_submit_button("💾 保存", use_container_width=True)

            with col_submit2:
                cancel = st.form_submit_button("❌ 取消", use_container_width=True)

            with col_submit3:
                if is_edit:
                    delete = st.form_submit_button("🗑️ 删除", use_container_width=True)

            if submit:
                # 构建资产数据
                asset = {
                    '代码': code,
                    '名称': name,
                    '代码类型': code_type,
                    '资产类别': asset_category,
                    '初始份额': shares,
                    '初始金额': None  # 统一使用份额，金额为None
                }

                # 验证
                is_valid, error_msg = validate_asset(asset)
                if not is_valid:
                    st.error(f"❌ {error_msg}")
                else:
                    assets = st.session_state.get('assets', [])

                    if is_edit:
                        assets[editing_index] = asset
                        st.success(f"✅ 已更新资产：{name}")
                    else:
                        assets.append(asset)
                        st.success(f"✅ 已添加资产：{name}")

                    st.session_state.assets = assets
                    save_to_session('investment_assets', assets)
                    st.session_state.show_add_form = False
                    st.session_state.editing_index = None
                    # 清除缓存并跳转到首页
                    st.cache_data.clear()
                    st.session_state.current_page = 'dashboard'
                    st.rerun()

            if cancel:
                st.session_state.show_add_form = False
                st.session_state.editing_index = None
                st.rerun()

            if is_edit and delete:
                assets = st.session_state.get('assets', [])
                deleted_name = assets[editing_index].get('名称', '未知')
                assets.pop(editing_index)
                st.session_state.assets = assets
                save_to_session('investment_assets', assets)
                st.session_state.show_add_form = False
                st.session_state.editing_index = None
                # 清除缓存并跳转到首页
                st.cache_data.clear()
                st.session_state.current_page = 'dashboard'
                st.success(f"✅ 已删除资产：{deleted_name}")
                st.rerun()

        # 表单外的金额计算器按钮
        st.markdown("---")
        col_calc_btn, _ = st.columns([1, 3])
        with col_calc_btn:
            if st.button("💰 金额计算器", use_container_width=True):
                # 从表单获取代码和类型
                st.session_state.calc_code = st.session_state.get('temp_code', '')
                st.session_state.calc_code_type = st.session_state.get('temp_code_type', '场内ETF')
                st.session_state.calc_price_fetched = False
                st.session_state.show_calculator = True
                st.rerun()

        st.markdown("---")

    # 配置列表（只读显示，点击编辑）
    st.subheader("📋 资产配置列表")

    assets = st.session_state.get('assets', [])

    if not assets:
        st.warning("⚠️ 当前没有配置任何资产，点击上方「➕ 添加资产」开始")
        return

    # 显示资产列表
    for idx, asset in enumerate(assets):
        shares = asset.get('初始份额', 0)
        amount = asset.get('初始金额', 0)

        # 构建显示信息
        holding_info = []
        if shares and shares > 0:
            holding_info.append(f"{shares:,.2f} 份")
        if amount and amount > 0:
            holding_info.append(f"¥{amount:,.2f}")

        holding_display = " | ".join(holding_info) if holding_info else "未配置"

        with st.expander(f"{idx + 1}. {asset['名称']} ({asset['代码']}) - {holding_display}", expanded=False):
            col_info1, col_info2, col_info3 = st.columns([2, 2, 1])

            with col_info1:
                st.write(f"**代码**: {asset['代码']}")
                st.write(f"**名称**: {asset['名称']}")

            with col_info2:
                st.write(f"**代码类型**: {asset['代码类型']}")
                st.write(f"**资产类别**: {asset['资产类别']}")

            with col_info3:
                # 显示持有信息
                if shares and shares > 0:
                    st.metric("初始份额", f"{shares:,.2f}")
                if amount and amount > 0:
                    st.metric("初始金额", f"¥{amount:,.2f}")

                st.markdown("<br>", unsafe_allow_html=True)  # 添加间距

                if st.button(f"✏️ 编辑", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.show_add_form = True
                    st.session_state.editing_index = idx
                    st.rerun()

    st.markdown("---")
    st.caption(f"📊 当前配置：共 {len(assets)} 个资产")
    st.caption("💡 提示：点击资产左侧的 ▶ 展开详情，点击「编辑」按钮修改配置")
def load_assets_config():
    """加载资产配置 - 按优先级"""
    # 1. 尝试从 session_state 加载（用户修改后的配置）
    session_config = load_from_session('investment_assets')
    if session_config and len(session_config) > 0:
        logger.info("从 session_state 加载配置")
        return session_config

    # 2. 默认使用默认配置（4个资产）
    # 注意：secrets.toml 的配置可以通过"导入配置"功能手动导入
    logger.info("使用默认配置")
    return get_default_assets()


def main():
    """主函数"""

    # 初始化session state
    if 'assets' not in st.session_state:
        st.session_state.assets = load_assets_config()

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # 初始化数字显示状态（默认隐藏）
    if 'show_numbers' not in st.session_state:
        st.session_state.show_numbers = False

    # 侧边栏页面导航
    with st.sidebar:
        st.title("📊 导航")
        page = st.radio(
            "选择页面",
            options=["📊 数据看板", "⚙️ 配置管理"],
            index=0 if st.session_state.get('current_page') == 'dashboard' else 1,
            key="page_navigation"
        )

        # 更新当前页面状态
        if page == "📊 数据看板":
            st.session_state.current_page = 'dashboard'
        elif page == "⚙️ 配置管理":
            st.session_state.current_page = 'config'

    # 根据选择的页面显示不同内容
    if st.session_state.current_page == 'config':
        render_config_manager()
        return

    st.title("📊 投资组合仪表盘")
    st.markdown("---")

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

        # 计算总资产的涨幅
        total_stats = calculate_change_percentages(portfolio_data, '总资产')

        # 第一行：总资产信息
        st.markdown("### 💰 总资产概览")
        col_total1, col_total2, col_total3, col_total4 = st.columns(4)

        with col_total1:
            st.metric(
                "当前总金额",
                f"¥{latest['总资产']:,.2f}",
                delta=f"{total_stats['daily_change']:+.2f}%" if total_stats['daily_change'] is not None else None,
                help="相比前一天的涨跌幅"
            )

        with col_total2:
            if total_stats['weekly_change'] is not None:
                st.metric("近一周", f"{total_stats['weekly_change']:+.2f}%", help="相比7天前的涨跌幅")
            else:
                st.metric("近一周", "暂无数据")

        with col_total3:
            if total_stats['monthly_change'] is not None:
                st.metric("近一月", f"{total_stats['monthly_change']:+.2f}%", help="相比30天前的涨跌幅")
            else:
                st.metric("近一月", "暂无数据")

        with col_total4:
            if total_stats['total_change'] is not None:
                st.metric("累计涨幅", f"{total_stats['total_change']:+.2f}%", help="相比第一天的累计涨跌幅")
            else:
                st.metric("累计涨幅", "暂无数据")

        st.markdown("---")

        # 第二行：各资产类型详情
        st.markdown("### 📊 资产类型详情")

        asset_types = [
            {'name': '股票', 'icon': '📈', 'color': '#1f77b4'},
            {'name': '黄金', 'icon': '🏅', 'color': '#ff7f0e'},
            {'name': '现金', 'icon': '💵', 'color': '#2ca02c'},
            {'name': '国债', 'icon': '📜', 'color': '#d62728'}
        ]

        cols = st.columns(4)
        for idx, asset_info in enumerate(asset_types):
            asset_name = asset_info['name']
            with cols[idx]:
                # 计算该资产类型的涨幅
                asset_stats = calculate_change_percentages(portfolio_data, asset_name)

                # 显示金额和占比
                amount = latest[asset_name]
                percentage = latest[f'{asset_name}占比']

                st.markdown(f"#### {asset_info['icon']} {asset_name}")

                # 金额
                st.metric(
                    "总金额",
                    f"¥{amount:,.2f}",
                    delta=f"{asset_stats['daily_change']:+.2f}%" if asset_stats and asset_stats['daily_change'] is not None else None
                )

                # 占比
                st.metric(
                    "占比",
                    f"{percentage:.2f}%"
                )

                # 涨幅详情（使用expander折叠）
                if asset_stats:
                    with st.expander("📊 涨幅详情", expanded=False):
                        if asset_stats['weekly_change'] is not None:
                            st.write(f"📅 近一周: **{asset_stats['weekly_change']:+.2f}%**")
                        if asset_stats['monthly_change'] is not None:
                            st.write(f"📅 近一月: **{asset_stats['monthly_change']:+.2f}%**")
                        if asset_stats['total_change'] is not None:
                            st.write(f"📅 累计: **{asset_stats['total_change']:+.2f}%**")

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
