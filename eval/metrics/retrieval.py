"""
传统检索评估指标
不依赖 LLM，纯计算指标：Precision@K, Recall@K, MRR, NDCG@K, MAP

用于评估检索各阶段（BM25、BGE向量、粗排融合、精排）的独立效果
"""

import logging
import math
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Precision@K: Top-K 结果中相关文档的比例"""
    if k <= 0 or not retrieved_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / k


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Recall@K: 相关文档中有多少被检索到了 Top-K 中"""
    if not relevant_ids:
        return 0.0
    if k <= 0 or not retrieved_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """MRR (Mean Reciprocal Rank): 第一个相关文档的排名倒数"""
    if not relevant_ids or not retrieved_ids:
        return 0.0
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(
    retrieved_ids: list[str],
    relevance_map: dict[str, float],
    k: int,
) -> float:
    """NDCG@K: 归一化折损累计增益，考虑相关度分值和排名位置"""
    if k <= 0 or not retrieved_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    dcg = 0.0
    for i, doc_id in enumerate(top_k):
        rel = relevance_map.get(doc_id, 0.0)
        if rel > 0:
            dcg += rel / math.log2(i + 2)

    ideal_rels = sorted(relevance_map.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_rels):
        if rel > 0:
            idcg += rel / math.log2(i + 2)

    if idcg == 0:
        return 0.0
    return dcg / idcg


def average_precision(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Average Precision: 各召回点的 precision 平均值"""
    if not relevant_ids or not retrieved_ids:
        return 0.0
    hits = 0
    sum_prec = 0.0
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids:
            hits += 1
            sum_prec += hits / (i + 1)
    return sum_prec / len(relevant_ids)


def map_at_k(retrieved_lists: list[list[str]], relevant_sets: list[set[str]], k: int) -> float:
    """MAP@K: 多个查询的 Average Precision@K 均值"""
    if not retrieved_lists:
        return 0.0
    aps = []
    for retrieved, relevant in zip(retrieved_lists, relevant_sets):
        top_k = retrieved[:k]
        ap = average_precision(top_k, relevant)
        aps.append(ap)
    return float(np.mean(aps)) if aps else 0.0


def hit_rate_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Hit Rate@K: Top-K 中是否至少有 1 个相关文档 (0 or 1)"""
    if not relevant_ids or not retrieved_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    return 1.0 if any(doc_id in relevant_ids for doc_id in top_k) else 0.0


class RetrievalEvaluator:
    """
    检索评估器，计算各阶段的 IR 指标

    使用方式:
        evaluator = RetrievalEvaluator()
        result = evaluator.evaluate(
            method_name="BM25",
            retrieved_ids_list=bm25_doc_ids,
            relevant_ids_list=ground_truth_ids,
        )
    """

    def __init__(self, k_values: list[int] | None = None, method: str = "binary"):
        self.k_values = k_values or [1, 3, 5, 10, 20]
        self.method = method

    def evaluate_single(
        self,
        retrieved_ids: list[str],
        relevant_ids: set[str],
        relevance_map: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """单条查询的评估"""
        scores: dict[str, float] = {"MRR": mrr(retrieved_ids, relevant_ids)}
        for k in self.k_values:
            scores[f"Precision@{k}"] = precision_at_k(retrieved_ids, relevant_ids, k)
            scores[f"Recall@{k}"] = recall_at_k(retrieved_ids, relevant_ids, k)
            scores[f"HitRate@{k}"] = hit_rate_at_k(retrieved_ids, relevant_ids, k)
        if relevance_map:
            for k in self.k_values:
                scores[f"NDCG@{k}"] = ndcg_at_k(retrieved_ids, relevance_map, k)
        return scores

    def evaluate(
        self,
        method_name: str,
        retrieved_ids_list: list[list[str]],
        relevant_ids_list: list[set[str]],
        relevance_maps: list[dict[str, float]] | None = None,
    ) -> dict[str, Any]:
        """
        批量评估

        Args:
            method_name: 评估方法名称 (e.g. "BM25", "BGE-Vector", "CoarseRank", "FineRank")
            retrieved_ids_list: 每个查询的检索结果文档 ID 列表 (按排名排列)
            relevant_ids_list: 每个查询的相关文档 ID 集合
            relevance_maps: 可选，每个查询的相关度分值映射

        Returns:
            包含各项指标均值和详细 Per-Query 数据的字典
        """
        all_scores: list[dict[str, float]] = []
        for i, (retrieved, relevant) in enumerate(zip(retrieved_ids_list, relevant_ids_list)):
            rel_map = relevance_maps[i] if relevance_maps else None
            scores = self.evaluate_single(retrieved, relevant, rel_map)
            scores["query_index"] = i
            all_scores.append(scores)

        metric_keys = [k for k in all_scores[0].keys() if k != "query_index"] if all_scores else []
        means = {}
        for key in metric_keys:
            vals = [s[key] for s in all_scores]
            means[key] = float(np.mean(vals))

        result = {
            "method": method_name,
            "num_queries": len(retrieved_ids_list),
            "mean_scores": means,
            "per_query": all_scores,
        }
        self._log_result(result)
        return result

    @staticmethod
    def _log_result(result: dict[str, Any]) -> None:
        method = result["method"]
        n = result["num_queries"]
        means = result["mean_scores"]
        logger.info(f"[{method}] n={n} | MRR={means.get('MRR', 0):.4f} | "
                     f"P@5={means.get('Precision@5', 0):.4f} | R@5={means.get('Recall@5', 0):.4f}")

    def compare(
        self,
        results: list[dict[str, Any]],
    ) -> "RetrievalComparison":
        """对比多个方法的评估结果"""
        return RetrievalComparison(results, self.k_values)


class RetrievalComparison:
    """多方法对比结果"""

    def __init__(self, results: list[dict[str, Any]], k_values: list[int]):
        self.results = results
        self.k_values = k_values
        self.methods = [r["method"] for r in results]

    def to_dataframe(self):
        import pandas as pd
        rows = []
        for r in self.results:
            row = {"方法": r["method"]}
            row.update(r["mean_scores"])
            rows.append(row)
        return pd.DataFrame(rows)

    def summary(self) -> str:
        lines = ["=" * 70, "检索评估对比", "=" * 70]
        metrics = ["MRR"]
        for k in self.k_values:
            metrics.append(f"Precision@{k}")
            metrics.append(f"Recall@{k}")
        header = f"{'Method':<20}" + "".join(f"{m:>12}" for m in metrics)
        lines.append(header)
        lines.append("-" * 70)
        for r in self.results:
            means = r["mean_scores"]
            vals = "".join(f"{means.get(m, 0):>12.4f}" for m in metrics)
            lines.append(f"{r['method']:<20}{vals}")
        return "\n".join(lines)
