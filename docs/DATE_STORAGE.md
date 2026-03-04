# 配置存储说明

## 存储方案

本应用使用 **URL 查询参数** 作为唯一的配置存储方式，实现真正的多用户隔离。

### URL 查询参数（唯一存储）
- **存储方式**：URL 查询参数
- **日期参数名**：`date`（例如：`?date=2025-01-01`）
- **资产参数名**：`assets`（压缩编码）
- **适用场景**：所有环境（本地开发和 Streamlit Cloud）
- **特点**：
  - ✅ 每个用户完全独立的配置
  - ✅ 配置保存在 URL 中，刷新不会丢失
  - ✅ 可以分享配置 URL 给其他人
  - ✅ 不占用服务器存储空间
  - ✅ 不需要文件系统权限
  - ❌ URL 会变长（但通过压缩减少）

### localStorage（辅助存储）
- **存储方式**：浏览器 localStorage
- **用途**：仅作为辅助，用于 JavaScript 访问
- **注意**：Python 无法读取 localStorage，仅用于前端

## 工作原理

### 加载优先级

```
session_state（当前会话）
    ↓（未找到）
URL 查询参数（主要存储，多用户独立）
    ↓（未找到）
secrets.toml（仅资产配置，部署者配置的默认值）
    ↓（未找到）
默认配置（日期: 2025-01-01，资产: 空）
```

### 保存机制

用户修改配置时：
1. ✅ 保存到 `st.session_state`（当前会话立即生效）
2. ✅ 保存到 URL 查询参数（主要存储，多用户独立）
3. ✅ 保存到浏览器 `localStorage`（辅助存储，前端使用）

## URL 参数格式

### 日期参数
```
https://your-app.streamlit.app/?date=2025-01-01
```

### 资产配置参数（压缩编码）
```
https://your-app.streamlit.app/?date=2025-01-01&assets=eJyrVkrLz1O...
```

资产配置使用 zlib 压缩和 Base64 编码，大幅减少 URL 长度：
- 原始 JSON：约 2000 字符
- 压缩后：约 300-500 字符

## 多用户部署说明

### Streamlit Cloud 部署

**URL 参数方案的优势**：
- 每个用户有独立的 URL 和配置
- 不需要数据库或文件系统
- 配置不会丢失（保存在 URL 中）
- 可以分享配置 URL

**示例**：
- 用户 A：`https://app.com/?date=2025-01-01&assets=xxx`
- 用户 B：`https://app.com/?date=2024-06-01&assets=yyy`

两个用户完全独立，互不影响。

### 使用示例

```python
# 加载配置（从 URL 或默认值）
date = date_config_manager.load()
assets = assets_config_manager.load()

# 保存配置到 URL
date_config_manager.save(selected_date)
assets_config_manager.save(assets)
```

## 注意事项

1. **URL 长度限制**：
   - 大多数浏览器支持 2000+ 字符的 URL
   - 使用压缩后，日常配置通常在 500 字符以内
   - 如果资产非常多（50+），可能会接近限制

2. **书签保存**：
   - 用户可以将配置 URL 保存为书签
   - 下次打开书签会自动加载配置

3. **分享配置**：
   - 可以直接分享 URL 给其他人
   - 他们会看到相同的日期和资产配置

4. **不使用文件存储**：
   - ✅ 避免多用户文件冲突
   - ✅ 不需要文件系统权限
   - ✅ 简化部署流程
   - ✅ 配置完全隔离

## 与其他方案对比

### ❌ 文件存储（已弃用）
- 多用户共享配置
- 需要文件系统权限
- Streamlit Cloud 上会丢失

### ❌ 纯 localStorage（已弃用）
- Python 无法读取
- 需要复杂的同步机制

### ✅ URL 参数（当前方案）
- 完全隔离
- 持久化
- 可分享
- 无服务器存储需求
