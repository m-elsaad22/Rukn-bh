#!/usr/bin/env python3
"""Inject a unique local section into every Bahrain service×city article."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib.error
import urllib.request

BASE = "https://rukn-eltatawer.com/bh"
USER = os.environ.get("WP_USER", "melsaad")
PASSWORD = os.environ.get("WP_APP_PASSWORD", "")
WA = "971586634710"
MARK = "rukn-local-unique"

CITIES = {
    "المنامة": {
        "slug": "manama",
        "kind": "عاصمة ساحلية",
        "housing": "أبراج وشقق ومكاتب في الجفير والسيف والعدلية والقضيبية والحورة",
        "climate": "رطوبة عالية وملوحة هواء قرب البحر تسرّع تآكل العزل والمكيفات والحديد",
        "access": "ازدحام ساعات الدوام يجعل جدولة المعاينة الصباحية أو المسائية أوضح من منتصف النهار",
        "watch": "تسربات الخزانات العلوية في العمائر، ضعف تبريد الوحدات على الواجهات البحرية، ورطوبة خلف الجبس",
    },
    "المحرق": {
        "slug": "muharraq",
        "kind": "جزيرة سكنية كثيفة",
        "housing": "بيوت قديمة وأزقة ضيقة إلى جانب عمائر أحدث في الحد والمحرق الجديدة",
        "climate": "هواء بحري وملوحة أعلى من الداخل، مع تمديدات مياه أقدم في الأحياء التراثية",
        "access": "الجسر والازدحام نحو المطار يحدّدان زمن الوصول؛ نؤكد الموعد حسب حيّك",
        "watch": "تسربات المواسير القديمة، رطوبة الجدران، وانسداد مجاري البيوت المتلاصقة",
    },
    "الرفاع": {
        "slug": "riffa",
        "kind": "فلل ومساحات أكبر",
        "housing": "فلل وقصور وحدائق في الرفاع الشرقي والغربي والوسطى",
        "climate": "حرارة سطح أعلى صيفاً لأن المساحات المكشوفة أكبر من شقق العاصمة",
        "access": "المعاينة غالباً أسرع من المنامة لأن المواقع متباعدة لكن الطرق أوضح",
        "watch": "عزل الأسطح، صيانة المسابح، وحدائق تحتاج ريّاً ومكافحة حشرات موسمية",
    },
    "مدينة حمد": {
        "slug": "hamad-town",
        "kind": "مدينة سكنية هادئة",
        "housing": "بيوت متلاصقة وشقق أسرية بكثافة سكنية مستقرة",
        "climate": "حرارة صيفية طويلة داخل الأحياء السكنية مع حاجة تبريد يومي",
        "access": "التنقل داخل المدينة منتظم؛ نحدد الحي ورقم المنزل قبل التحرك",
        "watch": "عقود صيانة التكييف، تنظيف الخزانات، ومكافحة حشرات الحدائق الخلفية",
    },
    "مدينة عيسى": {
        "slug": "isa-town",
        "kind": "موقع متوسط بين المحافظات",
        "housing": "بيوت وشقق قريبة من الأسواق والمدارس",
        "climate": "رطوبة أقل من الساحل المباشر لكنها كافية لإظهار عفن الحمّامات",
        "access": "موقعها يختصر وقت الوصول من المنامة أو الرفاع إذا حُجز الموعد مسبقاً",
        "watch": "ترميم الحمّامات، تسليك المجاري، وصيانة كهرباء البيوت الأقدم",
    },
    "عالي": {
        "slug": "aali",
        "kind": "فلل وحدائق داخلية",
        "housing": "فلل مستقلة وحدائق أمامية أكثر من الأبراج",
        "climate": "تراب وحرارة سطح تؤثر على العزل الخارجي والمكيفات الخارجية",
        "access": "شوارع داخلية هادئة؛ نطلب علامة مميزة للفيلا حتى لا يتأخر الفني",
        "watch": "تنسيق الحدائق، عزل الأسطح، ومكافحة النمل والقوارض حول السور",
    },
    "سترة": {
        "slug": "sitra",
        "kind": "منطقة ساحلية وصناعية سكنية",
        "housing": "بيوت عمالية وسكن عائلي قرب المنشآت والميناء",
        "climate": "رطوبة وملوحة وغبار صناعي يسرّعان اتساخ الواجهات والمكيفات",
        "access": "حركة الشاحنات صباحاً؛ نفضّل مواعيد بعد الذروة إلا للطوارئ",
        "watch": "تنظيف الواجهات والخزانات، صيانة التكييف، وكشف تسربات بسبب الرطوبة",
    },
    "البديع": {
        "slug": "budaiya",
        "kind": "الساحل الغربي",
        "housing": "فلل بحرية وحدائق واسعة مقارنة بوسط المنامة",
        "climate": "رطوبة غرب البحرين أعلى مساءً؛ المكيف يعمل ساعات أطول",
        "access": "الطريق الساحلي واضح، لكن بعض الفلل داخل أزقة تحتاج وصفاً دقيقاً",
        "watch": "عزل الأسطح البحرية، صيانة المسابح، ومكافحة البعوض قرب المزروعات",
    },
}

SERVICE_ANGLES = [
    (("تسرب", "كشف تسرب", "تسريبات"), "التسرب هنا لا يُعالَج بالتخمين: الرطوبة والملوحة تخفيان المصدر خلف البلاط أو الجبس. نبدأ بأجهزة الكشف ثم تقرير مصوّر قبل أي تكسير."),
    (("عزل",), "العزل في البحرين يفشل غالباً من الحرارة ثم من ماء المطر النادر لكنه الغزير. نفحص الميل والصفايات ونوع الطبقة القديمة قبل اقتراح المادة."),
    (("تكييف", "مكيف", "فريون", "تبريد", "دكت"), "صيف البحرين يحمّل الوحدة فوق طاقتها. الصيانة الدورية هنا ليست رفاهية: فلتر مسدود أو فريون ناقص يرفع الفاتورة ويكسر الكمبروسر."),
    (("تنظيف", "تعقيم", "جلي", "غسيل"), "الغبار والرطوبة يجعلان التنظيف السطحي يعود بسرعة. نحدد نوع السطح (رخام، كنب، خزان، واجهة) ثم طريقة آمنة للمواد."),
    (("مكافحة", "حشرات", "صراصير", "نمل", "فئران", "قوارض", "بعوض", "حمام"), "المناخ الرطب والحدائق والمطابخ المفتوحة تجذب الحشرات على مدار السنة. نختار مادة مرخّصة ونحدد نقاط الدخول لا الرش العشوائي فقط."),
    (("سباك", "سباكة", "مجاري", "تسليك", "بيارات", "سخان", "مضخ"), "ضغط المياه والتمديدات القديمة في بعض الأحياء تظهر كضعف تدفق أو رائحة. نحدد إن كانت المشكلة شبكة داخلية أم عمومية قبل الفتح."),
    (("كهرب", "إنارة", "لوحات"), "الرطوبة تفسد نقاط التماس. أي شرر أو فصل متكرر يستدعي فحص اللوحة لا استبدال اللمبة فقط."),
    (("دهان", "صبغ", "بويات", "ورق حائط", "ديكور", "جبس"), "الرطوبة خلف الدهان تعيده خلال أشهر إن لم تُعالج. نفحص الجدار ثم نختار نوع الوجهة الداخلية أو الخارجية."),
    (("حديق", "عشب", "ري", "نخيل", "برجولة", "نافورة", "شلال"), "التربة والملوحة في البحرين تقتل العشب إن زُرع بلا طبقة صرف. نصمم الري والظل حسب اتجاه الشمس في موقعك."),
    (("مسابح", "مسبح"), "ماء البحر القريب والحرارة يسرّعان تآكل المضخات والفلاتر. الصيانة هنا جدول وليست زيارة عند العطل فقط."),
    (("شحن", "نقل", "عفش", "أثاث", "تخزين"), "الشوارع الضيقة في بعض الأحياء والمباني العالية تحتاج معدات رفع وتغليف مختلف عن فيلا مستقلة."),
    (("شمسية", "طاقة"), "السطوح هنا تتعرّض لغبار وملوحة. زاوية الألواح وتنظيفها الدوري يحددان العائد لا عدد الألواح وحده."),
    (("ترميم", "بناء", "ملاحق", "أسوار", "مطابخ", "حمامات"), "الترميم يبدأ بتشخيص الرطوبة والتشقق قبل الشكل. نفصل الإنشائي عن التشطيب حتى لا يُعاد العمل."),
    (("صيانة",), "عقد الصيانة في البحرين يختصر أعطال الذروة. نزور وفق جدول مكتوب: تكييف، سباكة، كهرباء، أو المبنى كاملاً."),
]


def auth() -> str:
    return "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()


def req(method: str, route: str, payload=None, timeout=90):
    url = f"{BASE}/?rest_route={route}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    headers = {
        "Authorization": auth(),
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 RuknBH-Unique/1.0",
    }
    if data:
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
            parsed = {"raw": body[:300]}
        return exc.code, parsed


def parse_title(title: str) -> tuple[str, str]:
    city = ""
    for name in sorted(CITIES, key=len, reverse=True):
        if f"في {name}" in title or title.endswith(name):
            city = name
            break
    service = title
    if city:
        service = re.sub(rf"\s*في\s+{re.escape(city)}\s*$", "", title)
    service = re.sub(r"^(شركة|فني)\s+", "", service).strip()
    return service, city


def service_angle(service: str) -> str:
    for keys, text in SERVICE_ANGLES:
        if any(k in service for k in keys):
            return text
    return "نبدأ بمعاينة مكتوبة ثم عرض سعر قبل التنفيذ، لأن كل عقار في البحرين يختلف في التمديدات والرطوبة وسهولة الوصول."


def variants(seed: str) -> int:
    return int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)


def build_block(title: str, slug: str) -> str:
    service, city = parse_title(title)
    info = CITIES.get(city) or {
        "kind": "مدينة بحرينية",
        "housing": "بيوت وفلل وشقق",
        "climate": "حرارة ورطوبة صيفية طويلة",
        "access": "نؤكد العنوان قبل التحرك",
        "watch": "التشخيص قبل الإصلاح",
        "slug": slug,
    }
    angle = service_angle(service)
    n = variants(f"{service}|{city}")
    leads = [
        f"{service} في {city} لا يُنفَّذ بنفس أسلوب شقق المنامة أو فلل الرفاع: {info['kind']} يغيّر زمن المعاينة ونوع العدة.",
        f"طلب {service} داخل {city} يبدأ من فهم العقار لا من قائمة أسعار جاهزة. {info['housing']}.",
        f"في {city} تظهر حاجة {service} غالباً بسبب {info['climate']}. لذلك المعاينة تسبق أي عرض مكتوب.",
        f"ركن التطور يقدّم {service} في {city} بفريق يصل إلى الموقع بعد تأكيد الحي ووصف المدخل عبر واتساب.",
    ]
    mids = [
        f"الوصول: {info['access']}",
        f"ما نراقبه ميدانياً: {info['watch']}",
        f"الفرق التشغيلي: {angle}",
    ]
    faqs = [
        (f"هل تأتي المعاينة في نفس اليوم داخل {city}؟", "إن كان الطلب طارئاً (تسرب ظاهر أو انقطاع تبريد) نرتّب أقرب نافذة بعد تأكيد العنوان. الأعمال المخططة تُجدول في نفس الأسبوع."),
        (f"هل السعر في {city} يختلف عن المنامة؟", "التسعير حسب حجم العمل وارتفاع المبنى وسهولة الرفع، لا حسب اسم المدينة وحدها. تستلم الرقم بعد المعاينة."),
        (f"ماذا أحضّر قبل زيارة {service}؟", "وصف مختصر للمشكلة، صور إن وُجدت، وأقرب معلم للمنزل. باقي التشخيص على أرض الموقع."),
        (f"هل تحتاج الجهة ترخيصاً أو ضماناً؟", "نوضّح نطاق الضمان والخامة المستخدمة في عرض السعر قبل البدء، ويُسلَّم العمل بعد معاينتك."),
    ]
    faq = faqs[n % len(faqs)]
    lead = leads[n % len(leads)]
    mid = mids[n % len(mids)]
    others = [c for c in CITIES if c != city][:4]
    links = " · ".join(f"{service} في {c}" for c in others)
    return f"""
<section class="{MARK}">
<h2>{service} في {city}: دليل محلي مختلف عن باقي البحرين</h2>
<p>{lead}</p>
<p>{mid}</p>
<p>{angle} هذا النص خاص بصفحة {title} حتى لا تختلط النتيجة مع صفحات المدن الأخرى.</p>
<h3>طبيعة العقار والعمل في {city}</h3>
<ul>
<li>نوع السكن الشائع: {info['housing']}</li>
<li>المناخ المؤثر: {info['climate']}</li>
<li>ما نراه أكثر في هذا الحي: {info['watch']}</li>
</ul>
<h3>{faq[0]}</h3>
<p>{faq[1]} للتواصل واتساب فقط على <a href="https://wa.me/{WA}">واتساب ركن التطور</a>.</p>
<p>صفحات مرتبطة بنفس الخدمة: {links}.</p>
</section>
"""


def unique_excerpt(title: str) -> str:
    service, city = parse_title(title)
    if not city:
        city = "البحرين"
    return (
        f"{title}: دليل محلي لـ{service} داخل {city} مع تشخيص قبل التنفيذ "
        f"وعرض سعر مكتوب. واتساب {WA}."
    )


def fetch_posts() -> list[dict]:
    posts = []
    page = 1
    while page <= 30:
        code, data = req(
            "GET",
            f"/wp/v2/posts&per_page=100&page={page}&context=edit&status=publish&_fields=id,title,content,slug,excerpt",
        )
        if code != 200 or not data:
            break
        posts.extend(data)
        if len(data) < 100:
            break
        page += 1
    return posts


def inject(raw: str, block: str) -> str:
    raw = re.sub(
        rf'<section class="{MARK}">.*?</section>',
        "",
        raw,
        flags=re.I | re.S,
    )
    if "</section>" in raw:
        return raw.replace("</section>", "</section>\n" + block, 1)
    return block + raw


def update_one(post: dict) -> tuple[int, str]:
    pid = post["id"]
    title = post.get("title", {}).get("raw") or ""
    raw = post.get("content", {}).get("raw") or ""
    if not raw or not title:
        return pid, "empty"
    block = build_block(title, post.get("slug") or "")
    new = inject(raw, block)
    payload = {"content": new, "excerpt": unique_excerpt(title)}
    code, out = req("POST", f"/wp/v2/posts/{pid}", payload)
    if code in (200, 201):
        return pid, "ok"
    return pid, f"err{code}:{str(out)[:70]}"


def main() -> int:
    if not PASSWORD:
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1
    posts = fetch_posts()
    print("posts", len(posts))
    ok = err = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(update_one, p) for p in posts]
        for i, fut in enumerate(as_completed(futs), 1):
            pid, st = fut.result()
            if st == "ok":
                ok += 1
            else:
                err += 1
                if err <= 6:
                    print("fail", pid, st)
            if i % 200 == 0:
                print(f"progress {i}/{len(posts)} ok={ok} err={err}")
    print(f"done ok={ok} err={err}")
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
