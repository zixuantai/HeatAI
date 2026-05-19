from pydantic_settings import BaseSettings


class EvalSettings(BaseSettings):
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_EVAL_MODEL: str = "qwen3.6-plus"
    DASHSCOPE_EVAL_MODEL_LITE: str = "qwen-plus"

    EVAL_MAX_QUESTIONS: int = 0
    EVAL_OUTPUT_DIR: str = "./eval_output"
    EVAL_BATCH_SIZE: int = 10

    EVAL_JUDGE_TEMPERATURE: float = 0.0

    EVAL_RETRIEVAL_TOP_K: int = 10
    EVAL_FINAL_TOP_K: int = 8

    EVAL_ABLATION_VARIANTS: list = [
        "full",
        "no_rewrite",
        "no_bm25",
        "no_fine_rank",
        "no_context_enrich",
    ]

    EVAL_EMBEDDING_MODEL: str = "BAAI/bge-large-zh-v1.5"
    EVAL_EMBEDDING_DEVICE: str = "cpu"
    EVAL_EMBEDDING_DIM: int = 1024

    REPORT_INCLUDE_LATEX: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


eval_settings = EvalSettings()
