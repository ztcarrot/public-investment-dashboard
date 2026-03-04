# 日期配置存储说明

## 存储方案

本应用使用**混合存储策略**，支持本地开发和 Streamlit Cloud 部署：

### 1. 本地开发环境
- **存储方式**：文件存储 (`data/date_config.json`)
- **路径**：项目根目录下的 `data/` 文件夹
- **适用场景**：单用户本地开发

### 2. Streamlit Cloud 部署
- **存储方式**：浏览器 localStorage
- **键名**：`investment_start_date`
- **适用场景**：多用户云端部署
- **特点**：
  - ✅ 每个用户独立存储
  - ✅ 不占用服务器空间
  - ❌ 换设备/浏览器会丢失
  - ❌ 清除浏览器缓存会丢失

## 工作原理

### 加载优先级

```
session_state（当前会话）
    ↓（未找到）
localStorage（浏览器存储）
    ↓（未找到或本地开发）
文件存储（本地文件）
    ↓（未找到）
默认值（2025-01-01）
```

### 保存机制

用户修改日期时：
1. ✅ 保存到 `st.session_state`（当前会话立即生效）
2. ✅ 保存到浏览器 `localStorage`（Streamlit Cloud 多用户）
3. ✅ 保存到文件 `data/date_config.json`（本地开发单用户）

## 文件格式

### `data/date_config.json`

```json
{
  "start_date": "2024-06-01",
  "updated_at": "2026-03-04 13:00:00"
}
```

## 多用户部署说明

### Streamlit Cloud 部署

**问题**：
- 文件系统是临时的，每次重启会丢失
- 多用户共享同一个文件会冲突

**解决方案**：
- 使用浏览器 `localStorage` 存储每个用户的配置
- 每个用户在各自浏览器中独立存储
- 适合个人使用或小团队部署

**局限性**：
- 用户换设备/浏览器会丢失配置
- 无法跨设备同步
- 清除浏览器缓存会丢失

### 企业级部署（未实现）

如需真正的多用户持久化，建议使用：

1. **数据库方案**：
   - SQLite（小型应用）
   - PostgreSQL（生产环境）
   - Redis（高性能缓存）

2. **用户认证**：
   - 添加用户登录系统
   - 每个用户独立存储配置

3. **云存储**：
   - Firebase
   - AWS S3
   - Vercel KV

## 使用示例

### 本地开发

```python
# 自动从 data/date_config.json 加载
date = date_config_manager.load()

# 用户修改后保存
date_config_manager.save(selected_date)
```

### Streamlit Cloud

```python
# 自动从 localStorage 加载（每个用户独立）
date = date_config_manager.load()

# 保存到用户浏览器
date_config_manager.save(selected_date)
```

## 注意事项

1. **本地开发**：配置会保存在 `data/date_config.json`，提交到 Git 前请添加到 `.gitignore`

2. **Streamlit Cloud**：配置存储在用户浏览器，无法跨设备同步

3. **清除缓存**：用户清除浏览器缓存后，配置会恢复为默认值（2025-01-01）

4. **文件权限**：确保应用有写入 `data/` 目录的权限
