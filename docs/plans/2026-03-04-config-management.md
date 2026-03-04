# 配置管理功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现基于浏览器的配置管理功能，允许用户在页面上添加、编辑、删除资产配置，支持导入导出，数据持久化到 LocalStorage，并按优先级加载配置（LocalStorage > secrets.toml > 默认配置）

**架构:**
- 使用 Streamlit 的 `st.data_editor` 实现可编辑表格
- 通过 Streamlit 自定义组件实现 LocalStorage 读写
- 修改数据获取逻辑，根据代码类型选择不同的 API（场内ETF/基金用东方财富API，股票用东方财富股票API，债券用债券API）
- 实现份额/金额互斥计算逻辑

**技术栈:** Streamlit, Python, pandas, requests, JavaScript (LocalStorage)

---

## Task 1: 创建默认配置模块

**Files:**
- Create: `utils/config_manager.py`

**Step 1: 创建配置管理器模块**

创建文件 `utils/config_manager.py`，实现配置加载、保存、验证等功能：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import streamlit as st
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def get_default_assets() -> List[Dict]:
    """
    获取默认配置

    Returns:
        默认资产配置列表
    """
    return [
        {
            '代码': '511130',
            '名称': '国债30年',
            '代码类型': '场内ETF',
            '资产类别': '国债',
            '初始份额': 1000.0,
            '初始金额': None
        },
        {
            '代码': '510300',
            '名称': '300ETF',
            '代码类型': '场内ETF',
            '资产类别': '股票',
            '初始份额': 22000.0,
            '初始金额': None
        },
        {
            '代码': '518660',
            '名称': '工银黄金',
            '代码类型': '场内ETF',
            '资产类别': '黄金',
            '初始份额': 8700.0,
            '初始金额': None
        },
        {
            '代码': '005350',
            '名称': '短债基金',
            '代码类型': '债券',
            '资产类别': '现金',
            '初始份额': 90000.0,
            '初始金额': None
        }
    ]


def parse_secrets_assets(assets_data) -> List[Dict]:
    """
    解析 secrets 中的资产配置

    Args:
        assets_data: secrets 中的 assets 数据

    Returns:
        资产配置列表
    """
    if isinstance(assets_data, str):
        try:
            assets = json.loads(assets_data)
        except json.JSONDecodeError:
            logger.error("Secrets 配置格式错误：assets 必须是有效的 JSON 数组")
            return []
    elif isinstance(assets_data, list):
        assets = assets_data
    else:
        logger.error(f"未知的配置格式: {type(assets_data)}")
        return []

    # 转换为标准格式
    result = []
    for asset in assets:
        result.append({
            '代码': asset.get('代码', ''),
            '名称': asset.get('名称', ''),
            '代码类型': asset.get('代码类型', '基金'),
            '资产类别': asset.get('资产类别', '股票'),
            '初始份额': float(asset.get('初始份额', 0)),
            '初始金额': None
        })

    return result


def validate_asset(asset: Dict) -> tuple[bool, str]:
    """
    验证单个资产配置

    Args:
        asset: 资产配置字典

    Returns:
        (是否有效, 错误信息)
    """
    if not asset.get('代码'):
        return False, "代码不能为空"

    if not asset.get('名称'):
        return False, "名称不能为空"

    code_type = asset.get('代码类型', '')
    if code_type not in ['场内ETF', '基金', '股票', '债券']:
        return False, f"无效的代码类型: {code_type}"

    asset_type = asset.get('资产类别', '')
    if asset_type not in ['国债', '股票', '黄金', '现金']:
        return False, f"无效的资产类别: {asset_type}"

    # 检查份额和金额互斥
    shares = asset.get('初始份额')
    amount = asset.get('初始金额')

    if shares is not None and amount is not None:
        if shares > 0 and amount > 0:
            return False, "初始份额和初始金额不能同时输入"

    if shares is None and amount is None:
        return False, "初始份额和初始金额必须输入其中一个"

    return True, ""


def calculate_shares_or_amount(asset: Dict, current_price: float) -> Dict:
    """
    根据当前价格计算份额或金额

    Args:
        asset: 资产配置
        current_price: 当前价格

    Returns:
        更新后的资产配置
    """
    shares = asset.get('初始份额')
    amount = asset.get('初始金额')

    if shares is not None and shares > 0:
        # 已有份额，计算金额
        asset['当前市值'] = shares * current_price
        asset['初始金额'] = asset['当前市值']
    elif amount is not None and amount > 0:
        # 已有金额，计算份额
        asset['初始份额'] = amount / current_price if current_price > 0 else 0
        asset['当前市值'] = amount

    return asset
```

**Step 2: Commit**

```bash
git add utils/config_manager.py
git commit -m "feat: add configuration manager module"
```

---

## Task 2: 添加 LocalStorage 组件

**Files:**
- Create: `utils/local_storage.py`

**Step 1: 创建 LocalStorage 管理模块**

创建文件 `utils/local_storage.py`，实现浏览器 LocalStorage 读写：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器 LocalStorage 管理
"""

import streamlit as st
import streamlit.components.v1 as components
import json

# 声明一个组件
_component_func = None


def local_storage_component(key: str, value: str = None, get: bool = False):
    """
    LocalStorage 组件

    Args:
        key: 存储键
        value: 要存储的值（JSON字符串）
        get: 是否为获取操作
    """
    global _component_func

    if _component_func is None:
        # 第一次调用时创建组件
        _component_func = components.declare_component(
            "local_storage",
            path="utils/local_storage"
        )

    # 调用组件
    return _component_func(key=key, value=value, get=get, default=None)


def save_to_localstorage(key: str, data: dict) -> bool:
    """
    保存数据到 LocalStorage

    Args:
        key: 存储键
        data: 要保存的数据

    Returns:
        是否成功
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        local_storage_component(key, json_str, get=False)
        return True
    except Exception as e:
        st.error(f"保存到 LocalStorage 失败: {e}")
        return False


def load_from_localstorage(key: str) -> Optional[dict]:
    """
    从 LocalStorage 加载数据

    Args:
        key: 存储键

    Returns:
        加载的数据，失败返回 None
    """
    try:
        result = local_storage_component(key, get=True)
        if result:
            return json.loads(result)
        return None
    except Exception as e:
        st.error(f"从 LocalStorage 加载失败: {e}")
        return None
```

**Step 2: 创建 LocalStorage 前端组件**

创建目录 `utils/local_storage`，并在其中创建以下文件：

创建 `utils/local_storage/local_storage.html`：

```html
<!DOCTYPE html>
<html>
<head>
    <title>LocalStorage</title>
</head>
<body>
    <div id="root"></div>
    <script>
        const { key, value, get } = window.props;

        if (get) {
            // 获取数据
            const data = localStorage.getItem(key);
            window.parent.postMessage({ type: 'streamlit:setComponentValue', value: data }, '*');
        } else {
            // 保存数据
            localStorage.setItem(key, value);
            window.parent.postMessage({ type: 'streamlit:setComponentValue', value: true }, '*');
        }
    </script>
</body>
</html>
```

创建 `utils/local_storage/__init__.py`：

```python
import os
import streamlit.components.v1 as components

# 构建组件路径
_parent_dir = os.path.dirname(os.path.abspath(__file__))
_component_dir = os.path.join(_parent_dir, "local_storage")

# 声明组件
_local_storage = components.declare_component("local_storage", path=_component_dir)
```

**Step 3: Commit**

```bash
git add utils/local_storage.py utils/local_storage/
git commit -m "feat: add LocalStorage component"
```

---

## Task 3: 修改 data_fetcher.py - 添加东方财富股票API

**Files:**
- Modify: `utils/data_fetcher.py:98-153`

**Step 1: 在 DataFetcher 类中添加东方财富股票API方法**

在 `utils/data_fetcher.py` 的 `DataFetcher` 类中，在 `get_stock_historical_from_sina` 方法后面添加新方法：

```python
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

        # 判断市场
        if stock_code.startswith('5') or stock_code.startswith('6') or stock_code.startswith('11'):
            # 上海市场
            secid = f"1.{stock_code}"
        else:
            # 深圳市场
            secid = f"0.{stock_code}"

        # 东方财富K线接口
        url = f"http://push2.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=101&fqt=0&beg={start_date.replace('-', '')}&end={end_date.replace('-', '')}"

        response = requests.get(url, headers=self.headers, timeout=15)

        if response.status_code != 200:
            logger.warning(f"获取股票 {stock_code} 数据失败: HTTP {response.status_code}")
            return []

        data = response.json()

        if not data.get('data') or not data['data'].get('klines'):
            return []

        klines = data['data']['klines']

        result = []
        for kline in klines:
            parts = kline.split(',')
            if len(parts) >= 4:
                date_str = parts[0]
                close_price = float(parts[2])  # 收盘价

                if start_date <= date_str <= end_date:
                    result.append({
                        '日期': date_str,
                        '净值': close_price
                    })

        if result:
            logger.info(f"股票 {stock_code} 获取到 {len(result)} 条历史数据")

        return result

    except Exception as e:
        logger.error(f"获取股票 {stock_code} 历史数据出错: {e}")
        return []
```

**Step 2: 修改 fetch_asset_data 方法，根据代码类型选择API**

找到 `fetch_asset_data` 方法（第262-323行），修改获取历史数据的部分：

```python
# 获取历史数据
# 特殊处理19789（25特国06）
if code == '19789' or code == '019789':
    history = self.get_bond_19789_historical(start_date, end_date)
elif code_type == '场内ETF' or code_type == '基金':
    # 场内ETF和基金使用东方财富API
    fetch_code = code.zfill(6) if len(code) < 6 else code
    history = self.get_fund_historical_from_eastmoney(fetch_code, start_date, end_date)
elif code_type == '股票':
    # 股票使用东方财富股票API
    fetch_code = code.zfill(6) if len(code) < 6 else code
    history = self.get_stock_historical_from_eastmoney(fetch_code, start_date, end_date)
elif code_type == '债券':
    # 债券使用债券API
    history = self.get_bond_19789_historical(start_date, end_date)
else:
    # 默认使用东方财富基金API
    fetch_code = code.zfill(6) if len(code) < 6 else code
    history = self.get_fund_historical_from_eastmoney(fetch_code, start_date, end_date)
```

**Step 3: Commit**

```bash
git add utils/data_fetcher.py
git commit -m "feat: add Eastmoney stock API and update API selection logic"
```

---

## Task 4: 修改 app.py - 更新配置加载逻辑

**Files:**
- Modify: `app.py:1-25, 340-381`

**Step 1: 在文件顶部添加导入**

在 `app.py` 的导入部分（第7-13行之后）添加：

```python
from utils.config_manager import get_default_assets, parse_secrets_assets, validate_asset, calculate_shares_or_amount
from utils.local_storage import save_to_localstorage, load_from_localstorage
import json
```

**Step 2: 替换 main 函数中的配置初始化逻辑**

找到 `main()` 函数中的配置初始化部分（第346-368行），替换为：

```python
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
```

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: update config loading logic with priority order"
```

---

## Task 5: 添加配置管理页面

**Files:**
- Modify: `app.py`

**Step 1: 在 main 函数之前添加配置管理页面函数**

在 `main()` 函数之前（第340行之前）添加：

```python
def render_config_manager():
    """渲染配置管理页面"""
    st.title("⚙️ 配置管理")
    st.markdown("---")

    # 操作按钮
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("➕ 添加资产", use_container_width=True):
            st.session_state.show_add_form = True

    with col2:
        # 导出配置
        if st.button("📤 导出配置", use_container_width=True):
            config_data = json.dumps(st.session_state.assets, ensure_ascii=False, indent=2)
            st.download_button(
                label="下载配置文件",
                data=config_data,
                file_name=f"investment_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )

    with col3:
        # 导入配置
        uploaded_file = st.file_uploader(
            "📥 导入配置",
            type=['json'],
            label_visibility="collapsed"
        )
        if uploaded_file:
            try:
                config = json.load(uploaded_file)
                if isinstance(config, list):
                    st.session_state.assets = config
                    save_to_localstorage('investment_assets', config)
                    st.success(f"✅ 成功导入 {len(config)} 个资产")
                    st.rerun()
                else:
                    st.error("❌ 配置文件格式错误：必须是资产列表")
            except Exception as e:
                st.error(f"❌ 导入失败: {e}")

    with col4:
        if st.button("🔄 重置默认", use_container_width=True):
            if st.confirm("确定要重置为默认配置吗？当前配置将丢失。"):
                st.session_state.assets = get_default_assets()
                save_to_localstorage('investment_assets', st.session_state.assets)
                st.success("✅ 已重置为默认配置")
                st.rerun()

    st.markdown("---")

    # 显示当前配置
    st.subheader(f"📋 当前配置（{len(st.session_state.assets)} 个资产）")

    if not st.session_state.assets:
        st.info("💡 暂无配置，请点击上方按钮添加资产")
        return

    # 准备表格数据
    display_data = []
    for i, asset in enumerate(st.session_state.assets):
        display_data.append({
            '序号': i + 1,
            '代码': asset['代码'],
            '名称': asset['名称'],
            '代码类型': asset['代码类型'],
            '资产类别': asset['资产类别'],
            '初始份额': asset.get('初始份额', 0),
            '初始金额': asset.get('初始金额', 0)
        })

    # 使用 data_editor 编辑
    edited_data = st.data_editor(
        display_data,
        column_config={
            '序号': st.column_config.NumberColumn(
                '序号',
                width='small',
                disabled=True
            ),
            '代码': st.column_config.TextColumn(
                '代码',
                width='small',
                required=True
            ),
            '名称': st.column_config.TextColumn(
                '名称',
                width='medium',
                required=True
            ),
            '代码类型': st.column_config.SelectboxColumn(
                '代码类型',
                options=['场内ETF', '基金', '股票', '债券'],
                width='small',
                required=True
            ),
            '资产类别': st.column_config.SelectboxColumn(
                '资产类别',
                options=['国债', '股票', '黄金', '现金'],
                width='small',
                required=True
            ),
            '初始份额': st.column_config.NumberColumn(
                '初始份额',
                width='small',
                min_value=0
            ),
            '初始金额': st.column_config.NumberColumn(
                '初始金额',
                width='small',
                min_value=0
            )
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True
    )

    # 保存按钮
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 保存配置", type="primary", use_container_width=True):
            # 验证并保存
            valid_assets = []
            errors = []

            for row in edited_data.to_dict('records'):
                asset = {
                    '代码': row['代码'],
                    '名称': row['名称'],
                    '代码类型': row['代码类型'],
                    '资产类别': row['资产类别'],
                    '初始份额': row['初始份额'] if row['初始份额'] > 0 else None,
                    '初始金额': row['初始金额'] if row['初始金额'] > 0 else None
                }

                is_valid, error_msg = validate_asset(asset)
                if is_valid:
                    valid_assets.append(asset)
                else:
                    errors.append(f"行 {row['序号']}: {error_msg}")

            if errors:
                for error in errors:
                    st.error(error)
                st.error("❌ 配置验证失败，请检查后重试")
            else:
                st.session_state.assets = valid_assets
                save_to_localstorage('investment_assets', valid_assets)
                st.success(f"✅ 成功保存 {len(valid_assets)} 个资产配置")

    with col2:
        if st.button("🔙 返回看板", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()

    st.markdown("---")
    st.caption("💡 提示：初始份额和初始金额只能输入其中一个，系统会根据API获取的当前价格自动计算另一个值")
```

**Step 2: 修改 main 函数，添加页面导航**

在 `main()` 函数开始处添加页面选择：

```python
def main():
    """主函数"""

    # 页面导航
    page = st.sidebar.radio(
        "导航",
        ["📊 数据看板", "⚙️ 配置管理"],
        index=0 if st.session_state.get('current_page') == 'dashboard' else 1
    )

    if page == "⚙️ 配置管理":
        render_config_manager()
        return

    st.title("📊 投资组合仪表盘")
    st.markdown("---")
```

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add configuration management page"
```

---

## Task 6: 测试和验证

**Step 1: 启动应用测试**

```bash
streamlit run app.py
```

**Step 2: 验证配置加载优先级**

测试场景：
1. 第一次启动（无 LocalStorage，无 secrets）→ 应显示默认配置（4个资产）
2. 添加 secrets.toml 配置 → 应显示 secrets 配置
3. 修改配置并保存 → 刷新后应显示修改后的配置（从 LocalStorage 加载）

**Step 3: 验证配置管理功能**

测试功能：
- ✅ 添加新资产
- ✅ 编辑现有资产
- ✅ 删除资产
- ✅ 导出配置为 JSON
- ✅ 导入 JSON 配置
- ✅ 重置为默认配置
- ✅ 验证份额和金额互斥
- ✅ 验证必填字段

**Step 4: 验证 API 调用**

测试不同代码类型的数据获取：
- 场内ETF（511130）→ 应使用东方财富基金API
- 股票（510300）→ 应使用东方财富股票API
- 债券（005350）→ 应使用债券API

**Step 5: Commit 测试配置**

```bash
# 如果测试通过，可以添加测试说明文档
echo "# 测试说明

## 配置加载测试
- [ ] 默认配置加载
- [ ] secrets.toml 配置加载
- [ ] LocalStorage 配置加载
- [ ] 优先级正确性

## 配置管理测试
- [ ] 添加资产
- [ ] 编辑资产
- [ ] 删除资产
- [ ] 导出配置
- [ ] 导入配置
- [ ] 重置配置

## API 调用测试
- [ ] 场内ETF数据获取
- [ ] 股票数据获取
- [ ] 债券数据获取
" >> docs/TESTING.md

git add docs/TESTING.md
git commit -m "docs: add testing guide"
```

---

## Task 7: 文档更新

**Step 1: 更新 README.md**

如果项目有 README.md，添加配置管理说明：

```markdown
## 配置管理

### 默认配置

应用提供以下默认配置（按优先级加载）：

1. **浏览器 LocalStorage** - 用户自定义配置
2. **secrets.toml** - 部署配置
3. **内置默认配置** - 开箱即用

### 默认资产

- 511130 | 国债30年 | 场内ETF | 国债 | 1000份
- 510300 | 300ETF   | 场内ETF | 股票 | 22000份
- 518660 | 工银黄金 | 场内ETF | 黄金 | 8700份
- 005350 | 短债基金 | 债券   | 现金 | 90000份

### 配置管理

在应用中点击"⚙️ 配置管理"可以：
- ✅ 添加/编辑/删除资产
- ✅ 导出/导入配置（JSON格式）
- ✅ 自动保存到浏览器
- ✅ 份额/金额自动计算

### API 数据源

- **场内ETF/基金**: 东方财富基金API
- **股票**: 东方财富股票API
- **债券**: 专用债券API
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with configuration management"
```

---

## 总结

这个实现计划将：
1. ✅ 实现基于浏览器的配置管理
2. ✅ 支持配置导入导出
3. ✅ 按优先级加载配置（LocalStorage > secrets > 默认）
4. ✅ 根据代码类型选择不同 API
5. ✅ 支持份额/金额互斥计算
6. ✅ 保持向后兼容性

所有修改都是增量式的，不会破坏现有功能。
