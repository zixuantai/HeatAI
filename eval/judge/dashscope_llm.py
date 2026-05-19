"""
DashScope LLM 评判适配器
将阿里云 DashScope 接入 Ragas 的 LLM-as-a-Judge 评估体系

使用方式：
    from eval.judge.dashscope_llm import DashScopeLLM
    judge = DashScopeLLM(model="qwen3.6-plus")
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from dashscope import Generation
from langchain_core.language_models.llms import BaseLLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import LLMResult, Generation as LangChainGeneration

from eval.config import eval_settings

logger = logging.getLogger(__name__)


class DashScopeLLM(BaseLLM):
    """
    DashScope 评判 LLM，实现 LangChain BaseLLM 接口，
    可被 Ragas 的 evaluate() 直接使用。

    关键参数：
        model: DashScope 模型名，默认 qwen3.6-plus
        temperature: 评判温度，建议 0.0（确保评判一致性）
    """

    model: str = "qwen3.6-plus"
    api_key: str = ""
    temperature: float = 0.0
    _executor: ThreadPoolExecutor | None = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, model: str | None = None, api_key: str | None = None, temperature: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self.model = model or eval_settings.DASHSCOPE_EVAL_MODEL
        self.api_key = api_key or eval_settings.DASHSCOPE_API_KEY
        self.temperature = temperature if temperature is not None else eval_settings.EVAL_JUDGE_TEMPERATURE
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置，请在 .env 文件中设置")

    @property
    def _llm_type(self) -> str:
        return "dashscope"

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model, "temperature": self.temperature}

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs,
    ) -> str:
        try:
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                api_key=self.api_key,
                temperature=self.temperature,
                result_format="message",
            )
            if response.status_code != 200:
                logger.error(f"DashScope 调用失败: {response.message}")
                return ""
            content = response.output.choices[0].message.get("content", "")
            return content if content else ""
        except Exception as e:
            logger.error(f"DashScope 异常: {e}")
            return ""

    def _generate(
        self,
        prompts: list[str],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs,
    ) -> LLMResult:
        generations = []
        for prompt in prompts:
            text = self._call(prompt, stop=stop, run_manager=run_manager, **kwargs)
            generations.append([LangChainGeneration(text=text)])
        return LLMResult(generations=generations)


def create_judge_llm(model: str | None = None) -> DashScopeLLM:
    """工厂函数：创建评判 LLM 实例"""
    return DashScopeLLM(model=model)


def create_fast_judge_llm() -> DashScopeLLM:
    """创建轻量评判 LLM（用于快速迭代，降低成本）"""
    return DashScopeLLM(model=eval_settings.DASHSCOPE_EVAL_MODEL_LITE)
