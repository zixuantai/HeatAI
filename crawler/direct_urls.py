"""
供热行业公开文档直链库 v2.0
——覆盖北方主要城市最新供热管理条例/标准/便民指南

新增城市：北京、天津、河北/石家庄、山西/太原、内蒙古/呼和浩特、
         辽宁/沈阳/大连、吉林/长春/吉林市、黑龙江/哈尔滨、
         山东/济南/聊城、河南/许昌、陕西/西安、甘肃/兰州、
         宁夏/银川、新疆/乌鲁木齐

所有链接来源于政府网站(.gov.cn)、人大网站或行业协会公开页面。
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class DirectDoc:
    url: str
    title: str
    category: str  # standard / regulation / service / notice / reference
    doc_format: str  # pdf / doc / html / docx
    source: str = ""
    description: str = ""


DIRECT_DOCS: List[DirectDoc] = [

    # ================================================================
    #  最新国家标准（2021-2024）
    # ================================================================
    DirectDoc(
        url="https://www.jsrq.org.cn/kindeditor/attached/file/20241014/20241014143751_84071.pdf",
        title="供热工程项目规范 GB 55010-2021（全文PDF）",
        category="standard", doc_format="pdf",
        source="江苏省燃气热力协会",
        description="强制性国标，2022.1.1实施。全部条文必须严格执行。",
    ),
    DirectDoc(
        url="https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_17339_767030.html",
        title="住建部公告：城镇供热管网设计标准 CJJ/T 34-2022",
        category="standard", doc_format="html",
        source="住房和城乡建设部",
        description="2022版，替代CJJ 34-2010。含PDF附件。",
    ),
    DirectDoc(
        url="https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2021/art_17339_761189.html",
        title="住建部公告：供热工程项目规范 GB 55010-2021",
        category="standard", doc_format="html",
        source="住房和城乡建设部",
        description="强制性规范公告页，含PDF附件。",
    ),
    DirectDoc(
        url="https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_133ee4084cf845f2929981f15658f5b3.html",
        title="住建部：城镇供热工程智能化技术标准（征求意见稿）",
        category="standard", doc_format="html",
        source="住房和城乡建设部",
        description="行业标准征求意见稿，含PDF附件下载。",
    ),
    DirectDoc(
        url="https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_4122044ed24e413cb2bf0cca2f49f057.html",
        title="住建部：供热燃气锅炉烟气冷凝热能回收装置（国标征求意见稿）",
        category="standard", doc_format="html",
        source="住房和城乡建设部",
        description="含DOC附件。",
    ),
    DirectDoc(
        url="http://www.weboos.cn:8078/assets/basicStandard/std_506936.pdf",
        title="城镇供热管网工程施工及验收规范 CJJ 28-2014",
        category="standard", doc_format="pdf",
        source="标准资源库",
        description="2014.10.1实施。供热管道安装、焊接、试验规范。",
    ),
    DirectDoc(
        url="https://www.guifanku.com/tag/4705/",
        title="规范库：城镇供热管网标签页（多项标准合集）",
        category="standard", doc_format="html",
        source="规范库",
        description="含CJJ 34-2022、CJJ 28-2014等多份标准。",
    ),

    # ================================================================
    #  华北：北京
    # ================================================================
    DirectDoc(
        url="https://csglw.beijing.gov.cn/zwxx/2024zcwj/202405/t20240517_3687134.html",
        title="北京市供热采暖管理办法（现行有效）",
        category="regulation", doc_format="html",
        source="北京市城市管理委员会",
        description="2009年发布，现行有效。采暖期11.15-3.15，室温≥18℃。",
    ),
    DirectDoc(
        url="https://csglw.beijing.gov.cn/csyxbz/fwxx/grfw/",
        title="北京市供热服务页面（报修电话+常见问题）",
        category="service", doc_format="html",
        source="北京市城管委",
        description="供热服务电话、供热常见问题汇总、合同示范文本。",
    ),

    # ================================================================
    #  华北：天津
    # ================================================================
    DirectDoc(
        url="https://csgl.tj.gov.cn/zwgk_57/xzcwj/CGWWJ/202603/t20260327_7271119.html",
        title="天津市供热采暖收费管理办法（2026年3月新版）",
        category="regulation", doc_format="html",
        source="天津市城市管理委员会",
        description="2026.3.26施行，有效期5年。居民25元/㎡，非居民40元/㎡。",
    ),
    DirectDoc(
        url="https://csgl.tj.gov.cn/zwgk_57/xzcwj/CGWWJ/202512/t20251222_7203792.html",
        title="天津市供热采暖收费管理办法（2025版全文）",
        category="regulation", doc_format="html",
        source="天津市城管委",
        description="含计费面积详细计算规则。",
    ),
    DirectDoc(
        url="https://www.tjwq.gov.cn/zwgk/zfxxgk/wbj2/qcsglw1/fdzdgknr14/zdmsxx14/szjs14/cszhzf/202512/t20251226_7208856.html",
        title="天津市供热用热条例（全文）",
        category="regulation", doc_format="html",
        source="天津市武清区城管委",
        description="天津市供热基本法规，含规划建设、供热用热、设施管理全章。",
    ),

    # ================================================================
    #  华北：河北（省级+石家庄）
    # ================================================================
    DirectDoc(
        url="https://www.hebei.gov.cn/columns/8d411a3a-3243-4e60-9d39-17028524ba32/202604/07/413fd779-2a70-4ea9-a419-15ef3b6a0142.html",
        title="河北省供热用热办法（2025修订，2026.1.1施行）",
        category="regulation", doc_format="html",
        source="河北省人民政府",
        description="2025.11.7省政府通过，2026.1.1施行。替代2013版。含投诉举报制度。",
    ),
    DirectDoc(
        url="http://www.hebei.gov.cn/attachments/1/202512/09/25ZFL1020251209161014690.pdf",
        title="河北省供热用热办法（2025版）PDF",
        category="regulation", doc_format="pdf",
        source="河北省人民政府",
        description="最新版PDF全文。",
    ),
    DirectDoc(
        url="http://cgj.sjz.gov.cn/atm/7/20221009144929576.pdf",
        title="石家庄市供热用热条例 PDF",
        category="regulation", doc_format="pdf",
        source="石家庄市城管局",
        description="2022年修订版。采暖期11.15-3.15，室温≥18℃。",
    ),
    DirectDoc(
        url="https://cgzf.hd.gov.cn/static/upload/file/20251127/1764205673969540.pdf",
        title="邯郸市城市供热用热条例 PDF",
        category="regulation", doc_format="pdf",
        source="邯郸市人民政府",
        description="邯郸市供热管理地方性法规。",
    ),

    # ================================================================
    #  华北：山西（省级·2026全新！+太原）
    # ================================================================
    DirectDoc(
        url="http://www.sxpc.gov.cn/zyfb/zxfg/art/2026/art_5fb6ec6e02f94147905d87d4611a5c02.html",
        title="山西省供热管理条例（2026年4月14日通过，7月1日施行）★最新",
        category="regulation", doc_format="html",
        source="山西省人大常委会",
        description="省级全新条例！2026.4.14通过，2026.7.1施行。全文55条，含智慧供热、投诉机制。",
    ),
    DirectDoc(
        url="http://www.sxpc.gov.cn/zyfb/gg/art/2026/art_8bacf1ca46e8454c8438e79d59515b92.html",
        title="山西省人大常委会公告（第六十八号）——供热管理条例通过",
        category="regulation", doc_format="html",
        source="山西省人大常委会",
        description="2026.4.15发布公告。",
    ),
    DirectDoc(
        url="https://down.waizi.org.cn/fagui/9728.html",
        title="太原市城市供热管理条例（全文+PDF下载）",
        category="regulation", doc_format="html",
        source="数字资源网",
        description="采暖期11.1-3.31，室温18±2℃。",
    ),

    # ================================================================
    #  华北：内蒙古（呼和浩特）
    # ================================================================
    DirectDoc(
        url="http://zfcxjsj.huhhot.gov.cn/ztzl_91/yfxz/flfg/202410/t20241009_1784624.html",
        title="呼和浩特市城市供热管理条例（2023年版全文）",
        category="regulation", doc_format="html",
        source="呼和浩特市住建局",
        description="2023年修订版，含2023年修正内容。",
    ),

    # ================================================================
    #  东北：辽宁（省级+沈阳+大连）
    # ================================================================
    DirectDoc(
        url="https://zjj.fuxin.gov.cn/szj/file/2023-05-15/16841145558374028e49287c1e8f951701881d0cc3bd5e71.pdf",
        title="辽宁省城市供热条例 PDF",
        category="regulation", doc_format="pdf",
        source="阜新市住建局",
        description="辽宁省供热基本法规。含温度标准、服务要求、违规处罚。",
    ),
    DirectDoc(
        url="https://www.syrd.gov.cn/flfg/dfxfg/202312/t20231212_4571550.html",
        title="沈阳市民用建筑供热用热管理条例（全文）",
        category="regulation", doc_format="html",
        source="沈阳市人大",
        description="2011年施行。沈阳市供热基本法规。",
    ),
    DirectDoc(
        url="http://www.changtu.gov.cn/changtu/ztzl21/ggqsydwxxgk/gr/gr/ctshrdyxgs/zdwj/2025012414042439176/index.html",
        title="辽宁省城市供热条例（昌图县全文公开）",
        category="regulation", doc_format="html",
        source="昌图县人民政府",
        description="2022修订版全文。室温≥18℃。",
    ),
    DirectDoc(
        url="https://www.shenyang.gov.cn/zmhd/zxft/202510/t20251030_4927452.html",
        title="沈阳供暖民生连线（2025.10.30）——不热咋办？收费？投诉？",
        category="service", doc_format="html",
        source="沈阳市人民政府",
        description="沈阳市房产部门+供热企业详细解答供暖温度、缴费、停供、投诉。",
    ),
    DirectDoc(
        url="https://m.dl.bendibao.com/weixin/csfw/?controller=home.Index&action=banshi&bid=72942",
        title="大连市供热用热条例（全文）",
        category="regulation", doc_format="html",
        source="大连本地宝/大连市人大",
        description="采暖期11.5-4.5。室温≥18℃（卧室/客厅），≥16℃（其他）。",
    ),

    # ================================================================
    #  东北：吉林（省级+长春+吉林市）
    # ================================================================
    DirectDoc(
        url="http://www.jlrd.gov.cn/jlsjk/202311/P020231102787950527509.pdf",
        title="吉林市城区供热管理条例 PDF",
        category="regulation", doc_format="pdf",
        source="吉林省人大",
        description="吉林市供热管理基本法规PDF。",
    ),
    DirectDoc(
        url="http://www.jlrd.gov.cn/jlsjk/202311/P020240807343313192976.pdf",
        title="长春市城市供热管理条例 PDF",
        category="regulation", doc_format="pdf",
        source="吉林省人大",
        description="长春市供热管理地方性法规。采暖期10.20-4.6，约168天。",
    ),

    # ================================================================
    #  东北：黑龙江（省级+哈尔滨）
    # ================================================================
    DirectDoc(
        url="https://www.hlj.gov.cn/hlj/c107858/202510/c00_31880041.shtml",
        title="哈尔滨市供热管理拟出新规（2025.10征求意见稿）",
        category="regulation", doc_format="html",
        source="黑龙江省人民政府",
        description="2025.10.15发布征求意见。采暖期10.20-4.20，室温≥20℃（新标准）。",
    ),
    DirectDoc(
        url="https://www.harbin.gov.cn/haerbin/c104529/202009/c01_87866.shtml",
        title="哈尔滨市城市供热办法（全文）",
        category="regulation", doc_format="html",
        source="哈尔滨市人民政府",
        description="2011年发布，2017年修正。哈尔滨核心供热法规。",
    ),
    DirectDoc(
        url="https://www.hljyy.gov.cn/yy/15349/202403/c07_21172.shtml",
        title="黑龙江省城市供热条例（2021修正全文）",
        category="regulation", doc_format="html",
        source="友谊县住建局/黑龙江省人大",
        description="省级供热条例，2021年第四次修正。",
    ),

    # ================================================================
    #  华东：山东（省级+济南+聊城）
    # ================================================================
    DirectDoc(
        url="http://www.laiwu.gov.cn/gongkai/site_laiwuquqzfhcxjsjljnslwrqrlyxzrgsg/channel_jns_laiwuquqzfhcxjsjljnslwrqrlyxzrgsg_75d/doc_6832620369f50955ab80b20f.html",
        title="山东省供热条例（2025年修订版全文）",
        category="regulation", doc_format="html",
        source="济南市莱芜区/山东省人大",
        description="2025.3.20第三次修正。省级供热基本法规。",
    ),
    DirectDoc(
        url="http://www.jncq.gov.cn/gongkai/site_changqingquqzfcxjsjljnzqrdyxgse/channel_jn_changqingquqzfcxjsjljnzqrdyxgse_75d/doc_673fe376e9c8d9ceeec44314.html",
        title="济南市城市集中供热管理条例（全文）",
        category="regulation", doc_format="html",
        source="济南市长清区",
        description="采暖期11.15-3.15。室温≥18℃。",
    ),
    DirectDoc(
        url="http://renda.liaocheng.gov.cn/lfgz/dffg/2025-09-29/6333.html",
        title="聊城市供热条例（2025年11月1日施行）★新",
        category="regulation", doc_format="html",
        source="聊城市人大",
        description="2025.8.28通过，2025.11.1施行。含智慧供热、投诉争议处理。",
    ),

    # ================================================================
    #  华中：河南（许昌）
    # ================================================================
    DirectDoc(
        url="https://www.xuchang.gov.cn/openDetailDynamic.html?infoid=bbcfd115-9ee8-43cf-b216-e160bce70570",
        title="许昌市集中供热条例（2025年新通过）",
        category="regulation", doc_format="html",
        source="许昌市人民政府",
        description="2025.4.24通过，河南省人大批准。含智慧供热、投诉制度。",
    ),

    # ================================================================
    #  西北：陕西（西安）
    # ================================================================
    DirectDoc(
        url="https://www.china-xa.gov.cn/pages/detail/index.html?id=9589",
        title="西安市集中供热条例（2020修正全文）",
        category="regulation", doc_format="html",
        source="西安人大网",
        description="采暖期11.15-3.15。室温≥18℃。含集中供热联席会议制度。",
    ),
    DirectDoc(
        url="https://www.xa.gov.cn/gk/zcfg/szfbgtwj/1873990577175470081.html",
        title="西安市促进供热行业提质增效若干措施（2024.12）",
        category="regulation", doc_format="html",
        source="西安市人民政府",
        description="市政办发〔2024〕69号，含PDF附件。",
    ),

    # ================================================================
    #  西北：甘肃（兰州）
    # ================================================================
    DirectDoc(
        url="https://www.lanzhou.gov.cn/attach/0/65e5704467e543a9aadf338ac6a1b62c.pdf",
        title="兰州市供热用热条例实施办法（2024.4.1施行）PDF",
        category="regulation", doc_format="pdf",
        source="兰州市人民政府",
        description="2023.12.22通过，2024.4.1施行。替代2005版。全文41条。",
    ),
    DirectDoc(
        url="http://www.lanzhourd.gov.cn/art/2024/12/18/art_14455_1420121.html",
        title="兰州市供热用热条例（2021修正全文）",
        category="regulation", doc_format="html",
        source="兰州市人大",
        description="兰州市供热基本法规，2021年修正。",
    ),

    # ================================================================
    #  西北：宁夏（省级+银川）
    # ================================================================
    DirectDoc(
        url="https://jst.nx.gov.cn/zwgk/zcwjk/flfg/202512/t20251223_5116781.html",
        title="宁夏回族自治区供热条例（2025修订，11.1施行）★最新",
        category="regulation", doc_format="html",
        source="宁夏住建厅",
        description="2025.9.29修订通过，2025.11.1施行。含智慧供热、采暖费计收。",
    ),
    DirectDoc(
        url="https://yc.bendibao.com/news/20241030/56506.shtm",
        title="银川市城市供热条例（2022.9.1施行全文）",
        category="regulation", doc_format="html",
        source="银川本地宝",
        description="银川市供热法规全文，2022年修订。",
    ),

    # ================================================================
    #  西北：新疆（乌鲁木齐）
    # ================================================================
    DirectDoc(
        url="https://www.uetd.gov.cn/jjjskfq/c119884/202312/351d7e4e76244e75a8850532e786ca0f.shtml",
        title="乌鲁木齐市城市热力管理条例（全文）",
        category="regulation", doc_format="html",
        source="乌鲁木齐经开区管委会",
        description="采暖期10.10-4.10。室温≥20℃（全国最高标准之一）。",
    ),
    DirectDoc(
        url="https://www.wlmq.gov.cn/wlmqs/c119242/202408/791c272b46d8454cad0a2af73e8ecbbf.shtml",
        title="乌鲁木齐供热公示信息（价格+服务承诺+投诉方式）",
        category="service", doc_format="html",
        source="乌鲁木齐市人民政府",
        description="居民22元/㎡,非居民31元/㎡。24小时服务热线。",
    ),

    # ================================================================
    #  便民服务/投诉指南
    # ================================================================
    DirectDoc(
        url="https://www.yantai.gov.cn/art/2025/11/9/art_69003_3152132.html",
        title="烟台市供热服务指南（报修+投诉电话+服务承诺）",
        category="service", doc_format="html",
        source="烟台市人民政府",
        description="片区报修电话、12345投诉热线、偷暖举报电话、维修流程。",
    ),
    DirectDoc(
        url="https://www.tj.gov.cn/sy/tjxw/202603/t20260329_7271587.html",
        title="天津市供热采暖收费新政解读（2026.3.29天津日报）",
        category="service", doc_format="html",
        source="天津政务网",
        description="多退少补原则、逾期违约金、计费面积等通俗解读。",
    ),

    # ================================================================
    #  铁岭
    # ================================================================
    DirectDoc(
        url="http://www.tieling.gov.cn/tieling/attachDir/2025/12/2025122610452841511.pdf",
        title="铁岭市城市供热管理办法 PDF",
        category="regulation", doc_format="pdf",
        source="铁岭市人民政府",
        description="铁岭市供热管理政府规章。",
    ),

    # ================================================================
    #  住建部政策文件库
    # ================================================================
    DirectDoc(
        url="https://www.mohurd.gov.cn/gongkai/zc/wjk/index.html",
        title="住建部政策文件列表（可检索供热相关标准公告）",
        category="notice", doc_format="html",
        source="住房和城乡建设部",
        description="住建部全部政策文件，可查供热标准发布公告。",
    ),
]


def get_docs_by_category(category: str) -> List[DirectDoc]:
    return [d for d in DIRECT_DOCS if d.category == category]


def get_pdf_docs() -> List[DirectDoc]:
    return [d for d in DIRECT_DOCS if d.doc_format == "pdf"]
