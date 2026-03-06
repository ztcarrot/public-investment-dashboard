# 短债基金筛选功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 添加短债基金筛选页面，通过 akshare API 获取数据，按年化收益率和最大回撤筛选，支持添加到投资组合配置

**架构:** 新增 `fund_cache.py` 和 `fund_screener.py` 模块处理数据，在 `app.py` 添加页面路由和渲染函数，使用本地文件缓存减少 API 调用

**技术栈:** Python, Streamlit, akshare, pandas, concurrent.futures

---

## 任务概览

1. 创建缓存目录和缓存管理器
2. 实现基金筛选核心逻辑
3. 在主应用添加页面路由和UI
4. 测试和优化

---

## Task 1: 创建缓存目录和缓存管理器

**文件:**
- 创建: `utils/fund_cache.py`
- 修改: 无
- 测试: 无（集成测试覆盖）

### Step 1: 创建缓存目录

创建 `cache` 目录用于存储基金数据缓存。

运行:
```bash
mkdir -p cache
touch cache/.gitkeep
```

预期结果: `cache/` 目录已创建

### Step 2: 编写缓存管理器类

创建 `utils/fund_cache.py`，包含 `FundCacheManager` 类：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金数据缓存管理模块

使用本地 JSON 文件缓存基金筛选结果，减少 API 调用。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class FundCacheManager:
    """基金数据缓存管理器"""

    def __init__(self, cache_file: str = "cache/fund_screening.json"):
        """
        初始化缓存管理器

        Args:
            cache_file: 缓存文件路径
        """
        self.cache_file = cache_file
        self.cache_dir = os.path.dirname(cache_file)

        # 确保缓存目录存在
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"创建缓存目录: {self.cache_dir}")

    def load(self) -> Optional[Dict]:
        """
        从文件加载缓存数据

        Returns:
            缓存数据字典，如果不存在或已损坏返回 None
        """
        try:
            if not os.path.exists(self.cache_file):
                logger.debug(f"缓存文件不存在: {self.cache_file}")
                return None

            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"成功加载缓存: {self.cache_file}")
            return data

        except json.JSONDecodeError as e:
            logger.error(f"缓存文件损坏，将重新获取数据: {e}")
            # 删除损坏的缓存文件
            try:
                os.remove(self.cache_file)
                logger.info(f"已删除损坏的缓存文件: {self.cache_file}")
            except Exception as remove_error:
                logger.error(f"删除损坏缓存文件失败: {remove_error}")
            return None
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return None

    def save(self, data: Dict) -> bool:
        """
        保存数据到缓存文件

        Args:
            data: 要缓存的数据字典

        Returns:
            是否保存成功
        """
        try:
            # 添加更新时间戳
            data['update_time'] = datetime.now().strftime('%Y-%m-%d')

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"缓存已保存: {self.cache_file}")
            return True

        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            return False

    def is_expired(self, days: int = 7) -> bool:
        """
        检查缓存是否过期

        Args:
            days: 过期天数阈值，默认7天

        Returns:
            是否过期
        """
        data = self.load()
        if not data:
            return True

        try:
            update_time_str = data.get('update_time')
            if not update_time_str:
                return True

            update_time = datetime.strptime(update_time_str, '%Y-%m-%d')
            expire_time = datetime.now() - timedelta(days=days)

            is_expired = update_time < expire_time

            if is_expired:
                logger.info(f"缓存已过期: {update_time_str}")
            else:
                age_days = (datetime.now() - update_time).days
                logger.debug(f"缓存未过期，已使用 {age_days} 天")

            return is_expired

        except Exception as e:
            logger.error(f"检查缓存过期失败: {e}")
            return True

    def get_cache_age_days(self) -> int:
        """
        获取缓存年龄（天数）

        Returns:
            缓存年龄天数，如果无法获取返回 -1
        """
        data = self.load()
        if not data:
            return -1

        try:
            update_time_str = data.get('update_time')
            if not update_time_str:
                return -1

            update_time = datetime.strptime(update_time_str, '%Y-%m-%d')
            age = (datetime.now() - update_time).days
            return age

        except Exception as e:
            logger.error(f"获取缓存年龄失败: {e}")
            return -1

    def clear(self) -> bool:
        """
        清除缓存文件

        Returns:
            是否清除成功
        """
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info(f"缓存已清除: {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False


# 全局实例
fund_cache_manager = FundCacheManager()
```

### Step 3: 提交缓存管理器

运行:
```bash
git add utils/fund_cache.py cache/.gitkeep
git commit -m "feat: 添加基金数据缓存管理器

- 新增 FundCacheManager 类
- 支持缓存读写、过期检查
- 自动处理损坏的缓存文件
- 缓存有效期7天

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

预期结果: Git commit 成功

---

## Task 2: 实现基金筛选核心逻辑

**文件:**
- 创建: `utils/fund_screener.py`
- 修改: 无
- 测试: 无（集成测试覆盖）

### Step 1: 编写基金筛选模块

创建 `utils/fund_screener.py`，包含基金筛选逻辑：

```python
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
```

### Step 2: 提交基金筛选模块

运行:
```bash
git add utils/fund_screener.py
git commit -m "feat: 添加短债基金筛选核心逻辑

- 新增基金列表获取和短债基金筛选
- 实现年化收益率和最大回撤计算
- 使用多线程并行处理提升性能
- 支持进度回调函数

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

预期结果: Git commit 成功

---

## Task 3: 在主应用添加页面路由

**文件:**
- 修改: `app.py`
- 位置: `main()` 函数中的侧边栏导航部分（约第1656-1664行）

### Step 1: 修改页面导航选项

修改 `app.py` 的侧边栏导航，添加"基金筛选"选项：

找到这部分代码（约第1656-1664行）：
```python
page = st.radio(
    "选择页面",
    options=["📊 数据看板", "⚙️ 配置管理"],
    index=st.session_state.page_selection
)
```

修改为：
```python
page = st.radio(
    "选择页面",
    options=["📊 数据看板", "🔍 基金筛选", "⚙️ 配置管理"],
    index=st.session_state.page_selection
)
```

### Step 2: 更新页面选择逻辑

修改页面选择状态映射（约第1662-1664行）：

找到：
```python
# 更新状态
st.session_state.page_selection = 0 if page == "📊 数据看板" else 1
st.session_state.current_page = 'dashboard' if page == "📊 数据看板" else 'config'
```

修改为：
```python
# 更新状态
if page == "📊 数据看板":
    st.session_state.page_selection = 0
    st.session_state.current_page = 'dashboard'
elif page == "🔍 基金筛选":
    st.session_state.page_selection = 1
    st.session_state.current_page = 'fund_screener'
else:  # ⚙️ 配置管理
    st.session_state.page_selection = 2
    st.session_state.current_page = 'config'
```

### Step 3: 更新 session_state 初始化逻辑

修改 `main()` 函数中的页面选择初始化（约第1647-1654行）：

找到：
```python
# 初始化页面选择
if 'page_selection' not in st.session_state:
    st.session_state.page_selection = 0 if st.session_state.get('current_page') == 'dashboard' else 1

# 根据current_page更新索引（防止按钮跳转后radio不更新）
if st.session_state.get('current_page') == 'dashboard' and st.session_state.page_selection != 0:
    st.session_state.page_selection = 0
elif st.session_state.get('current_page') == 'config' and st.session_state.page_selection != 1:
    st.session_state.page_selection = 1
```

修改为：
```python
# 初始化页面选择
if 'page_selection' not in st.session_state:
    current_page = st.session_state.get('current_page', 'dashboard')
    if current_page == 'dashboard':
        st.session_state.page_selection = 0
    elif current_page == 'fund_screener':
        st.session_state.page_selection = 1
    else:  # config
        st.session_state.page_selection = 2

# 根据current_page更新索引（防止按钮跳转后radio不更新）
current_page = st.session_state.get('current_page')
if current_page == 'dashboard' and st.session_state.page_selection != 0:
    st.session_state.page_selection = 0
elif current_page == 'fund_screener' and st.session_state.page_selection != 1:
    st.session_state.page_selection = 1
elif current_page == 'config' and st.session_state.page_selection != 2:
    st.session_state.page_selection = 2
```

### Step 4: 提交路由修改

运行:
```bash
git add app.py
git commit -m "feat: 添加基金筛选页面路由

- 在侧边栏导航添加「基金筛选」选项
- 更新页面选择状态映射逻辑
- 支持三个页面：看板、筛选、配置

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

预期结果: Git commit 成功

---

## Task 4: 创建基金筛选页面渲染函数

**文件:**
- 修改: `app.py`
- 位置: 在 `render_config_manager()` 函数之后添加新函数

### Step 1: 编写基金筛选页面渲染函数

在 `app.py` 中添加 `render_fund_screener()` 函数（插入在 `render_config_manager()` 函数之后，约第1660行之后）：

```python
def render_fund_screener():
    """渲染基金筛选页面"""
    st.title("🔍 短债基金筛选")

    from utils.fund_screener import screen_funds, AKSHARE_AVAILABLE
    from utils.fund_cache import fund_cache_manager

    # 检查 akshare 是否可用
    if not AKSHARE_AVAILABLE:
        st.error("❌ akshare 库不可用，请先安装：`pip install akshare`")
        return

    # 加载缓存数据
    cache_age = fund_cache_manager.get_cache_age_days()
    cache_data = fund_cache_manager.load()

    # 顶部控制栏
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("🔄 刷新数据", use_container_width=True):
            # 清除缓存并重新加载
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
        screened_funds = cache_data.get('screened_funds', [])
        total_funds = cache_data.get('total_funds', 0)

        st.success(f"✅ 使用缓存数据：共筛选出 {len(screened_funds)} 只基金（从 {total_funds} 只短债基金中）")

        # 展示筛选结果
        _display_fund_results(screened_funds)

    else:
        # 重新获取数据
        st.info("🔄 正在从 akshare 获取最新数据...")

        # 创建进度条
        progress_bar = st.progress(0, text="正在获取基金数据...")
        status_text = st.empty()

        def update_progress(current, total, fund_info):
            """更新进度"""
            if total > 0:
                progress = min((current + 1) / total, 1.0)
                progress_bar.progress(progress, text=f"正在获取基金数据... ({current + 1}/{total})")

            if fund_info:
                status_text.text(f"📊 正在处理: {fund_info.get('名称', '')} ({fund_info.get('代码', '')})")
            else:
                status_text.empty()

        try:
            # 执行筛选
            result = screen_funds(progress_callback=update_progress)

            if result:
                # 保存到缓存
                fund_cache_manager.save(result)

                # 清空进度条
                progress_bar.empty()
                status_text.empty()

                # 展示结果
                screened_funds = result.get('screened_funds', [])
                total_funds = result.get('total_funds', 0)

                st.success(f"✅ 筛选完成：共找到 {len(screened_funds)} 只优质基金（从 {total_funds} 只短债基金中）")

                # 展示筛选结果
                _display_fund_results(screened_funds)
            else:
                progress_bar.empty()
                status_text.empty()
                st.error("❌ 获取基金数据失败，请稍后重试")

        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            logger.error(f"基金筛选失败: {e}")
            st.error(f"❌ 发生错误: {str(e)}")


def _display_fund_results(funds: list):
    """
    展示基金筛选结果

    Args:
        funds: 基金列表
    """
    if not funds:
        st.warning("⚠️ 没有找到符合条件的基金")
        return

    # 转换为 DataFrame
    import pandas as pd
    df = pd.DataFrame(funds)

    # 格式化显示
    display_df = df.copy()

    # 格式化百分比列
    if '年化收益率' in display_df.columns:
        display_df['年化收益率'] = display_df['年化收益率'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )

    if '最大回撤' in display_df.columns:
        display_df['最大回撤'] = display_df['最大回撤'].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A"
        )

    # 选择要显示的列
    display_cols = ['基金代码', '基金简称', '年化收益率', '最大回撤']
    if '基金类型' in display_df.columns:
        display_cols.insert(2, '基金类型')
    if '成立日期' in display_df.columns:
        display_cols.append('成立日期')

    # 只显示存在的列
    display_cols = [col for col in display_cols if col in display_df.columns]

    st.markdown("### 📊 筛选结果（前 30 名）")
    st.dataframe(
        display_df[display_cols],
        use_container_width=True,
        hide_index=True
    )

    # 添加操作说明
    with st.expander("💡 如何添加到投资组合？"):
        st.markdown("""
        1. 记下感兴趣的基金代码（如 `005350`）
        2. 点击左侧导航进入 **⚙️ 配置管理**
        3. 点击 **➕ 添加资产**
        4. 填写基金信息：
           - **代码**: 基金代码
           - **名称**: 基金名称
           - **代码类型**: 债券
           - **资产类别**: 现金
           - **初始份额**: 购买的份额数量
        5. 点击保存
        """)

    # 统计信息
    with st.expander("📈 统计信息"):
        if '年化收益率' in df.columns:
            avg_return = df['年化收益率'].mean()
            max_return = df['年化收益率'].max()
            min_return = df['年化收益率'].min()

            col1, col2, col3 = st.columns(3)
            col1.metric("平均年化收益", f"{avg_return:.2f}%")
            col2.metric("最高年化收益", f"{max_return:.2f}%")
            col3.metric("最低年化收益", f"{min_return:.2f}%")

        if '最大回撤' in df.columns:
            avg_drawdown = df['最大回撤'].mean()
            max_drawdown = df['最大回撤'].min()  # 最小值 = 最大回撤
            min_drawdown = df['最大回撤'].max()  # 最大值 = 最小回撤

            col1, col2, col3 = st.columns(3)
            col1.metric("平均最大回撤", f"{avg_drawdown:.2f}%")
            col2.metric("最大回撤（最差）", f"{max_drawdown:.2f}%")
            col3.metric("最大回撤（最好）", f"{min_drawdown:.2f}%")
```

### Step 2: 添加路由处理

在 `main()` 函数中添加基金筛选页面的路由调用（约第1667-1669行之后）：

找到：
```python
# 根据选择的页面显示不同内容
if st.session_state.current_page == 'config':
    render_config_manager()
    return
```

修改为：
```python
# 根据选择的页面显示不同内容
if st.session_state.current_page == 'fund_screener':
    render_fund_screener()
    return

if st.session_state.current_page == 'config':
    render_config_manager()
    return
```

### Step 3: 提交页面渲染函数

运行:
```bash
git add app.py
git commit -m "feat: 添加基金筛选页面渲染函数

- 新增 render_fund_screener() 函数
- 实现缓存检查和自动更新逻辑
- 添加进度条显示数据加载状态
- 展示筛选结果和统计信息
- 提供添加到配置的操作说明

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

预期结果: Git commit 成功

---

## Task 5: 测试和验证

**文件:**
- 无
- 测试: 手动功能测试

### Step 1: 启动应用测试

运行:
```bash
streamlit run app.py
```

预期结果: 应用正常启动

### Step 2: 测试页面导航

1. 在浏览器打开应用
2. 点击侧边栏的"🔍 基金筛选"
3. 验证页面正常显示

预期结果:
- 页面标题显示"🔍 短债基金筛选"
- 顶部有"🔄 刷新数据"和"🏠 返回首页"按钮
- 显示缓存状态

### Step 3: 测试数据获取

1. 首次访问时，应该触发数据获取
2. 观察进度条显示
3. 等待数据加载完成

预期结果:
- 显示进度条和当前处理的基金
- 最终显示筛选结果表格
- 数据保存到 `cache/fund_screening.json`

### Step 4: 测试缓存功能

1. 刷新页面
2. 验证使用缓存数据
3. 点击"🔄 刷新数据"按钮

预期结果:
- 第二次访问直接显示缓存数据
- 点击刷新按钮会清除缓存并重新获取

### Step 5: 测试页面跳转

1. 点击"🏠 返回首页"
2. 再次进入"🔍 基金筛选"

预期结果:
- 正确跳转到数据看板
- 再次进入筛选页面显示缓存数据

### Step 6: 验证缓存文件

运行:
```bash
cat cache/fund_screening.json | head -20
```

预期结果:
- JSON 格式正确
- 包含 `update_time` 和 `screened_funds` 字段

### Step 7: 提交测试结果（如果需要修复）

如果测试中发现问题，修复后提交：

```bash
git add app.py utils/fund_screener.py utils/fund_cache.py
git commit -m "fix: 修复基金筛选功能测试中发现的问题

- 修复问题描述
- 其他修复

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 完成确认清单

- [ ] 缓存目录已创建
- [ ] `fund_cache.py` 已实现并测试
- [ ] `fund_screener.py` 已实现并测试
- [ ] 页面路由已更新
- [ ] 渲染函数已实现
- [ ] 功能测试通过
- [ ] 缓存功能正常工作
- [ ] 代码已提交到 Git

---

## 后续优化建议

- 添加更多筛选条件（基金规模、基金经理等）
- 实现直接从筛选页面添加到配置的功能
- 添加基金详情页面（净值走势图）
- 支持导出筛选结果到 Excel
