"""
HeatAI 供热行业公开文档合规爬虫

用法:
    # ★ 推荐：直接下载已验证的供热行业PDF/标准文档
    python -m crawler.main direct

    # 从网站入口爬取链接
    python -m crawler.main crawl
    python -m crawler.main crawl --category policy

    # 扫描手动下载的文件，解析并生成清单
    python -m crawler.main scan

    # 其他
    python -m crawler.main list         # 列出站点
    python -m crawler.main stats        # 查看统计
    python -m crawler.main test --url .. # 测试URL
    python -m crawler.main export       # 导出清单

注意事项:
    - 遵守各网站 robots.txt 规定
    - 请求间隔默认 2-5 秒，避免对服务器造成压力
    - 仅爬取公开可访问的文档
    - 文档存放在 crawler/docs_downloaded/ 目录
"""
import argparse
import csv
import json
import logging
import os
import sys

from crawler.config import config
from crawler.sites import SITES, get_enabled_sites
from crawler.scheduler import scheduler


def setup_logging():
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    root = logging.getLogger("HeatAI")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def cmd_direct(args):
    """★ 主力命令：直接下载已验证的供热行业公开文档"""
    from crawler.direct_urls import DIRECT_DOCS

    category = args.category
    docs = DIRECT_DOCS if not category else [
        d for d in DIRECT_DOCS if d.category == category
    ]

    print(f"\n{'='*60}")
    print(f"  供热行业公开文档直链下载")
    print(f"  总计 {len(docs)} 条链接")
    if category:
        print(f"  分类: {category}")
    print(f"{'='*60}\n")

    pdf_count = sum(1 for d in docs if d.doc_format == "pdf")
    html_count = sum(1 for d in docs if d.doc_format == "html")
    print(f"  PDF: {pdf_count}  |  HTML: {html_count}  |  其他: {len(docs) - pdf_count - html_count}")
    print(f"  标准规范: {sum(1 for d in docs if d.category == 'standard')}")
    print(f"  地方法规: {sum(1 for d in docs if d.category == 'regulation')}")
    print(f"  便民服务: {sum(1 for d in docs if d.category == 'service')}")
    print(f"  政策公告: {sum(1 for d in docs if d.category == 'notice')}")
    print()

    total = scheduler.crawl_direct_docs(docs, label="供热行业公开文档直链下载")

    print(f"\n[完成] 成功下载 {total}/{len(docs)} 个文档。")
    print(f"   文档目录: {config.DOWNLOAD_DIR}")
    print(f"   文档清单: {config.MANIFEST_FILE}")
    print(f"   运行日志: {config.LOG_FILE}")
    print(f"\n   提示: 标准文档PDF也可手动搜索下载到 docs_downloaded/")
    print(f"         然后运行: python -m crawler.main scan")
    print(f"         再运行: python -m crawler.main export")


def cmd_crawl(args):
    categories = [args.category] if args.category else None
    total = scheduler.crawl_all(categories=categories)
    print(f"\n[完成] 爬取完成！成功下载 {total} 个文档。")
    print(f"   文档目录: {config.DOWNLOAD_DIR}")
    print(f"   文档清单: {config.MANIFEST_FILE}")
    print(f"\n   提示: 推荐使用 python -m crawler.main direct 获得更好的结果")


def cmd_scan(args):
    scan_dir = args.dir or config.DOWNLOAD_DIR
    print(f"\n扫描目录: {scan_dir}\n")
    count = scheduler.scan_directory(directory=scan_dir)
    print(f"\n[完成] 扫描完成！成功解析 {count} 个文件。")
    print(f"   文档清单: {config.MANIFEST_FILE}")


def cmd_list(args):
    print(f"\n{'='*70}")
    print(f"  供热行业公开文档爬虫 - 站点列表")
    print(f"{'='*70}\n")
    enabled = get_enabled_sites()
    print(f"已启用站点: {len(enabled)} 个\n")
    categories = {}
    for site in SITES:
        categories.setdefault(site.category, []).append(site)
    cat_names = {
        "policy": "政策法规", "standard": "标准规范",
        "tech": "技术指南", "association": "行业协会", "other": "其他",
    }
    for cat, sites in categories.items():
        label = cat_names.get(cat, cat)
        print(f"  [{label}]")
        for site in sites:
            status = "[启用]" if site.enabled else "[禁用]"
            print(f"    {status}  {site.name}")
            print(f"           {site.description}")
        print()
    print()


def cmd_stats(args):
    stats = scheduler.get_stats()
    print(f"\n{'='*50}")
    print(f"  爬取统计")
    print(f"{'='*50}")
    print(f"  已下载文档:  {stats['total_downloaded']}")
    print(f"  已跳过链接:  {stats['total_skipped']}")
    print(f"  已完成URL:   {stats['completed_urls_count']}")
    print(f"  清单条目数:  {stats['manifest_entries']}")
    print(f"  下载目录:    {stats['download_dir']}")
    print(f"  清单文件:    {stats['manifest_file']}")
    print(f"{'='*50}\n")

    if os.path.exists(config.MANIFEST_FILE):
        with open(config.MANIFEST_FILE, "r", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if rows:
            print(f"  最新记录:")
            print(f"  {'文件名':<50} {'格式':<6} {'状态'}")
            print(f"  {'-'*70}")
            for row in rows[-10:]:
                fname = row.get("filename", "")[:48]
                fmt = row.get("doc_format", "")
                status = row.get("parse_status", "")
                print(f"  {fname:<50} {fmt:<6} {status}")
        print()


def cmd_test(args):
    from crawler.fetcher import fetcher
    print(f"\n测试 URL: {args.url}\n")
    html = fetcher.fetch_page(args.url)
    if html:
        links = fetcher.extract_links_from_html(html, args.url)
        print(f"  页面内容长度: {len(html)} 字符")
        print(f"  发现文档链接: {len(links)} 个")
        for link_url, link_text in links[:20]:
            print(f"    - {link_text[:50] if link_text else '(无文本)'}")
            print(f"      {link_url}")
    else:
        print("  [警告] 无法获取页面内容")


def cmd_export(args):
    fmt = args.format or "json"
    if not os.path.exists(config.MANIFEST_FILE):
        print("[警告] 没有清单文件，请先运行 direct、crawl 或 scan 命令。")
        print(f"  推荐: python -m crawler.main direct")
        return
    with open(config.MANIFEST_FILE, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if fmt == "json":
        out_path = os.path.join(config.DOWNLOAD_DIR, "manifest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
        print(f"[完成] 已导出 JSON: {out_path} ({len(rows)} 条)")
    elif fmt == "txt":
        out_path = os.path.join(config.DOWNLOAD_DIR, "manifest.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(f"{row.get('filename','')} | {row.get('source_url','')} | {row.get('title','')}\n")
        print(f"[完成] 已导出 TXT: {out_path} ({len(rows)} 条)")


def main():
    parser = argparse.ArgumentParser(
        description="HeatAI 供热行业公开文档合规爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m crawler.main direct                    # ★ 主力：直接下载供热PDF/标准
  python -m crawler.main direct --category standard # 仅下载标准规范
  python -m crawler.main crawl                      # 从网站入口爬取
  python -m crawler.main scan                       # 扫描已有文件生成清单
  python -m crawler.main stats                      # 查看统计
  python -m crawler.main export                     # 导出清单JSON
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="")

    direct_parser = subparsers.add_parser("direct", help="★ 主力：直接下载已验证的供热行业公开文档")
    direct_parser.add_argument("--category", "-c",
                               choices=["standard", "regulation", "service", "notice"],
                               help="按分类筛选")

    crawl_parser = subparsers.add_parser("crawl", help="从网站入口页面爬取链接")
    crawl_parser.add_argument("--category", "-c",
                              choices=["policy", "standard", "tech", "association", "other"],
                              help="按分类筛选")

    scan_parser = subparsers.add_parser("scan", help="扫描已下载文件目录，解析并生成清单")
    scan_parser.add_argument("--dir", "-d", help="扫描目录路径")

    subparsers.add_parser("list", help="列出所有站点")
    subparsers.add_parser("stats", help="显示爬取统计")

    test_parser = subparsers.add_parser("test", help="测试单个 URL")
    test_parser.add_argument("--url", "-u", required=True, help="测试 URL")

    export_parser = subparsers.add_parser("export", help="导出文档清单")
    export_parser.add_argument("--format", "-f", choices=["json", "txt"], default="json", help="导出格式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    setup_logging()

    commands = {
        "direct": cmd_direct,
        "crawl": cmd_crawl,
        "scan": cmd_scan,
        "list": cmd_list,
        "stats": cmd_stats,
        "test": cmd_test,
        "export": cmd_export,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
