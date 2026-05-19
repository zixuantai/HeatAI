"""
评估报告生成器 —— 论文级数据可视化

支持的图表类型：
1. 雷达图 (Radar Chart)         - 多维度指标总览
2. 分组柱状图 (Grouped Bar)     - 多方法/多阶段对比
3. 热力图 (Heatmap)             - 类别 x 指标的交叉分析
4. 消融瀑布图 (Ablation Waterfall) - 组件贡献度
5. 箱线图 (Box Plot)            - Per-sample 得分分布
6. Recall@K 曲线                - 检索性能随 K 变化
7. Score-K 关系曲线             - Precision/Recall/NDCG 随 K 变化
8. 分布直方图 (Histogram)       - 单指标得分分布
9. 类别性能矩阵 (Category Matrix)  - 按问题类型对比各指标

所有图表使用 matplotlib 学术风格，适合直接用于论文。
"""

import logging
import math
import os
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.patches import FancyBboxPatch

logger = logging.getLogger(__name__)

_CJK_FONTS = []
try:
    import matplotlib.font_manager as fm
    for f in fm.fontManager.ttflist:
        if f.name in ("Microsoft YaHei", "SimHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC"):
            _CJK_FONTS.append(f.name)
except Exception:
    pass

PLOT_STYLE = {
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.color": "#cccccc",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.family": "sans-serif",
    "font.sans-serif": (["Microsoft YaHei", "SimHei"] if _CJK_FONTS else []) + ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.unicode_minus": False,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
}

COLOR_PALETTE = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B", "#6A994E", "#118AB2", "#EF476F"]

METHOD_COLORS = {
    "BM25": "#2E86AB",
    "BGE-Vector": "#A23B72",
    "CoarseRank": "#F18F01",
    "FineRank(Full)": "#C73E1D",
    "Full Pipeline": "#2E86AB",
    "no_rewrite": "#F18F01",
    "no_bm25": "#A23B72",
    "no_fine_rank": "#C73E1D",
    "no_context_enrich": "#6A994E",
    "no_long_term_memory": "#118AB2",
}

FRIENDLY_NAMES = {
    "faithfulness": "Faithfulness\n(忠实度)",
    "answer_relevancy": "Answer Relevancy\n(回答相关性)",
    "context_precision": "Context Precision\n(上下文精准度)",
    "context_recall": "Context Recall\n(上下文召回率)",
    "context_relevancy": "Context Relevancy\n(上下文相关性)",
    "Precision@1": "P@1", "Precision@3": "P@3", "Precision@5": "P@5",
    "Precision@10": "P@10", "Precision@20": "P@20",
    "Recall@1": "R@1", "Recall@3": "R@3", "Recall@5": "R@5",
    "Recall@10": "R@10", "Recall@20": "R@20",
    "NDCG@1": "NDCG@1", "NDCG@3": "NDCG@3", "NDCG@5": "NDCG@5",
    "NDCG@10": "NDCG@10", "NDCG@20": "NDCG@20",
    "HitRate@1": "Hit@1", "HitRate@3": "Hit@3", "HitRate@5": "Hit@5",
    "HitRate@10": "Hit@10", "HitRate@20": "Hit@20",
    "MRR": "MRR",
    "no_rewrite": "w/o Query Rewrite",
    "no_bm25": "w/o BM25",
    "no_fine_rank": "w/o Fine Rank",
    "no_context_enrich": "w/o Context Enrich",
    "no_long_term_memory": "w/o Long Memory",
}


def _get_color(method: str, idx: int = 0) -> str:
    if method in METHOD_COLORS:
        return METHOD_COLORS[method]
    return COLOR_PALETTE[idx % len(COLOR_PALETTE)]


def _friendly(name: str) -> str:
    return FRIENDLY_NAMES.get(name, name)


class EvalReport:
    """评估报告生成器"""

    def __init__(self, output_dir: str = "./eval_output/figures"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        plt.style.use(PLOT_STYLE)

    # ================================================================
    # 图表 1: 雷达图 —— RAG 多维度指标总览
    # ================================================================
    def plot_radar_chart(
        self,
        scores: dict[str, float],
        title: str = "RAG System Evaluation Radar",
        filename: str = "radar_overview.pdf",
        show_std: dict[str, float] | None = None,
    ) -> str:
        """
        雷达图：展示 RAG 系统在多个维度的综合表现
        适合论文中的 overall performance overview
        """
        metrics = list(scores.keys())
        values = [scores[m] for m in metrics]
        n = len(metrics)

        angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        ax.fill(angles, values, alpha=0.25, color="#2E86AB", edgecolor="#2E86AB", linewidth=2)
        ax.plot(angles, values, "o-", color="#2E86AB", linewidth=2, markersize=6)

        if show_std:
            std_vals = [show_std.get(m, 0) for m in metrics] + [show_std.get(metrics[0], 0)]
            upper = [min(1.0, v + s) for v, s in zip(values, std_vals)]
            lower = [max(0.0, v - s) for v, s in zip(values, std_vals)]
            ax.fill_between(angles, lower, upper, alpha=0.1, color="#2E86AB")

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([_friendly(m) for m in metrics], fontsize=9)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=7)
        ax.set_title(title, fontsize=14, fontweight="bold", pad=25)
        ax.grid(True, alpha=0.3)

        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"雷达图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 2: 分组柱状图 —— 多方法/多阶段检索对比
    # ================================================================
    def plot_retrieval_comparison(
        self,
        results: list[dict[str, Any]],
        title: str = "Retrieval Performance Comparison",
        filename: str = "retrieval_comparison.pdf",
        figsize: tuple = (12, 5),
        metrics_subset: list[str] | None = None,
    ) -> str:
        """
        分组柱状图：对比 BM25 / BGE-Vector / CoarseRank / FineRank 的检索指标
        """
        if not results:
            return ""

        methods = [r["method"] for r in results]
        all_metrics = list(results[0]["mean_scores"].keys())

        if metrics_subset:
            display_metrics = [m for m in metrics_subset if m in all_metrics]
        else:
            priority = ["MRR", "Precision@5", "Recall@5", "Precision@10", "Recall@10", "NDCG@10"]
            display_metrics = [m for m in priority if m in all_metrics]
            if not display_metrics:
                display_metrics = all_metrics[:6]

        n_methods = len(methods)
        n_metrics = len(display_metrics)
        x = np.arange(n_metrics)
        width = 0.8 / n_methods

        fig, ax = plt.subplots(figsize=figsize)
        for i, method in enumerate(methods):
            means = results[i]["mean_scores"]
            vals = [means.get(m, 0) for m in display_metrics]
            offset = (i - n_methods / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width, label=_friendly(method),
                         color=_get_color(method, i), alpha=0.88, edgecolor="white", linewidth=0.5)

            for bar, val in zip(bars, vals):
                if val > 0.03:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                            f"{val:.3f}", ha="center", va="bottom", fontsize=7, color="#333333")

        ax.set_xlabel("Metrics", fontweight="bold")
        ax.set_ylabel("Score", fontweight="bold")
        ax.set_title(title, fontweight="bold", fontsize=13)
        ax.set_xticks(x)
        ax.set_xticklabels([_friendly(m) for m in display_metrics])
        ax.set_ylim(0, max(1.0, max(
            results[i]["mean_scores"].get(m, 0) for i in range(n_methods) for m in display_metrics
        ) * 1.18))
        ax.legend(loc="upper right", framealpha=0.9, edgecolor="#cccccc")
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"检索对比图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 3: Ragas 端到端指标柱状图
    # ================================================================
    def plot_ragas_overview(
        self,
        mean_scores: dict[str, float],
        title: str = "End-to-End RAG Evaluation (Ragas)",
        filename: str = "ragas_overview.pdf",
        figsize: tuple = (10, 5),
    ) -> str:
        """
        Ragas 指标总览柱状图
        """
        score_items = [(k, v) for k, v in mean_scores.items() if not k.endswith("_std")]
        metrics = [item[0] for item in score_items]
        values = [item[1] for item in score_items]

        colors = []
        for val, metric in zip(values, metrics):
            if val >= 0.85:
                colors.append("#6A994E")
            elif val >= 0.70:
                colors.append("#F18F01")
            else:
                colors.append("#C73E1D")

        fig, ax = plt.subplots(figsize=figsize)
        bars = ax.bar(range(len(metrics)), values, color=colors, alpha=0.88, edgecolor="white", linewidth=0.8, width=0.55)

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                    f"{val:.4f}", ha="center", va="bottom", fontsize=11, fontweight="bold", color="#333333")

        for std_key, std_val in mean_scores.items():
            if std_key.endswith("_std"):
                base_key = std_key.replace("_std", "")
                if base_key in metrics:
                    idx = metrics.index(base_key)
                    ax.errorbar(idx, values[idx], yerr=std_val, fmt="none", ecolor="#555555",
                               capsize=4, capthick=1.2, linewidth=1.2)

        ax.set_xticks(range(len(metrics)))
        ax.set_xticklabels([_friendly(m) for m in metrics], fontsize=10)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Score", fontweight="bold", fontsize=12)
        ax.set_title(title, fontweight="bold", fontsize=13)
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.axhline(y=0.85, color="#6A994E", linestyle="--", alpha=0.5, linewidth=1)
        ax.text(len(metrics) - 0.5, 0.86, "Excellent (0.85)", fontsize=8, color="#6A994E", alpha=0.8)
        ax.axhline(y=0.70, color="#F18F01", linestyle="--", alpha=0.5, linewidth=1)
        ax.text(len(metrics) - 0.5, 0.71, "Good (0.70)", fontsize=8, color="#F18F01", alpha=0.8)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"Ragas 总览图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 4: 热力图 —— 类别 x 指标的交叉分析
    # ================================================================
    def plot_category_heatmap(
        self,
        category_scores: dict[str, dict[str, float]],
        title: str = "RAG Performance by Question Category",
        filename: str = "category_heatmap.pdf",
        figsize: tuple = (12, 7),
    ) -> str:
        """
        热力图：展示不同问题类别在各指标上的表现
        """
        categories = sorted(category_scores.keys())
        all_metrics = set()
        for scores in category_scores.values():
            all_metrics.update(k for k in scores.keys() if not k.endswith("_std"))
        metrics = sorted(all_metrics)

        data = np.zeros((len(metrics), len(categories)))
        annotations: list[list[str]] = []
        for i, metric in enumerate(metrics):
            row_annotations: list[str] = []
            for j, cat in enumerate(categories):
                val = category_scores[cat].get(metric, 0)
                data[i, j] = val
                row_annotations.append(f"{val:.3f}")
            annotations.append(row_annotations)

        fig, ax = plt.subplots(figsize=figsize)
        im = ax.imshow(data, cmap="RdYlGn", aspect="auto", vmin=0.4, vmax=1.0)

        for i in range(len(metrics)):
            for j in range(len(categories)):
                val = data[i, j]
                text_color = "white" if val < 0.65 else "#333333"
                ax.text(j, i, f"{val:.3f}", ha="center", va="center", fontsize=10,
                       fontweight="bold", color=text_color)

        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, fontsize=9, rotation=30, ha="right")
        ax.set_yticks(range(len(metrics)))
        ax.set_yticklabels([_friendly(m).replace("\n", " ") for m in metrics], fontsize=10)
        ax.set_title(title, fontweight="bold", fontsize=13, pad=15)

        cbar = fig.colorbar(im, ax=ax, shrink=0.85, pad=0.02)
        cbar.set_label("Score", fontsize=10, fontweight="bold")
        cbar.ax.tick_params(labelsize=9)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"类别热力图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 5: 消融实验瀑布图
    # ================================================================
    def plot_ablation_waterfall(
        self,
        deltas: list[dict[str, Any]],
        title: str = "Ablation Study: Component Contribution Analysis",
        filename: str = "ablation_waterfall.pdf",
        figsize: tuple = (12, 7),
    ) -> str:
        """
        消融实验贡献度瀑布图：展示移除每个组件后各指标的下降幅度
        """
        if not deltas:
            return ""

        variants = [d["variant"] for d in deltas]
        delta_keys = [k for k in deltas[0].keys() if k.endswith("_delta_pct")]
        metric_keys = [k.replace("_delta_pct", "") for k in delta_keys]

        fig, ax = plt.subplots(figsize=figsize)
        x = np.arange(len(metric_keys))
        n_variants = len(variants)
        width = 0.8 / n_variants

        for i, (variant, d) in enumerate(zip(variants, deltas)):
            vals = [d.get(k, 0) for k in delta_keys]
            offset = (i - n_variants / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width, label=_friendly(variant),
                         color=_get_color(variant, i), alpha=0.85, edgecolor="white", linewidth=0.5)

            for bar, val in zip(bars, vals):
                y_pos = bar.get_height() if val >= 0 else 0
                va = "bottom" if val >= 0 else "top"
                ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                       f"{val:+.1f}%", ha="center", va=va, fontsize=7, color="#333333")

        ax.axhline(y=0, color="#333333", linewidth=1, alpha=0.6)
        ax.set_xlabel("Metrics", fontweight="bold")
        ax.set_ylabel("Performance Change (%)", fontweight="bold")
        ax.set_title(title, fontweight="bold", fontsize=13)
        ax.set_xticks(x)
        ax.set_xticklabels([_friendly(m) for m in metric_keys], fontsize=9)
        ax.legend(loc="lower left", framealpha=0.9, edgecolor="#cccccc", ncol=2)
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"消融瀑布图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 6: 箱线图 —— Per-sample 得分分布
    # ================================================================
    def plot_score_distribution(
        self,
        scores_list: list[list[float]],
        metric_names: list[str],
        title: str = "Score Distribution Across Samples",
        filename: str = "score_distribution.pdf",
        figsize: tuple = (11, 5),
    ) -> str:
        """
        箱线图：展示各指标的样本级得分分布
        """
        fig, ax = plt.subplots(figsize=figsize)

        bp = ax.boxplot(scores_list, patch_artist=True, widths=0.5,
                        medianprops=dict(color="#333333", linewidth=2),
                        whiskerprops=dict(color="#666666"),
                        capprops=dict(color="#666666"),
                        flierprops=dict(marker="o", markerfacecolor="#C73E1D", markersize=4, alpha=0.5))

        for i, (patch, name) in enumerate(zip(bp["boxes"], metric_names)):
            patch.set_facecolor(COLOR_PALETTE[i % len(COLOR_PALETTE)])
            patch.set_alpha(0.7)

        for i, scores in enumerate(scores_list):
            jitter = np.random.normal(0, 0.04, len(scores))
            ax.scatter(np.ones(len(scores)) * (i + 1) + jitter, scores, alpha=0.35,
                      s=20, color=COLOR_PALETTE[i % len(COLOR_PALETTE)], edgecolors="none")

        ax.set_xticks(range(1, len(metric_names) + 1))
        ax.set_xticklabels([_friendly(m) for m in metric_names], fontsize=9)
        ax.set_ylabel("Score", fontweight="bold", fontsize=12)
        ax.set_title(title, fontweight="bold", fontsize=13)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"箱线图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 7: Recall@K 曲线 —— 检索性能随 K 的变化
    # ================================================================
    def plot_recall_at_k_curve(
        self,
        results: list[dict[str, Any]],
        title: str = "Retrieval Performance vs. K",
        filename: str = "recall_at_k_curve.pdf",
        figsize: tuple = (10, 5),
    ) -> str:
        """
        折线图：展示不同方法的 Recall/Precision 随 K 值变化趋势
        """
        k_values = [1, 3, 5, 10, 20]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

        for i, r in enumerate(results):
            method = r["method"]
            means = r["mean_scores"]
            recall_vals = [means.get(f"Recall@{k}", 0) for k in k_values]
            prec_vals = [means.get(f"Precision@{k}", 0) for k in k_values]

            ax1.plot(k_values, recall_vals, "o-", label=_friendly(method),
                    color=_get_color(method, i), linewidth=2, markersize=7)
            ax2.plot(k_values, prec_vals, "s--", label=_friendly(method),
                    color=_get_color(method, i), linewidth=2, markersize=7)

        ax1.set_xlabel("K", fontweight="bold", fontsize=12)
        ax1.set_ylabel("Recall@K", fontweight="bold", fontsize=12)
        ax1.set_title("Recall@K", fontweight="bold", fontsize=12)
        ax1.set_xticks(k_values)
        ax1.set_ylim(0, 1)
        ax1.legend(fontsize=8, framealpha=0.9)
        ax1.grid(alpha=0.3)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)

        ax2.set_xlabel("K", fontweight="bold", fontsize=12)
        ax2.set_ylabel("Precision@K", fontweight="bold", fontsize=12)
        ax2.set_title("Precision@K", fontweight="bold", fontsize=12)
        ax2.set_xticks(k_values)
        ax2.set_ylim(0, 1)
        ax2.legend(fontsize=8, framealpha=0.9)
        ax2.grid(alpha=0.3)
        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        fig.suptitle(title, fontweight="bold", fontsize=14, y=1.02)
        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"Recall@K 曲线已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 8: 消融贡献度横向柱状图
    # ================================================================
    def plot_ablation_contribution(
        self,
        contribution: dict[str, float],
        title: str = "Component Contribution to Overall RAG Performance",
        filename: str = "ablation_contribution.pdf",
        figsize: tuple = (10, 5),
    ) -> str:
        """
        横向柱状图：各组件对 RAG 性能的平均贡献度（值越大越不可缺失）
        """
        sorted_items = sorted(contribution.items(), key=lambda x: x[1], reverse=True)
        names = [_friendly(n) for n, _ in sorted_items]
        values = [v for _, v in sorted_items]

        colors = []
        for v in values:
            if v > 15:
                colors.append("#C73E1D")
            elif v > 8:
                colors.append("#F18F01")
            else:
                colors.append("#2E86AB")

        fig, ax = plt.subplots(figsize=figsize)
        y_pos = range(len(names))
        bars = ax.barh(y_pos, values, color=colors, alpha=0.85, edgecolor="white", linewidth=0.8, height=0.55)

        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                   f"{val:.1f}%", va="center", fontsize=11, fontweight="bold", color="#333333")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(names, fontsize=10)
        ax.set_xlabel("Average Performance Drop (%)", fontweight="bold", fontsize=12)
        ax.set_title(title, fontweight="bold", fontsize=13)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"消融贡献图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 9: 阶段提升堆叠图
    # ================================================================
    def plot_stage_improvement(
        self,
        stage_scores: list[dict[str, float]],
        stage_names: list[str],
        title: str = "Cumulative Improvement Across Pipeline Stages",
        filename: str = "stage_improvement.pdf",
        figsize: tuple = (10, 5),
    ) -> str:
        """
        流水线各阶段累计提升图：展示从 BM25 到最终精排各阶段的增益
        """
        metric_keys = list(stage_scores[0].keys())
        if not metric_keys:
            return ""

        fig, ax = plt.subplots(figsize=figsize)
        x = np.arange(len(metric_keys))
        n_stages = len(stage_scores)
        width = 0.8 / n_stages

        for i, (name, scores) in enumerate(zip(stage_names, stage_scores)):
            vals = [scores.get(k, 0) for k in metric_keys]
            offset = (i - n_stages / 2 + 0.5) * width
            bars = ax.bar(x + offset, vals, width, label=name,
                         color=COLOR_PALETTE[i % len(COLOR_PALETTE)], alpha=0.85,
                         edgecolor="white", linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels([_friendly(k) for k in metric_keys], fontsize=9)
        ax.set_ylabel("Score", fontweight="bold", fontsize=12)
        ax.set_title(title, fontweight="bold", fontsize=13)
        ax.set_ylim(0, 1)
        ax.legend(loc="upper right", framealpha=0.9, edgecolor="#cccccc")
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        fig.tight_layout()
        file_path = str(self.output_dir / filename)
        fig.savefig(file_path)
        plt.close(fig)
        logger.info(f"阶段提升图已保存: {file_path}")
        return file_path

    # ================================================================
    # 图表 10: 综合 Dashboard（多图合并）
    # ================================================================
    def generate_full_report(
        self,
        ragas_result: Any,
        retrieval_comparison: Any = None,
        category_scores: dict[str, dict[str, float]] | None = None,
        ablation_comparison: Any = None,
        prefix: str = "dashboard",
    ) -> dict[str, str]:
        """
        一键生成完整评估报告的所有图表

        Returns:
            dict: {图表名称: 文件路径}
        """
        outputs: dict[str, str] = {}

        if ragas_result is not None:
            mean_scores = ragas_result.mean_scores
            outputs["ragas_overview"] = self.plot_ragas_overview(
                mean_scores,
                filename=f"{prefix}_ragas_overview.pdf",
            )

            if ragas_result.scores:
                metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
                scores_list = []
                valid_names = []
                for m in metric_names:
                    vals = [getattr(s, m, 0) for s in ragas_result.scores]
                    if vals:
                        scores_list.append(vals)
                        valid_names.append(m)
                if scores_list:
                    outputs["score_distribution"] = self.plot_score_distribution(
                        scores_list, valid_names,
                        filename=f"{prefix}_score_distribution.pdf",
                    )

                std_scores = {}
                for k, v in mean_scores.items():
                    if not k.endswith("_std"):
                        std_key = f"{k}_std"
                        if std_key in mean_scores:
                            std_scores[k] = mean_scores[std_key]

                outputs["radar"] = self.plot_radar_chart(
                    {k: v for k, v in mean_scores.items() if not k.endswith("_std")},
                    show_std=std_scores if std_scores else None,
                    filename=f"{prefix}_radar_overview.pdf",
                )

        if retrieval_comparison is not None:
            if hasattr(retrieval_comparison, "results"):
                results = retrieval_comparison.results
            else:
                results = retrieval_comparison
            outputs["retrieval_comparison"] = self.plot_retrieval_comparison(
                results,
                filename=f"{prefix}_retrieval_comparison.pdf",
            )
            outputs["recall_curve"] = self.plot_recall_at_k_curve(
                results,
                filename=f"{prefix}_recall_at_k_curve.pdf",
            )

        if category_scores:
            outputs["category_heatmap"] = self.plot_category_heatmap(
                category_scores,
                filename=f"{prefix}_category_heatmap.pdf",
            )

        if ablation_comparison is not None:
            deltas = ablation_comparison.compute_deltas()
            if deltas:
                outputs["ablation_waterfall"] = self.plot_ablation_waterfall(
                    deltas,
                    filename=f"{prefix}_ablation_waterfall.pdf",
                )
            contribution = ablation_comparison.compute_contribution()
            if contribution:
                outputs["ablation_contribution"] = self.plot_ablation_contribution(
                    contribution,
                    filename=f"{prefix}_ablation_contribution.pdf",
                )

        logger.info(f"完整报告已生成: {len(outputs)} 张图表")
        return outputs


    # ================================================================
    # 文本报告生成
    # ================================================================
    def generate_text_report(
        self,
        ragas_result: Any = None,
        retrieval_comparison: Any = None,
        category_scores: dict[str, dict[str, float]] | None = None,
        ablation_comparison: Any = None,
        filename: str = "eval_report.txt",
    ) -> str:
        """生成可读的文本评估报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("HeatAI RAG 系统评估报告")
        lines.append("=" * 70)
        lines.append("")

        if ragas_result is not None:
            lines.append("-" * 50)
            lines.append("一、端到端 RAG 评估 (Ragas)")
            lines.append("-" * 50)
            lines.append(f"  评估样本数: {ragas_result.num_samples}")
            lines.append(f"  评估耗时: {ragas_result.elapsed_seconds:.1f}s")
            lines.append("")
            lines.append("  指标得分:")
            for k, v in sorted(ragas_result.mean_scores.items()):
                if k.endswith("_std"):
                    continue
                std_key = f"{k}_std"
                std_val = ragas_result.mean_scores.get(std_key, 0)
                lines.append(f"    {_friendly(k).replace(chr(10), ' '):40s} {v:.4f} ± {std_val:.4f}")
            lines.append("")

        if retrieval_comparison is not None:
            lines.append("-" * 50)
            lines.append("二、检索层评估对比")
            lines.append("-" * 50)
            if hasattr(retrieval_comparison, "summary"):
                lines.append(retrieval_comparison.summary())
            lines.append("")

        if category_scores:
            lines.append("-" * 50)
            lines.append("三、按问题类别评估")
            lines.append("-" * 50)
            cats = sorted(category_scores.keys())
            sample_metrics = sorted([k for k in next(iter(category_scores.values())).keys() if not k.endswith("_std")])

            header = f"{'Category':<20}"
            for m in sample_metrics[:5]:
                header += f"{_friendly(m).replace(chr(10), ' '):>12}"
            lines.append(header)
            lines.append("-" * 80)
            for cat in cats:
                scores = category_scores[cat]
                row = f"{cat:<20}"
                for m in sample_metrics[:5]:
                    row += f"{scores.get(m, 0):>12.4f}"
                lines.append(row)
            lines.append("")

        if ablation_comparison is not None:
            lines.append("-" * 50)
            lines.append("四、消融实验分析")
            lines.append("-" * 50)
            deltas = ablation_comparison.compute_deltas()
            if deltas:
                lines.append("  各组件移除后指标变化（相对基线的百分比）:")
                for d in deltas:
                    variant = d["variant"]
                    desc = d.get("description", "")
                    lines.append(f"\n  [{_friendly(variant)}] {desc}")
                    delta_items = [(k, v) for k, v in d.items() if k.endswith("_delta_pct")]
                    for k, v in sorted(delta_items, key=lambda x: abs(x[1]), reverse=True):
                        metric_name = k.replace("_delta_pct", "")
                        lines.append(f"    {_friendly(metric_name).replace(chr(10), ' '):40s} {v:+.1f}%")
            lines.append("")

            contribution = ablation_comparison.compute_contribution()
            if contribution:
                lines.append("  各组件平均贡献度（值越大越重要）:")
                for name, val in sorted(contribution.items(), key=lambda x: x[1], reverse=True):
                    lines.append(f"    {_friendly(name):35s} {val:.1f}%")
            lines.append("")

        report = "\n".join(lines)
        file_path = str(self.output_dir / filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"文本报告已保存: {file_path}")
        return report
