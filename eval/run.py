"""
评估系统入口脚本

使用方式:
    # 仅运行检索评估
    python -m eval.run --mode retrieval --dataset eval_data/questions.json

    # 运行 Ragas 端到端评估
    python -m eval.run --mode ragas --dataset eval_data/questions.json

    # 运行完整评估（含消融实验）
    python -m eval.run --mode full --dataset eval_data/questions.json

    # 仅生成报告（使用已有的评估结果）
    python -m eval.run --mode report --result eval_output/eval_result.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.config import eval_settings
from eval.dataset.builder import DatasetBuilder, EvalDataset
from eval.report import EvalReport


def cmd_health():
    """健康检查：验证依赖和环境"""
    print("=" * 60)
    print("HeatAI 评估系统 - 环境检查")
    print("=" * 60)

    checks = []

    try:
        import numpy
        checks.append(("numpy", "OK", numpy.__version__))
    except ImportError:
        checks.append(("numpy", "NO", "not installed"))

    try:
        import pandas
        checks.append(("pandas", "OK", pandas.__version__))
    except ImportError:
        checks.append(("pandas", "NO", "not installed"))

    try:
        import matplotlib
        checks.append(("matplotlib", "OK", matplotlib.__version__))
    except ImportError:
        checks.append(("matplotlib", "NO", "not installed"))

    try:
        import ragas
        checks.append(("ragas", "OK", ragas.__version__))
    except ImportError:
        checks.append(("ragas", "NO", "not installed (no E2E eval)"))

    try:
        import dashscope
        checks.append(("dashscope", "OK", "installed"))
    except ImportError:
        checks.append(("dashscope", "NO", "not installed"))

    try:
        import langchain
        checks.append(("langchain", "OK", langchain.__version__))
    except ImportError:
        checks.append(("langchain", "NO", "not installed"))

    for name, status, version in checks:
        print(f"  [{status}] {name:<20} {version}")

    print(f"\n  DASHSCOPE_API_KEY: {'configured' if eval_settings.DASHSCOPE_API_KEY else 'NOT CONFIGURED (set in .env)'}")

    print("\n数据集目录:")
    data_dir = Path(__file__).parent / "eval_data"
    if data_dir.exists():
        for f in data_dir.glob("*"):
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print("  (eval_data/ 目录不存在)")

    print("\n输出目录:")
    output_dir = Path(eval_settings.EVAL_OUTPUT_DIR)
    print(f"  {output_dir.resolve()}")


def cmd_load_dataset(dataset_path: str):
    """加载并预览数据集"""
    path = Path(dataset_path)
    if not path.exists():
        print(f"Error: dataset file not found: {dataset_path}")
        return

    if path.suffix == ".json":
        ds = DatasetBuilder.from_json(str(path))
    elif path.suffix == ".csv":
        ds = DatasetBuilder.from_csv(str(path))
    else:
        print(f"Unsupported format: {path.suffix}")
        return

    print(f"\nDataset: {dataset_path}")
    print(f"  Samples: {len(ds)}")
    print(f"\nCategory distribution:")
    for cat, count in sorted(ds.category_distribution().items()):
        bar = "#" * min(count, 50)
        print(f"  {cat:<16} {count:>4}  {bar}")

    print(f"\nFirst 5 samples:")
    for i, record in enumerate(ds[:5]):
        q = record.get("question", "")
        cat = record.get("category", "")
        gt = record.get("ground_truth", "")
        print(f"  [{i+1}] [{cat}] {q[:70]}")
        if gt:
            print(f"      GT: {gt[:70]}")


def cmd_report(result_path: str, prefix: str = "dashboard"):
    """从评估结果 JSON 生成报告"""
    path = Path(result_path)
    if not path.exists():
        print(f"Error: result file not found: {result_path}")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    report = EvalReport()
    outputs = {}

    ragas_data = data.get("ragas_scores", {})
    if ragas_data:
        print("Generating Ragas overview chart...")
        mean_scores = ragas_data.get("mean_scores", {})
        clean_scores = {}
        std_scores = {}
        for k, v in mean_scores.items():
            if k.endswith("_std"):
                std_scores[k.replace("_std", "")] = v
            else:
                clean_scores[k] = v

        outputs["overview"] = report.plot_ragas_overview(clean_scores, filename=f"{prefix}_ragas_overview.pdf")
        outputs["radar"] = report.plot_radar_chart(clean_scores, show_std=std_scores, filename=f"{prefix}_radar_overview.pdf")

        per_sample = ragas_data.get("per_sample", [])
        if per_sample:
            metric_names = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
            scores_list = []
            valid_names = []
            for m in metric_names:
                vals = [s.get(m, 0) for s in per_sample if s.get(m, 0) and s.get(m, 0) > 0]
                if vals:
                    scores_list.append(vals)
                    valid_names.append(m)
            if scores_list:
                outputs["distribution"] = report.plot_score_distribution(scores_list, valid_names, filename=f"{prefix}_score_distribution.pdf")

    by_category = data.get("by_category", {})
    if by_category:
        print("Generating category heatmap...")
        cat_scores = {}
        for cat_name, cat_data in by_category.items():
            cat_scores[cat_name] = {k: v for k, v in cat_data.get("mean_scores", {}).items() if not k.endswith("_std")}
        if cat_scores:
            outputs["heatmap"] = report.plot_category_heatmap(cat_scores, filename=f"{prefix}_category_heatmap.pdf")

    ablation_data = data.get("ablation", {})
    if ablation_data:
        print("Generating ablation charts...")
        deltas = ablation_data.get("deltas", [])
        contribution = ablation_data.get("contribution", {})

        if deltas:
            outputs["ablation_waterfall"] = report.plot_ablation_waterfall(deltas, filename=f"{prefix}_ablation_waterfall.pdf")
        if contribution:
            outputs["ablation_contribution"] = report.plot_ablation_contribution(contribution, filename=f"{prefix}_ablation_contribution.pdf")

    print(f"\nReport generated successfully!")
    for name, filepath in outputs.items():
        print(f"  {name:<25} -> {filepath}")


def main():
    parser = argparse.ArgumentParser(description="HeatAI RAG 评估系统")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    subparsers.add_parser("health", help="环境健康检查")

    parser_load = subparsers.add_parser("load", help="加载并预览数据集")
    parser_load.add_argument("--dataset", "-d", required=True, help="数据集文件路径 (JSON/CSV)")

    parser_report = subparsers.add_parser("report", help="从评估结果生成图表报告")
    parser_report.add_argument("--result", "-r", required=True, help="评估结果 JSON 文件路径")
    parser_report.add_argument("--prefix", "-p", default="dashboard", help="输出文件名前缀")

    args = parser.parse_args()

    if args.command == "health":
        cmd_health()
    elif args.command == "load":
        cmd_load_dataset(args.dataset)
    elif args.command == "report":
        cmd_report(args.result, args.prefix)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
