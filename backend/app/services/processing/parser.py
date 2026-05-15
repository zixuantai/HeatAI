import io
from typing import List, Tuple


class DocumentParser:
    SUPPORTED_TYPES = {"pdf", "docx", "html", "htm", "txt"}

    @staticmethod
    def parse(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in DocumentParser.SUPPORTED_TYPES:
            raise ValueError(f"不支持的文件类型: .{ext}")

        if ext == "pdf":
            return DocumentParser._parse_pdf(file_bytes, filename)
        elif ext in ("docx",):
            return DocumentParser._parse_docx(file_bytes, filename)
        elif ext in ("html", "htm"):
            return DocumentParser._parse_html(file_bytes, filename)
        elif ext == "txt":
            return DocumentParser._parse_txt(file_bytes, filename)
        else:
            raise ValueError(f"不支持的文件类型: .{ext}")

    @staticmethod
    def _parse_pdf(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        import pdfplumber

        texts: List[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_parts: List[str] = []
                header = f"[第{i + 1}页]"
                page_parts.append(header)

                page_text = page.extract_text()
                if page_text:
                    page_parts.append(page_text)

                tables = page.extract_tables()
                if tables:
                    page_parts.append("")
                    for ti, table in enumerate(tables):
                        if not table:
                            continue
                        page_parts.append(f"[表格 {ti + 1}]")

                        filtered_rows = []
                        for row in table:
                            filtered = [str(c).strip() if c is not None else "" for c in row]
                            if any(filtered):
                                filtered_rows.append(filtered)
                        if not filtered_rows:
                            continue

                        header_row = filtered_rows[0]
                        col_count = len(header_row)
                        header_str = " | ".join(header_row)
                        sep_str = " | ".join("---" for _ in range(col_count))
                        page_parts.append(header_str)
                        page_parts.append(sep_str)

                        for row in filtered_rows[1:]:
                            padded = row + [""] * (col_count - len(row))
                            page_parts.append(" | ".join(padded[:col_count]))
                        page_parts.append("")

                texts.append("\n".join(page_parts))

        full_text = "\n\n".join(texts)
        title = filename.rsplit(".", 1)[0]
        return full_text, title

    @staticmethod
    def _parse_docx(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(file_bytes))
        paragraphs: List[str] = []

        for para in doc.paragraphs:
            style = para.style.name if para.style else ""
            text = para.text.strip()
            if not text:
                continue
            if "Heading" in style or "heading" in style or "标题" in style:
                paragraphs.append(f"## {text}")
            else:
                paragraphs.append(text)

        for table in doc.tables:
            table_lines: List[str] = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                table_lines.append(" | ".join(cells))
            if table_lines:
                paragraphs.append("\n" + "\n".join(table_lines) + "\n")

        full_text = "\n\n".join(paragraphs)
        title = filename.rsplit(".", 1)[0]
        return full_text, title

    @staticmethod
    def _parse_html(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        from bs4 import BeautifulSoup

        encoding = DocumentParser._detect_encoding(file_bytes)
        logger.info(f"[HTML解析] 检测到编码: {encoding}, 文件名: {filename}")

        html_content = file_bytes.decode(encoding, errors="replace")

        meta_encoding = DocumentParser._extract_html_charset(html_content)
        if meta_encoding and meta_encoding.lower() != encoding.lower():
            try:
                html_content = file_bytes.decode(meta_encoding, errors="replace")
                logger.info(f"[HTML解析] 使用HTML声明的编码: {meta_encoding}")
            except (UnicodeDecodeError, LookupError):
                logger.warning(f"[HTML解析] HTML声明编码 {meta_encoding} 无效, 回退到 {encoding}")

        soup = BeautifulSoup(html_content, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else filename.rsplit(".", 1)[0]

        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        if not text or not text.strip():
            text = soup.get_text(separator="\n")
            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

        if not text or not text.strip():
            logger.warning(f"[HTML解析] 文档解析后内容为空，可能为SPA动态渲染页面: {filename}")
            return "", title

        return text, title

    @staticmethod
    def _extract_html_charset(html: str) -> str | None:
        import re
        meta_pattern = re.compile(
            r'<meta[^>]+charset\s*=\s*["\']?([\w\-\d]+)["\']?',
            re.IGNORECASE,
        )
        match = meta_pattern.search(html[:4096])
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _detect_encoding(file_bytes: bytes) -> str:
        for enc in ["utf-8", "gb18030", "gbk", "gb2312", "latin-1"]:
            try:
                file_bytes.decode(enc)
                return enc
            except (UnicodeDecodeError, LookupError):
                continue
        try:
            import chardet
            result = chardet.detect(file_bytes)
            detected = result.get("encoding")
            if detected and detected.lower() != "utf-8":
                try:
                    file_bytes.decode(detected)
                    return detected
                except (UnicodeDecodeError, LookupError):
                    pass
        except ImportError:
            pass
        return "utf-8"

    @staticmethod
    def _parse_txt(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        encoding = DocumentParser._detect_encoding(file_bytes)
        text = file_bytes.decode(encoding, errors="replace")
        title = filename.rsplit(".", 1)[0]
        return text, title


document_parser = DocumentParser()