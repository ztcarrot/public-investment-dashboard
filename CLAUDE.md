# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 运行命令

```bash
# 启动应用（开发）
streamlit run app.py

# 安装依赖
pip install -r requirements.txt

# 快速启动（包含环境检查和依赖安装）
./run.sh

# 激活虚拟环境（手动）
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

## 核心架构

### 配置存储策略

**重要**：应用使用 URL 查询参数作为主要存储方式，实现多用户隔离。

**加载优先级**：
1. `st.session_state`（当前会话，最高优先级）
2. URL 查询参数（主要存储，多用户独立）
3. `.streamlit/secrets.toml`（部署配置，仅资产）
4. 默认配置（内置后备）

**保存机制**：
- 保存到 `st.session_state`（立即生效）
- 保存到 URL 查询参数（持久化，使用 zlib 压缩 + Base64 编码）
- 保存到浏览器 localStorage（辅助，前端使用）

**配置管理器**：
- `AssetsConfigManager`（`utils/assets_config.py`）- 资产配置
- `DateConfigManager`（`utils/date_config.py`）- 日期配置
- `URLConfigManager`（`utils/url_config.py`）- URL 参数读写

**重要实现细节**：
- `compress_json()` / `decompress_json()` - 使用 zlib 压缩 + Base64 编码，减少 URL 长度
- URL 安全处理：`+` → `-`，`/` → `_`，移除 `=` padding

### 数据获取架构

`DataFetcher` 类（`utils/data_fetcher.py`）根据**代码类型**自动选择数据源：

- **场内ETF** → 新浪财经 API（交易价格）
- **基金** → 东方财富基金 API（净值数据）
- **股票** → 东方财富股票 API（K线数据）
- **债券** → 东方财富基金 API 或特殊处理（如 19789）

**特殊处理**：
- 代码 `19789` 或 `019789` 使用专用债券价格推算
- 基金净值日期需要 +1 天调整（收盘后公布）

**数据流程**：
```
fetch_all_assets_data()
  → fetch_asset_data() 每个资产
    → API 调用（根据代码类型）
      → DataFrame 转换
        → 合并所有数据
```

**API 端点**：
- 东方财富基金：`http://fund.eastmoney.com/pingzhongdata/{code}.js`
- 新浪财经股票：`http://hq.sinajs.cn/list={code}`
- 东方财富股票：`http://push2.eastmoney.com/api/qt/stock/kline/get`

### 应用结构

**主应用文件**（`app.py`）：
- `load_data()` - 数据加载函数，使用 `st.session_state` 缓存（key: `data_cache_{date}`）
- `load_assets_config()` - 资产配置加载
- `main()` - 主函数，处理页面导航和状态初始化
- `render_config_manager()` - 配置管理页面（表单编辑、导入导出）
- `calculate_change_percentages()` - 计算涨跌幅（日/周/月/累计）
- `render_total_assets_chart()` - 总资产走势图（含回撤分析）
- `render_allocation_chart()` - 资产配置图表（饼图 + 堆叠面积图）
- `render_asset_performance()` - 各标的归一化走势图
- `render_data_table()` - 历史数据表格展示

**页面导航**：
- 侧边栏使用 `st.radio` 在"📊 数据看板"和"⚙️ 配置管理"之间切换
- 通过 `st.session_state.current_page` 和 `page_selection` 同步状态

**关键状态变量**：
- `st.session_state.assets` - 资产配置列表
- `st.session_state.start_date` - 开始日期
- `st.session_state.show_numbers` - 是否显示金额（默认 False，隐藏）
- `st.session_state.current_page` - 当前页面（'dashboard' 或 'config'）
- `st.session_state.page_selection` - 页面选择索引（0=看板, 1=配置）
- `st.session_state.show_add_form` - 是否显示添加/编辑表单
- `st.session_state.editing_index` - 当前编辑的资产索引
- `data_cache_{date}` - 数据缓存键（避免重复 API 调用）

### 数据格式

**资产配置字段**：
```python
{
    '代码': '511130',           # 6位数字代码
    '名称': '国债30年',
    '代码类型': '场内ETF',       # 场内ETF/基金/股票/债券
    '资产类别': '国债',          # 国债/股票/黄金/现金
    '初始份额': 1000.0,         # 与初始金额二选一
    '初始金额': None
}
```

**DataFrame 结构**（`fetch_all_assets_data` 返回）：
- 日期 | 代码 | 名称 | 代码类型 | 资产类型 | 最新价格 | 持有份额 | 当前市值 | 收益率

### Streamlit 特殊注意事项

**延迟访问 Streamlit API**：
- 模块导入时不能访问 `st.query_params`、`st.session_state` 等
- 使用 `@property` 装饰器延迟加载（见 `URLConfigManager.__init__`）
- 全局实例化时避免初始化 Streamlit 对象

**CSS 注入**：
- 页面配置后（`st.set_page_config`）立即注入 CSS
- 移动端检测使用 `@media (max-width: 768px)` 媒体查询
- Metric 组件数字左对齐：`[data-testid="stMetricValue"] { text-align: left; }`

**组件使用**：
- `st.components.v1.html()` - 注入 JavaScript（localStorage 操作）
- `st.query_params` - URL 参数读写（支持中文编码）
- `st.form()` - 表单提交（避免频繁重渲染）
- `st.expander()` - 可折叠面板（详情展示）
- `st.tabs()` - 标签页（图表分类）
- `st.metric()` - 数据卡片（红涨绿跌，使用 `delta_color="inverse"`）

**性能优化**：
- 数据缓存：`st.session_state[data_cache_{date}]`
- 价格缓存：`st.session_state.current_price_cache`
- 按需加载：只在显示表单时获取当前价格
- 后台刷新：配置修改后不跳转，后台刷新数据

### 默认资产配置

永久投资组合四大核心资产：
- 511130 | 国债30年 | 场内ETF | 国债 | 1000份
- 510300 | 300ETF   | 场内ETF | 股票 | 22000份
- 518660 | 工银黄金 | 场内ETF | 黄金 | 8700份
- 005350 | 短债基金 | 债券   | 现金 | 90000份

### 图表与可视化

**总资产走势图**（`render_total_assets_chart`）：
- 折线图 + 趋势线
- 关键点标记：初值、末值、最大值、最小值
- 最大回撤矩形标注（红色半透明）
- 最长恢复期矩形标注（绿色虚线）
- 统计指标：CAGR、最大回撤、恢复期、投资天数

**资产配置图**（`render_allocation_chart`）：
- 甜甜圈图：金额分布
- 堆叠面积图：占比趋势 + 金额趋势
- 贡献度分析：各资产类别对总增值的贡献率

**标的表现图**（`render_asset_performance`）：
- 按资产类型分组
- 归一化显示（起点=100）
- 支持多标的对比

### 金额显示控制

**隐藏/显示金额**：
- 状态：`st.session_state.show_numbers`（默认 False）
- URL 参数：`?show=1`（显示） / `?show=0`（隐藏）
- 切换按钮："🙈 显示金额" ↔ "👁️ 隐藏金额"
- 隐藏模式：金额显示为 `*****`，仍显示涨跌幅百分比

### 测试清单

详见 `docs/TESTING.md`，包含：
- 配置加载测试（默认/secrets/URL 优先级）
- 配置管理测试（添加/编辑/删除/导入导出）
- API 调用测试（不同代码类型的数据源）
- 浏览器兼容性（Chrome/Firefox/Safari）
- 性能测试（50+ 资产加载）

### 常见问题

**Q: 配置保存在哪里？**
A: 主要保存在 URL 查询参数中（压缩 + Base64 编码），支持分享和书签。

**Q: 如何分享配置？**
A: 直接复制浏览器地址栏的完整 URL，发送给其他人即可。

**Q: 数据从哪里来？**
A: 从公开 API 实时抓取（东方财富、新浪财经），无需用户申请 API Key。

**Q: 支持哪些资产？**
A: 场内ETF、基金、股票、债券。资产类别：国债、股票、黄金、现金。

**Q: 如何添加新资产？**
A: 进入"⚙️ 配置管理" → "➕ 添加资产" → 填写信息 → 保存。配置自动保存到 URL。

### 项目结构

```
public-investment-dashboard/
├── app.py                      # 主应用（1700+ 行）
├── requirements.txt            # Python 依赖
├── run.sh                      # 快速启动脚本
├── CLAUDE.md                   # 本文件（Claude Code 指南）
├── README.md                   # 项目说明文档
├── utils/
│   ├── __init__.py
│   ├── data_fetcher.py         # 数据抓取（多数据源）
│   ├── assets_config.py        # 资产配置管理器
│   ├── date_config.py          # 日期配置管理器
│   ├── url_config.py           # URL 参数管理器
│   ├── config_manager.py       # 默认配置 + 验证
│   └── local_storage.py        # LocalStorage 组件
├── docs/
│   ├── TESTING.md              # 测试清单
│   └── DATE_STORAGE.md         # 日期存储说明
└── .streamlit/
    └── secrets.toml            # 部署配置（可选）
```

### 开发工作流

**1. 添加新功能**：
- 优先编辑现有文件，避免创建新文件
- 遵循现有代码风格和命名规范
- 使用中文注释和文档字符串

**2. 修改数据抓取逻辑**：
- 主要修改 `utils/data_fetcher.py`
- 添加新的 API 端点支持
- 更新 `fetch_asset_data()` 方法的类型判断

**3. 修改配置存储**：
- 资产配置：`utils/assets_config.py`
- 日期配置：`utils/date_config.py`
- URL 读写：`utils/url_config.py`

**4. 修改页面布局**：
- 主看板：`app.py` 的 `main()` 函数
- 配置页面：`app.py` 的 `render_config_manager()` 函数
- CSS 样式：`app.py` 顶部的 `st.markdown()` 注入

**5. 测试**：
- 运行 `./run.sh` 启动应用
- 参考 `docs/TESTING.md` 进行测试
- 检查不同浏览器的兼容性

**6. 部署**：
- Streamlit Cloud：自动从 GitHub 部署
- Docker：使用 `Dockerfile` 和 `docker-compose.yml`
- 确保在 `.streamlit/secrets.toml` 中配置资产（可选）

### 代码风格与约定

**命名规范**：
- 函数：小写 + 下划线（如 `load_data`）
- 类：大驼峰（如 `DataFetcher`）
- 常量：大写 + 下划线（如 `MAX_RETRIES`）
- 私有方法：单下划线前缀（如 `_save_to_localstorage`）

**中文处理**：
- 用户界面文本：中文（如 `st.title("📊 永久投资组合仪表盘")`）
- 日志消息：中文（如 `logger.info("从 URL 加载资产配置")`）
- 变量名和函数名：英文（如 `assets_config`）
- 注释：中文

**错误处理**：
- API 调用失败：记录警告日志，返回空列表/None，不抛出异常
- 用户输入验证：使用 `validate_asset()` 函数，显示友好的错误消息
- 数据缺失：显示提示信息，不崩溃

**日志记录**：
- 使用 `logging` 模块
- 级别：`logger.debug()`（调试）、`logger.info()`（重要操作）、`logger.warning()`（异常情况）、`logger.error()`（错误）
- 包含上下文信息（如资产代码、数据长度）

**Streamlit 最佳实践**：
- 避免在模块顶层访问 Streamlit API
- 使用 `st.session_state` 缓存数据，避免重复计算
- 表单提交使用 `st.form()` 而不是实时更新
- 使用 `st.rerun()` 而不是 `st.experimental_rerun()`
- 图表使用 `use_container_width=True` 自适应宽度

**数据处理**：
- 使用 pandas DataFrame 进行数据操作
- 日期格式：`YYYY-MM-DD`（字符串）或 `datetime.date` 对象
- 金额：使用 `float` 类型，显示时格式化为 `¥{:, .2f}`
- 百分比：使用 `float` 类型，显示时格式化为 `{:+.2f}%`（带符号）
