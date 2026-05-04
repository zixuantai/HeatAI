"""
Ragas 端到端 RAG 评估指标封装

将 DashScope 评判 LLM 接入 Ragas，实现：
- Faithfulness (忠实度)
- Answer Relevancy (回答相关性)
- Context Precision (上下文精准度)
- Context Recall (上下文召回率)
- Context Relevancy (上下文相关性)

可选（需要 ground_truth）:
- Answer Correctness (准确性)
- Answer Similarity (语义相似度)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from datasets import Dataset as HFDataset

from eval.config import eval_settings
from eval.dataset.builder import EvalDataset
from eval.judge.dashscope_llm import DashScopeLLM

logger = logging.getLogger(__name__)


@dataclass
class RagasScore:
    """单条 Ragas 评估得分"""
    question: str = ""
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    context_relevancy: float = 0.0
    answer_correctness: float | None = None
    answer_similarity: float | None = None
    category: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class RagasResult:
    """Ragas 评估结果汇总"""
    scores: list[RagasScore] = field(default_factory=list)
    mean_scores: dict[str, float] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    num_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "mean_scores": self.mean_scores,
            "num_samples": self.num_samples,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "per_sample": [
                {
                    "question": s.question[:60],
                    "faithfulness": round(s.faithfulness, 4),
                    "answer_relevancy": round(s.answer_relevancy, 4),
                    "context_precision": round(s.context_precision, 4),
                    "context_recall": round(s.context_recall, 4),
                    "context_relevancy": round(s.context_relevancy, 4),
                    "category": s.category,
                }
                for s in self.scores
            ],
        }


class RagasEvaluator:
    """
    Ragas 端到端评估器

    使用方式:
        from eval.judge.dashscope_llm import create_judge_llm
        from eval.dataset.builder import DatasetBuilder

        ds = DatasetBuilder.from_json("eval_data/questions.json")
        judge = create_judge_llm("qwen3-max")
        evaluator = RagasEvaluator(judge_llm=judge)
        result = evaluator.evaluate(eval_dataset=ds)
    """

    def __init__(
        self,
        judge_llm: DashScopeLLM | None = None,
        embedding_model: str | None = None,
        embedding_device: str | None = None,
    ):
        self.judge_llm = judge_llm
        self._embedding_model = None
        self._embedding_model_name = embedding_model or eval_settings.EVAL_EMBEDDING_MODEL
        self._embedding_device = embedding_device or eval_settings.EVAL_EMBEDDING_DEVICE

    def _get_judge(self) -> DashScopeLLM:
        if self.judge_llm is None:
            from eval.judge.dashscope_llm import create_judge_llm
            self.judge_llm = create_judge_llm()
        return self.judge_llm

    def _get_embedding(self):
        if self._embedding_model is None:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self._embedding_model = HuggingFaceEmbeddings(
                model_name=self._embedding_model_name,
                model_kwargs={"device": self._embedding_device},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embedding_model

    @staticmethod
    def _to_hf_dataset(eval_dataset: EvalDataset) -> HFDataset:
        """将 EvalDataset 转为 HuggingFace Dataset"""
        data = eval_dataset.to_ragas_dict()
        return HFDataset.from_dict(data)

    @staticmethod
    def _calc_mean_std(values: list[float]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0
        arr = np.array(values)
        return float(np.mean(arr)), float(np.std(arr))

    def evaluate(
        self,
        eval_dataset: EvalDataset,
        metrics: list[str] | None = None,
        batch_size: int | None = None,
    ) -> RagasResult:
        """
        执行 Ragas 端到端评估

        Args:
            eval_dataset: 包含 question, answer, contexts 的评估数据集
            metrics: 要计算的指标列表，默认全部
            batch_size: 批处理大小

        Returns:
            RagasResult 评估结果
        """
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            context_relevancy,
            answer_correctness,
            answer_similarity,
        )

        if metrics is None:
            metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "context_relevancy"]

        if batch_size is None:
            batch_size = eval_settings.EVAL_BATCH_SIZE

        if len(eval_dataset) == 0:
            logger.warning("评估数据集为空")
            return RagasResult(num_samples=0)

        hf_ds = self._to_hf_dataset(eval_dataset)
        judge = self._get_judge()

        metric_map = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
            "context_recall": context_recall,
            "context_relevancy": context_relevancy,
            "answer_correctness": answer_correctness,
            "answer_similarity": answer_similarity,
        }
        selected_metrics = [metric_map[m] for m in metrics if m in metric_map]

        if not selected_metrics:
            logger.warning("未选择任何有效指标")
            return RagasResult(num_samples=len(eval_dataset))

        logger.info(f"开始 Ragas 评估: {len(eval_dataset)} 条, 指标={metrics}, batch_size={batch_size}")

        t0 = time.time()

        eval_kwargs = {
            "dataset": hf_ds,
            "metrics": selected_metrics,
            "llm": judge,
        }

        if "answer_similarity" in metrics or "answer_correctness" in metrics:
            eval_kwargs["embeddings"] = self._get_embedding()

        try:
            result_df = ragas_evaluate(**eval_kwargs)
            result_df = result_df.to_pandas()
        except Exception as e:
            logger.error(f"Ragas 评估失败: {e}")
            raise

        elapsed = time.time() - t0

        scores = []
        for i in range(len(eval_dataset)):
            row = result_df.iloc[i]
            score = RagasScore(
                question=eval_dataset[i].get("question", ""),
                faithfulness=float(row.get("faithfulness", 0) or 0),
                answer_relevancy=float(row.get("answer_relevancy", 0) or 0),
                context_precision=float(row.get("context_precision", 0) or 0),
                context_recall=float(row.get("context_recall", 0) or 0),
                context_relevancy=float(row.get("context_relevancy", 0) or 0),
                answer_correctness=float(row.get("answer_correctness", 0)) if "answer_correctness" in row else None,
                answer_similarity=float(row.get("answer_similarity", 0)) if "answer_similarity" in row else None,
                category=eval_dataset[i].get("category", ""),
            )
            scores.append(score)

        mean = {}
        metric_cols = [m for m in metrics if m in result_df.columns]
        for col in metric_cols:
            vals = [float(v) for v in result_df[col] if v is not None and not np.isnan(v)]
            if vals:
                mean_val, std_val = self._calc_mean_std(vals)
                mean[col] = round(mean_val, 4)
                mean[f"{col}_std"] = round(std_val, 4)

        result = RagasResult(
            scores=scores,
            mean_scores=mean,
            elapsed_seconds=elapsed,
            num_samples=len(eval_dataset),
        )

        logger.info(f"Ragas 评估完成: 耗时 {elapsed:.1f}s, 得分: {mean}")
        return result

    def evaluate_by_category(
        self,
        eval_dataset: EvalDataset,
        metrics: list[str] | None = None,
    ) -> dict[str, RagasResult]:
        """按类别分组评估"""
        results: dict[str, RagasResult] = {}
        categories = set(eval_dataset.categories)
        for cat in categories:
            subset = eval_dataset.filter_by_category(cat)
            if len(subset) == 0:
                continue
            logger.info(f"评估类别: {cat} ({len(subset)} 条)")
            results[cat] = self.evaluate(subset, metrics=metrics)
        return results
