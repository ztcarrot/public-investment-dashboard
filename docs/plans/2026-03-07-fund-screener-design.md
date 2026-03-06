# 短债基金筛选功能设计文档

**日期**: 2026-03-07
**状态**: 已批准
**作者**: Claude

---

## 1. 功能概述

在现有 Streamlit 应用中添加一个独立的短债基金筛选页面，帮助用户找到表现最优的短债基金，并可一键添加到投资组合配置中。

---

## 2. 核心需求

| 需求项 | 说明 |
|--------|------|
| **筛选条件** | 基金名称包含"短债"，成立≥5年 |
| **筛选流程** | 按成立至今年化收益率选前100，再按最大回撤选前30 |
| **数据来源** | akshare API（`fund_name_em` + 历史净值数据） |
| **缓存策略** | 每周更新一次，其他时候使用缓存 |
| **集成方式** | 可添加到投资组合配置 |

---

## 3. 架构设计

### 3.1 新增文件

```
utils/
├── fund_screener.py      # 基金筛选核心逻辑
├── fund_cache.py         # 基金数据缓存管理

cache/
└── fund_screening.json   # 缓存文件（自动创建）
```

### 3.2 修改文件

```
app.py                    # 添加新页面路由和渲染函数
requirements.txt          # 无需修改（akshare已存在）
```

### 3.3 数据流程

```
用户访问筛选页面
    ↓
检查缓存（文件存储：cache/fund_screening.json）
    ↓
缓存存在且未过期？→ 加载缓存
    ↓ 否
从 akshare 获取数据：
  1. fund_name_em() - 获取所有基金
  2. 筛选短债基金（名称包含"短债"）
  3. 获取历史净值（fund_open_fund_info_em）
  4. 计算年化收益率和最大回撤
    ↓
保存到缓存
    ↓
展示筛选结果（前30名）
```

---

## 4. 功能模块设计

### 4.1 页面导航

**修改位置**：`app.py` 的 `main()` 函数侧边栏

**新增选项**：
```python
page = st.radio(
    "选择页面",
    options=["📊 数据看板", "🔍 基金筛选", "⚙️ 配置管理"],
    index=st.session_state.page_selection
)
```

**状态管理**：
- `page_selection`: 0=看板, 1=基金筛选, 2=配置
- `current_page`: 'dashboard', 'fund_screener', 'config'

### 4.2 筛选逻辑（`utils/fund_screener.py`）

#### 核心函数

| 函数名 | 功能 |
|--------|------|
| `get_all_funds()` | 获取所有基金列表 |
| `filter_short_bond_funds(funds)` | 筛选短债基金 |
| `get_fund_nav_history(code)` | 获取基金历史净值 |
| `calculate_annual_return(nav_data)` | 计算年化收益率 |
| `calculate_max_drawdown(nav_data)` | 计算最大回撤 |
| `screen_funds()` | 执行完整筛选流程 |

#### 筛选步骤

```python
# 步骤1: 基础筛选
funds = fund_name_em()
short_bond_funds = funds[funds['基金简称'].str.contains('短债')]
short_bond_funds = short_bond_funds[
    short_bond_funds['成立日期'] <= (today - 5years)
]

# 步骤2: 计算指标
for fund in short_bond_funds:
    nav_data = get_fund_nav(fund['基金代码'])
    fund['年化收益率'] = calculate_annual_return(nav_data)
    fund['最大回撤'] = calculate_max_drawdown(nav_data)

# 步骤3: 串联筛选
top100 = funds.nlargest(100, '年化收益率')
top30 = top100.nsmallest(30, '最大回撤')
```

#### 计算公式

**年化收益率**：
```python
annual_return = (当前净值 / 初始净值) ^ (365 / 运营天数) - 1
```

**最大回撤**：
```python
drawdown = (峰值 - 当前值) / 峰值
max_drawdown = max(drawdown)
```

### 4.3 缓存管理（`utils/fund_cache.py`）

#### 缓存文件结构

**路径**：`cache/fund_screening.json`

**数据结构**：
```json
{
  "update_time": "2026-03-07",
  "total_funds": 150,
  "screened_funds": [
    {
      "基金代码": "005350",
      "基金简称": "嘉实短债A",
      "基金类型": "债券型",
      "成立日期": "2018-05-10",
      "年化收益率": 4.2,
      "最大回撤": -0.15,
      "基金规模": 50.3,
      "基金经理": "张三",
      "基金公司": "嘉实基金"
    }
  ]
}
```

#### 缓存策略类

```python
class FundCacheManager:
    def load(self) -> dict | None
    def save(self, data: dict) -> None
    def is_expired(self, days: int = 7) -> bool
    def get_cache_age_days(self) -> int
```

**过期判断**：
- 检查 `update_time` 与当前日期差值
- 如果差值 ≥ 7天，返回 `True`
- 提供手动刷新按钮强制更新

---

## 5. UI 设计

### 5.1 页面布局

```
┌─────────────────────────────────────────┐
│ 🔍 短债基金筛选                          │
├─────────────────────────────────────────┤
│ [🔄 刷新数据] 缓存时间: 2026-03-01      │
│ ⚠️ 共找到 150 只短债基金，成立≥5年      │
│                                          │
│ 📊 筛选结果（前 30 名）                  │
│ ┌────────────────────────────────────┐  │
│ │ 代码  │ 名称 │ 年化收益 │ 最大回撤 │  │
│ │ 005350│ 嘉实 │ 4.2%    │ -0.15%  │  │
│ │ [➕]  │      │         │         │  │
│ └────────────────────────────────────┘  │
│                                          │
│ 📈 选中基金的详情（点击行查看）          │
└─────────────────────────────────────────┘
```

### 5.2 数据表格

使用 `st.dataframe()` 展示，包含列：

| 列名 | 说明 | 样式 |
|------|------|------|
| 基金代码 | 6位代码 | - |
| 基金简称 | 基金名称 | - |
| 基金类型 | 如"债券型" | - |
| 成立日期 | YYYY-MM-DD | - |
| 年化收益率 | 百分比 | 高=绿色 |
| 最大回撤 | 负百分比 | 低=绿色 |
| 基金规模 | 亿元 | - |
| 基金经理 | 姓名 | - |
| 基金公司 | 公司名称 | - |
| 操作 | "➕ 添加"按钮 | - |

### 5.3 添加到配置功能

**交互流程**：
1. 用户点击表格中的"➕ 添加"按钮
2. 弹出侧边栏或对话框，输入初始份额/金额
3. 点击确认后：
   - 保存到 `st.session_state.assets`
   - 同步到 URL 参数
   - 显示成功提示："✅ 已添加 嘉实短债A 到投资组合"

**表单字段**：
- 基金代码（自动填充，只读）
- 基金名称（自动填充，只读）
- 代码类型（固定为"债券"）
- 资产类别（固定为"现金"）
- 初始份额（必填）
- 初始金额（可选，与份额二选一）

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|----------|
| **API 调用失败** | 显示友好提示，使用缓存数据（如果有） |
| **数据缺失** | 跳过该基金，记录日志 |
| **计算异常** | 使用默认值（0），在表格中标注"数据异常" |
| **缓存文件损坏** | 删除缓存，重新获取数据 |
| **网络超时** | 显示"数据获取中..."，30秒后提示超时 |

---

## 7. 性能优化

### 7.1 并行获取

使用 `concurrent.futures.ThreadPoolExecutor` 并行获取多只基金的净值数据：

```python
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {
        executor.submit(get_fund_nav, code): code
        for code in fund_codes
    }
    for future in as_completed(futures):
        result = future.result()
```

### 7.2 进度显示

使用 `st.progress()` 显示数据加载进度：

```python
progress_bar = st.progress(0, text="正在获取基金数据...")
for i, fund in enumerate(funds):
    # 处理基金数据
    progress_bar.progress((i + 1) / len(funds))
```

### 7.3 增量更新

- 只更新缓存中不存在的基金
- 如果基金数量 ≤ 100，全量更新

---

## 8. 测试计划

### 8.1 单元测试

| 测试项 | 验证内容 |
|--------|----------|
| 缓存读写 | 验证缓存文件正确保存和加载 |
| 过期判断 | 验证7天过期逻辑 |
| 筛选逻辑 | 验证短债基金筛选结果 |
| 计算函数 | 验证年化收益和回撤计算 |

### 8.2 集成测试

| 测试项 | 验证内容 |
|--------|----------|
| 页面导航 | 验证新页面可以正常访问 |
| 数据展示 | 验证表格正确显示 |
| 添加配置 | 验证添加功能正常工作 |
| 缓存更新 | 验证手动刷新按钮功能 |

### 8.3 性能测试

| 测试项 | 目标 |
|--------|------|
| 100只基金加载 | < 30秒 |
| 缓存加载 | < 1秒 |
| 表格渲染 | < 2秒 |

---

## 9. 实现步骤概览

1. 创建 `utils/fund_cache.py` - 缓存管理
2. 创建 `utils/fund_screener.py` - 筛选逻辑
3. 修改 `app.py` - 添加页面路由和渲染
4. 测试功能完整性
5. 性能优化和错误处理完善

---

## 10. 后续优化方向

- [ ] 支持更多筛选条件（基金规模、基金经理等）
- [ ] 添加基金详情页面（净值走势图）
- [ ] 支持导出筛选结果到 Excel
- [ ] 添加基金对比功能
