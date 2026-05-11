# Alphalens WebUI — 快速命令参考

## 环境准备

```bash
# 首次安装依赖（前端 npm + 后端 pip）
python manage.py init
```

## 启动系统

```bash
# 普通启动（无测试数据）
python manage.py start

# 启动 + 生成测试 CSV（模拟首次使用，需手动上传）
python manage.py start --generate-test-data

# 启动 + 预加载测试数据库（直接开始分析）
python manage.py start --generate-test-db
```

启动后访问：**http://localhost:5173**

## 生成测试数据（不启动服务）

```bash
python backend/scripts/generate_test_data.py
```

输出文件位于 `db/test_data/`：
- `factor.csv` — 因子数据（1,260 行，date/asset/factor_value）
- `prices.csv` — 价格数据（252 行，date/5只股票）

## 服务管理

所有服务通过 `alphalens/definitions/*.py` 自动发现，无需硬编码。

### 交互式菜单模式（推荐）

```bash
# 进入交互式菜单（选择式管理）
python manage.py menu

# 生产环境模式
python manage.py menu --mode prod

# 快捷方式（同上）
python -m alphalens
```

菜单选项：
```
  1)  Start all services       7)  Start specific service
  2)  Stop all services        8)  Stop specific service
  3)  Restart all services     9)  View service logs
  4)  Show status              10) Database info
  5)  Health check             11) Generate test data
  6)  List registered services 12) Run tests
  0)  Exit
```

### 命令行模式

```bash
python manage.py service list                  # 列出所有注册服务
python manage.py service register <name> ...   # 注册新服务
python manage.py service unregister <name>     # 移除注册服务

python manage.py stop              # 停止所有服务
python manage.py stop backend      # 停止特定服务
python manage.py restart           # 重启所有服务
python manage.py status            # 查看所有服务状态
python manage.py health            # 健康检查
python manage.py logs backend      # 查看日志
```

### 注册自定义服务示例

```bash
python manage.py service register my-worker \
  --display-name "My Worker" \
  --order 35 \
  --health-check "http:http://localhost:9000/health" \
  -- python3 -m my_worker.server
```

## 数据库管理

```bash
python manage.py db info           # 查看数据库统计信息
python manage.py db reset          # 重置数据库
```

## 运行测试

```bash
python manage.py test contract     # API 合约测试
python manage.py test e2e          # E2E 测试
python manage.py test              # 全部测试
```

## 完整操作流程

详见 [workflow_price_factor.md](workflow_price_factor.md)，包含：

- **Track A**（预加载数据库）：`start --generate-test-db` → 打开浏览器 → Templates（模板选择）→ 配置参数 → 运行 → 实时进度 → 查看结果
- **Track B**（全新 CSV 完整流程）：`start --generate-test-data` → 创建 Session → 上传数据 → Templates → 配置参数 → 运行 → 查看结果

### 新架构特性

- **Template 模板驱动**：5 种预定义工作流模板（full_analysis / ic_only / returns_only / event_study_only / turnover_only）
- **Perfact 串行执行器**：替代 Celery，逐步执行原子操作，状态实时持久化到 SQLite
- **Service 插件发现**：`alphalens/definitions/*.py` 自动注册，无需修改 manage.py
