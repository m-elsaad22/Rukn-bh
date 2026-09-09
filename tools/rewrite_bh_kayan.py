#!/usr/bin/env python3
"""Rewrite Bahrain posts with unique KAYAN-theme copy, shortcodes, and template meta."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rewrite_bh_articles import (  # noqa: E402
    AREA_NOTES,
    CITIES,
    PACKS,
    angle_for,
    area_tour,
    parse_title,
    pick,
    seed,
    visible_text,
    word_list,
)

BASE = "https://rukn-eltatawer.com/bh"
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
WA = "971586634710"
IMG = "https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp"
PRIMARY = "#076bb5"
ACCENT = "#2c86fd"
NAVY = "#0A1F4E"

CITY_SLUG = {
    "المنامة": "manama",
    "المحرق": "muharraq",
    "الرفاع": "riffa",
    "مدينة حمد": "hamad-town",
    "مدينة عيسى": "isa-town",
    "عالي": "aali",
    "سترة": "sitra",
    "البديع": "budaiya",
}

ICONS = {
    "leak": "fa-droplet",
    "insul": "fa-layer-group",
    "ac": "fa-snowflake",
    "clean": "fa-broom",
    "pest": "fa-bug",
    "plumb": "fa-wrench",
    "elec": "fa-bolt",
    "paint": "fa-paint-roller",
    "garden": "fa-tree",
    "pool": "fa-water",
    "move": "fa-truck",
    "solar": "fa-solar-panel",
    "build": "fa-hammer",
    "maint": "fa-clipboard-check",
    "gen": "fa-house-chimney",
}

LEN_TARGET = {"long": 2100, "mid": 1750, "std": 1450}
STRING_META = (
    "whatsapp_number",
    "hide__card__callbutton",
    "hide__service__callbutton",
    "hide__floating__call",
    "whatsapp_chat_mode",
    "floating_whatsapp_chat_mode",
    "last_update",
    "rank_math_title",
    "rank_math_description",
    "rank_math_focus_keyword",
)


def auth() -> str:
    return "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


def req(method: str, route: str, payload=None, timeout=120):
    url = f"{BASE}/?rest_route={route}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    headers = {
        "Authorization": auth(),
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 RuknBH-Kayan/1.0",
    }
    if data:
        headers["Content-Type"] = "application/json; charset=utf-8"
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
            parsed = {"raw": body[:400]}
        return exc.code, parsed


def cli(cmd: str, write: bool = False, timeout: int = 90):
    payload = {"command": cmd}
    if write:
        payload["confirm_write"] = True
    return req("POST", "/wpvibe/v1/cli/run", payload, timeout=timeout)[1]


def scrub(text: str) -> str:
    return (text or "").replace("'", "’").replace("\r", " ").replace("\n", " ").strip()


def php_serialize(obj) -> str:
    if obj is None:
        return "N;"
    if isinstance(obj, bool):
        return "b:1;" if obj else "b:0;"
    if isinstance(obj, int) and not isinstance(obj, bool):
        return f"i:{obj};"
    if isinstance(obj, str):
        s = scrub(obj)
        b = s.encode("utf-8")
        return 's:%d:"%s";' % (len(b), s)
    if isinstance(obj, list):
        inner = "".join(php_serialize(i) + php_serialize(v) for i, v in enumerate(obj))
        return "a:%d:{%s}" % (len(obj), inner)
    if isinstance(obj, dict):
        inner = "".join(php_serialize(k) + php_serialize(v) for k, v in obj.items())
        return "a:%d:{%s}" % (len(obj), inner)
    raise TypeError(type(obj))


def set_meta(pid: int, key: str, value) -> bool:
    if isinstance(value, (dict, list)):
        raw = php_serialize(value)
        cmd = f"post meta update {pid} {key} '{raw}' --force"
    else:
        val = json.dumps(scrub(str(value)), ensure_ascii=False)
        cmd = f"post meta update {pid} {key} {val} --force"
    out = cli(cmd, write=True)
    ok = isinstance(out, dict) and out.get("exit_code") == 0
    return ok


def kw_hits(text: str, full: str, kw: str) -> int:
    return text.count(full) + text.count(kw)


def style_block() -> str:
    return (
        "<style>"
        ".kayan-article .responsive-table{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:18px 0}"
        ".kayan-article table{width:100%;border-collapse:collapse;min-width:280px}"
        f".kayan-article th{{background:{PRIMARY};color:#fff;padding:10px;font-size:15px}}"
        ".kayan-article td{border:1px solid #d7e4f2;padding:10px;font-size:15px}"
        ".kayan-article tr:nth-child(even) td{background:#f5f9fd}"
        f".kayan-tip{{background:#eef6fc;border-right:5px solid {PRIMARY};padding:14px 16px;border-radius:12px;margin:18px 0}}"
        ".kayan-warn{background:#fff7ea;border-right:5px solid #d97706;padding:14px 16px;border-radius:12px;margin:18px 0}"
        f".kayan-hero{{background:linear-gradient(135deg,{NAVY},{PRIMARY});color:#fff;padding:22px 18px;border-radius:16px;margin:18px 0}}"
        ".kayan-hero a{display:inline-block;background:#25D366;color:#fff;padding:12px 18px;border-radius:10px;font-weight:700;text-decoration:none;margin-top:10px}"
        ".kayan-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:18px 0}"
        ".kayan-card{background:#fff;border:1px solid #d7e4f2;border-radius:14px;padding:14px}"
        f".kayan-card i{{color:{ACCENT};font-size:22px}}"
        ".kayan-steps{display:grid;gap:10px;margin:18px 0}"
        f".kayan-step{{display:flex;gap:12px;background:#fff;border:1px solid #d7e4f2;border-radius:14px;padding:12px}}"
        f".kayan-num{{min-width:42px;height:42px;border-radius:50%;background:{PRIMARY};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}}"
        ".kayan-snippet{background:#eef6fc;border:1px solid #d7e4f2;border-right:5px solid "
        f"{PRIMARY};padding:14px 16px;border-radius:12px;margin:18px 0;line-height:1.85}}"
        ".kayan-article .yc-shortcode--single-features-item{min-width:0!important;flex:1 1 240px;"
        "padding:16px!important;flex-direction:column;align-items:flex-start}"
        ".kayan-article .yc-shortcode-features--icon{margin-inline-end:0!important;margin-bottom:8px;font-size:28px}"
        ".kayan-article .-FaqsSimple-vsingle-Content-Row-v1{display:block!important;max-height:none!important;opacity:1!important}"
        ".kayan-article .yc-shortcode--box{margin:22px 0}"
        "@media(max-width:640px){.kayan-article table{font-size:14px}.kayan-hero{padding:16px}"
        ".kayan-article .yc-shortcode--single-features-item{min-width:100%!important;margin:8px 0!important}"
        ".kayan-article .yc-shortcode--features--items{margin:0!important;display:block}}"
        "</style>"
    )


def table(headers, rows) -> str:
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = []
    for row in rows:
        trs.append("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    return f'<div class="responsive-table"><table><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'


def tip(title: str, body: str) -> str:
    return f'<blockquote class="kayan-tip"><i class="fas fa-lightbulb"></i> <strong>{title}:</strong> {body}</blockquote>'


def warn(body: str) -> str:
    return f'<blockquote class="kayan-warn"><i class="fas fa-exclamation-triangle"></i> <strong>تنبيه:</strong> {body}</blockquote>'


def kayan_features(title: str, desc: str, items: list, icon: str) -> str:
    cards = []
    for it in items:
        cards.append(
            '<div class="yc-shortcode--single-features-item">'
            f'<div class="yc-shortcode-features--icon"><i class="fas {icon}"></i></div>'
            '<div class="yc-shortcode--step--info">'
            f"<h3>{it['title']}</h3><p>{it['content']}</p></div></div>"
        )
    return (
        f'<div class="yc-shortcode--box yc-shortcode--features"><h2 class="--short--code--title">{title}</h2>'
        f'<p class="--short--code--content">{desc}</p>'
        f'<div class="yc-shortcode--features--items">{"".join(cards)}</div></div>'
    )


def kayan_steps(title: str, desc: str, items: list) -> str:
    rows = []
    for i, it in enumerate(items, 1):
        rows.append(
            '<div class="yc-shortcode--single-worksteps-item">'
            f'<div class="yc-shortcode-worksteps--image">{i:02d}</div>'
            f'<div class="yc-shortcode--worksteps--info"><h3>{it["title"]}</h3><p>{it["content"]}</p></div></div>'
        )
    return (
        f'<div class="yc-shortcode--box yc-shortcode--work-steps"><h2 class="--short--code--title">{title}</h2>'
        f'<p class="--short--code--content">{desc}</p>'
        f'<div class="yc-shortcode--steps--items">{"".join(rows)}</div></div>'
    )


def kayan_services(title: str, desc: str, items: list) -> str:
    rows = []
    for it in items:
        rows.append(
            '<div class="yc-shortcode--single-services-item">'
            f'<div class="yc-shortcode--services--info"><h3>{it["title"]}</h3><p>{it["content"]}</p></div></div>'
        )
    return (
        f'<div class="yc-shortcode--box yc-shortcode--post-services"><h2 class="--short--code--title">{title}</h2>'
        f'<p class="--short--code--content">{desc}</p>'
        f'<div class="yc-shortcode--services--items">{"".join(rows)}</div></div>'
    )


def kayan_prices(title: str, desc: str, items: list) -> str:
    trs = "".join(f"<tr><td>{it['title']}</td><td>{it['value']}</td></tr>" for it in items)
    return (
        f'<div class="yc-shortcode--box yc-shortcode--price_list"><h2 class="--short--code--title">{title}</h2>'
        f'<p class="--short--code--content">{desc}</p>'
        '<div class="yc-shortcode--price_list--items"><div class="responsive-table">'
        f'<table class="price-table"><thead><tr><th>العامل</th><th>التحديد</th></tr></thead><tbody>{trs}</tbody></table>'
        "</div></div></div>"
    )


def kayan_call(title: str, desc: str) -> str:
    return (
        '<div class="yc-shortcode--box yc-shortcode--section--contactus"><div class="--contact--post-info">'
        f'<h2 class="--shortcode--section--contactus--title">{title}</h2>'
        f'<p class="--shortcode--section--contactus--content">{desc}</p></div>'
        '<div class="--contact--post-call--buttons">'
        f'<a target="_blank" rel="nofollow" class="--contact--button-call-link --button-call-link-whatsapp -BTN--hoverable" href="https://wa.me/{WA}">'
        '<i class="fa-brands fa-whatsapp"></i><strong>الواتساب</strong></a></div></div>'
    )


def kayan_faq(faqs: list) -> str:
    items = []
    for i, f in enumerate(faqs):
        active = " active" if i == 0 else ""
        items.append(
            f'<div class="-YC-FaqsSimple-vsingle-Item-v2{active}">'
            f'<div class="-YC-FaqsSimple-vsingle-Title" data-toggle-faqs="{i}">'
            f'<div class="--fq-count">{i+1:02d}</div><h2>{f["question"]}</h2>'
            '<i class="fa-solid fa-plus"></i></div>'
            '<div class="-FaqsSimple-vsingle-Content-Row-v1 -Toggle-Content">'
            f'<div class="-p-FaqsSimple-vsingle-ContentValue-v1 -ToggleContentValue">{f["answer"]}</div></div></div>'
        )
    return (
        '<div class="-YC-FaqsSimple-vsingle"><h2 class="--widget--sidebar--title">الأسئلة الشائعة</h2>'
        f'<div class="-YC-FaqsSimple-vsingle-items">{"".join(items)}</div></div>'
    )


def hero(full: str, city: str, n: int) -> str:
    lines = [
        f"معاينة مكتوبة ثم عرض سعر — بلا تخمين من الرسالة داخل {city}.",
        f"نبدأ من المصدر لا من العرض السريع، ثم نحدد عدة العمل حسب العقار.",
        "التواصل واتساب فقط حتى تبقى الصور والحي في محادثة واحدة.",
    ]
    heads = ["تشخيص قبل التنفيذ", "عرض مكتوب بعد المعاينة", f"خدمة ميدانية داخل {city}"]
    return (
        f'<section class="kayan-hero"><span>ركن التطور — البحرين</span>'
        f"<h2>{pick(n, heads)}</h2>"
        f"<p>{pick(n + 1, lines)}</p>"
        f'<a href="https://wa.me/{WA}"><i class="fa-brands fa-whatsapp"></i> واتساب {full}</a></section>'
    )


def snippet_box(text: str) -> str:
    return f'<aside class="kayan-snippet"><strong>مقتطف:</strong> {text}</aside>'


def schema_ld(full: str, city: str, excerpt: str, faqs: list) -> str:
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["question"], "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}}
            for f in faqs
        ],
    }
    service = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": full,
        "description": excerpt,
        "provider": {"@type": "LocalBusiness", "name": "ركن التطور", "areaServed": city},
        "areaServed": {"@type": "City", "name": city, "containedInPlace": {"@type": "Country", "name": "Bahrain"}},
    }
    return (
        f'<script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>'
        f'<script type="application/ld+json">{json.dumps(service, ensure_ascii=False)}</script>'
    )


def local_scene(service: str, city: str, info: dict, pack: dict, n: int) -> str:
    areas = info["areas"]
    a1 = areas[n % len(areas)]
    a2 = areas[(n + 2) % len(areas)]
    a3 = areas[(n + 4) % len(areas)]
    frames = [
        f"في {a1} يختلف المدخل عن {a2}: {info['access']} لذلك نطلب معلماً واضحاً قبل الخروج.",
        f"حالة في {a3} قد تبدو مطابقة لجارة في {a1}، لكن {info['housing']} يغيّر العدة والزمن.",
        f"{info['season']} وفي {a2} يظهر ذلك أسرع من {a3} لأن التعرض للشمس أو الرطوبة مختلف.",
        f"لا ننسخ تقرير {a1} على {a2}. {pack['angle']}",
    ]
    return f"<p>{pick(n, frames)} {info['note']}</p>"


def topical_sections(code: str, service: str, city: str, info: dict, full: str, kw: str, n: int) -> list[str]:
    a0, a1, a2 = info["areas"][0], info["areas"][min(1, len(info["areas"]) - 1)], info["areas"][min(2, len(info["areas"]) - 1)]
    packs = {
        "leak": [
            (f"ما الذي يعنيه التسرب داخل {city}؟",
             f"التسرب هنا ليس دائماً ماءً ظاهراً على البلاط. الرطوبة والملوحة في {info['kind']} تجعل البقعة أوسع من مصدرها. "
             f"في {a0} قد يبدأ الأمر من حمّام علوي، وفي {a1} من خزان أو خط تغذية. نحدد المسار بأجهزة قبل أي تكسير."),
            (f"علامات ظاهرة وعلامات خفية",
             f"الظاهر: بقعة، صوت، أو تملّح. الخفي: ارتفاع فاتورة أو رائحة عفن بلا ماء مرئي. {info['season']} "
             f"لا تؤجّل لأن الجدار «شبه جاف»؛ في {city} الجفاف السطحي لا يعني انغلاق المصدر."),
            (f"كيف يتم الكشف بدون تكسير عشوائي؟",
             f"نبدأ بحرارة السطح ورطوبة البلاط وصوت الخط المضغوط. التكسير يكون مربعاً معلوماً بعد التقرير. "
             f"{info['note']} هذا يغيّر ترتيب العمل بين برج وبيت متلاصق."),
            (f"الحمّامات والخزانات والمسابح",
             f"ثلاث نقاط متكررة في {city}: سيليكون حمّام، خزان علوي، ومسبح في الفلل. كل نقطة عدة مختلفة. "
             f"خلطها في زيارة واحدة دون تشخيص يضاعف الفتح بلا داع."),
        ],
        "clean": [
            (f"ما الذي يشمله تنظيف المنزل عملياً؟",
             f"ليس مسحاً سطحياً. نفصل الأرضيات عن الكنب عن الخزان عن الواجهة لأن المادة التي تنظّف الرخام قد تؤذي القماش. "
             f"في {a0} الغبار البحري يلتصق بالرطوبة فيصير طبقة لزجة لا تزول بالماء فقط."),
            (f"الغرف والمطبخ والحمّام",
             f"المطبخ يحتاج إزالة ترسب لا معطّراً. الحمّام يحتاج ميلاً وجفاف زوايا. الغرف تعتمد على نوع الأرضية. "
             f"{info['climate']} يجعل إعادة الاتساخ سريعة إن بقي مصدر الغبار (مكيف أو خزان)."),
            (f"بعد الإشغال أو التشطيب",
             f"غبار الجبس والأسمنت يلتصق بالرطوبة. في {a1} نستخدم تسلسلاً لا يخدش الرخام. المدة أطول من نظافة دورية، ونكتب ذلك في العرض."),
            (f"الخزان والواجهة",
             f"رائحة الحنفية غالباً خزان. الواجهة العالية تحتاج تنسيق ارتفاع مختلف عن شقة أرضية في {a2}."),
        ],
        "ac": [
            (f"لماذا يضعف التبريد في {city}؟",
             f"الصيف يحمّل الوحدة فوق طاقتها. فلتر أو وحدة خارجية مغبرة أو نقص فريون يرفع الاستهلاك قبل أن «تموت» الوحدة. "
             f"{info['climate']}"),
            (f"الصيانة قبل الذروة لا في أغسطس فقط",
             f"العقد الدوري في أبريل أوفر من كمبروسر محترق. في {a0} الواجهة البحرية تتسخ أسرع فنزيد غسيل الخارج."),
            (f"ماء تحت الوحدة الداخلية",
             f"غالباً تصريف لا تسرب سقف. نفحص قبل اتهام السباكة. {info['note']}"),
            (f"الدكت والفلل",
             f"حرارة سطح {city} تقتل التبريد داخل دكت غير معزول. نفحص العزل والغبار قبل استبدال الوحدة."),
        ],
        "pest": [
            (f"لماذا تعود الحشرة بعد رشة عامة؟",
             f"المناخ الرطب يبقي التكاثر طوال السنة. الرش على البلاط دون إغلاق مجرى أو سور في {a0} يعيد الإصابة. نحدد النوع ثم المادة."),
            (f"المطبخ والحديقة والسقف",
             f"{info['risk']} كل نطاق نقطة دخول مختلفة. الجل للصراصير غير طعم القوارض وغير مكافحة البعوض عند المسبح."),
            (f"السلامة والمتابعة",
             f"نوضّح إن كانت زيارة ثانية ضمن العرض. ظهور حشرة بعد أسبوع قد يعني خروجاً من العش لا فشل المادة."),
            (f"ما الذي تحضّره قبل الزيارة؟",
             f"إخلاء طعام مكشوف، غلق أحواض السمك إن وُجدت، ووصف الحي. في أزقة {a1} نجهّز عدة يدوية."),
        ],
        "plumb": [
            (f"ضعف التدفق ليس دائماً انسداداً",
             f"قد تكون مضخة أو سخان أو خط عمومي. في البيوت المتلاصقة قرب {a0} الانسداد قد يكون مشتركاً. نحدد الاتجاه قبل السوبر."),
            (f"المطبخ والبيارة",
             f"دهون المجلى تراكمت في الأفقي. رائحة صباحية بعد إغلاق طويل قد تكون كفراً جافاً. {info['housing']}"),
            (f"متى نفتح البلاط؟",
             f"بعد أن تفشل الطرق غير الإتلافية أو تظهر نقطة محددة. لا نفتح «على الاحتمال»."),
            (f"السلامة",
             f"مياه مجاري ليست عمل أدوات منزلية. نمنع الخلط بين الكهربائي والسباكة قبل فك السخان."),
        ],
        "insul": [
            (f"العزل يفشل من الميل قبل المادة",
             f"حرارة {city} تفتح شعراً إن تجمّع الماء. نجرّب الميل بماء قبل اختيار اللون. {info['risk']}"),
            (f"مائي وحراري — متى نخلط؟",
             f"الخلط بلا فحص الطبقة القديمة يحبس رطوبة. في {a0} نفحص الطبقة القائمة أولاً."),
            (f"الحمّام قبل البلاط",
             f"أرخص من كشف لاحق. نكتب السماكة ومدة الجفاف في العرض."),
            (f"اختبار بعد التنفيذ",
             f"تجربة ماء وحدود صفاية. بدون هذا الاختبار العزل ديكور."),
        ],
        "elec": [
            (f"الرطوبة تفسد التماس",
             f"شرر أو قاطع يتكرر فحص لوحة لا لمبة. في {city} العلب المدفونة تتأثر أسرع. أوقف الدائرة عند رائحة احتراق."),
            (f"حمل المكيف والسخان",
             f"قاطع لا يناسب الحمل يفصل في الذروة. نقيس قبل استبدال القاطع بعشوائية."),
            (f"الإنارة الخارجية",
             f"ملوحة {info['kind']} تآكل نقاط الحديقة. نختار إغلاقاً مناسباً لا لمبة أرخص."),
        ],
        "paint": [
            (f"لا تدهن فوق رطوبة",
             f"الوجهة فوق تملّح في {a0} تتفلفص قبل الموسم التالي. نعالج المصدر ثم الوجهة."),
            (f"داخلي وخارجي",
             f"الشمس والملوحة يغيّران الخامة. الخارجي غير الداخلي ولو تشابه اللون."),
            (f"الجبس والشعر",
             f"شعر حراري غير شعر هبوط. التشخيص يمنع إعادة الصبغ بعد شهر."),
        ],
        "garden": [
            (f"الملوحة تقتل النجيل بلا صرف",
             f"في {city} نبدأ بالصرف واتجاه الشمس لا بعدد النخل. {info['housing']}"),
            (f"الري",
             f"الغمر يغرق الجذور. التنقيط حسب الظل في {a0}."),
            (f"الحديقة والحشرات",
             f"برك الري تجذب البعوض. نربط الري بالمكافحة إن لزم."),
        ],
        "pool": [
            (f"انخفاض المنسوب ليس تبخراً فقط",
             f"في فلل {city} الانخفاض اليومي الثابت تسرب أو غسيل فلتر خاطئ. نقيس ثم نحدد."),
            (f"المضخة والفلتر",
             f"الحرارة تستهلك القطع. الجدول الدوري أرخص من استبدال المضخة في أغسطس."),
            (f"كيماويات الماء",
             f"لا تُسكب عشوائياً. نقرأ الكلور وpH قبل أي جرعة."),
        ],
        "maint": [
            (f"عقد بلا بنود يتحول خلافاً",
             f"نكتب المشمول والمنفصل. {info['note']} الذروة تُحجز قبل مايو."),
            (f"التكييف والسباكة والكهرباء",
             f"زيارة واحدة بمن قائمة أوضح من ثلاث زيارات متنازعة."),
            (f"سجل الزيارات",
             f"صور قبل/بعد بعد كل جولة حتى لا يُعاد النقاش من الصفر."),
        ],
        "move": [
            (f"البرج غير الفيلا",
             f"{info['access']} المصعد والطابق يحدّدان العدة. أبلغ عن الزجاج والأدراج الثقيلة قبل يوم النقل."),
            (f"التغليف",
             f"الأزقة في {a0} تحتاج عربات أضيق. نحمي المداخل."),
        ],
        "solar": [
            (f"الغبار يخفض العائد",
             f"{info['climate']} تنظيف بعد العاصفة يعيد إنتاجاً أكثر من لوح إضافي."),
            (f"التثبيت ضد الرياح",
             f"سطح {city} يحتاج تثبيتاً لا يفتح العزل. نفحص الاثنين معاً."),
        ],
        "build": [
            (f"الترميم يبدأ من الرطوبة",
             f"{info['risk']} التشطيب فوق جدار يبكي يُعاد. نفصل الإنشائي عن الوجهة."),
            (f"الملاحق والأسوار",
             f"الأساس المناسب لملحق {city} غير جدار تجميلي. نكتبه في العرض."),
        ],
        "gen": [
            (f"ما الذي ننفّذه فعلاً؟",
             f"نحدد في المعاينة ما يتم اليوم وما يُؤجَّل لخامة أو جفاف. في {city} هذا التوضيح يمنع سوء الفهم."),
            (f"لماذا تختلف العدة؟",
             f"{info['housing']} {info['access']}"),
        ],
    }
    items = packs.get(code, packs["gen"])
    start = n % len(items)
    ordered = [items[(start + i) % len(items)] for i in range(len(items))]
    out = []
    for title, body in ordered:
        out.append(f"<h2>{title}</h2><p>{body}</p>")
    return out


def unique_intro(voice: int, full: str, kw: str, service: str, city: str, info: dict, pack: dict) -> str:
    a0 = info["areas"][0]
    a1 = info["areas"][min(1, len(info["areas"]) - 1)]
    variants = [
        f"إذا لاحظت تغيراً في الراحة أو الفاتورة أو الرائحة داخل {city} فالمطلوب ليس «حلّاً سريعاً» يُعاد بعد أسبوع. "
        f"{pack['angle']} نقرأ العقار في {a0} وبقية الأحياء كحالة مستقلة: صور على واتساب، ثم معاينة، ثم عرض مكتوب.",
        f"{info['season']} لذلك يتكرر طلب {service} في هذا التوقيت. المهم أن تعرف: التشخيص يسبق العدة. "
        f"{info['housing']} يغيّر الوقت والأدوات مقارنة بمدينة أخرى حتى لو تشابه الاسم.",
        f"ابدأ من السؤال الصحيح: هل العَرَض مصدره ظاهر أم خفي؟ في {info['kind']} الجواب يغيّر مسار العمل. "
        f"{pack['angle']} التواصل واتساب فقط حتى لا تضيع التفاصيل.",
        f"ركن التطور ينفّذ {service} داخل {city} بعد معاينة ميدانية. لا نثبت رقماً من الرسالة لأن {info['access']}",
        f"الفرق العملي: نغلق السبب لا العرض. {info['risk']} إن كان منزلك في {a0} أرسل أقرب معلم مع الصور.",
        f"{kw} يناسب من يريد تقريراً يفهمه لا جملاً عامة. {info['climate']} نكتب النطاق والمدة قبل البدء.",
        f"في {a1} تختلف قصة المدخل عن {a0} حتى داخل {city}. {full} ليست قالباً يُلصق على كل عنوان. "
        f"{info['note']}",
        f"من يبحث عن {service} في {city} يريد عادةً معرفة المصدر والتكلفة بعد الرؤية لا قبلها. "
        f"{pack['angle']} نثبت ذلك في واتساب بالصور.",
        f"{info['climate']} هذا وحده يكفي لجعل نفس الخدمة في مدينة أخرى نتيجة مختلفة. "
        f"لذلك {full} تُكتب بعد المعاينة لا من عنوان الرسالة.",
        f"لا نبدأ بعدّة جاهزة. في {info['kind']} نسأل أولاً: أين العَرَض ومتى يظهر؟ ثم نزور {a0} أو الحي الذي تحدده. "
        f"{info['risk']}",
        f"طلب {service} من {a0} غير طلبها من {a1}: {info['access']} نرتّب النافذة بعد تأكيد المعلم.",
        f"إذا عاد العَرَض بعد «حل سريع» فالمشكلة غالباً في التشخيص لا في اسم الخدمة. "
        f"{full} عندنا مسار معاينة ثم عرض ثم تنفيذ.",
    ]
    return variants[voice % len(variants)]


def expand_unique(html: str, service: str, city: str, info: dict, full: str, pack: dict, n: int, target: int) -> str:
    areas = info["areas"]
    extras = [
        f"<h2>ماذا يحدث إن أُجّلت المعالجة في {city}؟</h2><p>{info['season']} التأجيل لا يوفّر المال إذا عاد العَرَض خلال أسابيع. "
        f"في {areas[0]} نلاحظ أن {info['risk']} يتسع مع الرطوبة. الفرق بين زيارة الآن وزيارة بعد شهر هو غالباً مساحة أكبر أو خامة إضافية لا «نفس السعر». "
        f"نكتب في العرض ما يُنفَّذ فوراً وما يُراقَب حتى لا يُفهم التأجيل على أنه إهمال.</p>"
        f"<p>{info['housing']} يجعل بعض النقاط أعلى أو أضيق فيصعب الوصول لاحقاً إن تدهورت. لذلك المعاينة المبكرة أوضح للطرفين.</p>",
        f"<h2>معاينة {service} في عقار مرتفع أو ضيق</h2><p>{info['note']} هذا يغيّر زمن الزيارة وعدة الرفع. "
        f"أبلغ عن الطابق والمصعد ولون السور قبل أن نتحرك. في {areas[min(2,len(areas)-1)]} المدخل قد لا يناسب سيارة عدة كبيرة فنجهّز بديلاً يدوياً. "
        f"{info['access']}</p>",
        f"<h2>الفرق بين زيارة واحدة وعمل مرحلي</h2><p>بعض حالات {service} تحتاج جفافاً أو خامة أو موافقة على فتح محدود. "
        f"نصرّح بذلك قبل البدء. {pack['angle']} إن طُلب إنهاء كل شيء في ساعات بينما السطح يحتاج انتظاراً، نرفض اختصار الجودة.</p>",
        f"<h2>السلامة أثناء التنفيذ</h2><p>لا نخلط العدة. إن تداخل الكهرباء مع الماء أو المواد الكيميائية نوقف العمل ونوضح السبب. "
        f"في {city} الرطوبة ترفع هذا الاحتمال. {info['access']} الأطفال والحيوانات يُبعدون عن نطاق المادة حتى يجف السطح المتفق عليه.</p>",
        f"<h3>حي {areas[min(1, len(areas)-1)]}</h3><p>{AREA_NOTES.get(areas[min(1, len(areas)-1)], info['access'])} "
        f"لذلك {service} هنا لا يُنسخ من {areas[0]} حتى داخل {city}. نطلب معلماً واضحاً وصورة للمدخل.</p>",
        f"<h3>حي {areas[min(3, len(areas)-1)]}</h3><p>{AREA_NOTES.get(areas[min(3, len(areas)-1)], info['note'])} "
        f"نؤكد المعلم حتى يصل الفني من أول مرة. {info['climate']}</p>",
        f"<p>بعد التسليم تبقى محادثة واتساب مرجعاً للصور إن عاد عَرَض ضمن المتفق. هذا يغلق الملف بدل شكاوى بلا سياق. "
        f"إن ظهرت نقطة جديدة خارج النطاق نفتح عرضاً منفصلاً لا نخلطه مع العمل السابق.</p>",
        f"<p>إن تغيّر الوضع بعد الحجز وقبل الزيارة، أرسل صورة محدّثة. ذلك يمنع عدة ناقصة داخل {city}. "
        f"مثال: بقعة اتسعت أو انقطع تبريد أو ظهرت رائحة — كلها تغيّر ترتيب الفحص.</p>",
        f"<h2>ماذا نوثّق في التقرير؟</h2><p>المصدر إن ظهر، وما يحتاج متابعة، وما هو خارج الزيارة. "
        f"في {areas[0]} نضيف ملاحظة الوصول لأن الازدحام أو الأزقة تغيّر الزمن. التقرير لك لا للأرشيف الداخلي فقط.</p>",
        f"<h2>خدمات مرتبطة دون خلط الفاتورة</h2><p>قد يظهر أثناء المعاينة بند مجاور (عزل بعد تسرب، أو تنظيف بعد مكافحة). "
        f"لا نضيفه صامتاً. يُذكر كخيار. {pack['angle']}</p>",
    ]
    i = 0
    wc = len(word_list(html))
    vis = visible_text(html)
    dens = vis.count(full) / max(wc, 1)
    while (wc < target or dens < 0.0075) and i < len(extras):
        html = html.replace("</article>", extras[(n + i) % len(extras)] + "</article>", 1)
        wc = len(word_list(html))
        vis = visible_text(html)
        dens = vis.count(full) / max(wc, 1)
        i += 1
    pad = 0
    while wc < 1000 and pad < 6:
        html = html.replace(
            "</article>",
            f"<p>للتقدم: أرسل موقعك في {city} عبر واتساب بخصوص {full} مع صورة واضحة للجزء المطلوب.</p></article>",
            1,
        )
        wc = len(word_list(html))
        vis = visible_text(html)
        pad += 1
    inserts = [
        f"<p>{full} تبدأ بالتشخيص الميداني لا بالسعر الجاهز.</p>",
        f"<p>اختر {full} إذا كنت تريد عرضاً مكتوباً بعد المعاينة.</p>",
        f"<p>نطاق {full} يتحدد بعد رؤية العقار لا من الرسالة وحدها.</p>",
        f"<p>تواصل واتساب لحجز {full} مع صورة الحي.</p>",
        f"<p>خلاصة تشغيلية: {full} مسار معاينة ثم تنفيذ.</p>",
        f"<p>الفريق يصل بعد تأكيد المدخل لتنفيذ {full}.</p>",
        f"<p>لا نخلط {full} مع خدمة مجاورة في نفس العرض إلا ببند مكتوب.</p>",
        f"<p>المتابعة بعد {full} تكون عبر نفس محادثة واتساب.</p>",
        f"<p>في {city} تُكتب نتيجة {full} بعد المعاينة لا قبلها.</p>",
        f"<p>صور المدخل تختصر زمن {full} وتمنع عدة ناقصة.</p>",
        f"<p>إن تغيّر العَرَض قبل الزيارة أرسل صورة محدّثة لـ {full}.</p>",
        f"<p>التقرير جزء من {full} وليس مرفقاً اختيارياً.</p>",
        f"<p>نرفض بدء {full} فوق سبب غير مشخص.</p>",
        f"<p>عرض {full} يذكر المدة والخامة قبل التنفيذ.</p>",
        f"<p>أحياء {city} لا تُعامل نسخة واحدة داخل {full}.</p>",
        f"<p>واتساب يبقى مرجع الصور بعد تسليم {full}.</p>",
        f"<p>العدة تتحدد في الموقع أثناء {full} حسب الارتفاع والمدخل.</p>",
        f"<p>لا نثبت موعد {full} قبل تأكيد المعلم الأقرب.</p>",
    ]
    j = 0
    vis = visible_text(html)
    while vis.count(full) / max(len(word_list(html)), 1) < 0.0075 and j < len(inserts):
        nxt = vis.count(full) + 1
        nxt_wc = len(word_list(html)) + len(word_list(inserts[(n + j) % len(inserts)]))
        if nxt / max(nxt_wc, 1) > 0.0105:
            break
        html = html.replace("</article>", inserts[(n + j) % len(inserts)] + "</article>", 1)
        vis = visible_text(html)
        j += 1
    return html


def build_payload(title: str, slug: str) -> dict:
    service, city = parse_title(title)
    if city not in CITIES:
        city = "المنامة"
    info = CITIES[city]
    code = angle_for(service)
    pack = PACKS[code]
    kw = f"{service} في {city}"
    full = title
    n = seed(title, slug)
    voice = n % 12
    icon = ICONS.get(code, "fa-house-chimney")
    areas = info["areas"]
    a0, a_last = areas[0], areas[-1]

    intro = unique_intro(voice, full, kw, service, city, info, pack)
    if full not in intro:
        intro = f"{intro} هذا سياق {full}."
    what = pick(
        n,
        [
            f"<h2>ما الذي تشمله {service} داخل {city}؟</h2><p>{pack['angle']} نربط التنفيذ بنوع العقار: {info['housing']}. "
            f"الهدف نتيجة ثابتة بعد المعاينة لا زيارة تُعاد بلا تقرير.</p>",
            f"<h2>متى تستدعي {service} زيارة في {city}؟</h2><p>عندما يتكرر العَرَض أو يرتفع أثره على الفاتورة أو راحة السكن. "
            f"{info['risk']} علامتان فأكثر تستدعيان رسالة واتساب بصور الحي.</p>",
            f"<h2>لمن تناسب {service} في أحياء مثل {a0}؟</h2><p>لمن يريد تشخيصاً مكتوباً قبل العدة. "
            f"{info['kind']}. لا تناسب من يطلب رقماً ثابتاً من الرسالة دون صور.</p>",
            f"<h2>ما الذي لا تفعله الزيارة؟</h2><p>لا نغلق عرضاً ونترك المصدر. في {city} {info['climate']} "
            f"لذلك التشخيص أولاً ثم النطاق المكتوب.</p>",
        ],
    )
    signs = [
        [pick(n, ["تغير فاتورة أو رائحة", "بقعة أو ضعف أداء", "العَرَض يعود بعد أيام"]), "المصدر لم يُغلق", info["risk"][:42]],
        ["تكرار خلال أسبوعين", "الحل السابق عالج الشكل", f"مناخ {city} يعيد المشكلة"],
        [info["access"][:40], "العدة أو الزمن مختلف", "يُذكر في العرض"],
    ]
    area_rows = []
    for i in range(0, min(len(areas), 8), 2):
        note_l = AREA_NOTES.get(areas[i], info["access"])
        note_r = AREA_NOTES.get(areas[i + 1], info["note"]) if i + 1 < len(areas) else info["note"]
        right_area = areas[i + 1] if i + 1 < len(areas) else areas[0]
        area_rows.append([f"{areas[i]} — {note_l}", f"{right_area} — {note_r}"])

    causes = "".join(
        f"<li>{c} — نلاحظه في {areas[(n + i) % len(areas)]} أكثر من وصف عام.</li>"
        for i, c in enumerate(pack["causes"])
    )
    tools = "".join(
        f"<li>{t} داخل {city} مع مراعاة {info['climate'][:36]}.</li>" if i == 0 else f"<li>{t}</li>"
        for i, t in enumerate(pack["tools"])
    )
    tips_ul = "".join(
        f"<li>{t} في {areas[(n + i + 1) % len(areas)]}.</li>" if i % 2 == 0 else f"<li>{t}</li>"
        for i, t in enumerate(pack["tips"])
    )
    mistakes = [
        f"طلب سعر ثابت دون معاينة داخل {info['kind']}.",
        f"إهمال {info['risk']} ثم انتظار عودة المشكلة.",
        "فتح أو رش أو دهان فوق سبب غير محدد.",
        "تجاهل المناخ عند اختيار الخامة.",
        "اعتماد اتصال هاتفي بدل واتساب وضياع الصور.",
    ]
    mistakes = [mistakes[(n + i) % 5] for i in range(4)]

    price_rows = [
        ["حجم العمل والمساحة", info["housing"][:48]],
        ["سهولة الوصول والرفع", info["access"][:48]],
        ["حالة السطح أو التمديد", info["risk"][:48]],
        ["إعادة عمل سابق غير مكتمل", "يزيد الوقت لا الرقم العشوائي"],
    ]
    cmp_rows = [
        ["التشخيص", "معاينة ثم تقرير", "رقم يُقال بلا كشف"],
        ["المناخ", info["climate"][:40], "قالب دولة أخرى"],
        ["التواصل", "واتساب يحتفظ بالصور", "أرقام بلا أثر"],
    ]

    related = [c for c in CITIES if c != city]
    related = related[(n % max(len(related), 1)) :] + related[: (n % max(len(related), 1))]
    links = "، ".join(f"{service} في {c}" for c in related[:3])

    faqs_all = [
        {"question": f"هل تغطون أحياء {city} مثل {a0}؟", "answer": f"نعم ضمن نطاق عملنا مثل {', '.join(areas[:4])}. نؤكد زمن الوصول بعد الحي."},
        {"question": f"كم تستغرق {service} داخل {city}؟", "answer": f"المدة تُكتب بعد المعاينة. في {info['kind']} الظاهر أقصر من الخفي."},
        {"question": "هل يوجد ضمان مكتوب؟", "answer": "نطاق الضمان والخامة يُذكران في عرض السعر قبل البدء."},
        {"question": "لماذا لا يُثبت السعر من الرسالة؟", "answer": f"لأن {info['housing']} يغيّر العدة والوقت. الرقم بلا معاينة يضلل الطرفين."},
        {"question": "ماذا أرسل قبل الزيارة؟", "answer": f"وصف الحي في {city}، صور واضحة، وأقرب معلم. الباقي يُستكمل في الموقع."},
        {"question": f"هل تناسب الشقق والفلل في {city}؟", "answer": f"نعم مع اختلاف العدة حسب {info['kind']}."},
        {"question": "كيف أتواصل؟", "answer": "واتساب فقط حتى تبقى الصور والعنوان في محادثة واحدة. لا نعتمد الاتصال الهاتفي."},
        {"question": "هل تشمل الزيارة قطعاً أو مواد؟", "answer": "إن لزم بند إضافي يُذكر في العرض منفصلاً إلا إذا اتُفق كتابياً."},
        {"question": f"متى تكون الحالة طارئة في {city}؟", "answer": "تسرب ظاهر أو انقطاع تبريد أو خطر كهرباء. نرتّب أقرب نافذة بعد تأكيد العنوان."},
        {"question": f"هل تعملون في {a0} و{a_last}؟", "answer": f"نعم. نطلب وصفاً للمدخل لأن {info['access']}"},
        {"question": f"ما الذي يميّز التنفيذ في {city} عن مدينة أخرى؟", "answer": f"{info['climate']} {info['note']}"},
        {"question": "هل تزورون أكثر من مرة؟", "answer": "إن لزم جفاف أو خامة نكتبه في العرض. لا نعد بإنهاء كل شيء في ساعات إن كانت الحالة لا تسمح."},
    ]
    faqs = [faqs_all[(n + i * 3) % len(faqs_all)] for i in range(8 + (n % 3))]

    feat_src = pack["services"][n % max(len(pack["services"]), 1) :] + pack["services"][: n % max(len(pack["services"]), 1)]
    feat_items = [{"title": " ".join(x.split()[:4]), "content": f"{x} — نناقشه في معاينة {city}."} for x in feat_src[:6]]
    step_items = [
        {"title": pick(n, ["استلام الطلب", "رسالة واتساب", "تأكيد العنوان"]), "content": f"واتساب مع الحي في {city} وصورة تصف {service}."},
        {"title": pick(n + 1, ["المعاينة الميدانية", "التشخيص", "قراءة المصدر"]), "content": f"نفحص المصدر لا العرض. {info['note']}"},
        {"title": pick(n + 2, ["العرض المكتوب", "نطاق العمل", "اعتماد البنود"]), "content": "نطاق ومدة وخامة قبل البدء. لا نبدأ دون اعتماد."},
        {"title": pick(n + 3, ["التنفيذ والتسليم", "إغلاق الملف", "المعاينة النهائية"]), "content": "عمل حسب التقرير ثم معاينتك على واتساب إن لزم توثيق."},
    ]
    svc_items = [{"title": s, "content": f"{s} حسب حالة العقار في {city} و{a0}."} for s in feat_src[:5]]
    price_items = [
        {"title": r[0], "value": pick(n + i, ["بعد المعاينة", f"يُحدَّد في {city}", "يُكتب في العرض"])}
        for i, r in enumerate(price_rows)
    ]

    excerpt = f"{full}: معاينة في {info['kind']} ثم عرض مكتوب. واتساب {WA} — بدون اتصال هاتفي."
    rm_title = f"{full} | ركن التطور البحرين"
    rm_desc = f"{full} بعد معاينة ميدانية. تشخيص مكتوب قبل التنفيذ. تواصل واتساب لحجز الموعد في {city}."
    if len(rm_desc) > 160:
        rm_desc = rm_desc[:157] + "…"

    blocks = {
        "features": kayan_features(f"مميزات التنفيذ في {city}", f"بنود نناقشها أثناء معاينة {service} وليست قائمة تسويق عامة.", feat_items, icon),
        "steps": kayan_steps(f"خطوات {service} في {city}", f"مسار واضح من الرسالة حتى التسليم داخل {a0} وبقية الأحياء.", step_items),
        "services": kayan_services(f"نطاق {service}", f"قد يُستبعد بند إن لم يلزم لحالتك في {city}.", svc_items),
        "prices": kayan_prices(f"عوامل تسعير {service} في {city}", "لا أسعار مخترعة. القيمة تُكتب بعد المعاينة.", price_items),
        "call": kayan_call(f"هل تحتاج {service} في {city}؟", "أرسل الحي والصور على واتساب لتحديد المعاينة. بدون اتصال هاتفي."),
        "body": "",
    }

    refuse = pick(
        n,
        [
            f"<h2>ما الذي نرفضه في {city}؟</h2><p>نرفض تثبيت سعر قبل الرؤية، وخلط خدمة مجاورة في نفس الفاتورة دون بند، "
            f"والعمل فوق رطوبة أو عطل غير مشخص. {info['risk']}</p>",
            f"<h2>حدود الزيارة في {a0}</h2><p>{info['access']} إن تعذر التوقف أو الرفع نكتب بديلاً قبل التحرك. "
            f"هذا أوضح من الاعتذار بعد الوصول.</p>",
        ],
    )
    topical = topical_sections(code, service, city, info, full, kw, n)
    mid_body = [
        what,
        local_scene(service, city, info, pack, n),
        f"<h2>علامات تساعدك تقرر في {city}</h2><p>الجدول قراءة ميدانية لا قائمة تسويق.</p>{table(['العلامة','المعنى','إن أُجِّل في '+city], signs)}",
        *topical,
        f"<h2>أسباب تتكرر حول {a0}</h2><ul>{causes}</ul>{warn(info['risk'])}",
        f"<h2>الأدوات والخامات المناسبة لمناخ {city}</h2><ul>{tools}</ul>",
        refuse,
        f"<h2>أخطاء ترفع التكلفة داخل {city}</h2><ul>{''.join(f'<li>{x}</li>' for x in mistakes)}</ul>",
        f"<h2>كيف تُقاس تكلفة {service} هنا؟</h2><p>لا نخترع أسعاراً ثابتة. هذه عوامل القياس بعد المعاينة في {city}.</p>{table(['العامل','كيف يظهر محلياً'], price_rows)}",
        f"<h2>مقارنة قرار التنفيذ في {city}</h2>{table(['المعيار','ركن التطور','الشائع'], cmp_rows)}",
        f"<h2>نصائح قبل زيارة {a_last}</h2><ul>{tips_ul}</ul>{tip('نصيحة', info['note'])}",
        f"<h2>نطاق الأحياء داخل {city}</h2><p>نغطي المدينة حسب وصف المدخل لا حسب اسم عام.</p>{table(['نطاق','نطاق مجاور'], area_rows)}",
        area_tour(city, info, kw, full, n),
        f"<p>خدمات باسم مشابه في مدن أخرى لا تعني نفس العدة: {links}. أرسل حالتك الحالية أولاً حتى لا تُخلط الزيارة.</p>",
        f"<h2>الخلاصة</h2><p>{full} يُحسم بالتشخيص داخل {city}. {pack['angle']} "
        f"إن كنت في {a0} أو {a_last} أرسل الصور على واتساب.</p>",
    ]
    rot_body = (n // 5) % max(len(mid_body) - 2, 1)
    mid_body = [mid_body[0], *mid_body[1 + rot_body :], *mid_body[1 : 1 + rot_body]]

    sc_order = pick(
        n // 7,
        [
            ["features", "body", "steps", "prices", "services", "call"],
            ["body", "features", "prices", "steps", "call", "services"],
            ["features", "steps", "body", "services", "prices", "call"],
            ["body", "steps", "features", "call", "prices", "services"],
            ["steps", "body", "services", "features", "prices", "call"],
        ],
    )

    parts = [
        style_block(),
        '<article class="kayan-article">',
        f'<img src="{IMG}" alt="{full} — ركن التطور البحرين" width="800" height="450" loading="eager" decoding="async"/>',
        f"<p>{intro}</p>",
        snippet_box(excerpt),
        hero(full, city, n),
    ]
    body_inserted = False
    for key in sc_order:
        if key == "body":
            parts.extend(mid_body)
            body_inserted = True
        else:
            parts.append(blocks[key])
    if not body_inserted:
        parts.extend(mid_body)
    parts.append(kayan_faq(faqs))
    parts.append(schema_ld(full, city, excerpt, faqs))
    parts.append("</article>")
    html = "\n".join(parts)
    html = expand_unique(html, service, city, info, full, pack, n, LEN_TARGET.get(pack["len"], 1450))

    tags = [service, city, "ركن التطور", "البحرين", " ".join(pack["services"][0].split()[:3])]
    meta = {k: v for k, v in {
        "whatsapp_number": WA,
        "hide__card__callbutton": "1",
        "hide__service__callbutton": "1",
        "hide__floating__call": "1",
        "whatsapp_chat_mode": "1",
        "floating_whatsapp_chat_mode": "1",
        "last_update": "09-09-2026",
        "rank_math_title": rm_title,
        "rank_math_description": rm_desc,
        "rank_math_focus_keyword": full,
    }.items() if k in STRING_META}
    return {
        "html": html,
        "excerpt": excerpt,
        "wc": len(word_list(html)),
        "dens": visible_text(html).count(full) / max(len(word_list(html)), 1),
        "city": city,
        "service": service,
        "full": full,
        "kw": kw,
        "code": code,
        "tags": tags,
        "meta": meta,
    }


TAG_CACHE: dict[str, int] = {}
CITY_IDS: dict[str, int] = {}
TAG_LOCK = threading.Lock()


def ensure_tag(name: str) -> int | None:
    name = scrub(name)[:80]
    with TAG_LOCK:
        if name in TAG_CACHE:
            return TAG_CACHE[name]
    code, data = req("GET", f"/wp/v2/tags&search={urllib.parse.quote(name)}&per_page=5")
    if code == 200 and isinstance(data, list):
        for t in data:
            if t.get("name") == name:
                with TAG_LOCK:
                    TAG_CACHE[name] = t["id"]
                return t["id"]
    code, data = req("POST", "/wp/v2/tags", {"name": name})
    if code in (200, 201) and isinstance(data, dict) and data.get("id"):
        with TAG_LOCK:
            TAG_CACHE[name] = data["id"]
        return data["id"]
    return None


def load_city_ids():
    if CITY_IDS:
        return
    page = 1
    while page <= 3:
        code, data = req("GET", f"/wp/v2/cities&per_page=50&page={page}")
        if code != 200 or not data:
            break
        for t in data:
            CITY_IDS[t.get("name", "")] = t["id"]
        if len(data) < 50:
            break
        page += 1


def fetch_posts() -> list[dict]:
    posts = []
    page = 1
    while page <= 30:
        code, data = req("GET", f"/wp/v2/posts&per_page=100&page={page}&context=edit&status=publish&_fields=id,title,slug")
        if code != 200 or not data:
            break
        posts.extend(data)
        if len(data) < 100:
            break
        page += 1
    return posts


def update_one(post: dict) -> tuple[int, str, int, float]:
    pid = post["id"]
    title = post.get("title", {}).get("raw") or post.get("title", {}).get("rendered") or ""
    slug = post.get("slug") or ""
    built = build_payload(title, slug)
    tag_ids = [i for i in (ensure_tag(t) for t in built["tags"]) if i]
    payload = {"content": built["html"], "excerpt": built["excerpt"]}
    if tag_ids:
        payload["tags"] = tag_ids
    load_city_ids()
    cid = CITY_IDS.get(built["city"])
    if cid:
        payload["cities"] = [cid]
    payload["meta"] = built["meta"]
    code, out = req("POST", f"/wp/v2/posts/{pid}", payload)
    if code not in (200, 201):
        payload.pop("meta", None)
        code, out = req("POST", f"/wp/v2/posts/{pid}", payload)
        if code not in (200, 201):
            return pid, f"err{code}:{str(out)[:80]}", built["wc"], built["dens"]
    slug_city = CITY_SLUG.get(built["city"])
    if slug_city:
        cli(f"post term set {pid} cities {slug_city}", write=True)
    fail_meta = 0
    for k in ("rank_math_title", "rank_math_description", "rank_math_focus_keyword", "whatsapp_number",
              "hide__floating__call", "whatsapp_chat_mode"):
        if k in built["meta"] and not set_meta(pid, k, built["meta"][k]):
            fail_meta += 1
    st = "ok" if fail_meta == 0 else f"ok-meta{fail_meta}"
    return pid, st, built["wc"], built["dens"]


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"\w{3,}", text) if w}


def sample_report() -> None:
    samples = [
        ("شركة تنظيف منازل في المنامة", "home-cleaning-manama"),
        ("شركة تنظيف منازل في المحرق", "home-cleaning-muharraq"),
        ("شركة كشف تسربات المياه في المنامة", "water-leak-detection-manama"),
        ("فني أنظمة صوت منزلية في الرفاع", "home-audio-riffa"),
        ("شركة مكافحة حشرات في سترة", "pest-control-sitra"),
        ("شركة عزل أسطح في عالي", "roof-insulation-aali"),
    ]
    print("=== kayan sample quality ===")
    leads = []
    h2sets = []
    bodies = []
    for t, s in samples:
        b = build_payload(t, s)
        html = b["html"]
        vis = visible_text(html)
        print(
            f"{t}: words={b['wc']} dens={b['dens']:.3%} tables={html.count('<table')} "
            f"feat={html.count('yc-shortcode--features')} steps={html.count('yc-shortcode--work-steps')} "
            f"svc={html.count('yc-shortcode--post-services')} prices={html.count('yc-shortcode--price_list')} "
            f"faq={html.count('-YC-FaqsSimple-vsingle')} call={html.count('yc-shortcode--section--contactus')} "
            f"sc={html.count('[post_')} h2={html.count('<h2')} tel={'tel:' in html} ld={'application/ld+json' in html}"
        )
        if b["wc"] < 1000:
            print("  WARN short")
        if not (0.0065 <= b["dens"] <= 0.012):
            print("  WARN density")
        leads.append(vis[:280])
        h2sets.append(tuple(re.findall(r"<h2(?:\s[^>]*)?>(.*?)</h2>", html)[:10]))
        bodies.append(_tokens(vis))
    print("unique_leads", len(set(leads)), "/", len(leads))
    print("unique_h2", len(set(h2sets)), "/", len(h2sets))
    jacc = []
    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            a, c = bodies[i], bodies[j]
            if not a or not c:
                continue
            jacc.append(len(a & c) / max(len(a | c), 1))
    if jacc:
        print(f"pairwise_jaccard max={max(jacc):.3f} mean={sum(jacc)/len(jacc):.3f}")
    city_pair = []
    for city, slug_c in [("المنامة", "manama"), ("المحرق", "muharraq"), ("الرفاع", "riffa"), ("سترة", "sitra")]:
        b = build_payload(f"شركة تنظيف منازل في {city}", f"home-cleaning-{slug_c}")
        city_pair.append(_tokens(visible_text(b["html"])))
    cj = []
    for i in range(len(city_pair)):
        for j in range(i + 1, len(city_pair)):
            a, c = city_pair[i], city_pair[j]
            cj.append(len(a & c) / max(len(a | c), 1))
    if cj:
        print(f"same_service_city_jaccard max={max(cj):.3f} mean={sum(cj)/len(cj):.3f}")


def main() -> int:
    if "--dry-run" in sys.argv:
        sample_report()
        return 0
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1
    sample_report()
    posts = fetch_posts()
    if "--limit" in sys.argv:
        posts = posts[: int(sys.argv[sys.argv.index("--limit") + 1])]
    print("posts", len(posts))
    ok = err = 0
    wmin = 10**9
    dmin = 1.0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(update_one, p) for p in posts]
        for i, fut in enumerate(as_completed(futs), 1):
            pid, st, wc, dens = fut.result()
            wmin = min(wmin, wc)
            dmin = min(dmin, dens)
            if st.startswith("ok"):
                ok += 1
            else:
                err += 1
                if err <= 8:
                    print("fail", pid, st)
            if i % 80 == 0:
                print(f"progress {i}/{len(posts)} ok={ok} err={err} min_words={wmin} min_dens={dmin:.3%}")
    print(f"done ok={ok} err={err} min_words={wmin} min_dens={dmin:.3%}")
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
