#!/usr/bin/env python3
"""Live SEO/content repair for https://rukn-eltatawer.com/bh/"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://rukn-eltatawer.com/bh"
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
PHONE = "+971586634710"
WA = "971586634710"
IMG = "https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp"
CONTACT = "https://rukn-eltatawer.com/bh/index.php/contact-us/"
CAT = "https://rukn-eltatawer.com/bh/index.php/category/"
SITE = "https://rukn-eltatawer.com/bh/index.php/"

CAT_MAP = [
    (10, ("كشف", "تسرب")),
    (12, ("عزل",)),
    (16, ("سباك", "مجاري", "تسليك", "أدوات صحية", "صحي")),
    (18, ("تكييف", "مكيف", "فريون", "كهرباء", "إنارة")),
    (20, ("تنظيف", "تعقيم")),
    (22, ("حشرات", "صراصير", "قوارض", "مكافحة")),
    (24, ("حديق", "مسابح", "مسبح", "عشب", "نافورة")),
    (26, ("صبغ", "ديكور", "جبس", "دهان")),
    (14, ("صيانة", "ترميم", "إنشاء")),
]


def auth_header() -> str:
    return "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


def req(method: str, route: str, payload=None, timeout=120):
    url = f"{BASE}/?rest_route={route}"
    data = None
    headers = {
        "Authorization": auth_header(),
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 RuknBH-SEO/1.0",
    }
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body[:800]}
        return exc.code, parsed


def cli(command: str, write: bool = True, timeout: int = 120):
    return req(
        "POST",
        "/wpvibe/v1/cli/run",
        {"command": command, "confirm_write": write},
        timeout=timeout,
    )


def content_edit(post_id: int, field: str, old: str, new: str):
    return req(
        "POST",
        "/wpvibe/v1/content/edit",
        {
            "target_type": "post",
            "post_id": post_id,
            "field": field,
            "old_content": old,
            "new_content": new,
            "replace_all": True,
        },
    )


def fix_html(html: str) -> str:
    html = html.replace("{PHONE_RUKN_BAHRAIN}", PHONE)
    html = html.replace("{WHATSAPP_RUKN_BAHRAIN}", WA)
    html = html.replace("[[رقم الهاتف/واتساب]]", PHONE)
    html = html.replace("[[عدد المشاريع]]", "+350")
    html = html.replace("[[سنة التأسيس]]", "2024")
    html = html.replace("كل مدن المملكة", "كل مدن البحرين")
    html = html.replace("مدن المملكة", "مدن البحرين")
    html = html.replace("داخل المملكة", "داخل مملكة البحرين")
    html = html.replace("يغطي المملكة", "يغطي مملكة البحرين")
    html = re.sub(r'src="service-\d+\.webp"', f'src="{IMG}"', html)
    html = re.sub(r"<h1(\s[^>]*)?>", r"<h2\1>", html, flags=re.I)
    html = re.sub(r"</h1>", "</h2>", html, flags=re.I)
    return html


def category_for(title: str) -> int:
    for term_id, keys in CAT_MAP:
        if any(k in title for k in keys):
            return term_id
    return 14


def excerpt_for(title: str) -> str:
    return (
        f"{title} مع ركن التطور في مملكة البحرين: تشخيص قبل الإصلاح، "
        f"تقرير مصوّر، وعرض سعر مكتوب. نغطي المنامة والمحرق والرفاع "
        f"وكل مدن البحرين. اتصال أو واتساب {PHONE}."
    )


def patch_homeintro() -> None:
    patches = [
        (
            "slider_intro_v1 title",
            "option patch update HomeIntro slider_intro_v1 title "
            "'ركن التطور البحرين — {%الخدمات المنزلية المتكاملة%} في كل مدن البحرين'",
        ),
        (
            "sub_text",
            "option patch update HomeIntro slider_intro_v1 sub_text "
            "'من كشف تسربات المياه بدون تكسير وعزل الأسطح، إلى الصيانة العامة والتكييف والتنظيف ومكافحة الحشرات وتنسيق الحدائق والمسابح — فريق مقيم في البحرين يغطي مملكة البحرين، بتشخيص قبل الإصلاح وعرض سعر مكتوب.'",
        ),
        (
            "quote_url",
            f"option patch update HomeIntro slider_intro_v1 quote_button_url '{CONTACT}'",
        ),
    ]
    urls = [
        (0, f"{CAT}water-leak-detection/"),
        (1, f"{CAT}roof-insulation/"),
        (2, f"{CAT}ac-electrical/"),
        (3, f"{CAT}cleaning/"),
        (4, f"{CAT}pest-control/"),
        (5, f"{CAT}plumbing/"),
    ]
    for i, url in urls:
        patches.append(
            (
                f"dash {i}",
                f"option patch update HomeIntro slider_intro_v1 dash_services {i} url '{url}'",
            )
        )
    for label, cmd in patches:
        code, out = cli(cmd)
        print(f"HomeIntro {label}: {code} {str(out.get('stdout') or out.get('message') or out)[:160]}")


def patch_rankmath() -> None:
    cmds = [
        "option patch update rank-math-options-titles homepage_description "
        "'خدمات منزلية متكاملة في مملكة البحرين: كشف تسربات بدون تكسير، عزل الأسطح، صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات في المنامة والمحرق والرفاع وكل مدن البحرين. اتصال +971586634710'",
        "option patch update rank-math-options-titles breadcrumbs_home_label 'الرئيسية'",
        "option patch update rank-math-options-titles knowledgegraph_name 'ركن التطور - البحرين'",
        "option patch update rank-math-options-titles website_name 'ركن التطور - البحرين'",
        "option patch update rank-math-options-titles local_business_type 'GeneralContractor'",
        "option patch update rank-math-options-titles title_post '%title% %sep% ركن التطور البحرين'",
        "option patch update rank-math-options-titles pt_post_default_rich_snippet 'article'",
        "option patch update rank-math-options-sitemap html_sitemap on",
        "option update timezone_string Asia/Bahrain",
        "option update default_comment_status closed",
        "option update default_ping_status closed",
        "option update blogdescription 'ركن التطور البحرين: كشف تسربات بدون تكسير، عزل الأسطح، صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات في المنامة والمحرق والرفاع وكل مدن البحرين.'",
    ]
    for cmd in cmds:
        code, out = cli(cmd)
        print(f"RM {code}: {str(out.get('stdout') or out.get('stderr') or out.get('message') or '')[:180]}")


def update_snippet() -> None:
    snippet = open(
        os.path.join(os.path.dirname(__file__), "bh-indexing-mu-snippet.php"),
        encoding="utf-8",
    ).read()
    body = snippet.replace("<?php", "", 1).strip()
    # strip the ABSPATH guard; WPCode already runs inside WP
    body = body.replace("if ( ! defined( 'ABSPATH' ) ) {\n\treturn;\n}", "", 1).strip()
    code, out = req(
        "POST",
        "/wpvibe/v1/code-snippet",
        {
            "action": "update",
            "id": 3257,
            "title": "Bahrain SEO Indexing Fix",
            "code": body,
            "code_type": "php",
            "location": "everywhere",
            "insert_method": "auto",
        },
    )
    print("snippet", code, str(out)[:240])


def page_html_contact_ar() -> str:
    return f"""
<h2>تواصل مع ركن التطور في البحرين</h2>
<p>نصل إليك للمعاينة في المنامة والمحرق والرفاع ومدينة حمد ومدينة عيسى وعالي وسترة وجدحفص والبديع وسار وتوبلي والحد. لا تسعير عبر الهاتف: الفني يعاين الموقع ثم تستلم عرض سعر مكتوباً.</p>
<p><strong>الهاتف:</strong> <a href="tel:{PHONE}">{PHONE}</a><br>
<strong>واتساب:</strong> <a href="https://wa.me/{WA}" rel="noopener">راسلنا مباشرة</a></p>
<h3>متى تتصل؟</h3>
<ul>
<li>بقع رطوبة أو ارتفاع مفاجئ في فاتورة المياه — نكشف التسرب بدون تكسير.</li>
<li>حرارة سطح أو تسرب بعد موجة رطوبة بحرينية — نراجع العزل قبل موسم الصيف.</li>
<li>ضعف تبريد أو صوت المكيف — الصيف في البحرين لا يحتمل تأخيراً.</li>
<li>انسداد مجاري أو تسرب أدوات صحية في الفلل والشقق.</li>
</ul>
<h3>ماذا يحدث بعد الرسالة؟</h3>
<ol>
<li>نؤكد المدينة ونوع الخدمة.</li>
<li>نحدد موعد معاينة.</li>
<li>تستلم تقريراً مصوراً وعرض سعر قبل أي تنفيذ.</li>
</ol>
<p>لخصوصية بياناتك راجع <a href="{SITE}privacy-policy/">سياسة الخصوصية</a>.</p>
"""


def page_html_about_ar() -> str:
    return f"""
<h2>من نحن — ركن التطور في مملكة البحرين</h2>
<p>ركن التطور شركة خدمات منزلية متكاملة تعمل داخل البحرين بفريق يصل إلى العاصمة المنامة والجزر والمدن السكنية. لسنا نسخة من موقع دولة أخرى: المحتوى والمدن وطبيعة العمل هنا مبنية على مناخ البحرين (رطوبة عالية، ملوحة هواء ساحلي، وأحمال تكييف صيفية طويلة).</p>
<h3>لماذا يهم التشخيص قبل الإصلاح؟</h3>
<p>كثير من تسربات المنامة والمحرق تبدأ من تمديدات قديمة أو عزل سطح تآكل بسبب الرطوبة، لا من «كسر بلاط عشوائي». نبدأ بالكاميرا الحرارية والأجهزة، ثم التقرير، ثم السعر.</p>
<h3>الخدمات</h3>
<ul>
<li><a href="{CAT}water-leak-detection/">كشف تسربات المياه</a></li>
<li><a href="{CAT}roof-insulation/">عزل الأسطح</a></li>
<li><a href="{CAT}general-maintenance/">الصيانة العامة</a></li>
<li><a href="{CAT}plumbing/">السباكة وتسليك المجاري</a></li>
<li><a href="{CAT}ac-electrical/">التكييف والكهرباء</a></li>
<li><a href="{CAT}cleaning/">التنظيف والتعقيم</a></li>
<li><a href="{CAT}pest-control/">مكافحة الحشرات</a></li>
<li><a href="{CAT}gardens-pools/">الحدائق والمسابح</a></li>
<li><a href="{CAT}painting-decor/">الصبغ والديكورات</a></li>
</ul>
<p>للتواصل: <a href="{CONTACT}">صفحة الاتصال</a> أو {PHONE}.</p>
"""


def page_html_privacy_ar() -> str:
    return f"""
<h2>سياسة الخصوصية — ركن التطور البحرين</h2>
<p>نجمع اسمك ورقم هاتفك ومدينتك ووصف المشكلة فقط للرد على طلب المعاينة. لا نبيع البيانات ولا نشاركها مع أطراف تسويقية.</p>
<h3>ما الذي نحتفظ به؟</h3>
<ul>
<li>بيانات التواصل التي ترسلها عبر النموذج أو واتساب.</li>
<li>عنوان تقريبي للموقع عند جدولة الزيارة.</li>
</ul>
<h3>حقوقك</h3>
<p>يمكنك طلب حذف بياناتك عبر {PHONE}. تُستخدم البيانات لتنفيذ الخدمة والضمان فقط.</p>
"""


def page_html_services_ar() -> str:
    return f"""
<h2>خدمات ركن التطور في البحرين</h2>
<p>صفحة الخدمات هذه هي المركز العربي لكل فئة. اختر الخدمة ثم مدينتك من المقالات المرتبطة. كل مقال مكتوب لمدينة بحرينية محددة حتى لا تختلط النتائج مع السعودية أو الإمارات.</p>
<ul>
<li><a href="{CAT}water-leak-detection/">كشف تسربات المياه بدون تكسير</a> — مهم مع الرطوبة وارتفاع فواتير المياه.</li>
<li><a href="{CAT}roof-insulation/">عزل الأسطح والخزانات</a> — حماية من الحرارة الصيفية والتسرب.</li>
<li><a href="{CAT}general-maintenance/">الصيانة العامة للمباني</a></li>
<li><a href="{CAT}plumbing/">السباكة وتسليك المجاري</a></li>
<li><a href="{CAT}ac-electrical/">التكييف والكهرباء</a> — صيانة قبل ذروة الصيف.</li>
<li><a href="{CAT}cleaning/">التنظيف والتعقيم</a></li>
<li><a href="{CAT}pest-control/">مكافحة الحشرات والقوارض</a> — شائع في المناطق الساحلية والحدائق.</li>
<li><a href="{CAT}gardens-pools/">تنسيق الحدائق وصيانة المسابح</a></li>
<li><a href="{CAT}painting-decor/">الصبغ والديكورات والجبس</a></li>
</ul>
<p><a href="{CONTACT}">اطلب معاينة</a> — {PHONE}</p>
"""


def page_html_cities_ar() -> str:
    cities = [
        ("المنامة", "عاصمة البحرين ومقر كثير من العمائر والشقق الساحلية."),
        ("المحرق", "جزيرة بكثافة سكنية وتمديدات تحتاج فحص تسرب دوري."),
        ("الرفاع", "فلل ومساحات أكبر: عزل أسطح ومسابح وصيانة دورية."),
        ("مدينة حمد", "أحياء سكنية هادئة بطلب مرتفع على التكييف والتنظيف."),
        ("مدينة عيسى", "موقع متوسط يسهل جدولة المعاينات السريعة."),
        ("عالي", "فلل وحدائق: سباكة ومكافحة حشرات وتنسيق خارجي."),
        ("سترة", "منطقة صناعية وسكنية بجانب الساحل."),
        ("جدحفص", "بيوت قديمة تستفيد من كشف التسرب بدون تكسير."),
        ("البديع", "الساحل الغربي: رطوبة وعزل وأحمال تكييف."),
        ("سار", "فلل حديثة ومساحات خارجية."),
        ("توبلي", "قرب الخليج: رطوبة ومجاري تحتاج صيانة."),
        ("الحد", "المحرق الشرقية: صيانة وتكييف وتنظيف."),
    ]
    items = "".join(f"<li><strong>{n}</strong> — {d}</li>" for n, d in cities)
    return f"""
<h2>مدن نغطيها في مملكة البحرين</h2>
<p>ركن التطور يغطي 12 مدينة. المقالات مرتبطة باسم المدينة حتى تظهر في البحث العربي لمستخدمي البحرين لا دول الخليج الأخرى.</p>
<ul>{items}</ul>
<p>اختر خدمتك من <a href="{SITE}services/">دليل الخدمات</a> أو <a href="{CONTACT}">تواصل معنا</a>.</p>
"""


def page_html_en_home() -> str:
    return f"""
<h2>Rukn Al Tatawor in the Kingdom of Bahrain</h2>
<p>Home services for Manama, Muharraq, Riffa, Hamad Town, Isa Town, A'ali, Sitra, Jidhafs, Budaiya, Saar, Tubli and Hidd. This English hub is written for Bahrain — humidity, coastal air, and long AC seasons — not copied from another GCC country site.</p>
<h3>What we do</h3>
<ul>
<li>Non-destructive water leak detection with a photo report before any breaking.</li>
<li>Roof and tank waterproofing before the summer heat load.</li>
<li>AC, electrical, plumbing, cleaning, pest control, gardens, pools, painting and gypsum.</li>
</ul>
<h3>How a visit works</h3>
<p>Call or WhatsApp {PHONE}. A technician inspects on site, then you receive a written quote. We do not price serious leaks or insulation over the phone.</p>
<p><a href="{SITE}contact-us-en/">Contact us in English</a> · <a href="{CONTACT}">Arabic contact</a></p>
"""


def page_html_en_services() -> str:
    return f"""
<h2>Home services in Bahrain</h2>
<p>Use this English services index, then open the Arabic city articles if you need a specific neighbourhood. Each Arabic article is unique to one Bahraini city so Google can rank it locally.</p>
<ul>
<li>Water leak detection without demolition</li>
<li>Roof and tank insulation for humid summers</li>
<li>General building maintenance</li>
<li>Plumbing and drain clearing</li>
<li>Air conditioning and electrics</li>
<li>Deep cleaning and sanitising</li>
<li>Licensed pest control</li>
<li>Gardens and swimming pools</li>
<li>Painting, gypsum and interiors</li>
</ul>
<p>Book an inspection: {PHONE} or <a href="{SITE}contact-us-en/">English contact page</a>.</p>
"""


def page_html_en_cities() -> str:
    return f"""
<h2>Cities we cover in Bahrain</h2>
<p>Manama (capital and coastal towers), Muharraq (dense island housing), Riffa (villas and larger roofs), Hamad Town, Isa Town, A'ali, Sitra, Jidhafs, Budaiya, Saar, Tubli and Hidd. Response time is confirmed when you message us — Bahrain is compact, but traffic around the causeways still matters for same-day visits.</p>
<p><a href="{SITE}home-services-bahrain/">English home</a> · <a href="{SITE}cities/">Arabic cities</a></p>
"""


def page_html_en_contact() -> str:
    return f"""
<h2>Contact Rukn Al Tatawor — Bahrain</h2>
<p>Phone / WhatsApp: <a href="tel:{PHONE}">{PHONE}</a> · <a href="https://wa.me/{WA}">WhatsApp</a></p>
<p>Tell us your city in Bahrain, the service, and a short description. We schedule an inspection, then send a written quote. We serve residents and facility managers in Manama, Muharraq, Riffa and the towns listed on our cities page.</p>
<p>Arabic contact page: <a href="{CONTACT}">تواصل معنا</a></p>
"""


def page_html_en_about() -> str:
    return f"""
<h2>About Rukn Al Tatawor in Bahrain</h2>
<p>We provide multi-trade home services inside the Kingdom of Bahrain. The Arabic site holds city-level guides; this English page explains the same operating model for residents who search in English.</p>
<p>Bahrain’s climate (high humidity, salt air, long cooling season) changes how leaks, insulation and AC should be diagnosed. That is why we refuse copy-paste “Kingdom” wording from other country sites and name Bahraini cities explicitly.</p>
<p>Call {PHONE} or open <a href="{SITE}contact-us-en/">the English contact page</a>.</p>
"""


def create_page(title: str, slug: str, html: str, excerpt: str) -> int | None:
    b64 = base64.b64encode(html.encode()).decode()
    cmd = (
        f"post create --post_type=page --post_status=publish --post_title={json.dumps(title)} "
        f"--post_name={slug} --post_content_base64={b64} --porcelain"
    )
    code, out = cli(cmd, timeout=180)
    print(f"page {slug}: {code} {str(out.get('stdout') or out.get('stderr') or out)[:220]}")
    stdout = out.get("stdout") if isinstance(out, dict) else ""
    pid = None
    if isinstance(stdout, dict):
        pid = stdout.get("ID") or stdout.get("id") or stdout.get("post_id")
    if not pid and isinstance(stdout, str):
        m = re.search(r"\d+", stdout)
        if m:
            pid = int(m.group(0))
        else:
            try:
                parsed = json.loads(stdout)
                pid = parsed.get("ID") or parsed.get("id")
            except Exception:
                pid = None
    if pid:
        content_edit(int(pid), "post_excerpt", "", excerpt)
        req(
            "POST",
            f"/wp/v2/pages/{int(pid)}",
            {
                "excerpt": excerpt,
                "slug": slug,
            },
        )
    return int(pid) if pid else None


def create_core_pages() -> dict[str, int]:
    specs = [
        ("تواصل معنا — ركن التطور البحرين", "contact-us", page_html_contact_ar(), "عنوان وواتساب ركن التطور في البحرين للمعاينة في كل مدن المملكة".replace("المملكة", "البحرين")),
        ("من نحن — ركن التطور البحرين", "about-us", page_html_about_ar(), "تعرف على ركن التطور في مملكة البحرين وخدماتنا المنزلية المتكاملة."),
        ("سياسة الخصوصية — ركن التطور البحرين", "privacy-policy", page_html_privacy_ar(), "كيف نتعامل مع بيانات طلبات المعاينة في البحرين."),
        ("خدمات ركن التطور في البحرين", "services", page_html_services_ar(), "دليل خدمات كشف التسربات والعزل والصيانة والتكييف في البحرين."),
        ("مدن البحرين التي نغطيها", "cities", page_html_cities_ar(), "المنامة والمحرق والرفاع و10 مدن أخرى يغطيها ركن التطور."),
        ("Rukn Al Tatawor Bahrain — Home Services", "home-services-bahrain", page_html_en_home(), "English hub for home services in the Kingdom of Bahrain."),
        ("Home services in Bahrain", "services-en", page_html_en_services(), "English index of leak detection, insulation, AC and maintenance in Bahrain."),
        ("Cities we cover in Bahrain", "cities-en", page_html_en_cities(), "Manama, Muharraq, Riffa and towns served by Rukn Al Tatawor."),
        ("Contact us — Bahrain", "contact-us-en", page_html_en_contact(), "English contact for inspections in Bahrain. WhatsApp " + PHONE),
        ("About Rukn Al Tatawor in Bahrain", "about-us-en", page_html_en_about(), "Who we are and why Bahrain content is written for Bahrain."),
    ]
    created = {}
    for title, slug, html, excerpt in specs:
        pid = create_page(title, slug, html, excerpt)
        if pid:
            created[slug] = pid
    return created


def build_html_sitemap(posts: list[dict]) -> None:
    groups: dict[int, list[tuple[str, str]]] = {}
    for p in posts:
        title = p.get("title") or ""
        slug = p.get("slug") or ""
        if not slug:
            continue
        cat = category_for(title)
        groups.setdefault(cat, []).append((title, slug))
    names = {
        10: "كشف تسربات المياه",
        12: "عزل الأسطح",
        14: "الصيانة العامة",
        16: "السباكة وتسليك المجاري",
        18: "التكييف والكهرباء",
        20: "التنظيف والتعقيم",
        22: "مكافحة الحشرات",
        24: "الحدائق والمسابح",
        26: "الصبغ والديكورات",
    }
    parts = [
        "<h2>خريطة موقع ركن التطور البحرين</h2>",
        "<p>روابط المقالات الجاهزة للفهرسة. استخدم هذه الصفحة إذا لم تُفتح الروابط المختصرة بعد.</p>",
        f'<p><a href="{SITE}services/">الخدمات</a> · <a href="{SITE}cities/">المدن</a> · <a href="{CONTACT}">تواصل</a> · <a href="{SITE}home-services-bahrain/">English</a></p>',
    ]
    for cat, items in sorted(groups.items()):
        parts.append(f"<h3>{names.get(cat, 'خدمات')}</h3><ul>")
        for title, slug in sorted(items, key=lambda x: x[0])[:400]:
            parts.append(f'<li><a href="{SITE}{slug}/">{title}</a></li>')
        parts.append("</ul>")
    html = "\n".join(parts)
    create_page(
        "خريطة الموقع — ركن التطور البحرين",
        "html-sitemap",
        html,
        "خريطة روابط مقالات ركن التطور في البحرين للفهرسة.",
    )


def fetch_all_posts() -> list[dict]:
    posts = []
    page = 1
    while page <= 30:
        code, data = req(
            "GET",
            f"/wp/v2/posts&per_page=100&page={page}&context=edit&status=publish&_fields=id,title,content,excerpt,slug,categories,link",
            timeout=120,
        )
        if code != 200 or not isinstance(data, list) or not data:
            print("list page", page, code, type(data).__name__)
            break
        posts.extend(data)
        print(f"fetched page {page}: {len(data)} (total {len(posts)})")
        if len(data) < 100:
            break
        page += 1
    return posts


def update_one_post(post: dict) -> tuple[int, str]:
    pid = post["id"]
    title = post.get("title", {})
    title_raw = title.get("raw") if isinstance(title, dict) else str(title)
    content = post.get("content", {})
    raw = content.get("raw") if isinstance(content, dict) else ""
    if not raw:
        return pid, "empty"
    fixed = fix_html(raw)
    cat = category_for(title_raw)
    excerpt = excerpt_for(title_raw)
    payload = {
        "content": fixed,
        "excerpt": excerpt,
        "categories": [cat],
    }
    # only send if changed or still uncategorized
    if fixed == raw and post.get("categories") == [cat]:
        return pid, "skip"
    code, out = req("POST", f"/wp/v2/posts/{pid}", payload, timeout=90)
    if code in (200, 201):
        return pid, "ok"
    return pid, f"err{code}:{str(out)[:80]}"


def bulk_fix_posts() -> list[dict]:
    posts = fetch_all_posts()
    print("posts to process", len(posts))
    ok = skip = err = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(update_one_post, p) for p in posts]
        for i, fut in enumerate(as_completed(futs), 1):
            pid, status = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                err += 1
                print("fail", pid, status)
            if i % 100 == 0:
                print(f"progress {i}/{len(posts)} ok={ok} skip={skip} err={err}")
    print(f"bulk done ok={ok} skip={skip} err={err}")
    return posts


def create_menu(created: dict[str, int]) -> None:
    code, out = cli("menu create 'القائمة الرئيسية' --porcelain")
    print("menu create", code, out.get("stdout") or out.get("stderr"))
    items = [
        ("الرئيسية", f"{BASE}/"),
        ("خدماتنا", f"{SITE}services/"),
        ("المدن", f"{SITE}cities/"),
        ("من نحن", f"{SITE}about-us/"),
        ("تواصل معنا", CONTACT),
        ("English", f"{SITE}home-services-bahrain/"),
        ("خريطة الموقع", f"{SITE}html-sitemap/"),
    ]
    for title, url in items:
        code, out = cli(
            f"menu item add-custom 'القائمة الرئيسية' '{title}' '{url}'"
        )
        print("menu item", title, code, str(out.get("stdout") or out.get("stderr") or "")[:120])
    for loc in ("primary", "menu-1", "main", "header", "primary_menu"):
        code, out = cli(f"menu location assign 'القائمة الرئيسية' {loc}")
        print("assign", loc, code, str(out.get("stdout") or out.get("stderr") or "")[:120])


def ping_indexnow(urls: list[str]) -> None:
    key = "7f4be9622f554c1ca60e6d1a16517dcd"
    payload = {
        "host": "rukn-eltatawer.com",
        "key": key,
        "keyLocation": f"{BASE}/index.php/{key}.txt",
        "urlList": urls[:10],
    }
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            print("indexnow", resp.status, resp.read()[:200])
    except urllib.error.HTTPError as exc:
        print("indexnow", exc.code, exc.read()[:300])
    except Exception as exc:
        print("indexnow err", exc)


def purge() -> None:
    code, out = cli("cache purge")
    print("purge", code, str(out.get("stdout") or out.get("stderr") or "")[:200])


def main() -> int:
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1
    print("=== snippet ===")
    update_snippet()
    print("=== homeintro ===")
    patch_homeintro()
    print("=== rankmath ===")
    patch_rankmath()
    print("=== pages ===")
    created = create_core_pages()
    print("created", created)
    print("=== posts ===")
    posts = bulk_fix_posts()
    slim = []
    for p in posts:
        title = p.get("title", {})
        slim.append(
            {
                "title": title.get("raw") if isinstance(title, dict) else str(title),
                "slug": p.get("slug"),
            }
        )
    print("=== html sitemap ===")
    build_html_sitemap(slim)
    print("=== menu ===")
    create_menu(created)
    print("=== ping ===")
    ping_indexnow(
        [
            f"{BASE}/",
            f"{BASE}/index.php/sitemap_index.xml",
            CONTACT,
            f"{SITE}services/",
            f"{SITE}cities/",
            f"{SITE}home-services-bahrain/",
            f"{SITE}html-sitemap/",
            f"{BASE}/index.php/post-sitemap1.xml",
        ]
    )
    print("=== purge ===")
    purge()
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
