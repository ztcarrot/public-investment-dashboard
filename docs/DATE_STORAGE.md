# 日期配置存储说明

## 存储方案

本应用使用**URL 查询参数为主**的多层存储策略，支持本地开发和 Streamlit Cloud 部署：

### 1. URL 查询参数（主要存储）
- **存储方式**：URL 查询参数
- **参数名**：`date`（例如：`?date=2025-01-01`）
- **适用场景**：所有环境，特别是 Streamlit Cloud
- **特点**：
  - ✅ 每个用户完全独立的配置
  - ✅ 配置保存在 URL 中，刷新不会丢失
  - ✅ 可以分享配置 URL 给其他人
  - ✅ 不占用服务器存储空间
  - ❌ URL 会变长

### 2. 本地文件存储（后备存储）
- **存储方式**：文件存储 (`data/date_config.json`)
- **路径**：项目根目录下的 `data/` 文件夹
- **适用场景**：单用户本地开发
- **特点**：
  - ✅ 配置持久化
  - ❌ 多用户共享（不适合云端部署）

### 3. 浏览器 localStorage（辅助存储）
- **存储方式**：浏览器 localStorage
- **键名**：`investment_start_date`
- **特点**：
  - ✅ 每个用户独立存储
  - ❌ 无法从 Python 读取（仅用于 JavaScript）
  - ❌ 清除浏览器缓存会丢失

## 工作原理

### 加载优先级

```
session_state（当前会话）
    ↓（未找到）
URL 查询参数（主要存储，多用户独立）
    ↓（未找到）
文件存储（本地开发后备）
    ↓（未找到）
默认值（2025-01-01）
```

### 保存机制

用户修改日期时：
1. ✅ 保存到 `st.session_state`（当前会话立即生效）
2. ✅ 保存到 URL 查询参数（主要存储，多用户独立）
3. ✅ 保存到浏览器 `localStorage`（辅助存储）
4. ✅ 保存到文件 `data/date_config.json`（本地开发后备）

## URL 参数格式

### 日期参数
```
https://your-app.streamlit.app/?date=2025-01-01
```

### 资产配置参数（压缩编码）
```
https://your-app.streamlit.app/?date=2025-01-01&assets=eJyrVkrLz1O...
```

资产配置使用压缩和 Base64 编码，减少 URL 长度。

## 多用户部署说明

### Streamlit Cloud 部署

**URL 参数方案的优势**：
- 每个用户有独立的 URL 和配置
- 不需要数据库或文件系统
- 配置不会丢失（保存在 URL 中）
- 可以分享配置 URL

**示例**：
- 用户 A：`https://app.com/?date=2025-01-01&assets=...`
- 用户 B：`https://app.com/?date=2024-06-01&assets=...`

两个用户完全独立，互不影响。

### 使用示例

#### 本地开发
```python
# 自动从 URL 参数加载（优先）或文件加载
date = date_config_manager.load()

# 用户修改后保存到 URL 和文件
date_config_manager.save(selected_date)
```

#### Streamlit Cloud
```python
# 自动从 URL 参数加载
date = date_config_manager.load()

# 保存到 URL 参数
date_config_manager.save(selected_date)
```

## 注意事项

1. **URL 长度限制**：大多数浏览器支持 2000+ 字符的 URL，足够存储日常配置

2. **书签保存**：用户可以将配置 URL 保存为书签，方便下次访问

3. **分享配置**：可以直接分享 URL 给其他人，他们会看到相同的配置

4. **本地开发**：配置会保存在 `data/date_config.json`，提交到 Git 前请添加到 `.gitignore`

5. **文件权限**：确保应用有写入 `data/` 目录的权限（仅本地开发需要）

## 对比之前的方案

### 之前的问题
- ❌ localStorage 无法从 Python 读取
- ❌ 文件存储在多用户环境下共享
- ❌ 用户配置会互相覆盖

### 现在的优势
- ✅ URL 参数完全独立，多用户隔离
- ✅ 配置持久化，刷新不丢失
- ✅ 可以分享和保存配置 URL
- ✅ 不依赖服务器存储空间
