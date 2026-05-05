import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class CrawlerConfig:

    DOWNLOAD_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs_downloaded")

    REQUEST_DELAY_MIN: float = 2.0
    REQUEST_DELAY_MAX: float = 5.0

    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 5.0

    USER_AGENT: str = (
        "HeatAI-Crawler/1.0 "
        "(research bot; contact@example.com) "
        "Python-Requests/2.31"
    )

    CHECKPOINT_FILE: str = os.path.join(DOWNLOAD_DIR, "checkpoint.json")
    MANIFEST_FILE: str = os.path.join(DOWNLOAD_DIR, "manifest.csv")
    LOG_FILE: str = os.path.join(DOWNLOAD_DIR, "crawler.log")

    MAX_PAGE_DEPTH: int = 1
    MAX_LINKS_PER_SITE: int = 50

    TARGET_FILE_TYPES: List[str] = field(default_factory=lambda: [".pdf", ".doc", ".docx", ".html", ".htm", ".txt"])

    SEARCH_KEYWORDS: List[str] = field(default_factory=lambda: [
        "供热", "供暖", "热力", "集中供热",
        "供热管网", "热源", "换热站",
        "供热系统", "供热节能", "供热计量",
        "供热管理", "供热条例", "供热标准",
        "城市供热", "供热技术", "供热安全",
        "热电联产", "热力管道", "供热设备",
        "建筑节能", "供热改造", "清洁供暖",
        "供热规范", "供热规划", "供热价格",
    ])


config = CrawlerConfig()
