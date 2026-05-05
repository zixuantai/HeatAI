# HeatAI RAG 评估模块

对 HeatAI 供热智能问答系统的检索增强生成（RAG）流水线进行多维度自动化评估。

---

## 目录结构

```
eval/
├── README.md                  # 本说明文档
├── __init__.py
├── config.py                  # 全局配置（模型、路径、超参）
├── bridge.py                  # 【桥梁函数】对接后端真实 RAG 流水线
├── runner.py                  # 评估执行器（编排完整流程）
├── ablation.py                # 消融实验模块
├── report.py                  # 论文级可视化报告生成器
├── run.py                     # 子命令入口（health / load / report）
├── run_eval.py                # 【一键运行脚本】（推荐入口）
├── requirements.txt           # 依赖清单
├── .env.example               # 环境变量模板
│
├── config/
│   └── [预留] 多套评估场景配置文件
│
├── dataset/
│   ├── __init__.py
│   └── builder.py             # 数据集构建器（JSON/CSV/Parquet → EvalDataset）
│
├── judge/
│   ├── __init__.py
│   └── dashscope_llm.py       # DashScope LLM 评判适配器（供 Ragas 调用）
│
├── metrics/
│   ├── __init__.py
│   ├── retrieval.py           # 传统 IR 指标（Precision@K, Recall@K, MRR, NDCG, MAP）
│   └── ragas_eval.py          # Ragas 端到端评估指标（Faithfulness 等）
│
├── eval_data/
│   ├── eval_questions.json    # 正式评测集（50 条，8 类别）
│   └── sample_questions.json  # 示例评测集（10 条）
│
└── eval_output/               # 评估输出目录（自动创建，已 gitignore）
    ├── eval_result.json       # 评估结果 JSON
    ├── figures/               # 图表输出
    │   ├── dashboard_ragas_overview.pdf
    │   ├── dashboard_radar_overview.pdf
    │   ├── dashboard_score_distribution.pdf
    │   ├── dashboard_category_heatmap.pdf
    │   ├── dashboard_ablation_waterfall.pdf
    │   └── dashboard_ablation_contribution.pdf
    └── eval_report.txt        # 文本评估报告
```

---

## 功能总览

### 一、评估指标体系

#### 1. 传统检索指标（无需 LLM，纯数学计算）

| 指标 | 说明 |
|------|------|
| **Precision@K** | Top-K 结果中相关文档的占比 |
| **Recall@K** | 全部相关文档中被检索到 Top-K 的比例 |
| **MRR** | Mean Reciprocal Rank，第一个相关文档的排名倒数 |
| **NDCG@K** | 归一化折损累计增益，考虑相关度分值和排名位置 |
| **MAP@K** | Mean Average Precision，多查询的平均精度均值 |
| **Hit Rate@K** | Top-K 中至少命中 1 个相关文档的比例 |

#### 2. Ragas 端到端评估指标（LLM-as-Judge）

| 指标 | 评判方式 | 说明 |
|------|---------|------|
| **Faithfulness**（忠实度） | LLM 判断 answer 中每句话是否都能从 contexts 找到依据 | 检测幻觉/编造 |
| **Answer Relevancy**（回答相关性） | LLM 从 answer 反向生成问题，计算语义相似度 | 回答是否紧扣问题 |
| **Context Precision**（上下文精准度） | LLM 判断 contexts 中是否含无用信息 | 检索噪声水平 |
| **Context Recall**（上下文召回率） | LLM 对比 answer 与 reference，判断是否遗漏关键信息 | 检索覆盖度 |
| **Answer Correctness**（准确性） | LLM 对比 answer 与 ground_truth | 需提供 reference |
| **Answer Similarity**（语义相似度） | Embedding 计算 answer 与 ground_truth 的余弦相似度 | 需提供 reference |

### 二、消融实验

通过**系统性移除 RAG 流水线中的单个组件**，量化每个组件对整体性能的贡献：

| 消融变体 | 操作 | 对应组件 |
|---------|------|---------|
| `no_rewrite` | 跳过 Query LLM 改写，直接用原始问题检索 | Query Rewriter |
| `no_bm25` | 去掉 BM25 关键词检索，仅用 BGE 向量检索 | BM25 双路召回 |
| `no_fine_rank` | 去掉 Cross-Encoder 精排，仅用粗排结果 | Cross-Encoder Reranker |
| `no_context_enrich` | 去掉相邻 chunk 上下文补全 | 上下文增强 |

### 三、可视化报告（10 种论文级图表）

| 图表 | 输出文件 | 用途 |
|------|---------|------|
| 雷达图 | `radar_overview.pdf` | 多维度综合表现总览 |
| Ragas 总览柱状图 | `ragas_overview.pdf` | 各指标均值 + 误差棒 |
| 箱线图 | `score_distribution.pdf` | 样本间得分离散程度 |
| 类别热力图 | `category_heatmap.pdf` | 问题类别 × 指标交叉分析 |
| 消融瀑布图 | `ablation_waterfall.pdf` | 移除组件后各指标下降幅度 |
| 消融贡献度图 | `ablation_contribution.pdf` | 各组件平均重要性排名 |
| Recall@K 曲线 | `recall_at_k_curve.pdf` | 检索性能随 K 值变化趋势 |
| 检索对比柱状图 | `retrieval_comparison.pdf` | 多阶段检索效果对比 |
| 流水线阶段提升图 | `stage_improvement.pdf` | 各阶段累计增益 |
| 得分分布直方图 | 按需生成 | 单指标得分分布 |

所有图表输出为 **300 DPI PDF 矢量图**，支持中文（Microsoft YaHei / SimHei 字体），可直接用于学术论文。

---

## 评测数据集

正式评测集 `eval_data/eval_questions.json` 包含 **50 条问题**，覆盖 8 个类别：

| 类别 | 数量 | 难度 | 说明 |
|------|------|------|------|
| 简单事实查询 | 5 | ★ | 标准答案唯一、可直接从文档获取 |
| 专业术语查询 | 10 | ★★ | 行业技术术语的定义和解析 |
| 跨文档综合问题 | 10 | ★★★ | 需要跨多份文档综合信息 |
| 口语化模糊问题 | 5 | ★★ | 模拟用户日常非专业表达 |
| 时间敏感问题 | 5 | ★★ | 关注信息的时效性和最新标准 |
| 需要工具调用 | 5 | ★★★ | 触发 Function Calling |
| 多轮追问 | 5 | ★★★ | 依赖对话历史上下文 |
| 矛盾信息处理 | 5 | ★★★★ | 需辨别多源信息中的冲突 |

其中约 35 条配有 `ground_truth` 标准答案，15 条为开放式或工具类问题无标准答案。

---

## 快速开始

### 前提条件

1. **HeatAI 后端已配置**：知识库已导入文档，Milvus 和 BM25 索引已构建
2. **DashScope API Key 已配置**：在 `backend/.env` 或 `eval/.env` 中设置 `DASHSCOPE_API_KEY`
3. **Python 环境已就绪**：安装了 `eval/requirements.txt` 中的依赖

### 步骤 1：环境检查

```bash
cd E:\project\LLM\HeatAI
python eval/run_eval.py --health
```

输出示例：
```
[OK] numpy                 2.4.2
[OK] pandas                2.3.3
[OK] matplotlib            3.10.9
[OK] ragas                 0.4.3
[OK] dashscope             installed
[OK] langchain             1.2.10
DASHSCOPE_API_KEY:         configured
Bridge function status:    Bridge imported OK
```

### 步骤 2：预览评测集

```bash
python eval/run_eval.py --load
```

查看各问题类别分布和样本内容。

### 步骤 3：运行完整评估

```bash
python eval/run_eval.py --full
```

流程：
1. 加载 BGE Embedding + Cross-Encoder 模型
2. 从 Milvus 重建 BM25 索引
3. 逐条调用 RAG 流水线，收集 answer + contexts（~3-10 秒/条）
4. 运行 Ragas 端到端评估，LLM 逐条打分（~3-5 秒/条）
5. 按 8 个类别分组评估
6. 运行 4 组消融实验
7. 生成全部图表和文本报告

输出位置：`eval_output/`

### 步骤 4：查看结果

```bash
# 查看文本报告
cat eval_output/figures/eval_report.txt

# 图表在
explorer eval_output/figures
```

---

## 命令行参考

### `python eval/run_eval.py`（推荐）

| 命令 | 说明 |
|------|------|
| `--health` | 环境健康检查（依赖、API Key、Bridge） |
| `--load` | 加载并预览评测数据集 |
| `--full` | **一键完整评估**（Ragas + 消融 + 报告） |
| `--ragas` | 仅 Ragas 端到端评估（跳过消融，节省时间和 API 费用） |
| `--ablation` | 仅消融实验 |
| `--report` | 从已有结果重新生成图表 |
| `--step ragas/ablation/report` | 分步运行 |

### `python -m eval.run`（子命令模式）

| 命令 | 说明 |
|------|------|
| `health` | 环境健康检查 |
| `load -d <文件>` | 加载并预览数据集 |
| `report -r <结果JSON> -p <前缀>` | 从结果 JSON 生成报告图表 |

---

## 配置说明

### 环境变量（`.env`）

评估模块会按以下优先级自动加载配置：
1. `backend/.env`
2. 项目根目录 `.env`
3. `eval/.env`

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DASHSCOPE_API_KEY` | - | **必填**，DashScope API 密钥 |
| `DASHSCOPE_EVAL_MODEL` | `qwen3-max` | 评判 LLM 模型 |
| `DASHSCOPE_EVAL_MODEL_LITE` | `qwen-plus` | 轻量评判模型（降低成本） |
| `EVAL_MAX_QUESTIONS` | `0`（全部） | 限制评估样本数，0=不限制 |
| `EVAL_OUTPUT_DIR` | `./eval_output` | 评估结果输出目录 |
| `EVAL_BATCH_SIZE` | `10` | Ragas 评估批处理大小 |
| `EVAL_JUDGE_TEMPERATURE` | `0.0` | 评判 LLM 温度（建议 0 确保一致性） |
| `EVAL_RETRIEVAL_TOP_K` | `10` | 传统检索指标评估的 K 值上限 |
| `EVAL_FINAL_TOP_K` | `8` | 最终返回给 LLM 的上下文条数 |
| `EVAL_EMBEDDING_MODEL` | `BAAI/bge-large-zh-v1.5` | 评估用 Embedding 模型 |
| `EVAL_EMBEDDING_DEVICE` | `cpu` | Embedding 计算设备 |
| `REPORT_INCLUDE_LATEX` | `false` | 是否生成 LaTeX 源码 |

### 消融实验变体配置

在 `config.py` 中通过 `EVAL_ABLATION_VARIANTS` 控制：
```python
EVAL_ABLATION_VARIANTS = [
    "full",                 # 完整流水线（基线）
    "no_rewrite",           # 去掉查询改写
    "no_bm25",              # 去掉 BM25 检索
    "no_fine_rank",         # 去掉精排
    "no_context_enrich",    # 去掉上下文增强
    "no_long_term_memory",  # 去掉长期记忆（需额外提供 pipeline）
]
```

---

## 架构说明

### 评估数据流

```
eval_questions.json (50条)
         │
         ▼
  EvalRunner.run_full_evaluation()
         │
         ├─ [1] 逐条调用 bridge.full_pipeline_fn(question)
         │      ├─ query_rewriter.rewrite() → 查询改写
         │      ├─ search_and_rerank()      → BM25+BGE双路检索→粗排→精排
         │      ├─ merge_expanded_results() → 扩展查询召回合并
         │      ├─ enrich_adjacent_chunks() → 相邻chunk上下文补全
         │      └─ chat_service.ask()       → LLM 生成回答
         │      返回: {answer, contexts, context_ids, context_scores}
         │
         ├─ [2] Ragas 评估（LLM-as-Judge）
         │      Faithfulness | Answer Relevancy | Context Precision | Context Recall
         │
         ├─ [3] 按类别分组评估（8 个类别各自独立评估）
         │
         ├─ [4] 消融实验（4 个变体 × 全量流水线）
         │
         └─ [5] 生成报告
                eval_result.json + 图表 PDF + eval_report.txt
```

### 核心模块职责

| 模块 | 职责 |
|------|------|
| `bridge.py` | 唯一与后端交互的模块，封装完整 RAG 流水线调用，提供消融变体函数 |
| `runner.py` | 评估执行器，编排数据加载 → 流水线调用 → 指标计算 → 结果保存 |
| `dataset/builder.py` | 数据集构建，支持 JSON/CSV/Parquet/DB 导入，提供分类/过滤/采样 |
| `metrics/retrieval.py` | 传统 IR 指标（Precision/Recall/MRR/NDCG/MAP），可评估各检索阶段 |
| `metrics/ragas_eval.py` | Ragas 端到端评估封装，自动适配版本差异 |
| `judge/dashscope_llm.py` | DashScope LLM 适配为 Ragas 评判模型 |
| `ablation.py` | 消融实验编排和贡献度计算 |
| `report.py` | 论文级可视化报告（10 种图表 + 文本报告） |
| `run_eval.py` | 一键运行入口，含完整评估流程控制 |

---

## 常见问题

### Q: 评估运行过程中断了怎么办？
评估结果会逐步保存。重新运行 `python eval/run_eval.py --report` 可以从已有的 `eval_result.json` 重新生成图表。

### Q: 如何只评估部分问题？
在 `.env` 中设置 `EVAL_MAX_QUESTIONS=10`，或手动编辑 `eval_questions.json`。

### Q: Ragas 评估耗时多久？
每条样本约 3-5 秒（取决于 LLM 响应速度）。50 条 × 4 个指标 ≈ 10-15 分钟。

### Q: 消融实验耗时多久？
每个变体相当于一次完整 Ragas 评估。4 个变体 × 50 条 ≈ 额外 40-60 分钟。建议在最终评估时运行，日常开发用 `--ragas` 即可。

### Q: 如何添加自己的评测问题？
编辑 `eval_data/eval_questions.json`，按以下格式追加：
```json
{
    "question": "你的问题",
    "category": "简单事实查询",
    "ground_truth": "标准答案（可选）"
}
```

### Q: 图表中文显示为方框怎么办？
检查系统是否安装中文字体（Microsoft YaHei 或 SimHei）。若无，安装后将字体文件放入系统字体目录，并清除 matplotlib 字体缓存：
```bash
python -c "import matplotlib; print(matplotlib.get_cachedir())"
# 删除该目录下的所有 .json 文件后重新运行
```
