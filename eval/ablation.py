"""
消融实验模块

通过系统性地移除/替换流水线中的各个组件，量化每个组件的贡献：
- no_rewrite:  去掉查询改写（直接用原始问题检索）
- no_bm25:     去掉 BM25（仅用 BGE 向量检索）
- no_fine_rank: 去掉 Cross-Encoder 精排（仅用粗排结果）
- no_context_enrich: 去掉相邻 chunk 上下文增强
- no_long_term_memory: 去掉长期记忆注入

每个实验对比检索指标（每阶段截取结果）和 Ragas 端到端指标
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from eval.config import eval_settings
from eval.metrics.retrieval import RetrievalEvaluator, RetrievalComparison
from eval.metrics.ragas_eval import RagasResult

logger = logging.getLogger(__name__)


@dataclass
class AblationResult:
    """单组消融实验结果"""
    variant_name: str
    description: str
    retrieval_scores: dict[str, Any] | None = None
    ragas_result: RagasResult | None = None


@dataclass
class AblationComparison:
    """消融实验对比结果汇总"""
    baseline: AblationResult | None = None
    variants: list[AblationResult] = field(default_factory=list)

    def compute_deltas(self) -> list[dict[str, Any]]:
        """计算每个变体相对基线的变化量"""
        if self.baseline is None or not self.baseline.ragas_result:
            return []
        baseline_means = self.baseline.ragas_result.mean_scores
        deltas = []
        for v in self.variants:
            if v.ragas_result is None:
                continue
            row = {"variant": v.variant_name, "description": v.description}
            for metric, baseline_val in baseline_means.items():
                if metric.endswith("_std"):
                    continue
                variant_val = v.ragas_result.mean_scores.get(metric, 0)
                delta = variant_val - baseline_val
                row[metric] = round(variant_val, 4)
                row[f"{metric}_delta"] = round(delta, 4)
                if baseline_val != 0:
                    row[f"{metric}_delta_pct"] = round(delta / baseline_val * 100, 1)
            deltas.append(row)
        return deltas

    def compute_contribution(self) -> dict[str, float]:
        """计算各组件对最终 RAG 性能的贡献度（值越大越重要）"""
        if self.baseline is None or not self.baseline.ragas_result:
            return {}
        baseline_means = self.baseline.ragas_result.mean_scores
        contributions: dict[str, dict[str, float]] = {}

        for v in self.variants:
            if v.ragas_result is None:
                continue
            for metric, baseline_val in baseline_means.items():
                if metric.endswith("_std") or baseline_val == 0:
                    continue
                variant_val = v.ragas_result.mean_scores.get(metric, 0)
                delta_pct = abs((variant_val - baseline_val) / baseline_val * 100)
                if v.variant_name not in contributions:
                    contributions[v.variant_name] = {}
                contributions[v.variant_name][metric] = delta_pct

        avg_contribution: dict[str, float] = {}
        for variant, metrics in contributions.items():
            avg_contribution[variant] = float(np.mean(list(metrics.values())))

        return avg_contribution


def run_retrieval_ablation(
    questions: list[str],
    ground_truth_ids: list[set[str]],
    get_bm25_results_fn,
    get_vector_results_fn,
    get_coarse_results_fn,
    get_fine_results_fn,
    k_values: list[int] | None = None,
) -> RetrievalComparison:
    """
    检索层消融实验：对比 BM25 / BGE向量 / 粗排 / 精排 各阶段的检索效果

    Args:
        questions: 查询列表
        ground_truth_ids: 每个查询对应的相关文档 ID 集合
        get_bm25_results_fn: 获取 BM25 结果的函数，返回 list[list[str]]
        get_vector_results_fn: 获取 BGE 向量检索结果的函数
        get_coarse_results_fn: 获取粗排结果的函数
        get_fine_results_fn: 获取精排最终结果的函数
        k_values: 评估的 K 值列表

    Returns:
        RetrievalComparison 多方法对比结果
    """
    evaluator = RetrievalEvaluator(k_values=k_values or [1, 3, 5, 10, 20])

    logger.info("=" * 60)
    logger.info("消融实验 - 检索层对比")
    logger.info("=" * 60)

    bm25_ids = get_bm25_results_fn(questions)
    bm25_result = evaluator.evaluate("BM25", bm25_ids, ground_truth_ids)

    vector_ids = get_vector_results_fn(questions)
    vector_result = evaluator.evaluate("BGE-Vector", vector_ids, ground_truth_ids)

    coarse_ids = get_coarse_results_fn(questions)
    coarse_result = evaluator.evaluate("CoarseRank", coarse_ids, ground_truth_ids)

    fine_ids = get_fine_results_fn(questions)
    fine_result = evaluator.evaluate("FineRank(Full)", fine_ids, ground_truth_ids)

    comparison = evaluator.compare([bm25_result, vector_result, coarse_result, fine_result])
    logger.info("\n" + comparison.summary())

    return comparison


def analyze_ragas_ablation(
    full_result: RagasResult,
    ablated_results: dict[str, RagasResult],
) -> AblationComparison:
    """
    分析 Ragas 端到端消融实验结果

    Args:
        full_result: 完整流水线的评估结果（基线）
        ablated_results: 各消融变体的评估结果，key=变体名

    Returns:
        AblationComparison
    """
    comparison = AblationComparison()
    comparison.baseline = AblationResult(
        variant_name="full",
        description="完整流水线（基线）",
        ragas_result=full_result,
    )

    variant_descriptions = {
        "no_rewrite": "去掉查询改写（直接用原始问题）",
        "no_bm25": "去掉 BM25（仅用 BGE 向量检索）",
        "no_fine_rank": "去掉 Cross-Encoder 精排",
        "no_context_enrich": "去掉相邻 chunk 上下文增强",
    }

    for variant_name, result in ablated_results.items():
        comparison.variants.append(AblationResult(
            variant_name=variant_name,
            description=variant_descriptions.get(variant_name, variant_name),
            ragas_result=result,
        ))

    return comparison
