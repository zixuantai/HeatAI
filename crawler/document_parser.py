import io
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("HeatAI.crawler")


@dataclass
class ParsedDocument:
    filename: str
    file_ext: str
    source_url: str
    title: str
    text: str
    text_length: int
    parse_status: str  # "success" | "partial" | "failed"


class DocumentParser:

    SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".html", ".htm", ".shtml", ".shtm", ".txt"}

    @classmethod
    def parse(cls, content_bytes: bytes, filename: str, source_url: str = "") -> ParsedDocument:
        ext = cls._get_ext(filename)
        if ext not in cls.SUPPORTED_EXTS:
            raise ValueError(f"不支持的文件类型: {ext}")

        try:
            if ext == ".pdf":
                text, title = cls._parse_pdf(content_bytes, filename)
            elif ext in (".docx", ".doc"):
                text, title = cls._parse_docx(content_bytes, filename)
            elif ext in (".html", ".htm", ".shtml", ".shtm"):
                text, title = cls._parse_html(content_bytes, filename)
            elif ext == ".txt":
                text, title = cls._parse_txt(content_bytes, filename)
            else:
                raise ValueError(f"不支持的文件类型: {ext}")

            # 如果 text 为空但 content 有内容, 则为部分成功
            if not text or not text.strip():
                if len(content_bytes) > 100:
                    return ParsedDocument(
                        filename=filename,
                        file_ext=ext,
                        source_url=source_url,
                        title=title or filename,
                        text="(该文档无法提取文本内容，请手动查看)",
                        text_length=0,
                        parse_status="partial",
                    )
                else:
                    return ParsedDocument(
                        filename=filename,
                        file_ext=ext,
                        source_url=source_url,
                        title=title or filename,
                        text="",
                        text_length=0,
                        parse_status="failed",
                    )

            return ParsedDocument(
                filename=filename,
                file_ext=ext,
                source_url=source_url,
                title=title or filename,
                text=text,
                text_length=len(text),
                parse_status="success",
            )
        except Exception as e:
            logger.error(f"[解析失败] {filename}: {e}")
            return ParsedDocument(
                filename=filename,
                file_ext=ext,
                source_url=source_url,
                title=filename,
                text=f"(解析异常: {str(e)})",
                text_length=0,
                parse_status="failed",
            )

    @staticmethod
    def _get_ext(filename: str) -> str:
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""

    @staticmethod
    def _parse_pdf(content_bytes: bytes, filename: str):
        import pdfplumber

        texts = []
        with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)

        full_text = "\n\n".join(texts)
        return full_text, DocumentParser._guess_title(full_text, filename)

    @staticmethod
    def _parse_docx(content_bytes: bytes, filename: str):
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(content_bytes))
        paragraphs = []

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        for table in doc.tables:
            table_lines = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_lines.append(" | ".join(cells))
            if table_lines:
                paragraphs.append("\n" + "\n".join(table_lines) + "\n")

        full_text = "\n\n".join(paragraphs)
        return full_text, DocumentParser._guess_title(full_text, filename)

    @staticmethod
    def _parse_html(content_bytes: bytes, filename: str):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content_bytes, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else filename.rsplit(".", 1)[0]

        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        return text, title

    @staticmethod
    def _parse_txt(content_bytes: bytes, filename: str):
        text = content_bytes.decode("utf-8", errors="replace")
        return text, filename.rsplit(".", 1)[0]

    @staticmethod
    def _guess_title(text: str, filename: str) -> str:
        """从文本前几行推测标题"""
        if not text:
            return filename
        lines = text.strip().split("\n")
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) >= 5 and len(line) <= 100:
                return line
        return filename


parser = DocumentParser()
