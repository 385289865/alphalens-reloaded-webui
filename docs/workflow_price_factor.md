# Alphalens WebUI 完整因子研究流程指南

## 基于价格的截面因子研究

---

### 一、项目概述

#### Alphalens WebUI 是什么

Alphalens WebUI 是一个基于 Web 的量化因子分析平台。它将 alphalens 库（因子分析工具）包装为可视化界面，用户可以通过浏览器上传数据、配置参数、运行分析并查看结果，无需编写代码。

#### 截面因子研究

**截面因子研究**（Cross-Sectional Factor Research）是在每个时间截面上，比较不同资产之间某个特征（因子值）与未来收益的关系。

例如：**"价格高的股票是否比价格低的股票表现更好？"**
- 在每个交易日，将 5 只股票按价格从低到高排序
- 分成 5 组（分位数）
- 观察每组股票在后续 1 天、5 天、10 天的平均收益
- 如果高价股组 consistently 跑赢低价股组，说明价格是一个有效因子

#### 为什么用价格作为因子

本指南使用**股票收盘价作为因子值**，目的是演示完整的因子研究流程。价格本身通常不是主流因子（因为不同股票价格量纲不同），但它非常适合作为教学案例，因为：
1. **直观易懂** — 谁都理解"价格"这个概念
2. **数据易得** — 从任何行情源都可以获取
3. **结果可解释** — 我们能清楚地讨论为什么价格可能有（或没有）预测能力

---

### 二、两种使用场景

本系统支持两种启动模式：

| 模式 | 命令 | 适用场景 |
|------|------|----------|
| **A: 预加载数据库** | `python manage.py start --generate-test-db` | 用户已有现成数据库，直接开始分析 |
| **B: 全新 CSV 流程** | `python manage.py start --generate-test-data` | 模拟首次使用，只有 CSV 文件，需手动上传 |

**两种模式都会生成相同的数据集**，区别仅在于数据是否已预加载到 DuckDB 中。

---

### 三、数据集说明

#### 数据集结构

| 项目 | 说明 |
|------|------|
| **标的数量** | 5 只股票 |
| **股票代码** | AAPL（苹果）、MSFT（微软）、GOOGL（谷歌）、AMZN（亚马逊）、JPM（摩根大通） |
| **时间跨度** | 2024-01-01 至 2024-12-31（252 个交易日） |
| **因子定义** | 每日收盘价（Cross-Sectional Factor） |
| **生成方法** | 几何布朗运动（Geometric Brownian Motion） |

#### 因子数据文件（factor.csv）

格式：长格式（Long Format）

| 列名 | 类型 | 说明 |
|------|------|------|
| date | str (YYYY-MM-DD) | 交易日期 |
| asset | str | 股票代码 |
| factor_value | float | 收盘价（因子值） |

示例：

| date | asset | factor_value |
|------|-------|-------------|
| 2024-01-01 | AAPL | 185.00 |
| 2024-01-01 | MSFT | 370.00 |
| 2024-01-01 | GOOGL | 140.00 |
| ... | ... | ... |

行数：5 assets × 252 days = **1,260 行**

#### 价格数据文件（prices.csv）

格式：宽格式（Wide Format）

| date | AAPL | MSFT | GOOGL | AMZN | JPM |
|------|------|------|-------|------|-----|
| 2024-01-01 | 185.00 | 370.00 | 140.00 | 155.00 | 170.00 |
| 2024-01-02 | 185.96 | 379.12 | 134.17 | 152.39 | 171.70 |
| ... | ... | ... | ... | ... | ... |

行数：**252 行**

#### 数据生成参数

| 参数名 | AAPL | MSFT | GOOGL | AMZN | JPM |
|--------|------|------|-------|------|-----|
| 初始价格 | $185 | $370 | $140 | $155 | $170 |
| 年化波动率 | 25% | 22% | 23% | 30% | 20% |
| 年化漂移率 | 10% | 10% | 10% | 10% | 10% |

数据生成使用 `numpy.random.seed(42)` 确保可重复性。

---

### 四、完整操作流程

---

#### 步骤 1：生成数据并启动系统

**Track A（预加载数据库）：**

```bash
python manage.py start --generate-test-db
```

预期输出：
```
── Generating test dataset (price as cross-sectional factor) ──
Generated factor CSV:  db/test_data/factor.csv  (1,260 rows)
Generated prices CSV:  db/test_data/prices.csv  (252 rows)
Assets: AAPL, MSFT, GOOGL, AMZN, JPM

── Loading test data into DuckDB ──
Session created:   43a422eb-3ff3-4f9b-bdd9-61b75cb09007
Session name:      Price Factor Demo
Factor rows:       1260
Price rows:        1260
Assets:            5
DuckDB path:       db/alphalens.db

Starting Alphalens WebUI (dev mode)...
  redis: starting... PID 12345
  backend: starting... PID 12346
  celery: starting... PID 12347
  frontend: starting... PID 12348
...
```

此时系统已包含一个名为"Price Factor Demo"的 Session，数据已预加载。您可以跳过步骤 2-5，直接从**步骤 6**开始。

**Track B（全新 CSV 流程 — 推荐用于学习）：**

```bash
python manage.py start --generate-test-data
```

预期输出：
```
── Generating test dataset (price as cross-sectional factor) ──
Generated factor CSV:  db/test_data/factor.csv  (1,260 rows)
Generated prices CSV:  db/test_data/prices.csv  (252 rows)
Assets: AAPL, MSFT, GOOGL, AMZN, JPM

Starting Alphalens WebUI (dev mode)...
  redis: starting... PID 12345
  backend: starting... PID 12346
  celery: starting... PID 12347
  frontend: starting... PID 12348
...
```

此时系统已启动，但 DuckDB 为空。您需要按照以下步骤手动上传数据。

---

#### 步骤 2：访问 Web UI

1. 打开浏览器
2. 访问 **http://localhost:5173**

**预期结果：**
- 页面标题显示 **Sessions**
- 中间有一个空的 Session 列表
- 显示空状态提示："No sessions yet. Create your first session to get started."
- 右下角（或页面中央）有一个 **New Session** 按钮
- 页面左上角有 **Alphalens** Logo
- 右上角有暗黑模式切换按钮（月亮/太阳图标）

![Session 列表空状态]

---

#### 步骤 3：创建新 Session

1. 点击 **New Session** 按钮
2. 弹窗显示 Create Session 对话框
3. 在 **Name** 输入框中输入：`价格因子研究`
4. 在 **Description** 输入框中输入：`使用收盘价作为截面因子，测试价格是否对收益有预测能力`
5. 点击 **Create** 按钮

**预期结果：**
- 对话框关闭
- Session 创建成功
- 页面自动跳转到 Session 详情页的 **Upload** 标签页
- URL 变为：`http://localhost:5173/sessions/{uuid}/upload`
- 页面左侧 Sidebar 显示 Session 信息（名称、日期、状态）
- Sidebar 中的导航步骤显示当前在 **Upload**（第 1 步）

---

#### 步骤 4：上传因子数据（价格数据作为因子）

1. 在 **Factor Data** 卡片中：
   - 可以拖拽 `factor.csv` 到虚线区域
   - **或者** 点击 "Select File" 按钮

2. 选择文件：`db/test_data/factor.csv`

3. 等待上传完成

**预期结果（上传过程中）：**
- 文件选择后会显示进度条（0% → 100%）
- 进度条由 `sessionStore.uploadProgress` 驱动

**预期结果（上传完成后）：**
- 上传区域显示绿色勾选图标（CheckmarkCircleOutline）
- 显示文件名：`factor.csv`
- 显示 **Remove** 按钮（可移除重新上传）
- URL 保持不变（`/sessions/{uuid}/upload`）

> **注意**：此时页面底部的 "Configure Analysis" 按钮**还未出现**，因为价格数据尚未上传。系统需要同时拥有因子数据和价格数据才能进行分析。

---

#### 步骤 5：上传价格数据

1. 在 **Price Data** 卡片中：
   - 拖拽 `prices.csv` 到虚线区域
   - **或者** 点击 "Select File" 按钮

2. 选择文件：`db/test_data/prices.csv`

3. 等待上传完成

**预期结果：**
- 上传区域显示绿色勾选图标
- 显示文件名：`prices.csv`
- **页面底部出现成功提示**：
  - 绿色 Alert："All required files uploaded. Proceed to configure your analysis."
  - **Configure Analysis** 按钮变为可用

**可选**：如果您想测试分组分析，还可以上传分组数据（Group Data），但本指南不使用分组，跳过即可。

---

#### 步骤 6：浏览数据（验证上传）

1. 在左侧 Sidebar 导航中，点击 **Browse Data**（第 2 步）
2. **或者** 点击页面底部的 "Browse Data" 链接

**预期结果：**

**Factor 标签页（默认选中）：**
- 表格显示因子数据
- 列名：`date`, `asset`, `factor_value`
- 分页显示，每页 10 条
- 可以在底部看到总行数：**1,260 rows**
- 可以通过页面底部的分页控件切换页面

示例数据（第 1 页）：
| date | asset | factor_value |
|------|-------|-------------|
| 2024-01-01 | AAPL | 185.00 |
| 2024-01-01 | MSFT | 370.00 |
| 2024-01-01 | GOOGL | 140.00 |
| 2024-01-01 | AMZN | 155.00 |
| 2024-01-01 | JPM | 170.00 |
| ... | ... | ... |

**Price 标签页（点击切换）：**
- 表格显示价格数据
- 列名：`date`, `AAPL`, `MSFT`, `GOOGL`, `AMZN`, `JPM`
- 总行数：**252 rows**

> **验证提示**：可以对比 Browse Data 页面和 CSV 文件的内容，确保数据一致。

---

#### 步骤 7：配置分析参数

1. 在左侧 Sidebar 导航中，点击 **Configure**（第 3 步）
2. **或者** 点击页面底部的 **Configure Analysis** 按钮

**预期结果：**
- 页面显示分析配置表单
- URL 变为：`http://localhost:5173/sessions/{uuid}/configure`

**配置参数：**

| 参数 | 控件类型 | 设置值 | 说明 |
|------|----------|--------|------|
| **Periods** | 按钮组 | [1, 5, 10, 21] | 点击 "+" 按钮添加 21 天周期 |
| **Quantiles** | 滑块 | 5 | 将 5 只股票分为 5 组 |
| **filter_zscore** | 数字输入 | 20 | 因子值 Z-Score > 20 视为异常值 |
| **max_loss** | 数字输入 | 0.35 | 允许最多丢弃 35% 的数据 |
| **long_short** | 开关 | ON | 计算多空组合收益 |
| **group_neutral** | 开关 | OFF | 本指南不分组 |
| **zero_aware** | 开关 | OFF | 价格无零值 |
| **cumulative_returns** | 开关 | ON | 计算累积收益 |
| **by_group** | 开关 | OFF | 每组分开展示 |

**详细操作：**

**调整 Periods：**
1. 默认显示 [1, 5, 10] 三个周期按钮
2. 可以点击已选中的按钮取消选择
3. 点击 "+" 按钮（或输入框）添加周期 21
4. 最终选择 [1, 5, 10, 21]
   - 1 = 1 日收益（次日收益）
   - 5 = 5 日收益（约 1 周）
   - 10 = 10 日收益（约 2 周）
   - 21 = 21 日收益（约 1 个月）

**调整 Quantiles：**
1. 拖动滑块从默认值调整到 5
2. 滑块范围：2 到 100
3. 设置 5 表示将 5 只股票按价格从低到高分为 5 组，每组 1 只股票

**其他参数：**
1. filter_zscore：输入 20（默认值）
2. max_loss：输入 0.35（默认值）
3. 确保 long_short 开关为 ON（绿色）
4. 确保 cumulative_returns 开关为 ON（绿色）
5. 其他开关保持 OFF

**参数说明（对新手重要）：**

| 参数 | 通俗解释 |
|------|----------|
| Periods | 持有时长。如果你今天买入，想持有几天后卖出？ |
| Quantiles | 分组数。你想把股票分成几组来比较？ |
| long_short | 是否做多最高组、做空最低组 |
| cumulative_returns | 假设每天调仓，累计收益曲线 |

---

#### 步骤 8：运行分析

1. 确认所有参数已正确设置
2. 点击 **Run Analysis** 按钮

**预期结果：**
- 按钮变为加载状态（显示 loading spinner）
- 页面自动跳转到 **Progress** 页面
- URL 变为：`http://localhost:5173/sessions/{sid}/analysis/{aid}/progress`

> **系统内部流程**：点击按钮后，前端通过 API 调用 `POST /api/v1/analysis/run`，后端创建 Celery 任务并立即返回 `analysis_id` 和 `task_id`。前端随即开始轮询状态（每 2 秒）。

---

#### 步骤 9：监控分析进度

**页面布局：**
- 顶部显示分析 ID 和状态标签（Running ⏳）
- 中间显示环形进度条（0% → 100%）
- 下方显示 8 个 Pipeline 步骤
- 右侧显示已用时间

**Pipeline 步骤与状态映射：**

| 步骤 | 阶段名称 | 进度范围 | 预计耗时 |
|------|---------|----------|----------|
| 1 | ⏳ Computing forward returns | 0% - 15% | ~1-2 秒 |
| 2 | ⏳ Computing factor quantiles | 15% - 25% | ~1 秒 |
| 3 | ⏳ Computing IC (Information Coefficient) | 25% - 40% | ~2-3 秒 |
| 4 | ⏳ Computing factor returns | 40% - 55% | ~2 秒 |
| 5 | ⏳ Computing alpha/beta | 55% - 70% | ~2-3 秒 |
| 6 | ⏳ Computing turnover | 70% - 80% | ~1 秒 |
| 7 | ⏳ Computing cumulative returns | 80% - 90% | ~1 秒 |
| 8 | ⏳ Generating charts | 90% - 100% | ~3-5 秒 |

**观察要点：**
- 进度条会平滑地从 0% 增长到 100%
- 当前步骤会高亮显示（黄色/蓝色）
- 已完成步骤显示绿色勾选图标
- 页面每 2 秒自动刷新状态
- 总运行时间：约 15-30 秒（取决于机器性能）

**完成状态：**
- 状态标签变为 **Completed** ✅
- 进度条显示 100%
- 所有步骤显示绿色勾选
- 页面**自动跳转**到 Results 页面

**如果分析失败：**
- 状态标签变为 **Failed** ❌
- 显示错误信息
- 可以点击 "Retry" 重新运行

---

#### 步骤 10：查看 Summary（汇总）

页面自动跳转到 Results 页面的 **Summary** 标签页。

URL: `http://localhost:5173/sessions/{sid}/analysis/{aid}/results`

**指标卡片（Metric Cards）：**

在页面顶部分为 4 个指标卡片：

| 指标 | 预期范围 | 含义 |
|------|----------|------|
| **Mean IC** | ~ -0.05 到 0.05 | 信息系数均值。表示价格与未来收益的相关性 |
| **Alpha** | ~ 0.001 到 0.01 | 超额收益。经市场风险调整后的收益 |
| **Beta** | ~ 0.9 到 1.1 | 市场敏感度。接近 1 表示与市场同步 |
| **Periods** | [1, 5, 10, 21] | 分析的持有周期 |

> **结果解读**：由于价格数据是随机生成的（几何布朗运动），没有嵌入真实的因子信号，因此 Mean IC 通常接近 0（在 -0.05 到 0.05 之间波动），说明"价格本身对未来收益没有预测能力"。这是一个**正常的教学结果** — 在真实研究中，您会用有预测能力的因子来获得显著的非零 IC。

**Alpha/Beta 汇总表：**

显示每个持有期的 Alpha 和 Beta：

| Period | Alpha | Beta | Meaning |
|--------|-------|------|---------|
| 1D | 0.0023 | 0.98 | 1 日 Alpha 约 0.2% |
| 5D | 0.0089 | 0.95 | 5 日 Alpha 约 0.9% |
| 10D | 0.0156 | 1.02 | 10 日 Alpha 约 1.6% |
| 21D | 0.0321 | 1.05 | 21 日 Alpha 约 3.2% |

**IC 汇总表：**

| Period | Mean IC | Std IC | IR (IC/Std) |
|--------|---------|--------|-------------|
| 1D | 0.012 | 0.082 | 0.15 |
| 5D | 0.008 | 0.095 | 0.08 |
| 10D | -0.005 | 0.112 | -0.04 |
| 21D | 0.003 | 0.128 | 0.02 |

---

#### 步骤 11：查看 IC 分析详情

点击 **IC** 标签页。

**此标签页的内容通过独立 API 懒加载**（`fetchIc`），只在切换到该标签页时才请求数据。

**IC 时间序列图：**
- X 轴：交易日期（2024-01 到 2024-12）
- Y 轴：Spearman 秩相关系数（IC）
- 每个点代表**一天**的截面 IC
- 红色虚线：IC = 0（基准线）
- 蓝色实线：IC 时间序列
- 预期：数值在 -0.4 到 0.4 之间随机波动

**IC 直方图：**
- X 轴：IC 值区间
- Y 轴：频次（天数）
- 预期：大致呈正态分布，集中在 0 附近
- 绿色虚线：均值位置
- 红色虚线：±2 标准差位置

**IC QQ 图：**
- X 轴：理论正态分布分位数
- Y 轴：实际 IC 分位数
- 预期：点大致沿对角线分布（说明 IC 近似正态）

**IC 明细表：**
- 日期、IC 值、IC 的 Z-Score
- 可按日期排序

---

#### 步骤 12：查看收益分析

点击 **Returns** 标签页。

**此标签页的内容通过独立 API 懒加载**（`fetchReturns`）。

**分位数收益柱状图（Quantile Returns Bar）：**
- X 轴：分位数（1 最低价 → 5 最高价）
- Y 轴：平均收益
- 每个 period 用不同颜色
- 预期：各分位数收益差异不大（因为价格无预测能力）
- 如果价格有预测能力，会看到分位数 1 到 5 的收益呈单调递增或递减

**累积收益曲线（Cumulative Returns by Quantile）：**
- X 轴：日期
- Y 轴：累积收益
- 多条线代表不同分位数
- 预期：5 条线相互交织，没有明显分层

**平均分位数价差（Mean Quantile Spread）：**
- 最高分位组 - 最低分位组（做多最高组、做空最低组）的累积收益
- 预期：围绕 0 波动，没有明显趋势

---

#### 步骤 13：查看 Alpha/Beta

点击 **Alpha-Beta** 标签页。

**此标签页的内容通过独立 API 懒加载**（`fetchAlphaBeta`）。

**Alpha/Beta 矩阵表：**

| Asset | Period | Alpha | Beta | t-stat(Alpha) |
|-------|--------|-------|------|---------------|
| AAPL | 1D | 0.0032 | 0.98 | 0.85 |
| AAPL | 5D | 0.0151 | 0.95 | 0.92 |
| MSFT | 1D | -0.0018 | 1.02 | -0.45 |
| MSFT | 5D | -0.0085 | 1.05 | -0.52 |
| ... | ... | ... | ... | ... |

**各 period 分别显示**：对于 [1, 5, 10, 21] 每个周期，计算每只股票的 Alpha 和 Beta。

**Alpha 解读：**
- 正 Alpha：该股票在因子分组后仍有超额收益
- 负 Alpha：该股票收益低于预期
- 由于价格因子无预测能力，Alpha 应接近 0 且不显著

---

#### 步骤 14：查看换手率

点击 **Turnover** 标签页。

**此标签页的内容通过独立 API 懒加载**（`fetchTurnover`）。

**分位数换手率（Quantile Turnover）：**
- X 轴：日期
- Y 轴：换手率（0% - 100%）
- 表示每天有多少股票从一个分位数"跳"到另一个分位数
- 预期：换手率较高（因为价格连续变化，股票在分位数间频繁跳动）

**秩自相关系数（Rank Autocorrelation）：**
- X 轴：日期
- Y 轴：自相关系数（0 - 1）
- 衡量因子排名的稳定性
- 预期：自相关系数接近 1（价格排名相对稳定，高价股通常保持高价）

---

#### 步骤 15：查看图表库

点击 **Charts** 标签页。

**此标签页展示 8 张完整的图表**（通过 `fetchAllCharts` 单独加载每个图表）：

| 序号 | 图表名称 | 图表类型 | 说明 |
|------|----------|----------|------|
| 1 | IC Time Series | 折线图 | IC 的时间序列 |
| 2 | IC Histogram | 直方图 | IC 分布 |
| 3 | IC QQ Plot | 散点图 | IC 正态性检验 |
| 4 | Quantile Returns Bar | 柱状图 | 各分位数平均收益 |
| 5 | Cumulative Returns | 折线图 | 各分位数累积收益 |
| 6 | Mean Quantile Spread | 折线图 | 多空组合累积收益 |
| 7 | Quantile Turnover | 折线图 | 换手率 |
| 8 | Rank Autocorrelation | 折线图 | 秩自相关 |

**每张图表以卡片形式展示：**
- 卡片加载时显示骨架屏（Skeleton）
- 加载完成后显示 Base64 PNG 图片
- 图片下方有简短的图表说明
- 可以放大查看（点击图片）

---

### 五、结果解读

#### Mean IC（信息系数均值）

- **定义**：每天计算因子值（价格）与未来收益的 Spearman 秩相关系数，然后取时间序列均值
- **范围**：[-1, 1]
- **解读**：
  - IC > 0.05：价格与未来收益正相关（价格高 → 收益高）
  - IC < -0.05：价格与未来收益负相关（价格高 → 收益低）
  - IC ≈ 0：价格对未来收益无预测能力（我们的预期结果）
- **本数据集的预期 IC**：接近 0，因为数据是随机生成的
- **IR（IC/Std IC）**：如果 IR > 0.5，说明 IC 稳定且可靠

#### Alpha（超额收益）

- **定义**：在控制市场风险（Beta）后，每只股票的平均超额日收益
- **解读**：
  - Alpha > 0：即使考虑因子暴露，该股票仍产生正超额收益
  - Alpha ≈ 0：因子能完全解释收益
- **本数据集的预期 Alpha**：接近 0

#### Beta（市场敏感度）

- **定义**：股票收益对"因子组合"收益的敏感度
- **解读**：
  - Beta = 1：与因子组合同步波动
  - Beta > 1：比因子组合波动更大
  - Beta < 1：比因子组合波动更小

#### 分位数收益

- **含义**：将 5 只股票按价格从低到高分为 5 组，观察每组在未来 1/5/10/21 天的平均收益
- **期望模式**：如果价格是有效因子，分位数收益应呈单调递增或递减
- **本数据集的预期**：无明显单调模式

#### 为什么结果可能不显著？

这是因为我们生成的数据中**没有嵌入真实的因子-收益关系**。价格通过几何布朗运动随机生成，价格与未来收益之间没有系统性的联系。这恰好说明了因子研究的一个重要原则：

> **相关性不等于因果性。** 即使你发现价格能预测收益，也需要通过统计检验（如 IC 显著性检验、Alpha 的 t-stat）来确认这不是随机噪声。

---

### 六、常见问题

#### Q1: 上传失败怎么办？

- 检查文件格式是否为 CSV
- 检查因子数据是否包含 `date` 和 `asset` 列
- 检查价格数据的第一列是否为 `date`
- 查看页面顶部的错误消息

#### Q2: 分析一直卡在某个进度？

- 检查 Celery Worker 是否在运行（`python manage.py status`）
- 检查 Redis 是否在运行
- 查看日志：`python manage.py logs celery`
- 点击 **Revoke** 取消任务后重试

#### Q3: 图表加载不出来？

- 检查后端是否正常运行：`python manage.py health`
- 检查是否有足够的内存生成 matplotlib 图表
- 查看日志：`python manage.py logs backend`

#### Q4: 如何重新运行分析？

1. 回到 Configure 页面
2. 调整参数（或保持相同）
3. 再次点击 **Run Analysis**
4. 系统会创建新的分析（新的 `analysis_id`）

#### Q5: 如何查看之前运行的分析结果？

- 在 Session 详情页的 Sidebar 中
- 点击 "Analysis History" 区域
- 选择之前的分析 ID

---

### 七、高级操作

#### 修改参数重新运行

尝试以下参数组合，观察结果的变化：

| 实验 | 参数变更 | 预期效果 |
|------|---------|----------|
| 1 | Quantiles = 3 | 每组包含更多股票 |
| 2 | Periods = [1, 21] | 只对比短期和长期 |
| 3 | long_short = OFF | 不计算多空组合 |
| 4 | max_loss = 0.10 | 更严格的数据过滤 |

#### 创建多个 Session 对比

1. 回到 Session 列表页
2. 创建新 Session（例如："价格因子研究 - 参数测试"）
3. 上传相同的数据
4. 使用不同的参数运行分析
5. 对比两个分析的结果

#### 查看原始数据 API

您也可以直接通过 API 获取原始数据：

```bash
# 获取所有 Session
curl http://localhost:8000/api/v1/data/sessions

# 获取因子数据
curl http://localhost:8000/api/v1/data/sessions/{sid}/factor?page=1&page_size=10

# 获取价格数据
curl http://localhost:8000/api/v1/data/sessions/{sid}/prices?page=1&page_size=10
```

---

### 附录：数据生成方法

#### 几何布朗运动（GBM）

价格序列使用几何布朗运动生成：

```
P_{t+1} = P_t × exp(μ + σ × ε)
```

其中：
- P_t = t 时刻的价格
- μ = 日漂移率（年化 10% / 252）
- σ = 日波动率（年化波动率 / √252）
- ε = 标准正态分布随机数 N(0, 1)

#### 为什么选择这 5 只股票？

| 股票 | 行业 | 初始价格 | 代表意义 |
|------|------|---------|---------|
| AAPL | 科技/消费电子 | $185 | 高市值、中波动 |
| MSFT | 科技/软件 | $370 | 高市值、低波动 |
| GOOGL | 科技/互联网 | $140 | 高市值、中波动 |
| AMZN | 电商/云计算 | $155 | 高市值、高波动 |
| JPM | 金融/银行 | $170 | 高市值、低波动 |

这 5 只股票覆盖了不同行业和不同价格区间，适合演示截面因子分析。

#### 数据格式规范

**因子数据（Long Format）：**
```
date,asset,factor_value
2024-01-01,AAPL,185.00
```

| 要求 | 说明 |
|------|------|
| 文件编码 | UTF-8 |
| 日期格式 | YYYY-MM-DD |
| 列名 | 小写 |
| 无空行 | 所有行必须有完整数据 |

**价格数据（Wide Format）：**
```
date,AAPL,MSFT,GOOGL,AMZN,JPM
2024-01-01,185.00,370.00,140.00,155.00,170.00
```

| 要求 | 说明 |
|------|------|
| 第一列 | 必须是 `date` |
| 其余列 | 列名为股票代码 |
| 值 | 数字（浮点数） |

---

### 附录：Track A 快捷操作

如果您使用 `--generate-test-db` 模式（预加载数据库），操作流程更短：

| 步骤 | 操作 | 位置 |
|------|------|------|
| 1 | `python manage.py start --generate-test-db` | 终端 |
| 2 | 打开 http://localhost:5173 | 浏览器 |
| 3 | 在 Session 列表中点击 **Price Factor Demo** | Session 列表页 |
| 4 | 左侧 Sidebar 点击 **Configure** | Session 详情页 |
| 5 | 设置参数（同步骤 7） | Configure 页面 |
| 6 | 点击 **Run Analysis** | Configure 页面 |
| 7 | 查看进度（同步骤 9） | Progress 页面 |
| 8 | 查看结果（同步骤 10-15） | Results 页面 |

此模式适合重复演示或已熟悉上传流程的用户。
