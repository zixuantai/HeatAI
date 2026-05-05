"""
评估数据集构建器
支持多种数据来源构建评测集：
1. 从 JSON/CSV 文件加载
2. 从数据库 conversations 表导出
3. 通过 LLM 从知识库文档自动生成问答对
4. 人工标注的 ground_truth 数据集
"""

import json
import logging
import random
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

QUESTION_CATEGORIES = [
    "简单事实查询",
    "专业术语查询",
    "跨文档综合问题",
    "口语化模糊问题",
    "时间敏感问题",
    "需要工具调用",
    "多轮追问",
    "矛盾信息处理",
]


class EvalDataset:
    """
    评估数据集封装
    每条数据包含: question, answer?, contexts?, ground_truth?, category?, metadata?
    """

    def __init__(self):
        self.records: list[dict[str, Any]] = []

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def __getitem__(self, idx):
        return self.records[idx]

    @property
    def questions(self) -> list[str]:
        return [r["question"] for r in self.records]

    @property
    def categories(self) -> list[str]:
        return [r.get("category", "未分类") for r in self.records]

    def to_ragas_dict(self) -> dict[str, list[Any]]:
        """转为 Ragas 评估所需的 dict 格式 (0.4.x column names)"""
        data: dict[str, list[Any]] = {"user_input": [], "response": [], "retrieved_contexts": []}
        for r in self.records:
            data["user_input"].append(r["question"])
            data["response"].append(r.get("answer", ""))
            data["retrieved_contexts"].append(r.get("contexts", []))
        if any(r.get("ground_truth") for r in self.records):
            data["reference"] = [r.get("ground_truth", "") for r in self.records]
        return data

    def to_pandas(self) -> pd.DataFrame:
        return pd.DataFrame(self.records)

    def sample(self, n: int) -> "EvalDataset":
        """随机采样 n 条"""
        sampled = EvalDataset()
        sampled.records = random.sample(self.records, min(n, len(self.records)))
        return sampled

    def filter_by_category(self, category: str) -> "EvalDataset":
        """按类别筛选"""
        filtered = EvalDataset()
        filtered.records = [r for r in self.records if r.get("category") == category]
        return filtered

    def category_distribution(self) -> dict[str, int]:
        """统计类别分布"""
        dist: dict[str, int] = {}
        for r in self.records:
            cat = r.get("category", "未分类")
            dist[cat] = dist.get(cat, 0) + 1
        return dist


class DatasetBuilder:
    """数据集构建器"""

    @staticmethod
    def from_json(file_path: str) -> EvalDataset:
        """
        从 JSON 文件加载数据集

        JSON 格式示例:
        [
            {
                "question": "北京市供暖季什么时候结束？",
                "category": "简单事实查询",
                "ground_truth": "北京市供暖季通常于3月15日结束..."
            }
        ]
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"数据集文件不存在: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        ds = EvalDataset()
        for item in data:
            record = {
                "question": item.get("question", ""),
                "category": item.get("category", "未分类"),
                "ground_truth": item.get("ground_truth", ""),
                "metadata": item.get("metadata", {}),
            }
            ds.records.append(record)

        logger.info(f"从 JSON 加载了 {len(ds)} 条数据: {file_path}")
        return ds

    @staticmethod
    def from_csv(file_path: str) -> EvalDataset:
        """
        从 CSV 文件加载数据集
        CSV 必须包含 question 列，可选 category, ground_truth 列
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"数据集文件不存在: {file_path}")

        df = pd.read_csv(path, encoding="utf-8")
        ds = EvalDataset()
        for _, row in df.iterrows():
            record = {
                "question": str(row.get("question", "")),
                "category": str(row.get("category", "未分类")),
                "ground_truth": str(row.get("ground_truth", "")),
                "metadata": {},
            }
            ds.records.append(record)

        logger.info(f"从 CSV 加载了 {len(ds)} 条数据: {file_path}")
        return ds

    @staticmethod
    def from_question_list(questions: list[str], categories: list[str] | None = None) -> EvalDataset:
        """从问题列表构建数据集"""
        ds = EvalDataset()
        for i, q in enumerate(questions):
            cat = categories[i] if categories and i < len(categories) else "未分类"
            ds.records.append({"question": q, "category": cat, "ground_truth": "", "metadata": {}})
        logger.info(f"从列表构建了 {len(ds)} 条数据")
        return ds

    @staticmethod
    def load_synthetic_dataset(file_path: str) -> EvalDataset:
        """
        从 Ragas TestsetGenerator 生成的合成数据集加载
        这类数据通常包含 question, contexts, ground_truth
        """
        path = Path(file_path)
        ds = None

        if path.suffix == ".parquet":
            from datasets import load_dataset
            ds = load_dataset("parquet", data_files=str(path))["train"]
        elif path.suffix == ".jsonl":
            records = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    records.append(json.loads(line.strip()))
            ds = records
        else:
            return DatasetBuilder.from_json(file_path)

        eval_ds = EvalDataset()
        for item in ds:
            record = {
                "question": item.get("question", ""),
                "category": "合成数据",
                "ground_truth": item.get("ground_truth", "") or item.get("answer", ""),
                "contexts": item.get("contexts", []),
                "metadata": {"source": "synthetic"},
            }
            eval_ds.records.append(record)

        logger.info(f"加载合成数据集 {len(eval_ds)} 条: {file_path}")
        return eval_ds

    @staticmethod
    def merge(*datasets: EvalDataset) -> EvalDataset:
        """合并多个数据集"""
        merged = EvalDataset()
        for ds in datasets:
            merged.records.extend(ds.records)
        logger.info(f"合并数据集: {len(datasets)} 个来源, 共 {len(merged)} 条")
        return merged

    @staticmethod
    def export_to_json(dataset: EvalDataset, file_path: str) -> None:
        """导出为 JSON 文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(dataset.records, f, ensure_ascii=False, indent=2)
        logger.info(f"数据集已导出: {file_path} ({len(dataset)} 条)")

    @staticmethod
    def export_to_csv(dataset: EvalDataset, file_path: str) -> None:
        """导出为 CSV 文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = dataset.to_pandas()
        df.to_csv(path, index=False, encoding="utf-8")
        logger.info(f"数据集已导出: {file_path} ({len(dataset)} 条)")


def load_conversation_questions(db_url: str, limit: int = 200) -> list[str]:
    """
    从数据库 conversations 表中提取用户问题作为评估候选集
    需要数据库中有 conversations 表
    """
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "+pysqlite"))
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT DISTINCT question FROM conversations WHERE question IS NOT NULL AND question != '' ORDER BY created_at DESC LIMIT :limit"),
                {"limit": limit}
            )
            questions = [row[0] for row in result.fetchall()]
        logger.info(f"从数据库提取了 {len(questions)} 条用户问题")
        return questions
    except Exception as e:
        logger.warning(f"从数据库提取问题失败: {e}")
        return []
