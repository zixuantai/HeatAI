"""
供热行业公开网站配置

每个站点定义:
  - name: 站点名称
  - category: 分类 (policy/standard/tech/association/other)
  - base_url: 基础 URL
  - entry_urls: 入口页面列表（爬取链接用）
  - direct_doc_urls: 已知的公开文档直链（直接下载，跳过页面抓取）
  - description: 站点描述
  - enabled: 是否启用
  - link_filters: 链接过滤规则 (正则列表, 空列表表示不过滤)
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class SiteConfig:
    name: str
    category: str
    base_url: str
    entry_urls: List[str] = field(default_factory=list)
    direct_doc_urls: List[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True
    link_filters: List[str] = field(default_factory=list)


SITES: List[SiteConfig] = [

    # ========================================================================
    #  政策法规类
    # ========================================================================
    SiteConfig(
        name="国家发展改革委",
        category="policy",
        base_url="https://www.ndrc.gov.cn/",
        entry_urls=[
            "https://www.ndrc.gov.cn/fzggw/jgsj/",
            "https://www.ndrc.gov.cn/fzggw/wzslxdw/",
        ],
        description="能源政策、供热价格政策、清洁取暖政策",
        link_filters=[r"供热", r"供暖", r"能源", r"节能", r"清洁取暖", r"热电"],
    ),
    SiteConfig(
        name="住房和城乡建设部",
        category="policy",
        base_url="http://www.mohurd.gov.cn/",
        entry_urls=[
            "http://www.mohurd.gov.cn/gongkai/zhengce/filelib/",
            "http://www.mohurd.gov.cn/gongkai/fdzdgknr/zqyj/",
        ],
        description="供热政策、城市供热管理条例、建筑节能法规（可能需要浏览器访问）",
        link_filters=[r"供热", r"供暖", r"热力", r"节能", r"建筑节能", r"城市供热"],
    ),
    SiteConfig(
        name="国家能源局",
        category="policy",
        base_url="https://www.nea.gov.cn/",
        entry_urls=[
            "https://www.nea.gov.cn/",
        ],
        description="能源领域政策法规、供热规划",
        link_filters=[r"供热", r"供暖", r"热力", r"热电", r"清洁供暖", r"能源"],
    ),
    SiteConfig(
        name="地方住建部门 - 河北",
        category="policy",
        base_url="https://zfcxjst.hebei.gov.cn/",
        entry_urls=[
            "https://zfcxjst.hebei.gov.cn/",
        ],
        description="河北省供热政策（北方集中供热重点省份）",
        link_filters=[r"供热", r"供暖", r"热力", r"采暖"],
    ),
    SiteConfig(
        name="地方住建部门 - 北京",
        category="policy",
        base_url="https://zjw.beijing.gov.cn/",
        entry_urls=[
            "https://zjw.beijing.gov.cn/",
        ],
        description="北京市供热政策、地方标准",
        link_filters=[r"供热", r"供暖", r"热力", r"采暖"],
    ),
    SiteConfig(
        name="应急管理部",
        category="policy",
        base_url="https://www.mem.gov.cn/",
        entry_urls=[
            "https://www.mem.gov.cn/gk/zfxxgkpt/fdzdgknr/",
        ],
        description="供热安全管理规定、应急预案",
        link_filters=[r"供热", r"供暖", r"热力", r"锅炉", r"管网安全", r"供暖安全"],
    ),

    # ========================================================================
    #  标准规范类
    # ========================================================================
    SiteConfig(
        name="全国标准信息公共服务平台",
        category="standard",
        base_url="https://std.samr.gov.cn/",
        entry_urls=[
            "https://std.samr.gov.cn/gb/",
            "https://std.samr.gov.cn/hb/",
        ],
        description="GB国家标准、行业标准检索（动态页面，可能需要浏览器访问）",
        link_filters=[r"供热", r"供暖", r"热力", r"建筑节能", r"热网", r"锅炉"],
    ),
    SiteConfig(
        name="住建部标准定额",
        category="standard",
        base_url="http://www.mohurd.gov.cn/",
        entry_urls=[
            "http://www.mohurd.gov.cn/gongkai/zhengce/zhengcefilelib/",
        ],
        description="CJ/T城镇建设行业标准（可能需要浏览器访问）",
        link_filters=[r"标准", r"CJ/T", r"CJJ", r"城镇供热", r"供热"],
    ),

    # ========================================================================
    #  行业协会（需手动确认网站可访问性后启用）
    # ========================================================================
    SiteConfig(
        name="中国城镇供热协会",
        category="association",
        base_url="http://www.china-heating.org.cn/",
        entry_urls=["http://www.china-heating.org.cn/"],
        description="供热行业技术标准、运行指南、会议论文",
        link_filters=[r"供热", r"供暖", r"热力", r"管网", r"节能", r"技术"],
        enabled=False,
    ),
    SiteConfig(
        name="中国建筑节能协会",
        category="association",
        base_url="http://www.cabee.org/",
        entry_urls=["http://www.cabee.org/"],
        description="建筑节能政策、供热节能技术",
        link_filters=[r"供热", r"节能", r"建筑节能", r"清洁供暖"],
        enabled=False,
    ),

    # ========================================================================
    #  技术文档类（可公开访问的文档页面）
    # ========================================================================
    SiteConfig(
        name="河北省住建厅 - 政策文件",
        category="policy",
        base_url="https://zfcxjst.hebei.gov.cn/",
        entry_urls=[
            "https://zfcxjst.hebei.gov.cn/hbzjt/byw/byw/",
        ],
        description="河北省住建厅行业政策公开页面",
        link_filters=[r"供热", r"供暖", r"热力", r"采暖", r"节能"],
    ),
    SiteConfig(
        name="中国城市供热协会（中热协）",
        category="association",
        base_url="https://www.heating.org.cn/",
        entry_urls=["https://www.heating.org.cn/"],
        description="中国城市供热协会官方网站，技术标准与运行指南",
        link_filters=[r"供热", r"供暖", r"热力", r"管网", r"节能", r"技术", r"标准"],
        enabled=False,
    ),

    # ========================================================================
    #  搜索引擎辅助（通过百度/必应检索供热行业公开文档）
    #  注意：仅抓取搜索结果中的公开文档链接，不抓取搜索引擎本身
    # ========================================================================
    SiteConfig(
        name="百度搜索 - 供热政策文档",
        category="other",
        base_url="https://www.baidu.com/",
        entry_urls=[
            "https://www.baidu.com/s?wd=%E4%BE%9B%E7%83%AD+%E6%94%BF%E7%AD%96+%E6%96%87%E4%BB%B6%E7%B1%BB%E5%9E%8B%3Apdf&rn=20",
            "https://www.baidu.com/s?wd=%E4%BE%9B%E7%83%AD%E8%A1%8C%E4%B8%9A+%E6%A0%87%E5%87%86+%E8%A7%84%E8%8C%83+%E6%96%87%E4%BB%B6%E7%B1%BB%E5%9E%8B%3Apdf&rn=20",
        ],
        description="通过搜索引擎发现公开供热行业文档（仅抓取链接，不抓取搜索引擎内容本身）",
        link_filters=[r"\.pdf|\.doc|\.docx", r"供热|供暖|热力|采暖|热电"],
    ),

    # ========================================================================
    #  已知可访问的公开文档链接（直接下载，无需爬取页面）
    #  以下是政府网站中公开可见的供热相关文档示例URL
    #  注意：部分链接可能随时间变化而失效
    # ========================================================================
    SiteConfig(
        name="公开文档直链",
        category="policy",
        base_url="",
        entry_urls=[],
        direct_doc_urls=[
            # 发改委 - 北方地区冬季清洁取暖规划等政策
            "https://www.ndrc.gov.cn/fzggw/jgsj/yxj/sjdt/201712/t20171220_1150392.html",
            "https://www.ndrc.gov.cn/fzggw/jgsj/yxj/sjdt/201706/t20170613_1150393.html",
            # 住建部 - 城市供热管理条例相关
            "http://www.mohurd.gov.cn/gongkai/zhengce/zhengcefilelib/201803/20180314_235493.html",
            # 标准信息平台搜索页
            "https://std.samr.gov.cn/gb/search/gbDetailed?id=71D772D80C42D3A7E05397BE0A0AB82A",
            # 河北住建厅
            "https://zfcxjst.hebei.gov.cn/",
        ],
        description="已知的公开文档直链（优先尝试直接下载，跳过页面抓取）",
        link_filters=[],
    ),
]


def get_enabled_sites() -> List[SiteConfig]:
    return [s for s in SITES if s.enabled]


def get_sites_by_category(category: str) -> List[SiteConfig]:
    return [s for s in SITES if s.category == category and s.enabled]
