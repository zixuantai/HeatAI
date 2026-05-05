import hashlib
import io
import logging
import os
import re
import time
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from crawler.config import config

logger = logging.getLogger("HeatAI.crawler")


@dataclass
class FetchResult:
    url: str
    content_bytes: bytes
    content_type: str
    filename: str
    file_ext: str
    source_title: str = ""
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat())


class RobotChecker:
    """robots.txt 合规检查器"""

    def __init__(self):
        self._cache: Dict[str, Optional[Dict]] = {}

    def _get_robots_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _parse_robots(self, text: str) -> Dict:
        """解析 robots.txt, 提取 Disallow 规则 (简化实现)"""
        rules: Dict[str, List[str]] = {"disallow": [], "crawl_delay": None}
        current_agent = "*"
        agent_rules: Dict[str, List[str]] = {}

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 展开 field: value
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip().lower()
                value = value.strip()

                if field == "user-agent":
                    current_agent = value
                    if current_agent not in agent_rules:
                        agent_rules[current_agent] = []
                elif field == "disallow" and current_agent in ("*", "HeatAI-Crawler"):
                    agent_rules.setdefault(current_agent, []).append(value)
                elif field == "crawl-delay" and current_agent in ("*", "HeatAI-Crawler"):
                    try:
                        rules["crawl_delay"] = float(value)
                    except ValueError:
                        pass

        # 合并 * 和当前 agent 的规则
        for agent_key in ("*", "HeatAI-Crawler"):
            if agent_key in agent_rules:
                rules["disallow"].extend(agent_rules[agent_key])

        return rules

    def is_allowed(self, url: str, session: requests.Session) -> Tuple[bool, Optional[float]]:
        """检查 URL 是否允许爬取，返回 (是否允许, crawl_delay)"""
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        if base not in self._cache:
            robots_url = self._get_robots_url(url)
            try:
                resp = session.get(robots_url, timeout=10)
                if resp.status_code == 200:
                    self._cache[base] = self._parse_robots(resp.text)
                else:
                    self._cache[base] = None  # 无 robots.txt，默认允许
            except Exception:
                self._cache[base] = None  # 获取失败，默认允许

        rules = self._cache.get(base)
        if rules is None:
            return True, None

        path = parsed.path or "/"
        for disallow_path in rules["disallow"]:
            if disallow_path and path.startswith(disallow_path):
                logger.info(f"[robots.txt] 禁止爬取: {url} (匹配规则: {disallow_path})")
                return False, None

        return True, rules.get("crawl_delay")


class RateLimiter:
    """请求速率控制器"""

    def __init__(self, min_delay: float = None, max_delay: float = None):
        self.min_delay = min_delay or config.REQUEST_DELAY_MIN
        self.max_delay = max_delay or config.REQUEST_DELAY_MAX
        self._last_request: Dict[str, float] = {}

    def wait(self, domain: str):
        now = time.time()
        if domain in self._last_request:
            elapsed = now - self._last_request[domain]
            required = random.uniform(self.min_delay, self.max_delay)
            if elapsed < required:
                sleep_time = required - elapsed
                logger.debug(f"[限速] 等待 {sleep_time:.1f}s (域名: {domain})")
                time.sleep(sleep_time)
        self._last_request[domain] = time.time()


class DocumentFetcher:
    """HTTP 文档抓取器 —— 合规、限速、带重试"""

    def __init__(self):
        self.session = self._build_session()
        self.robot_checker = RobotChecker()
        self.rate_limiter = RateLimiter()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,image/apng,*/*;q=0.8,"
                "application/signed-exchange;v=b3;q=0.7"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
        })

        retry_strategy = Retry(
            total=config.MAX_RETRIES,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _extract_filename(self, url: str, content_type: str) -> Tuple[str, str]:
        """从 URL 提取文件名和扩展名"""
        parsed = urlparse(url)
        path = parsed.path

        # 尝试从 URL 路径提取
        basename = os.path.basename(path) if path else "index"
        if "." in basename:
            name, ext = basename.rsplit(".", 1)
            ext = f".{ext.lower()}"
        else:
            # 从 Content-Type 推断
            ct = content_type.lower()
            if "pdf" in ct:
                ext = ".pdf"
            elif "word" in ct or "docx" in ct or "msword" in ct:
                ext = ".docx" if "docx" in ct else ".doc"
            elif "html" in ct:
                ext = ".html"
            elif "plain" in ct:
                ext = ".txt"
            else:
                ext = ".html"
            name = basename

        # 如果文件名仍为空，用 URL 哈希生成
        if not name or name == "":
            name = hashlib.md5(url.encode()).hexdigest()[:12]

        filename = f"{name}{ext}"
        return filename, ext

    def _is_document_url(self, url: str, content_type: str = "") -> bool:
        """判断 URL 是否指向可下载文档"""
        url_lower = url.lower()

        # 过滤明显非文档链接
        skip_patterns = [
            "javascript:", "mailto:", "tel:", "#",
            "login", "register", "signin", "signup",
            "?replytocom", "share=", "?s=",
        ]
        for p in skip_patterns:
            if p in url_lower:
                return False

        # 排除图片、CSS、JS 等
        skip_exts = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js",
                     ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3"}
        for ext in skip_exts:
            if url_lower.endswith(ext):
                return False

        # 目标扩展名
        for ext in config.TARGET_FILE_TYPES:
            if url_lower.endswith(ext):
                return True

        # 从 Content-Type 判断
        ct = content_type.lower()
        doc_cts = {"pdf", "msword", "word", "document", "text/plain", "text/html"}
        for dct in doc_cts:
            if dct in ct:
                return True

        return False

    def fetch_page(self, url: str) -> Optional[str]:
        """抓取 HTML 页面，返回文本内容"""
        domain = urlparse(url).netloc

        allowed, robots_delay = self.robot_checker.is_allowed(url, self.session)
        if not allowed:
            return None

        self.rate_limiter.wait(domain)

        try:
            resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()

            if resp.encoding and resp.encoding.lower() != "utf-8":
                resp.encoding = resp.apparent_encoding or resp.encoding

            return resp.text
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            if status == 403:
                logger.warning(f"[页面被拒绝 403] {url} (网站可能需要浏览器Cookie或反爬机制)")
            elif status == 404:
                logger.warning(f"[页面不存在 404] {url}")
            elif status == 503:
                logger.warning(f"[服务不可用 503] {url}")
            else:
                logger.warning(f"[页面请求失败 {status}] {url}: {e}")
            return None
        except requests.ConnectionError as e:
            logger.warning(f"[连接失败] {url}: {e}")
            return None
        except requests.Timeout as e:
            logger.warning(f"[请求超时] {url}: {e}")
            return None
        except requests.RequestException as e:
            logger.warning(f"[页面请求失败] {url}: {e}")
            return None

    def fetch_document(self, url: str, source_title: str = "") -> Optional[FetchResult]:
        """下载文档，返回 FetchResult"""
        domain = urlparse(url).netloc

        allowed, robots_delay = self.robot_checker.is_allowed(url, self.session)
        if not allowed:
            return None

        self.rate_limiter.wait(domain)

        for attempt in range(config.MAX_RETRIES):
            try:
                # HEAD 请求先探测
                head_resp = self.session.head(url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True)
                content_type = head_resp.headers.get("Content-Type", "")
                content_length = head_resp.headers.get("Content-Length", "")

                # 如果 Content-Type 明显不是文档，跳过
                if not self._is_document_url(url, content_type):
                    logger.debug(f"[跳过] 非文档类型: {url} ({content_type})")
                    return None

                # GET 下载
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True)
                resp.raise_for_status()

                # 检查大小
                content = resp.content
                if len(content) < 100:
                    logger.debug(f"[跳过] 内容过小 ({len(content)} bytes): {url}")
                    return None
                if int(content_length or 0) > 50 * 1024 * 1024:  # 超过 50MB 跳过
                    logger.info(f"[跳过] 文件过大 ({content_length} bytes): {url}")
                    return None

                filename, ext = self._extract_filename(url, resp.headers.get("Content-Type", ""))
                return FetchResult(
                    url=url,
                    content_bytes=content,
                    content_type=resp.headers.get("Content-Type", ""),
                    filename=filename,
                    file_ext=ext,
                    source_title=source_title,
                )

            except requests.RequestException as e:
                logger.warning(f"[下载失败] 第{attempt+1}次尝试: {url}: {e}")
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(config.RETRY_DELAY)
                else:
                    logger.error(f"[下载失败] 已达最大重试次数: {url}")
                    return None

    def extract_links_from_html(self, html: str, base_url: str) -> List[Tuple[str, str]]:
        """从 HTML 中提取文档链接和页面链接"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        links: List[Tuple[str, str]] = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href:
                continue

            full_url = urljoin(base_url, href)
            link_text = a_tag.get_text(strip=True) or ""

            if self._is_document_url(full_url):
                links.append((full_url, link_text))

        return links


fetcher = DocumentFetcher()
