# 投资组合仪表盘

基于 Streamlit 的投资组合管理仪表盘，支持多种资产类型的配置、数据展示和可视化分析。

## 功能特性

- 📊 **数据可视化** - 总资产走势、资产配置、标的表现等多维度图表
- ⚙️ **配置管理** - 支持通过页面管理资产配置，无需修改代码
- 💾 **浏览器持久化** - 配置自动保存到浏览器 LocalStorage
- 📥 **配置导入导出** - 支持 JSON 格式的配置备份和迁移
- 🔄 **多数据源** - 根据资产类型自动选择最优数据源

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动应用

```bash
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

## 配置管理

### 默认配置

应用提供以下默认配置（按优先级加载）：

1. **浏览器 LocalStorage** - 用户自定义配置（最高优先级）
2. **secrets.toml** - 部署配置（中等优先级）
3. **内置默认配置** - 开箱即用（最低优先级）

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

### secrets.toml 配置

如需使用 secrets.toml 配置，在 `.streamlit/secrets.toml` 中添加：

```toml
# 国债类
[[assets]]
代码 = "511130"
名称 = "国债30年"
代码类型 = "场内ETF"
资产类别 = "国债"
初始份额 = 1000.0

# 股票类
[[assets]]
代码 = "510300"
名称 = "300ETF"
代码类型 = "场内ETF"
资产类别 = "股票"
初始份额 = 22000.0

# 更多资产...
```

## API 数据源

应用根据**代码类型**自动选择数据源：

- **场内ETF/基金**: 东方财富基金API
- **股票**: 东方财富股票API
- **债券**: 专用债券API

### 数据源说明

1. **东方财富基金API**
   - 适用于：场内ETF、基金
   - 数据：历史净值数据
   - 接口：`http://fund.eastmoney.com/pingzhongdata/{code}.js`

2. **东方财富股票API**
   - 适用于：股票
   - 数据：K线数据（收盘价）
   - 接口：`http://push2.eastmoney.com/api/qt/stock/kline/get`

3. **债券API**
   - 适用于：债券
   - 数据：国债价格
   - 接口：专用债券API + 倒推计算

## 项目结构

```
.
├── app.py                    # 主应用文件
├── requirements.txt          # Python 依赖
├── utils/
│   ├── __init__.py
│   ├── config_manager.py     # 配置管理模块
│   ├── data_fetcher.py       # 数据获取模块
│   └── local_storage.py      # LocalStorage 组件
└── .streamlit/
    └── secrets.toml          # 密钥配置（本地开发）
```

## 依赖项

- streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- requests >= 2.28.0
- plotly >= 5.14.0

## 开发

### 运行测试

```bash
# 启动应用
streamlit run app.py

# 访问 http://localhost:8501
```

### 测试清单

详见 [docs/TESTING.md](docs/TESTING.md)

## 部署

### Streamlit Cloud

1. Fork 项目到 GitHub
2. 在 [Streamlit Cloud](https://share.streamlit.io/) 导入项目
3. 在 Secrets 中配置 `assets`（可选）
4. 部署完成

### Docker

```bash
docker build -t investment-dashboard .
docker run -p 8501:8501 investment-dashboard
```

## 配置格式

### 资产配置字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| 代码 | string | ✅ | 资产代码（6位数字） |
| 名称 | string | ✅ | 资产名称 |
| 代码类型 | string | ✅ | 场内ETF/基金/股票/债券 |
| 资产类别 | string | ✅ | 国债/股票/黄金/现金 |
| 初始份额 | number | ⚠️ | 持有份额（与初始金额二选一） |
| 初始金额 | number | ⚠️ | 初始金额（与初始份额二选一） |

### 代码类型说明

- **场内ETF**: 交易所交易基金，使用东方财富基金API
- **基金**: 场外基金，使用东方财富基金API
- **股票**: 股票，使用东方财富股票API
- **债券**: 债券，使用专用债券API

### 资产类别说明

- **国债**: 国债类资产
- **股票**: 股票类资产
- **黄金**: 黄金类资产
- **现金**: 现金类资产（如货币基金）

## 常见问题

### Q: 如何备份配置？

A: 在配置管理页面点击"📤 导出配置"，下载 JSON 文件即可。

### Q: 如何恢复配置？

A: 在配置管理页面点击"📥 导入配置"，上传之前导出的 JSON 文件。

### Q: 配置保存在哪里？

A: 配置保存在浏览器的 LocalStorage 中，关闭浏览器后仍然保留。清除浏览器数据会导致配置丢失。

### Q: 如何清除配置？

A: 在配置管理页面点击"🔄 重置默认"，或在浏览器开发者工具中手动清除 LocalStorage。

### Q: 支持哪些资产？

A: 目前支持场内ETF、基金、股票、债券四种类型。资产类别分为国债、股票、黄金、现金四种。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
