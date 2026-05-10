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

```bash
python manage.py stop              # 停止所有服务
python manage.py stop backend      # 停止特定服务
python manage.py restart           # 重启所有服务
python manage.py status            # 查看所有服务状态
python manage.py health            # 健康检查
python manage.py logs backend      # 查看日志
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

- **Track A**（预加载数据库）：`start --generate-test-db` → 打开浏览器 → 配置 → 运行 → 查看结果
- **Track B**（全新 CSV 完整流程）：`start --generate-test-data` → 创建 Session → 上传数据 → 配置 → 运行 → 查看结果
