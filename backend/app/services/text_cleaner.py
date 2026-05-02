import re
from typing import List


class TextCleaner:

    @staticmethod
    def clean(text: str) -> str:
        text = TextCleaner._remove_control_chars(text)
        text = TextCleaner._normalize_whitespace(text)
        text = TextCleaner._remove_excessive_newlines(text)
        text = TextCleaner._remove_empty_lines(text)
        text = TextCleaner._normalize_punctuation(text)
        return text.strip()

    @staticmethod
    def _remove_control_chars(text: str) -> str:
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        text = re.sub(r"[^\S\n]+", " ", text)
        return text

    @staticmethod
    def _remove_excessive_newlines(text: str) -> str:
        return re.sub(r"\n{3,}", "\n\n", text)

    @staticmethod
    def _remove_empty_lines(text: str) -> str:
        lines = text.split("\n")
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                result.append(stripped)
            elif result and result[-1] != "":
                result.append("")
        while result and result[-1] == "":
            result.pop()
        return "\n".join(result)

    @staticmethod
    def _normalize_punctuation(text: str) -> str:
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "--")
        text = text.replace("\u00a0", " ")
        return text


text_cleaner = TextCleaner()
