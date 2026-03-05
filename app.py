#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
永久投资组合仪表盘 - 主应用
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging
import json

from utils.data_fetcher import DataFetcher
from utils.config_manager import get_default_assets, parse_secrets_assets, validate_asset
from utils.local_storage import save_to_session, load_from_session
from utils.date_config import date_config_manager
from utils.assets_config import assets_config_manager

# 配置日志
logger = logging.getLogger(__name__)


# 页面配置
st.set_page_config(
    page_title="永久投资组合仪表盘",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 注入CSS：移动端检测样式
st.markdown("""
<style>
/* 移动端提示 - 只在屏幕宽度 <= 768px 时显示 */
.mobile-only-warning {
    display: none;
}

@media (max-width: 768px) {
    .mobile-only-warning {
        display: block !important;
    }
}

/* 确保metric组件中的数字左对齐 */
[data-testid="stMetricValue"] {
    text-align: left;
}
</style>
""", unsafe_allow_html=True)


def load_data(start_date_str):
    """加载或抓取数据

    Args:
        start_date_str: 开始日期字符串，格式 'YYYY-MM-DD'
    """
    # 手动缓存管理 - 使用日期作为缓存key
    cache_key = f"data_cache_{start_date_str}"

    if cache_key in st.session_state:
        return st.session_state[cache_key]

    assets = st.session_state.get('assets', [])

    if not assets:
        return None, None

    # 计算日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = start_date_str

    # 抓取数据
    fetcher = DataFetcher()

    # 计算天数用于显示
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    days = (datetime.now() - start_dt).days

    with st.spinner(f"🔄 正在抓取最近{days}天数据..."):
        historical_data = fetcher.fetch_all_assets_data(assets, start_date, end_date)

    if historical_data.empty:
        return None, None

    # 生成组合数据
    portfolio_data = fetcher.get_portfolio_summary(historical_data)

    # 保存到缓存
    st.session_state[cache_key] = (historical_data, portfolio_data)

    return historical_data, portfolio_data


def calculate_change_percentages(portfolio_data, asset_name='总资产'):
    """计算不同时间段的涨跌幅和金额变化"""
    if portfolio_data is None or portfolio_data.empty or len(portfolio_data) < 2:
        return None

    latest = portfolio_data[asset_name].iloc[-1]

    result = {
        'latest': latest,
        'daily_change': None,
        'weekly_change': None,
        'monthly_change': None,
        'total_change': None,
        'daily_change_amount': None,
        'weekly_change_amount': None,
        'monthly_change_amount': None,
        'total_change_amount': None
    }

    # 日涨幅（相比前一天）
    if len(portfolio_data) >= 2:
        previous = portfolio_data[asset_name].iloc[-2]
        if previous > 0:
            result['daily_change'] = ((latest - previous) / previous * 100)
            result['daily_change_amount'] = latest - previous

    # 周涨幅（相比7天前）
    if len(portfolio_data) >= 7:
        week_ago = portfolio_data[asset_name].iloc[-7]
        if week_ago > 0:
            result['weekly_change'] = ((latest - week_ago) / week_ago * 100)
            result['weekly_change_amount'] = latest - week_ago

    # 月涨幅（相比30天前）
    if len(portfolio_data) >= 30:
        month_ago = portfolio_data[asset_name].iloc[-30]
        if month_ago > 0:
            result['monthly_change'] = ((latest - month_ago) / month_ago * 100)
            result['monthly_change_amount'] = latest - month_ago

    # 总涨幅（相比第一天）
    if len(portfolio_data) >= 2:
        first = portfolio_data[asset_name].iloc[0]
        if first > 0:
            result['total_change'] = ((latest - first) / first * 100)
            result['total_change_amount'] = latest - first

    return result


def render_total_assets_chart(portfolio_data):
    """渲染总资产走势图"""
    if portfolio_data is None or portfolio_data.empty:
        return

    fig = go.Figure()

    # 计算统计指标
    total_assets = portfolio_data['总资产']
    max_value = total_assets.max()
    min_value = total_assets.min()
    first_value = total_assets.iloc[0]
    last_value = total_assets.iloc[-1]

    # 使用 argmax/argmin 获取位置索引，而不是标签索引
    import numpy as np
    max_idx = np.argmax(total_assets.values)
    min_idx = np.argmin(total_assets.values)

    # 使用iloc通过位置访问，更安全
    max_date = portfolio_data.iloc[max_idx]['日期']
    min_date = portfolio_data.iloc[min_idx]['日期']
    first_date = portfolio_data.iloc[0]['日期']
    last_date = portfolio_data.iloc[-1]['日期']

    # 确保日期是字符串格式用于显示
    def format_date(date_val):
        """格式化日期为字符串"""
        if hasattr(date_val, 'strftime'):
            return date_val.strftime('%Y-%m-%d')
        return str(date_val)

    max_date_str = format_date(max_date)
    min_date_str = format_date(min_date)
    first_date_str = format_date(first_date)
    last_date_str = format_date(last_date)

    # 格式化数值用于显示
    first_value_str = f"¥{first_value:,.0f}"
    last_value_str = f"¥{last_value:,.0f}"

    # 计算最大回撤
    max_drawdown = 0
    max_drawdown_start = None
    max_drawdown_end = None
    peak_value = first_value
    peak_idx = 0

    for i in range(1, len(portfolio_data)):
        current_value = total_assets.iloc[i]
        # 更新峰值
        if current_value > peak_value:
            peak_value = current_value
            peak_idx = i

        # 计算从峰值的回撤
        drawdown = (peak_value - current_value) / peak_value if peak_value > 0 else 0

        # 更新最大回撤
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_start = portfolio_data.iloc[peak_idx]['日期']
            max_drawdown_end = portfolio_data.iloc[i]['日期']

    # 计算最长不增长时间区间（从峰值到创新高的最长时间）
    max_recovery_days = 0
    max_recovery_start = None
    max_recovery_end = None
    peak_idx = 0

    for i in range(1, len(portfolio_data)):
        current_value = total_assets.iloc[i]

        # 如果当前值超过了之前的峰值，检查恢复时间
        if current_value > total_assets.iloc[peak_idx]:
            recovery_days = i - peak_idx
            if recovery_days > max_recovery_days:
                max_recovery_days = recovery_days
                max_recovery_start = portfolio_data.iloc[peak_idx]['日期']
                max_recovery_end = portfolio_data.iloc[i]['日期']
            peak_idx = i

    max_recovery_start_str = format_date(max_recovery_start) if max_recovery_start is not None else None
    max_recovery_end_str = format_date(max_recovery_end) if max_recovery_end is not None else None

    max_drawdown_start_str = format_date(max_drawdown_start) if max_drawdown_start is not None else None
    max_drawdown_end_str = format_date(max_drawdown_end) if max_drawdown_end is not None else None

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

    # 添加关键点标记
    # 初值
    fig.add_trace(go.Scatter(
        x=[first_date],
        y=[first_value],
        mode='markers+text',
        name='初值',
        marker=dict(color='green', size=12, symbol='circle'),
        text=[f'初值: ¥{first_value:,.0f}'],
        textposition='top center',
        hovertemplate=f'%{{x}}<br>初值: ¥{first_value:,.2f}<extra></extra>'
    ))

    # 末值
    fig.add_trace(go.Scatter(
        x=[last_date],
        y=[last_value],
        mode='markers+text',
        name='末值',
        marker=dict(color='blue', size=12, symbol='circle'),
        text=[f'末值: ¥{last_value:,.0f}'],
        textposition='top center',
        hovertemplate=f'%{{x}}<br>末值: ¥{last_value:,.2f}<extra></extra>'
    ))

    # 最大值
    fig.add_trace(go.Scatter(
        x=[max_date],
        y=[max_value],
        mode='markers+text',
        name='最大值',
        marker=dict(color='red', size=15, symbol='star'),
        text=[f'最大值: ¥{max_value:,.0f}'],
        textposition='top center',
        hovertemplate=f'%{{x}}<br>最大值: ¥{max_value:,.2f}<extra></extra>'
    ))

    # 最小值
    fig.add_trace(go.Scatter(
        x=[min_date],
        y=[min_value],
        mode='markers+text',
        name='最小值',
        marker=dict(color='orange', size=15, symbol='star'),
        text=[f'最小值: ¥{min_value:,.0f}'],
        textposition='bottom center',
        hovertemplate=f'%{{x}}<br>最小值: ¥{min_value:,.2f}<extra></extra>'
    ))

    # 添加最大回撤矩形标注
    if max_drawdown > 0 and max_drawdown_start and max_drawdown_end:
        # 找到回撤开始和结束的索引
        start_idx = portfolio_data[portfolio_data['日期'] == max_drawdown_start].index[0]
        end_idx = portfolio_data[portfolio_data['日期'] == max_drawdown_end].index[0]

        # 获取回撤期间的数据
        drawdown_data = portfolio_data.loc[start_idx:end_idx]

        # 添加矩形标注
        fig.add_vrect(
            x0=max_drawdown_start,
            x1=max_drawdown_end,
            fillcolor="rgba(255, 0, 0, 0.2)",
            layer="below",
            line_width=0,
            annotation_text=f"最大回撤: {max_drawdown*100:.2f}%",
            annotation_position="top left",
            annotation_font_size=12,
            annotation_font_color="red"
        )

    # 添加最长恢复期矩形标注
    if max_recovery_days > 0 and max_recovery_start and max_recovery_end:
        # 找到恢复期的开始和结束索引
        recovery_start_idx = portfolio_data[portfolio_data['日期'] == max_recovery_start].index[0]
        recovery_end_idx = portfolio_data[portfolio_data['日期'] == max_recovery_end].index[0]

        # 添加矩形标注（绿色半透明）
        fig.add_vrect(
            x0=max_recovery_start,
            x1=max_recovery_end,
            fillcolor="rgba(0, 200, 0, 0.15)",
            layer="below",
            line_width=2,
            line=dict(color="green", dash="dash"),
            annotation_text=f"最长恢复期: {max_recovery_days}天",
            annotation_position="bottom left",
            annotation_font_size=12,
            annotation_font_color="green"
        )

    fig.update_layout(
        title="总资产走势（含最大回撤和最长恢复期）",
        xaxis_title="日期",
        yaxis_title="总资产（元）",
        hovermode='x unified',
        template='plotly_white',
        height=500,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # 计算年化增长率（CAGR）
    def calculate_cagr(start_value, end_value, days):
        """计算年化增长率"""
        if start_value <= 0 or days <= 0:
            return 0
        years = days / 365.0
        if years == 0:
            return 0
        cagr = (end_value / start_value) ** (1 / years) - 1
        return cagr * 100  # 转换为百分比

    # 计算总天数和年化增长率
    total_days = (last_date - first_date).days if hasattr(last_date, '__sub__') else 0
    if total_days <= 0:
        # 如果日期是字符串，尝试计算
        try:
            from datetime import datetime
            if isinstance(last_date, str) and isinstance(first_date, str):
                last_dt = datetime.strptime(str(last_date), '%Y-%m-%d')
                first_dt = datetime.strptime(str(first_date), '%Y-%m-%d')
                total_days = (last_dt - first_dt).days
        except:
            total_days = 0

    cagr = calculate_cagr(first_value, last_value, total_days)

    # 显示统计信息
    st.markdown("### 📊 统计摘要")

    # 第一行：基础统计
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📈 最大值",
            value=f"¥{max_value:,.2f}",
            help=f"日期: {max_date_str}"
        )

    with col2:
        st.metric(
            label="📉 最小值",
            value=f"¥{min_value:,.2f}",
            help=f"日期: {min_date_str}"
        )

    with col3:
        st.metric(
            label="➡️ 初值",
            value=f"¥{first_value:,.2f}",
            help=f"起始日期: {first_date_str}"
        )

    with col4:
        first_change = ((last_value - first_value) / first_value * 100) if first_value > 0 else 0
        st.metric(
            label="⬅️ 末值",
            value=f"¥{last_value:,.2f}",
            delta=f"{first_change:+.2f}%",
            help=f"截止日期: {last_date_str}"
        )

    # 第二行：高级统计
    st.markdown("### 📈 高级指标")

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            label="📊 年化增长率（CAGR）",
            value=f"{cagr:+.2f}%",
            help=f"复合年增长率：({last_value_str} / {first_value_str})^(1/{total_days/365:.2f}年) - 1",
            delta_color="normal"
        )

    with col6:
        if max_recovery_days > 0:
            st.metric(
                label="⏱️ 最长恢复期",
                value=f"{max_recovery_days} 天",
                help=f"从峰值到创新高的最长时间：{max_recovery_start_str} → {max_recovery_end_str}"
            )
        else:
            st.metric(
                label="⏱️ 最长恢复期",
                value="无",
                help="没有显著的恢复期"
            )

    with col7:
        st.metric(
            label="📊 最大回撤",
            value=f"{max_drawdown*100:.2f}%",
            delta=f"从 ¥{max_value:,.2f} 回落",
            help=f"回撤区间: {max_drawdown_start_str} → {max_drawdown_end_str}"
        )

    with col8:
        st.metric(
            label="📅 投资天数",
            value=f"{total_days} 天",
            help=f"从 {first_date_str} 到 {last_date_str}，约 {total_days/365:.1f} 年"
        )

    st.markdown("---")


def render_allocation_chart(portfolio_data):
    """渲染资产配置图"""
    if portfolio_data is None or portfolio_data.empty:
        return

    st.subheader("当前资产配置（最新一天）")

    # 资产金额饼图
    latest = portfolio_data.iloc[-1]

    fig_pie = go.Figure(data=[go.Pie(
        labels=['股票', '黄金', '现金', '国债'],
        values=[latest['股票'], latest['黄金'], latest['现金'], latest['国债']],
        textinfo='label+percent',
        texttemplate='%{label}<br>¥%{value:,.0f}<br>(%{percent})',
        hole=0.3,  # 甜甜圈图
        marker=dict(
            colors=['#FF6B6B', '#FFA500', '#4ECDC4', '#95E1D3']
        )
    )])

    fig_pie.update_layout(
        title="资产金额分布",
        template='plotly_white',
        height=400,
        showlegend=True
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

    st.markdown("---")

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

    # 显示各资产类别对总资产增值的贡献
    st.markdown("### 📈 各资产类别增值贡献")

    first_row = portfolio_data.iloc[0]
    last_row = portfolio_data.iloc[-1]

    # 计算总资产增值
    total_first_value = first_row['总资产']
    total_last_value = last_row['总资产']
    total_gain = total_last_value - total_first_value
    total_gain_pct = (total_gain / total_first_value * 100) if total_first_value > 0 else 0

    # 显示总增值
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="💰 总资产增值",
            value=f"¥{total_gain:,.2f}",
            delta=f"{total_gain_pct:+.2f}%"
        )
    with col2:
        st.metric(
            label="📊 总资产变化",
            value=f"¥{total_first_value:,.2f} → ¥{total_last_value:,.2f}"
        )

    # 计算并显示每个资产类别的贡献
    st.markdown("#### 各类别贡献分析")

    contribution_data = []
    for asset_type in ['股票', '黄金', '现金', '国债']:
        first_value = first_row[asset_type]
        last_value = last_row[asset_type]
        gain = last_value - first_value
        gain_pct = (gain / total_first_value * 100) if total_first_value > 0 else 0
        contribution_to_total_gain = (gain / total_gain * 100) if total_gain != 0 else 0

        contribution_data.append({
            '资产类别': asset_type,
            '初值': first_value,
            '末值': last_value,
            '增值': gain,
            '增值率': gain_pct,
            '对总增值贡献': contribution_to_total_gain
        })

    # 创建贡献度DataFrame并显示
    import pandas as pd
    contrib_df = pd.DataFrame(contribution_data)

    # 显示为表格
    st.dataframe(
        contrib_df.style.format({
            '初值': '¥{:,.2f}',
            '末值': '¥{:,.2f}',
            '增值': '¥{:,.2f}',
            '增值率': '{:.2f}%',
            '对总增值贡献': '{:.2f}%'
        }),
        use_container_width=True,
        hide_index=True
    )

    # 可视化贡献度（横向条形图）
    fig_contrib = go.Figure(data=[go.Bar(
        x=contrib_df['对总增值贡献'],
        y=contrib_df['资产类别'],
        orientation='h',
        text=[f"{x:.2f}%" for x in contrib_df['对总增值贡献']],
        textposition='outside',
        marker=dict(
            color=['#FF6B6B', '#FFA500', '#4ECDC4', '#95E1D3'],
            line=dict(color='white', width=2)
        ),
        hovertemplate='%{y}<br>贡献: %{x:.2f}%<extra></extra>'
    )])

    fig_contrib.update_layout(
        title="各资产类别对总资产增值的贡献率",
        xaxis_title="贡献率 (%)",
        yaxis_title="资产类别",
        template='plotly_white',
        height=300,
        margin=dict(l=20, r=150, t=40, b=40)
    )

    st.plotly_chart(fig_contrib, use_container_width=True)

    # 详细说明
    with st.expander("💡 如何理解贡献度？"):
        st.markdown("""
        **贡献度计算公式**：
        ```
        某资产类别贡献率 = (该资产类别增值 ÷ 总资产增值) × 100%

        其中：
        - 该资产类别增值 = 末值 - 初值
        - 总资产增值 = 所有资产增值的总和
        ```

        **解读示例**：
        - 如果股票贡献率是 60%，说明总资产增值中有 60% 来自股票的增值
        - 贡献率越高，该资产类别对整体收益的影响越大
        - 贡献率可能为负（该资产贬值），会拖累整体收益
        """)

    st.markdown("---")


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
    # 返回首页按钮
    if st.button("🏠 返回首页", key="back_to_dashboard"):
        st.session_state.current_page = 'dashboard'
        st.session_state.page_selection = 0
        st.rerun()

    st.title("⚙️ 配置管理")

    # 使用说明
    with st.expander("💡 使用说明", expanded=False):
        st.markdown("""
        ### 配置存储方式

        您的配置（日期和资产）**保存在网址（URL）中**，具有以下特点：

        - ✅ **完全独立**：每个用户有独立的配置，互不干扰
        - ✅ **自动保存**：修改配置后自动更新网址
        - ✅ **刷新不丢失**：配置保存在网址中，刷新页面配置不变
        - ✅ **可分享**：可以将配置网址分享给其他人
        - ✅ **书签保存**：可以将当前网址保存为浏览器书签，下次直接打开

        ### 如何保存配置？

        **方式一：保存为书签**（推荐）⭐
        - 按 `Ctrl+D`（Windows/Linux）或 `Cmd+D`（Mac）
        - 将当前页面保存为浏览器书签

        **方式二：手动复制网址**
        - 在浏览器地址栏中点击，选中完整网址
        - 按 `Ctrl+C`（Mac: `Cmd+C`）复制
        - 粘贴到笔记、文档或其他地方

        **方式三：分享链接**
        - 直接复制地址栏中的完整网址
        - 发送给其他人，他们可以看到相同的配置
        """)

        st.markdown("---")
        st.markdown("#### 📋 当前配置状态")

        # 显示当前配置信息
        query_params = st.query_params

        # 显示日期配置
        if 'date' in query_params:
            st.success(f"✅ 日期配置：{query_params['date']}")
        else:
            st.info("📅 日期：默认值（2025-01-01）")

        # 显示资产配置
        if 'assets' in query_params:
            st.success(f"✅ 资产配置：已配置（{len(query_params['assets'])} 字符）")
        else:
            st.info("📊 资产：使用默认配置或为空")

        st.markdown("---")

        # 提示框
        st.info("""
        💡 **提示**：您的所有配置都已保存在当前网址中！

        **查看完整配置网址的方法：**
        - 👆 看浏览器地址栏（页面顶部）
        - 完整网址包含您的所有配置信息
        - 复制整个网址即可保存或分享配置
        """)

    st.markdown("---")

    # 添加/编辑资产表单（弹窗形式）
    if st.session_state.get('show_add_form', False):
        editing_index = st.session_state.get('editing_index')
        is_edit = editing_index is not None

        if is_edit:
            assets = st.session_state.get('assets', [])
            current_asset = assets[editing_index]
            title = f"✏️ 编辑资产：{current_asset.get('名称', '未知')}"
        else:
            current_asset = {}
            title = "➕ 添加新资产"

        # 使用expander作为弹窗
        with st.expander(title, expanded=True):
            # 表单内容
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

                    # 持有份额输入
                    st.markdown("**持有信息**")
                    st.caption("输入持有份额")

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

                    shares = st.number_input(
                        "持有份额 *",
                        min_value=0.0,
                        step=100.0,
                        value=float(current_asset.get('初始份额', 0) if current_asset.get('初始份额') else 0.0),
                        format="%.2f",
                        help="输入持有份额",
                        key="form_shares"
                    )

                    # 显示当前价格和预估市值
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
                        '初始金额': None
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
                        assets_config_manager.save(assets)
                        st.session_state.show_add_form = False
                        st.session_state.editing_index = None

                        # 后台刷新数据（不跳转页面）
                        with st.spinner("🔄 正在后台刷新数据..."):
                            # 清除旧数据缓存
                            keys_to_remove = [k for k in st.session_state.keys() if k.startswith('data_cache_')]
                            for key in keys_to_remove:
                                del st.session_state[key]

                            # 重新加载数据
                            start_date_str = st.session_state.start_date.strftime('%Y-%m-%d')
                            historical_data, portfolio_data = load_data(start_date_str)

                            if historical_data is not None and portfolio_data is not None:
                                # 保存到session_state供配置页面使用
                                st.session_state['historical_data'] = historical_data
                                st.session_state['portfolio_data'] = portfolio_data
                                st.success("✅ 数据已刷新，配置页面金额已更新")

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
                    assets_config_manager.save(assets)
                    st.session_state.show_add_form = False
                    st.session_state.editing_index = None

                    # 后台刷新数据（不跳转页面）
                    with st.spinner("🔄 正在后台刷新数据..."):
                        # 清除旧数据缓存
                        keys_to_remove = [k for k in st.session_state.keys() if k.startswith('data_cache_')]
                        for key in keys_to_remove:
                            del st.session_state[key]

                        # 重新加载数据
                        start_date_str = st.session_state.start_date.strftime('%Y-%m-%d')
                        historical_data, portfolio_data = load_data(start_date_str)

                        if historical_data is not None and portfolio_data is not None:
                            # 保存到session_state供配置页面使用
                            st.session_state['historical_data'] = historical_data
                            st.session_state['portfolio_data'] = portfolio_data
                            st.success("✅ 数据已刷新，配置页面金额已更新")

                    st.rerun()

    # 配置列表（只读显示，点击编辑）

    # 配置列表（只读显示，点击编辑）
    st.subheader("📋 资产配置列表")

    assets = st.session_state.get('assets', [])

    if not assets:
        st.warning("⚠️ 当前没有配置任何资产")
        st.info("💡 请在下方点击「➕ 添加资产」开始配置，或从 secrets.toml 加载默认配置")
        return

    # 提示信息
    if 'historical_data' not in st.session_state or st.session_state['historical_data'].empty:
        st.info("💡 提示：请先返回首页加载数据，然后在此页面查看资产金额")
        latest_prices = {}
    else:
        # 从历史数据中获取最新价格
        historical_data = st.session_state['historical_data']
        latest_prices = {}
        for code in historical_data['代码'].unique():
            code_data = historical_data[historical_data['代码'] == code]
            if not code_data.empty and '最新价格' in code_data.columns:
                latest_prices[code] = float(code_data['最新价格'].iloc[-1])
        if not latest_prices:
            st.warning("⚠️ 未从首页数据获取到价格信息，请返回首页刷新数据")

    # 显示资产列表
    for idx, asset in enumerate(assets):
        shares = asset.get('初始份额', 0)
        code = asset.get('代码')
        code_type = asset.get('代码类型')

        # 获取当前价格和金额（优先使用dashboard数据）
        current_amount = None
        current_price = None
        if shares and shares > 0 and code:
            # 优先从dashboard数据获取
            if code in latest_prices:
                current_price = latest_prices[code]
                current_amount = current_price * shares
            else:
                # 如果dashboard没有数据，标记为待获取
                current_price = None
                current_amount = None

        # 构建显示信息
        holding_display = f"{shares:,.2f} 份" if shares and shares > 0 else "未配置"
        if current_amount:
            holding_display += f" ≈ ¥{current_amount:,.2f}"

        with st.expander(f"{idx + 1}. {asset['名称']} ({asset['代码']}) - {holding_display}", expanded=False):
            col_info1, col_info2, col_info3, col_info4 = st.columns([2, 2, 1.5, 1])

            with col_info1:
                st.write(f"**代码**: {asset['代码']}")
                st.write(f"**名称**: {asset['名称']}")

            with col_info2:
                st.write(f"**代码类型**: {asset['代码类型']}")
                st.write(f"**资产类别**: {asset['资产类别']}")

            with col_info3:
                # 显示持有份额
                if shares and shares > 0:
                    st.metric("持有份额", f"{shares:,.2f}")

                # 显示当前金额
                if current_amount:
                    st.metric("当前金额", f"¥{current_amount:,.2f}")
                elif current_price is not None:
                    st.metric("当前金额", f"¥{current_price * shares:,.2f}")

            with col_info4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"✏️ 编辑", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.show_add_form = True
                    st.session_state.editing_index = idx
                    st.session_state.scroll_to_form = True
                    st.rerun()

    st.markdown("---")
    st.caption(f"📊 当前配置：共 {len(assets)} 个资产")
    st.caption("💡 提示：点击资产左侧的 ▶ 展开详情，点击「编辑」按钮修改配置")

    # 添加资产按钮（列表下方）
    if st.button("➕ 添加资产", type="primary", use_container_width=True):
        st.session_state.show_add_form = True
        st.session_state.editing_index = None
        st.rerun()

    st.markdown("---")
    st.subheader("🛠️ 配置操作")

    # 第一行：返回首页
    if st.button("🏠 返回首页", use_container_width=True):
        st.session_state.current_page = 'dashboard'
        st.session_state.page_selection = 0
        st.rerun()

    # 第二行按钮
    col3, col4, col5 = st.columns(3)

    with col3:
        if st.button("📤 导出配置", use_container_width=True):
            assets = st.session_state.get('assets', [])
            if assets:
                json_data = json.dumps(assets, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ 下载配置文件",
                    data=json_data,
                    file_name=f"investment_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

    with col4:
        uploaded_file = st.file_uploader(
            "📥 导入配置",
            type=['json'],
            label_visibility="visible",
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
                        assets_config_manager.save(valid_assets)

                        # 后台刷新数据
                        with st.spinner("🔄 正在后台刷新数据..."):
                            # 清除旧数据缓存
                            keys_to_remove = [k for k in st.session_state.keys() if k.startswith('data_cache_')]
                            for key in keys_to_remove:
                                del st.session_state[key]

                            # 重新加载数据
                            start_date_str = st.session_state.start_date.strftime('%Y-%m-%d')
                            historical_data, portfolio_data = load_data(start_date_str)

                            if historical_data is not None and portfolio_data is not None:
                                # 保存到session_state供配置页面使用
                                st.session_state['historical_data'] = historical_data
                                st.session_state['portfolio_data'] = portfolio_data

                        st.success(f"✅ 成功导入 {len(valid_assets)} 个资产配置")
                        st.rerun()
                    else:
                        st.error("❌ 导入的配置中没有有效的资产")
                else:
                    st.error("❌ 配置文件格式错误：应为资产列表")
            except Exception as e:
                st.error(f"❌ 导入配置失败: {str(e)}")

    with col5:
        if st.button("🔄 重置配置", use_container_width=True):
            # 清除session_state中的配置
            if 'investment_assets' in st.session_state:
                del st.session_state['investment_assets']
            if 'assets' in st.session_state:
                del st.session_state['assets']

            # 重新加载配置（会按优先级：secrets → 默认）
            assets = load_assets_config()
            st.session_state.assets = assets
            assets_config_manager.save(assets)

            # 后台刷新数据
            with st.spinner("🔄 正在后台刷新数据..."):
                # 清除旧数据缓存
                keys_to_remove = [k for k in st.session_state.keys() if k.startswith('data_cache_')]
                for key in keys_to_remove:
                    del st.session_state[key]

                # 重新加载数据
                start_date_str = st.session_state.start_date.strftime('%Y-%m-%d')
                historical_data, portfolio_data = load_data(start_date_str)

                if historical_data is not None and portfolio_data is not None:
                    # 保存到session_state供配置页面使用
                    st.session_state['historical_data'] = historical_data
                    st.session_state['portfolio_data'] = portfolio_data

            # 显示来源信息
            if hasattr(st, 'secrets') and 'assets' in st.secrets:
                st.success(f"✅ 已从 secrets.toml 重新加载配置（{len(assets)} 个资产）")
            else:
                st.success(f"✅ 已重置为默认配置（{len(assets)} 个资产）")

            st.rerun()



def load_assets_config():
    """加载资产配置 - 使用配置管理器"""
    # 获取 secrets.toml 的配置（作为默认配置）
    secrets_assets = None
    try:
        if hasattr(st, 'secrets') and 'assets' in st.secrets:
            raw_assets = st.secrets['assets']
            logger.info(f"从 secrets.toml 读取配置: {len(raw_assets) if isinstance(raw_assets, list) else 1} 个资产")

            # 解析并验证 secrets 配置
            parsed_assets = []
            for asset in raw_assets:
                is_valid, error_msg = validate_asset(asset)
                if is_valid:
                    parsed_assets.append(asset)
                else:
                    logger.warning(f"secrets 中的资产配置无效: {error_msg}")

            if parsed_assets:
                secrets_assets = parsed_assets
            else:
                logger.warning("secrets.toml 中的资产配置全部无效")
    except Exception as e:
        logger.error(f"从 secrets.toml 加载配置失败: {str(e)}")

    # 获取默认配置
    default_assets = get_default_assets()

    # 使用配置管理器加载（优先级：session_state > 文件 > secrets > 默认）
    return assets_config_manager.load(secrets_assets, default_assets)


def main():
    """主函数"""

    # 初始化 session state（使用与资产配置相同的方式）
    if 'assets' not in st.session_state:
        st.session_state.assets = load_assets_config()

    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # 初始化数字显示状态（从 URL 读取，默认隐藏）
    if 'show_numbers' not in st.session_state:
        query_params = st.query_params
        if 'show' in query_params:
            # 从 URL 读取状态（"1" 表示显示，其他值表示隐藏）
            st.session_state.show_numbers = query_params['show'] == '1'
        else:
            st.session_state.show_numbers = False

    # 初始化开始日期（使用文件持久化）
    if 'start_date' not in st.session_state:
        # 优先级：文件 > session_state缓存 > 默认值
        file_date = date_config_manager.load()
        if file_date:
            st.session_state.start_date = file_date
            logger.info(f"从文件加载日期配置: {file_date}")
        else:
            # 使用默认值 2025-01-01
            st.session_state.start_date = datetime(2025, 1, 1).date()
            logger.info("使用默认日期: 2025-01-01")

    # 侧边栏页面导航
    with st.sidebar:
        st.title("📊 导航")

        # 初始化页面选择
        if 'page_selection' not in st.session_state:
            st.session_state.page_selection = 0 if st.session_state.get('current_page') == 'dashboard' else 1

        # 根据current_page更新索引（防止按钮跳转后radio不更新）
        if st.session_state.get('current_page') == 'dashboard' and st.session_state.page_selection != 0:
            st.session_state.page_selection = 0
        elif st.session_state.get('current_page') == 'config' and st.session_state.page_selection != 1:
            st.session_state.page_selection = 1

        page = st.radio(
            "选择页面",
            options=["📊 数据看板", "⚙️ 配置管理"],
            index=st.session_state.page_selection
        )

        # 更新状态
        st.session_state.page_selection = 0 if page == "📊 数据看板" else 1
        st.session_state.current_page = 'dashboard' if page == "📊 数据看板" else 'config'

    # 根据选择的页面显示不同内容
    if st.session_state.current_page == 'config':
        render_config_manager()
        return

    st.title("📊 永久投资组合仪表盘")

    # 移动端浏览建议（只在移动端显示）
    st.markdown("""
    <div class="mobile-only-warning stWarning">
        <div style="padding: 1rem; border-radius: 0.5rem; background-color: #FFFAEB; color: #663800; border: 1px solid #FCD34D; margin-bottom: 1rem;">
            💻 建议使用电脑浏览以获得最佳体验（移动端浏览可能显示效果受限）
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 检查是否使用默认配置（URL中没有assets参数）
    query_params = st.query_params
    has_custom_assets = 'assets' in query_params

    # 只在没有自定义配置时显示欢迎信息
    if not has_custom_assets:
        st.markdown("---")
        st.info("### 👋 欢迎使用永久投资组合仪表盘！")

        with st.expander("🎯 快速上手", expanded=True):
            st.markdown("""
            ### 🎯 永久投资组合追踪

            **四大核心资产**：股票（📈增长）、黄金（🏅保值）、现金（💰流动性）、国债（🏛️稳定收益）

            **当前状态**：⚠️ 您正在使用默认配置（示例数据）

            **💡 关于数据**：
            - 📊 **真实市场数据**：图表显示的是从市场抓取的真实历史数据
            - 🔄 **动态更新**：点击"🔄 刷新数据"可获取最新行情
            - 📈 **时间范围可调**：通过日期选择器查看不同时间段表现

            **如何使用**：
            1. 点击左侧 **⚙️ 配置管理**
            2. 添加您的资产（代码、类型、份额）
            3. 保存后配置会自动保存到网址中
            4. 下次访问直接打开保存的网址即可

            💡 **想先逛逛？** 没问题！您可以先随意浏览一下默认配置下的图表和数据展示，看看这个应用能做什么。等您觉得不错了，再点击左侧的 ⚙️ 配置管理 配置您自己的资产也不迟~
            """)
        st.markdown("---")

    st.markdown("---")

    # 检查是否有配置
    assets = st.session_state.get('assets', [])

    if not assets:
        st.warning("⚠️ 尚未配置任何资产")
        st.info("💡 请在 Streamlit Secrets 中配置 `assets` 来使用此应用")
        return

    # 数据抓取按钮
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button(f"📌 当前已配置 {len(assets)} 个资产", key="goto_config"):
            st.session_state.current_page = 'config'
            st.session_state.page_selection = 1
            st.rerun()

    with col2:
        if st.button("🔄 刷新数据", type="primary"):
            # 只清除数据缓存，不清除日期选择
            keys_to_remove = [k for k in st.session_state.keys() if k.startswith('data_cache_')]
            for key in keys_to_remove:
                del st.session_state[key]
            st.rerun()

    with col3:
        # 日期选择器
        saved_date = st.session_state.start_date

        # 日期选择器
        selected_date = st.date_input(
            "开始日期",
            value=saved_date,
            max_value=datetime.now().date(),
            key="start_date_input"
        )

        # 如果用户改变了日期，保存到文件和session_state
        if selected_date != saved_date:
            st.session_state.start_date = selected_date
            date_config_manager.save(selected_date)  # 保存到文件（持久化）
            save_to_session('investment_start_date', selected_date)  # 保存到session_state（会话内）
            st.rerun()

    st.markdown("---")

    # 加载数据
    start_date_str = st.session_state.start_date.strftime('%Y-%m-%d')
    historical_data, portfolio_data = load_data(start_date_str)

    if historical_data is None or portfolio_data is None:
        st.error("❌ 数据加载失败，请检查网络连接或配置")
        return

    # 保存数据到session_state供配置页面使用
    st.session_state['historical_data'] = historical_data
    st.session_state['portfolio_data'] = portfolio_data

    # 获取最新数据
    latest = portfolio_data.iloc[-1]

    # 第一行：总资产信息（标题 + 按钮）
    col_header, col_toggle = st.columns([3, 2])
    with col_header:
        st.markdown("### 💰 总资产概览")

    with col_toggle:
        if st.session_state.show_numbers:
            button_label = "👁️ 隐藏金额"
        else:
            button_label = "🙈 显示金额"
        if st.button(button_label, key="toggle_numbers"):
            # 切换状态并更新 URL
            st.session_state.show_numbers = not st.session_state.show_numbers
            # 更新 URL 参数
            st.query_params['show'] = '1' if st.session_state.show_numbers else '0'
            st.rerun()

    # 计算总资产的涨幅
    total_stats = calculate_change_percentages(portfolio_data, '总资产')

    # 总资产统计卡片
    col_total1, col_total2, col_total3 = st.columns(3)

    with col_total1:
        # 根据show_numbers状态决定是否显示金额
        if st.session_state.show_numbers:
            # 构建delta字符串：百分比 + 金额
            delta_text = None
            if total_stats['daily_change'] is not None:
                amount_str = f"¥{total_stats['daily_change_amount']:,.2f}" if total_stats['daily_change_amount'] is not None else ""
                delta_text = f"{total_stats['daily_change']:+.2f}% ({amount_str})"

            st.metric(
                "当前总金额",
                f"¥{latest['总资产']:,.2f}",
                delta=delta_text,
                help="相比前一天的涨跌幅"
            )
        else:
            # 隐藏金额，使用markdown显示
            st.markdown("### 当前总金额")
            st.markdown("###### \*\*\*\*\*\*")
            if total_stats['daily_change'] is not None:
                st.markdown(f"*日涨跌: {total_stats['daily_change']:+.2f}%*")

    with col_total2:
        if total_stats['weekly_change'] is not None:
            # 使用 st.metric，红涨绿跌
            if st.session_state.show_numbers and total_stats['weekly_change_amount'] is not None:
                amount_str = f"¥{total_stats['weekly_change_amount']:,.2f}"
                st.metric(
                    "近一周",
                    f"{total_stats['weekly_change']:+.2f}%",
                    delta=amount_str,
                    delta_color="inverse" if total_stats['weekly_change'] > 0 else ("normal" if total_stats['weekly_change'] < 0 else "off"),
                    help="相比7天前的涨跌幅"
                )
            else:
                # 隐藏模式：不显示 delta
                st.metric(
                    "近一周",
                    f"{total_stats['weekly_change']:+.2f}%",
                    help="相比7天前的涨跌幅"
                )
        else:
            st.metric("近一周", "暂无数据")

    with col_total3:
        if total_stats['monthly_change'] is not None:
            # 使用 st.metric，红涨绿跌
            if st.session_state.show_numbers and total_stats['monthly_change_amount'] is not None:
                amount_str = f"¥{total_stats['monthly_change_amount']:,.2f}"
                st.metric(
                    "近一月",
                    f"{total_stats['monthly_change']:+.2f}%",
                    delta=amount_str,
                    delta_color="inverse" if total_stats['monthly_change'] > 0 else ("normal" if total_stats['monthly_change'] < 0 else "off"),
                    help="相比30天前的涨跌幅"
                )
            else:
                # 隐藏模式：不显示 delta
                st.metric(
                    "近一月",
                    f"{total_stats['monthly_change']:+.2f}%",
                    help="相比30天前的涨跌幅"
                )
        else:
            st.metric("近一月", "暂无数据")

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

            # 金额（根据show_numbers状态决定是否显示）
            if st.session_state.show_numbers:
                # 构建delta字符串：百分比 + 金额
                delta_text = None
                if asset_stats and asset_stats['daily_change'] is not None:
                    amount_str = f"¥{asset_stats['daily_change_amount']:,.2f}" if asset_stats.get('daily_change_amount') is not None else ""
                    delta_text = f"{asset_stats['daily_change']:+.2f}% ({amount_str})"

                st.metric(
                    "总金额",
                    f"¥{amount:,.2f}",
                    delta=delta_text
                )
            else:
                # 隐藏金额显示
                st.markdown("**总金额:** \*\*\*\*\*\*")
                if asset_stats and asset_stats['daily_change'] is not None:
                    st.caption(f"日涨跌: {asset_stats['daily_change']:+.2f}%")

            # 占比（始终显示）
            st.metric(
                "占比",
                f"{percentage:.2f}%"
            )

    st.markdown("---")

    # 第三行：统一的涨幅详情折叠面板
    with st.expander("📊 各资产类型涨幅详情", expanded=False):
        st.caption("显示各资产类型在不同时间段内的涨跌幅")

        # 使用4列显示，增加列间距
        detail_cols = st.columns(4, gap="large")
        for idx, asset_info in enumerate(asset_types):
            asset_name = asset_info['name']
            asset_stats = calculate_change_percentages(portfolio_data, asset_name)

            with detail_cols[idx]:
                st.markdown(f"#### {asset_info['icon']} {asset_name}")

                if asset_stats:
                    # 涨跌幅详情折叠面板：始终只显示百分比，不显示金额
                    # 红色代表涨，绿色代表跌

                    def format_change(value, label):
                        """格式化涨跌幅显示，红色涨绿色跌"""
                        if value is None:
                            return None

                        color = "#ff4b4b" if value > 0 else "#26c281"  # 红涨绿跌
                        icon = "↑" if value > 0 else "↓" if value < 0 else "→"

                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: space-between; align-items: center; margin: 8px 0;">
                                <span style="color: #666;">{label}</span>
                                <span style="color: {color}; font-weight: bold; font-size: 1.1em;">
                                    {icon} {abs(value):.2f}%
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    format_change(asset_stats['daily_change'], "日涨幅")
                    format_change(asset_stats['weekly_change'], "近一周")
                    format_change(asset_stats['monthly_change'], "近一月")
                    format_change(asset_stats['total_change'], "累计涨幅")

    st.markdown("---")

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
