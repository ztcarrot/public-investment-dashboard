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

### 应用结构

**主应用文件**（`app.py`）：
- `load_data()` - 数据加载函数，使用 `st.session_state` 缓存（key: `data_cache_{date}`）
- `load_assets_config()` - 资产配置加载
- `main()` - 主函数，处理页面导航和状态初始化
- `render_config_manager()` - 配置管理页面（表格编辑、导入导出）

**页面导航**：
- 侧边栏使用 `st.radio` 在"📊 数据看板"和"⚙️ 配置管理"之间切换
- 通过 `st.session_state.current_page` 和 `page_selection` 同步状态

**关键状态变量**：
- `st.session_state.assets` - 资产配置列表
- `st.session_state.start_date` - 开始日期
- `st.session_state.show_numbers` - 是否显示金额（默认 False，隐藏）
- `st.session_state.current_page` - 当前页面（'dashboard' 或 'config'）

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

**组件使用**：
- `st.components.v1.html()` - 注入 JavaScript（localStorage 操作）
- `st.query_params` - URL 参数读写（支持中文编码）

### 默认资产配置

永久投资组合四大核心资产：
- 511130 | 国债30年 | 场内ETF | 国债 | 1000份
- 510300 | 300ETF   | 场内ETF | 股票 | 22000份
- 518660 | 工银黄金 | 场内ETF | 黄金 | 8700份
- 005350 | 短债基金 | 债券   | 现金 | 90000份

### 测试清单

详见 `docs/TESTING.md`，包含：
- 配置加载测试（默认/secrets/LocalStorage 优先级）
- 配置管理测试（添加/编辑/删除/导入导出）
- API 调用测试（不同代码类型的数据源）
- 浏览器兼容性（Chrome/Firefox/Safari）
- 性能测试（50+ 资产加载）
