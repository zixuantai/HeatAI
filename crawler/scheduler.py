import csv
import json
import logging
import os
import re
import time
import traceback
from datetime import datetime
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse

from crawler.config import config
from crawler.fetcher import fetcher, FetchResult
from crawler.document_parser import parser as doc_parser, ParsedDocument
from crawler.sites import get_enabled_sites, SiteConfig

logger = logging.getLogger("HeatAI.crawler")


class CrawlerScheduler:

    def __init__(self):
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

        self.checkpoint: Dict = self._load_checkpoint()
        self.completed_urls: Set[str] = set(self.checkpoint.get("completed_urls", []))
        self.total_downloaded: int = self.checkpoint.get("total_downloaded", 0)
        self.total_skipped: int = self.checkpoint.get("total_skipped", 0)

        self.manifest_entries: List[Dict] = self._load_manifest()

    # ===================================================================
    #  断点续抓
    # ===================================================================

    def _load_checkpoint(self) -> Dict:
        if os.path.exists(config.CHECKPOINT_FILE):
            try:
                with open(config.CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("读取检查点文件失败，将从头开始")
        return {}

    def _save_checkpoint(self):
        self.checkpoint["completed_urls"] = list(self.completed_urls)
        self.checkpoint["total_downloaded"] = self.total_downloaded
        self.checkpoint["total_skipped"] = self.total_skipped
        self.checkpoint["last_updated"] = datetime.now().isoformat()
        try:
            with open(config.CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.checkpoint, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")

    # ===================================================================
    #  文档清单
    # ===================================================================

    def _load_manifest(self) -> List[Dict]:
        if os.path.exists(config.MANIFEST_FILE):
            try:
                with open(config.MANIFEST_FILE, "r", encoding="utf-8-sig", newline="") as f:
                    return list(csv.DictReader(f))
            except Exception:
                return []
        return []

    def _append_manifest(self, entry: Dict):
        self.manifest_entries.append(entry)
        file_exists = os.path.exists(config.MANIFEST_FILE)
        try:
            with open(config.MANIFEST_FILE, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "filename", "source_url", "source_site", "category",
                    "doc_format", "title", "text_length", "parse_status",
                    "fetched_at",
                ])
                if not file_exists:
                    writer.writeheader()
                writer.writerow(entry)
        except Exception as e:
            logger.error(f"写入清单失败: {e}")

    # ===================================================================
    #  URL 规范化
    # ===================================================================

    def _normalize_url(self, url: str) -> str:
        url = url.split("#")[0]
        url = url.rstrip("/")
        return url

    # ===================================================================
    #  文件名生成（从URL提取有意义的文件名）
    # ===================================================================

    def _make_safe_filename(self, title: str, ext: str) -> str:
        """从标题生成安全的文件名"""
        safe = re.sub(r'[\\/:*?"<>|]', '_', title)
        safe = safe.replace('\n', ' ').replace('\r', ' ')
        safe = re.sub(r'\s+', ' ', safe).strip()
        if len(safe) > 80:
            safe = safe[:80]
        return f"{safe}{ext}"

    def _resolve_filename(self, url: str, result: FetchResult, doc_title: str = "") -> str:
        """智能命名：优先用给定标题，否则从URL末尾提取"""
        parsed = urlparse(url)
        basename = os.path.basename(parsed.path)
        ext = result.file_ext

        if doc_title:
            return self._make_safe_filename(doc_title, ext)

        if basename and len(basename) > 3 and "." in basename:
            # URL末尾是可读文件名（如 P020240807343313192976.pdf）
            return basename
        else:
            return result.filename

    # ===================================================================
    #  公告页附件提取（住建部页面 → 找到PDF下载链接）
    # ===================================================================

    def _extract_attachments_from_page(self, page_url: str, html: str) -> List[str]:
        """从住建部等公告页面中提取附件下载链接"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        pdf_urls = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href:
                continue

            full_url = urljoin(page_url, href)
            href_lower = full_url.lower()
            text = a_tag.get_text(strip=True)

            if href_lower.endswith(".pdf"):
                pdf_urls.append(full_url)
            elif href_lower.endswith(".doc") or href_lower.endswith(".docx"):
                pdf_urls.append(full_url)
            elif re.search(r"附件|下载|PDF|doc|文件", text) and not href.startswith("javascript"):
                if any(href_lower.endswith(ext) for ext in [".pdf", ".doc", ".docx", ".zip"]):
                    if full_url not in pdf_urls:
                        pdf_urls.append(full_url)

        return pdf_urls

    # ===================================================================
    #  核心：直接文档下载
    # ===================================================================

    def _download_single(self, url: str, doc_title: str = "", category: str = "",
                         source: str = "") -> Optional[ParsedDocument]:
        """下载单个文档并保存、解析、写入清单"""
        normalized = self._normalize_url(url)
        if normalized in self.completed_urls:
            logger.debug(f"  [已处理] 跳过: {url}")
            self.total_skipped += 1
            return None

        result = fetcher.fetch_document(url, source_title=source)
        if not result:
            logger.info(f"  [失败] 无法下载: {url}")
            return None

        filename = self._resolve_filename(url, result, doc_title)

        filepath = os.path.join(config.DOWNLOAD_DIR, filename)
        if os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(filepath):
                filepath = os.path.join(config.DOWNLOAD_DIR, f"{name}_{counter}{ext}")
                counter += 1
            filename = os.path.basename(filepath)

        with open(filepath, "wb") as f:
            f.write(result.content_bytes)

        parsed = doc_parser.parse(result.content_bytes, filename, url)

        fmt = result.file_ext.replace(".", "")
        logger.info(f"  [OK] {filename}  [{fmt}] ({parsed.text_length} chars, {parsed.parse_status})")

        self._append_manifest({
            "filename": filename,
            "source_url": url,
            "source_site": source,
            "category": category,
            "doc_format": fmt,
            "title": parsed.title,
            "text_length": str(parsed.text_length),
            "parse_status": parsed.parse_status,
            "fetched_at": result.fetched_at,
        })

        self.completed_urls.add(normalized)
        self.total_downloaded += 1
        return parsed

    # ===================================================================
    #  批量：从 DirectDoc 列表下载
    # ===================================================================

    def crawl_direct_docs(self, docs: List, label: str = "直接文档下载") -> int:
        """下载一批 DirectDoc 对象

        对 PDF 直链直接下载；
        对 HTML 页面（如住建部公告页），先抓页面再提取附件PDF链接后下载。
        """
        logger.info(f"\n{'#'*60}")
        logger.info(f"  {label}")
        logger.info(f"{'#'*60}\n")

        success_count = 0
        total = len(docs)

        for idx, doc in enumerate(docs, 1):
            url = doc.url
            title = doc.title
            fmt = doc.doc_format
            category = doc.category
            source = doc.source

            logger.info(f"[{idx}/{total}] {title[:60]}")
            logger.info(f"          {url}")

            if fmt == "pdf":
                # PDF 直链：直接下载
                parsed = self._download_single(url, doc_title=title, category=category, source=source)
                if parsed and parsed.parse_status != "failed":
                    success_count += 1

            elif fmt == "html":
                # HTML 页面：先获取，再从中提取附件PDF
                html = fetcher.fetch_page(url)
                if html:
                    attachments = self._extract_attachments_from_page(url, html)
                    if attachments:
                        logger.info(f"          → 页面中发现 {len(attachments)} 个附件")
                        for att_url in attachments:
                            att_parsed = self._download_single(
                                att_url, doc_title=title, category=category, source=source
                            )
                            if att_parsed and att_parsed.parse_status != "failed":
                                success_count += 1
                    else:
                        # 无附件，保存HTML页面本身
                        parsed = self._download_single(url, doc_title=title, category=category, source=source)
                        if parsed and parsed.parse_status != "failed":
                            success_count += 1
                else:
                    logger.info(f"  [失败] 无法访问页面: {url}")

            elif fmt in ("doc", "docx"):
                parsed = self._download_single(url, doc_title=title, category=category, source=source)
                if parsed and parsed.parse_status != "failed":
                    success_count += 1

            if idx % 5 == 0:
                self._save_checkpoint()

        self._save_checkpoint()
        logger.info(f"\n[{label}] 完成: 成功 {success_count}/{total}")
        return success_count

    # ===================================================================
    #  crawl 命令保留（从站点入口页面爬取链接）
    # ===================================================================

    def _link_matches_filters(self, link_url: str, link_text: str, site: SiteConfig) -> bool:
        if not site.link_filters:
            return True
        combined = f"{link_url} {link_text}"
        for pattern in site.link_filters:
            if re.search(pattern, combined):
                return True
        return False

    def _crawl_site_page(self, page_url: str, site: SiteConfig, depth: int = 0) -> List[str]:
        if depth > config.MAX_PAGE_DEPTH:
            return []

        logger.info(f"[爬取页面] (depth={depth}) {page_url}")
        html = fetcher.fetch_page(page_url)
        if not html:
            return []

        links = fetcher.extract_links_from_html(html, page_url)
        logger.info(f"  → 发现 {len(links)} 个文档链接")

        filtered_links = []
        for link_url, link_text in links:
            normalized = self._normalize_url(link_url)
            if normalized in self.completed_urls:
                self.total_skipped += 1
                continue
            if self._link_matches_filters(link_url, link_text, site):
                filtered_links.append(link_url)
            if len(filtered_links) >= config.MAX_LINKS_PER_SITE:
                break

        if filtered_links:
            logger.info(f"  → 关键词过滤后: {len(filtered_links)} 个")
        return filtered_links

    def crawl_site(self, site: SiteConfig):
        logger.info(f"{'='*60}")
        logger.info(f"[站点] {site.name} [{site.category}]")
        logger.info(f"  {site.description}")
        logger.info(f"{'='*60}")

        all_doc_links: Set[str] = set()

        for entry_url in site.entry_urls:
            try:
                links = self._crawl_site_page(entry_url, site, depth=0)
                all_doc_links.update(links)
            except Exception as e:
                logger.error(f"[入口页面错误] {entry_url}: {e}")
                traceback.print_exc()

        logger.info(f"[{site.name}] 共发现 {len(all_doc_links)} 个待下载文档")

        success_count = 0
        fail_count = 0
        for idx, doc_url in enumerate(all_doc_links, 1):
            normalized = self._normalize_url(doc_url)
            if normalized in self.completed_urls:
                self.total_skipped += 1
                continue

            logger.info(f"  [{idx}/{len(all_doc_links)}] 下载: {doc_url}")
            try:
                result = self._download_single(doc_url, category=site.category, source=site.name)
                if result is not None and result.parse_status != "failed":
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"  [下载错误] {doc_url}: {e}")
                fail_count += 1

            if idx % 10 == 0:
                self._save_checkpoint()

        self._save_checkpoint()
        logger.info(f"[{site.name}] 完成: 成功 {success_count}, 失败 {fail_count}")
        return success_count

    def crawl_all(self, categories: Optional[List[str]] = None):
        sites = get_enabled_sites()
        if categories:
            sites = [s for s in sites if s.category in categories]

        logger.info(f"共启用 {len(sites)} 个站点")
        total = 0
        for site in sites:
            try:
                total += self.crawl_site(site)
            except Exception as e:
                logger.error(f"[站点错误] {site.name}: {e}")

        logger.info(f"全部完成! 共下载 {total} 个文档")
        return total

    # ===================================================================
    #  统计 & 扫描
    # ===================================================================

    def get_stats(self) -> Dict:
        return {
            "total_downloaded": self.total_downloaded,
            "total_skipped": self.total_skipped,
            "completed_urls_count": len(self.completed_urls),
            "manifest_entries": len(self.manifest_entries),
            "download_dir": config.DOWNLOAD_DIR,
            "manifest_file": config.MANIFEST_FILE,
        }

    def scan_directory(self, directory: str = None) -> int:
        scan_dir = directory or config.DOWNLOAD_DIR
        if not os.path.isdir(scan_dir):
            logger.error(f"目录不存在: {scan_dir}")
            return 0

        supported_exts = {
            ".pdf", ".docx", ".doc", ".html", ".htm", ".shtml", ".shtm", ".txt",
            ".md", ".markdown", ".csv", ".json",
            ".xlsx", ".xls", ".pptx", ".ppt", ".epub",
            ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp",
        }
        files = [
            f for f in os.listdir(scan_dir)
            if os.path.isfile(os.path.join(scan_dir, f))
            and os.path.splitext(f)[1].lower() in supported_exts
        ]

        if not files:
            logger.info(f"目录 {scan_dir} 中没有找到支持的文档文件")
            return 0

        logger.info(f"[扫描目录] {scan_dir}, {len(files)} 个文件")
        existing_filenames = {e["filename"] for e in self.manifest_entries}
        parsed_count = 0

        for idx, filename in enumerate(files, 1):
            if filename in existing_filenames:
                continue
            filepath = os.path.join(scan_dir, filename)
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
            except Exception:
                continue

            ext = os.path.splitext(filename)[1].lower()
            parsed = doc_parser.parse(content, filename, source_url=f"file:///{filepath}")
            self._append_manifest({
                "filename": filename,
                "source_url": f"file:///{filepath}",
                "source_site": "(手动导入)",
                "category": "manual",
                "doc_format": ext.replace(".", ""),
                "title": parsed.title,
                "text_length": str(parsed.text_length),
                "parse_status": parsed.parse_status,
                "fetched_at": datetime.now().isoformat(),
            })
            existing_filenames.add(filename)
            parsed_count += 1
            logger.info(f"  [{idx}/{len(files)}] [OK] {filename}  ({parsed.text_length} chars)")

        self._save_checkpoint()
        logger.info(f"[扫描完成] 成功: {parsed_count}/{len(files)}")
        return parsed_count


scheduler = CrawlerScheduler()
