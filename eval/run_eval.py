"""
HeatAI RAG 评估一键运行脚本

使用方式:
    # 环境检查
    python eval/run_eval.py --health

    # 仅预览数据集
    python eval/run_eval.py --load

    # 运行完整评估（检索 + Ragas + 消融 + 报告）
    python eval/run_eval.py --full

    # 仅运行 Ragas 端到端评估（跳过消融实验，省时间）
    python eval/run_eval.py --ragas

    # 仅从已有结果生成报告
    python eval/run_eval.py --report

    # 分步骤运行
    python eval/run_eval.py --step ragas     # 仅 Ragas 评估
    python eval/run_eval.py --step ablation   # 仅消融实验
    python eval/run_eval.py --step report     # 仅生成报告

典型工作流:
    1. python eval/run_eval.py --health      检查环境是否就绪
    2. python eval/run_eval.py --load         预览问题集
    3. python eval/run_eval.py --full         一键完整评估
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_backend_dir = _project_root / "backend"
sys.path.insert(0, str(_project_root))
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

_env_loaded = False
for _env_path in [
    _project_root / "backend" / ".env",
    _project_root / ".env",
    Path(__file__).parent / ".env",
]:
    if _env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_env_path, override=False)
            _env_loaded = True
        except ImportError:
            pass

# Ensure backend's models directory env vars are set early
os.environ.setdefault("HF_HUB_CACHE", str(_project_root / "models"))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(_project_root / "models"))
os.environ.setdefault("TRANSFORMERS_CACHE", str(_project_root / "models" / "transformers"))

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

DATA_DIR = Path(__file__).parent / "eval_data"
DEFAULT_DATASET = str(DATA_DIR / "eval_questions.json")

for lib in ("sentence_transformers", "transformers", "tokenizers",
            "jieba", "rank_bm25", "pymilvus", "milvus_lite",
            "httpx", "httpcore", "urllib3", "openai",
            "datasets", "huggingface_hub", "filelock", "multiprocessing"):
    logging.getLogger(lib).setLevel(logging.WARNING)


def cmd_health():
    from eval.config import eval_settings
    from eval.run import cmd_health as _health
    _health()
    print()

    api_key = eval_settings.DASHSCOPE_API_KEY or ""
    if not api_key:
        print("WARNING: DASHSCOPE_API_KEY not configured. E2E evaluation will fail.")
        print("  Copy backend/.env to eval/.env or set eval/.env with DASHSCOPE_API_KEY.")
    else:
        print("DASHSCOPE_API_KEY: configured (ready for E2E evaluation)")

    print()
    print("Bridge function status:")
    try:
        from eval.bridge import full_pipeline_fn
        print("  Bridge imported OK")
    except Exception as e:
        print(f"  Bridge import FAILED: {e}")
        print("  Make sure backend dependencies are installed and models are downloaded.")


def cmd_load():
    from eval.run import cmd_load_dataset
    cmd_load_dataset(DEFAULT_DATASET)


def cmd_report():
    result_path = Path("eval_output") / "eval_result.json"
    if not result_path.exists():
        print(f"ERROR: Result file not found: {result_path}")
        print("  Run evaluation first: python eval/run_eval.py --full")
        return
    print(f"Generating report from: {result_path}")
    print()
    from eval.run import cmd_report
    cmd_report(str(result_path))
    print()
    print("Report complete. Check eval_output/figures/ for PDF charts.")


def _preload_models():
    import threading
    def _load():
        from backend.app.services.embedding import embedding_service
        embedding_service.ensure_loaded()
        from backend.app.services.cross_reranker_service import cross_reranker_service
        cross_reranker_service.ensure_loaded()
    t = threading.Thread(target=_load, daemon=True)
    t.start()
    t.join(timeout=120)


def _build_bm25():
    from backend.app.services.milvus_service import milvus_service
    from backend.app.services.bm25_service import bm25_service
    if bm25_service.chunk_count > 0:
        logger.info(f"BM25 index ready: {bm25_service.chunk_count} chunks")
        return
    logger.info("Building BM25 index from Milvus...")
    milvus_service._ensure_initialized()
    chunks = milvus_service.get_all_chunks()
    logger.info(f"Milvus has {len(chunks)} chunks")
    bm25_service.rebuild_from_milvus_chunks(chunks)
    logger.info(f"BM25 index built: {bm25_service.chunk_count} chunks")


def cmd_full():
    _preload_models()
    _build_bm25()

    from eval.config import eval_settings
    from eval.dataset.builder import DatasetBuilder
    from eval.runner import EvalRunner
    from eval.report import EvalReport
    from eval.bridge import full_pipeline_fn, ABLATION_PIPELINES

    api_key = eval_settings.DASHSCOPE_API_KEY
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY not configured.")
        print("  Create eval/.env with: DASHSCOPE_API_KEY=sk-...")
        return

    dataset = DatasetBuilder.from_json(DEFAULT_DATASET)
    print(f"\n{'='*60}")
    print(f"Dataset: {DEFAULT_DATASET}")
    print(f"Samples: {len(dataset)}")
    print(f"Categories: {dict(dataset.category_distribution())}")
    print(f"{'='*60}\n")

    runner = EvalRunner(
        dataset=dataset,
        pipeline_fn=full_pipeline_fn,
    )

    result = runner.run_full_evaluation(
        run_ragas=True,
        run_ablation=True,
        ablation_pipelines=ABLATION_PIPELINES,
    )

    result_path = runner.save_result(result)
    print(f"\nEvaluation result saved: {result_path}")

    report = EvalReport()
    outputs = report.generate_full_report(
        ragas_result=result.ragas_result,
        category_scores={cat: res.mean_scores for cat, res in result.ragas_by_category.items()},
        ablation_comparison=result.ablation_comparison,
        prefix="dashboard",
    )

    print(f"\nCharts generated: {len(outputs)} files")
    for name, path in outputs.items():
        print(f"  {name}: {path}")

    report_text = report.generate_text_report(
        ragas_result=result.ragas_result,
        category_scores={cat: res.mean_scores for cat, res in result.ragas_by_category.items()},
        ablation_comparison=result.ablation_comparison,
    )
    print(f"\nText report: {report.output_dir / 'eval_report.txt'}")

    print(f"\n{'='*60}")
    print("All done! Check eval_output/ for results and figures.")
    print(f"{'='*60}")


def cmd_ragas():
    """仅运行 Ragas 端到端评估（无消融实验）"""
    _preload_models()
    _build_bm25()

    from eval.config import eval_settings
    from eval.dataset.builder import DatasetBuilder
    from eval.runner import EvalRunner
    from eval.report import EvalReport
    from eval.bridge import full_pipeline_fn

    api_key = eval_settings.DASHSCOPE_API_KEY
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY not configured.")
        return

    dataset = DatasetBuilder.from_json(DEFAULT_DATASET)
    print(f"Dataset: {len(dataset)} samples, categories: {dict(dataset.category_distribution())}")

    runner = EvalRunner(dataset=dataset, pipeline_fn=full_pipeline_fn)
    result = runner.run_full_evaluation(run_ragas=True, run_ablation=False)
    result_path = runner.save_result(result)
    print(f"Result saved: {result_path}")

    report = EvalReport()
    outputs = report.generate_full_report(
        ragas_result=result.ragas_result,
        category_scores={cat: res.mean_scores for cat, res in result.ragas_by_category.items()},
        prefix="ragas_only",
    )
    print(f"Charts: {len(outputs)} files under eval_output/figures/")


def cmd_ablation():
    """仅运行消融实验（需先有 Ragas 基线结果，或提供完整流水线）"""
    _preload_models()
    _build_bm25()

    from eval.config import eval_settings
    from eval.dataset.builder import DatasetBuilder
    from eval.runner import EvalRunner
    from eval.bridge import full_pipeline_fn, ABLATION_PIPELINES

    api_key = eval_settings.DASHSCOPE_API_KEY
    if not api_key:
        print("ERROR: DASHSCOPE_API_KEY not configured.")
        return

    dataset = DatasetBuilder.from_json(DEFAULT_DATASET)
    print(f"Running ablation study with {len(dataset)} samples...")
    print(f"Variants: {list(ABLATION_PIPELINES.keys())}")

    runner = EvalRunner(dataset=dataset, pipeline_fn=full_pipeline_fn)
    result = runner.run_full_evaluation(
        run_ragas=True,
        run_ablation=True,
        ablation_pipelines=ABLATION_PIPELINES,
    )
    result_path = runner.save_result(result, filename="ablation_result.json")
    print(f"Ablation result saved: {result_path}")

    from eval.report import EvalReport
    report = EvalReport()
    deltas = result.ablation_comparison.compute_deltas()
    contribution = result.ablation_comparison.compute_contribution()

    print("\nAblation Summary:")
    if deltas:
        for d in deltas:
            print(f"  [{d['variant']}] {d.get('description', '')}:")
            for k, v in d.items():
                if k.endswith("_delta_pct"):
                    print(f"    {k.replace('_delta_pct', ''):>20s}: {v:+.1f}%")
    if contribution:
        print("\nComponent Contribution (higher = more critical):")
        for name, val in sorted(contribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  {name:>25s}: {val:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="HeatAI RAG Evaluation Runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--health", action="store_true", help="Environment health check")
    group.add_argument("--load", action="store_true", help="Load and preview dataset")
    group.add_argument("--full", action="store_true", help="Full evaluation (Ragas + ablation + report)")
    group.add_argument("--ragas", action="store_true", help="Ragas E2E evaluation only")
    group.add_argument("--ablation", action="store_true", help="Ablation study only")
    group.add_argument("--report", action="store_true", help="Generate report from existing results")
    group.add_argument("--step", choices=["ragas", "ablation", "report"],
                       help="Run a specific step")

    args = parser.parse_args()

    if args.health:
        cmd_health()
    elif args.load:
        cmd_load()
    elif args.full:
        cmd_full()
    elif args.ragas:
        cmd_ragas()
    elif args.ablation:
        cmd_ablation()
    elif args.report:
        cmd_report()
    elif args.step:
        if args.step == "ragas":
            cmd_ragas()
        elif args.step == "ablation":
            cmd_ablation()
        elif args.step == "report":
            cmd_report()
    else:
        parser.print_help()
        print()
        print("Quick start: python eval/run_eval.py --full")


if __name__ == "__main__":
    main()
