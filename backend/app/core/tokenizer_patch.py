"""
兼容 transformers 高版本 (>= 4.45) 中移除的 prepare_for_model 方法。

将兼容桩注入 PreTrainedTokenizerBase，所有子类（包括延迟加载的 XLMRobertaTokenizer）
通过 MRO 自动继承，无需逐个枚举。
"""

import logging

logger = logging.getLogger(__name__)

_PATCHED = False


def _stub_prepare_for_model(*args, **_kwargs):
    effective_args = args[1:] if args and hasattr(args[0], 'encode') else args
    if not effective_args:
        return {"input_ids": [], "attention_mask": []}
    token_ids_0 = effective_args[0]
    if isinstance(token_ids_0, dict):
        return token_ids_0
    ids = list(token_ids_0)
    if len(effective_args) > 1 and effective_args[1] is not None:
        token_ids_1 = effective_args[1]
        if isinstance(token_ids_1, dict):
            ids.extend(token_ids_1.get("input_ids", []))
        else:
            ids.extend(token_ids_1)
    return {"input_ids": ids, "attention_mask": [1] * len(ids)}


def apply_tokenizer_patch():
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    try:
        from transformers import PreTrainedTokenizerBase

        for base_cls in (PreTrainedTokenizerBase,):
            if not hasattr(base_cls, "prepare_for_model"):
                base_cls.prepare_for_model = _stub_prepare_for_model
                logger.info(f"[Tokenizer Patch] 已为 {base_cls.__name__} 添加 prepare_for_model 兼容桩")

            for cls in base_cls.__subclasses__():
                if not hasattr(cls, "prepare_for_model"):
                    cls.prepare_for_model = _stub_prepare_for_model
                    logger.debug(f"[Tokenizer Patch] 已为 {cls.__name__} 添加 prepare_for_model 兼容桩")

        logger.info("[Tokenizer Patch] prepare_for_model 兼容桩已就绪")
    except Exception as e:
        logger.warning(f"[Tokenizer Patch] 应用失败: {e}")
