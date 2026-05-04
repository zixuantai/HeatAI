"""
评估执行器主入口

编排完整的评估流程：
1. 加载数据集
2. 遍历问题，调用 RAG 流水线获取 context + answer
3. 计算传统检索指标
4. 计算 Ragas 端到端指标
5. 执行消融实验
6. 生成评估报告
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from eval.config import eval_settings
from eval.dataset.builder import EvalDataset, DatasetBuilder
from eval.metrics.retrieval import RetrievalEvaluator
from eval.metrics.ragas_eval import RagasEvaluator, RagasResult
from eval.ablation import analyze_ragas_ablation

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


@dataclass
class PipelineOutput:
    """RAG 流水线单次调用的输出"""
    question: str
    answer: str = ""
    contexts: list[str] = field(default_factory=list)
    context_ids: list[str] = field(default_factory=list)
    context_scores: list[float] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    """完整评估结果"""
    dataset_name: str = ""
    num_samples: int = 0
    ragas_result: RagasResult | None = None
    ragas_by_category: dict[str, RagasResult] = field(default_factory=dict)
    ablation_comparison: Any = None
    pipeline_outputs: list[PipelineOutput] = field(default_factory=list)
    total_elapsed: float = 0.0


class EvalRunner:
    """
    评估执行器

    使用方式:
        from eval.runner import EvalRunner

        runner = EvalRunner(
            dataset_path="eval_data/questions.json",
            pipeline_fn=my_rag_pipeline,
        )
        result = runner.run_full_evaluation()
    """

    def __init__(
        self,
        dataset_path: str | None = None,
        dataset: EvalDataset | None = None,
        pipeline_fn: Callable | None = None,
        output_dir: str | None = None,
    ):
        self.dataset_path = dataset_path
        self.dataset = dataset
        self.pipeline_fn = pipeline_fn
        self.output_dir = output_dir or eval_settings.EVAL_OUTPUT_DIR
        self.retrieval_evaluator = RetrievalEvaluator(k_values=[1, 3, 5, 10, 20])
        self.ragas_evaluator: RagasEvaluator | None = None

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def _load_dataset(self) -> EvalDataset:
        if self.dataset is not None:
            return self.dataset
        if self.dataset_path is None:
            raise ValueError("必须提供 dataset_path 或 dataset")

        path = Path(self.dataset_path)
        if path.suffix == ".json":
            ds = DatasetBuilder.from_json(str(path))
        elif path.suffix == ".csv":
            ds = DatasetBuilder.from_csv(str(path))
        elif path.suffix == ".parquet":
            ds = DatasetBuilder.load_synthetic_dataset(str(path))
        else:
            raise ValueError(f"不支持的文件格式: {path.suffix}")

        max_q = eval_settings.EVAL_MAX_QUESTIONS
        if max_q > 0 and len(ds) > max_q:
            logger.info(f"限制评估样本数: {len(ds)} -> {max_q}")
            ds = ds.sample(max_q)

        return ds

    def _run_rag_pipeline(self, question: str) -> PipelineOutput:
        """
        调用 RAG 流水线获取回答和上下文

        默认行为：调用外部传入的 pipeline_fn(question)，
        它应该返回 dict: {answer, contexts, context_ids}
        """
        t0 = time.time()

        if self.pipeline_fn is None:
            return PipelineOutput(
                question=question,
                answer="pipeline_fn 未配置",
                elapsed_seconds=time.time() - t0,
            )

        try:
            result = self.pipeline_fn(question)
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)

            contexts = result.get("contexts", [])
            context_ids = result.get("context_ids", [])
            if not contexts and result.get("search_results"):
                search_results = result["search_results"]
                contexts = [r.get("content", "") for r in search_results]
                context_ids = [r.get("document_id", "") for r in search_results]

            return PipelineOutput(
                question=question,
                answer=result.get("answer", ""),
                contexts=contexts,
                context_ids=context_ids,
                context_scores=result.get("context_scores", []),
                elapsed_seconds=time.time() - t0,
                metadata=result.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"RAG 流水线调用失败: {e}")
            return PipelineOutput(
                question=question,
                answer=f"[ERROR] {e}",
                elapsed_seconds=time.time() - t0,
            )

    def run_ragas_evaluation(self, dataset: EvalDataset) -> RagasResult:
        """运行 Ragas 端到端评估"""
        if self.ragas_evaluator is None:
            from eval.judge.dashscope_llm import create_judge_llm
            self.ragas_evaluator = RagasEvaluator(judge_llm=create_judge_llm())

        return self.ragas_evaluator.evaluate(dataset)

    def run_full_evaluation(
        self,
        run_ragas: bool = True,
        run_ablation: bool = False,
        ablation_pipelines: dict[str, Callable] | None = None,
    ) -> EvalResult:
        """
        完整评估流程

        Args:
            run_ragas: 是否运行 Ragas 端到端评估（需要 LLM 调用，成本较高）
            run_ablation: 是否运行消融实验
            ablation_pipelines: 消融实验中各变体的 pipeline 函数

        Returns:
            EvalResult
        """
        ds = self._load_dataset()
        logger.info(f"开始评估: {len(ds)} 条样本")

        total_start = time.time()
        result = EvalResult(
            dataset_name=self.dataset_path or "unknown",
            num_samples=len(ds),
        )

        logger.info("【步骤 1】运行 RAG 流水线，收集回答和上下文...")
        pipeline_outputs: list[PipelineOutput] = []
        for i, record in enumerate(ds):
            question = record.get("question", "")
            logger.info(f"  [{i+1}/{len(ds)}] {question[:60]}...")
            output = self._run_rag_pipeline(question)
            pipeline_outputs.append(output)

        result.pipeline_outputs = pipeline_outputs

        for record, output in zip(ds.records, pipeline_outputs):
            record["answer"] = output.answer
            record["contexts"] = output.contexts

        if run_ragas:
            logger.info("【步骤 2】运行 Ragas 端到端评估...")
            result.ragas_result = self.run_ragas_evaluation(ds)

            logger.info("【步骤 3】按类别分组评估...")
            categories = set(ds.categories)
            for cat in sorted(categories):
                subset = ds.filter_by_category(cat)
                if len(subset) < 2:
                    continue
                logger.info(f"  类别 [{cat}]: {len(subset)} 条")
                result.ragas_by_category[cat] = self.run_ragas_evaluation(subset)

        if run_ablation and ablation_pipelines:
            logger.info("【步骤 4】运行消融实验...")
            ablation_results: dict[str, RagasResult] = {}
            for variant_name, pipeline_fn in ablation_pipelines.items():
                logger.info(f"  变体 [{variant_name}]...")
                orig_fn = self.pipeline_fn
                self.pipeline_fn = pipeline_fn

                variant_ds = DatasetBuilder.from_json(self.dataset_path or "")
                for i, record in enumerate(variant_ds):
                    output = self._run_rag_pipeline(record["question"])
                    record["answer"] = output.answer
                    record["contexts"] = output.contexts

                ablation_results[variant_name] = self.run_ragas_evaluation(variant_ds)
                self.pipeline_fn = orig_fn

            if result.ragas_result:
                result.ablation_comparison = analyze_ragas_ablation(
                    result.ragas_result, ablation_results
                )

        result.total_elapsed = time.time() - total_start
        logger.info(f"评估完成: 总耗时 {result.total_elapsed:.1f}s")

        return result

    def save_result(self, result: EvalResult, filename: str = "eval_result.json") -> str:
        """保存评估结果到 JSON 文件"""
        file_path = str(Path(self.output_dir) / filename)

        data: dict[str, Any] = {
            "dataset_name": result.dataset_name,
            "num_samples": result.num_samples,
            "total_elapsed": round(result.total_elapsed, 1),
            "pipeline_stats": {
                "avg_latency": round(
                    sum(p.elapsed_seconds for p in result.pipeline_outputs) / max(len(result.pipeline_outputs), 1),
                    3,
                ),
            },
        }

        if result.ragas_result:
            data["ragas_scores"] = result.ragas_result.to_dict()

        data["by_category"] = {}
        for cat, r in result.ragas_by_category.items():
            data["by_category"][cat] = r.to_dict()

        if result.ablation_comparison:
            data["ablation"] = {
                "deltas": result.ablation_comparison.compute_deltas(),
                "contribution": result.ablation_comparison.compute_contribution(),
            }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"评估结果已保存: {file_path}")
        return file_path
