#!/usr/bin/env python3
"""Deploy homepage/trust chrome fixes and scrub shipping-log leaks."""
from __future__ import annotations

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rewrite_bh_kayan import cli  # noqa: E402

REPLACES = [
    (
        "أقرب للمكاتب والمستودعات التجارية؛ التخليص أوضح إن اكتملت الأوراق.",
        "الازدحام ومصعد الخدمة في السيف والجفير يحدّدان نافذة الوصول.",
    ),
    (
        "أقرب لمطار البحرين؛ الشحن الجوي من هنا أوفر في زمن الطريق.",
        "الجسر وحركة المطار يحدّدان زمن الوصول أكثر من المسافة على الخريطة.",
    ),
    (
        "مسافة أطول للمستودع أو المنفذ؛ نكتب زمن الطريق في العرض.",
        "الفلل المتباعدة تزيد زمن الطريق؛ نكتب أقرب معلم قبل الخروج.",
    ),
    (
        "مناسب للبضائع والمستندات المرتبطة بالميناء أكثر من الشحن السكني الخفيف.",
        "حركة الشاحنات قرب الميناء تقيّد التوقف صباحاً؛ نفضّل ما بعد الذروة.",
    ),
    (
        "الساحل الغربي يطيل الطريق إلى المطار أو المنفذ إن لم يُحسب مسبقاً.",
        "الساحل الغربي يطيل زمن الوصول إن لم يُحسب المدخل الداخلي مسبقاً.",
    ),
]


def run(cmd: str, write: bool = True) -> dict:
    out = cli(cmd, write=write)
    print(cmd[:110], "exit", out.get("exit_code"), (out.get("stdout") or out.get("stderr") or "")[:260], flush=True)
    return out


def snippet_code() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bh_chrome_snippet.php")
    return open(path, encoding="utf-8").read().lstrip()


def upsert_snippet() -> None:
    b64 = base64.b64encode(snippet_code().encode("utf-8")).decode("ascii")
    php = (
        "global $wpdb; "
        f'$code = base64_decode("{b64}"); '
        '$table = $wpdb->prefix . "snippets"; '
        '$id = (int) $wpdb->get_var("SELECT id FROM {$table} WHERE name=\\"Rukn BH Chrome SEO\\" LIMIT 1"); '
        '$data = array('
        '"name"=>"Rukn BH Chrome SEO",'
        '"description"=>"Homepage counters, WhatsApp-only chrome, hide empty ratings.",'
        '"code"=>$code,'
        '"tags"=>"bahrain,seo",'
        '"scope"=>"global",'
        '"condition_id"=>0,'
        '"priority"=>2,'
        '"active"=>1,'
        '"modified"=>current_time("mysql")'
        "); "
        "if ($id) { $wpdb->update($table, $data, array(\"id\"=>$id)); echo \"updated $id\"; } "
        "else { $data[\"revision\"]=1; $wpdb->insert($table, $data); echo \"inserted \".$wpdb->insert_id; }"
    )
    run("eval '" + php + "'")


def sql_lit(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def main() -> int:
    if not os.environ.get("WP_APP_PASSWORD"):
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1

    upsert_snippet()
    run(
        "option patch update rank-math-options-titles homepage_description "
        "'خدمات منزلية متكاملة في مملكة البحرين: كشف تسربات، عزل، صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات. "
        "صفحات تفصيلية لـ 8 مدن وتواصل واتساب.'"
    )
    run(
        "option update blogdescription "
        "'ركن التطور البحرين: خدمات منزلية في المنامة والمحرق والرفاع و5 مدن بصفحات تفصيلية. تواصل واتساب.'"
    )

    for old, new in REPLACES:
        sql = (
            "UPDATE 2GGpPu6Sy_posts SET post_content=REPLACE(post_content,'"
            + sql_lit(old)
            + "','"
            + sql_lit(new)
            + "') WHERE post_content LIKE '%"
            + sql_lit(old)
            + "%'"
        )
        run("db query \"" + sql + "\"")

    run(
        'db query "SELECT COUNT(*) AS leak_left FROM 2GGpPu6Sy_posts WHERE post_status=\'publish\' '
        "AND post_content LIKE '%الشحن الجوي%' AND post_title NOT LIKE '%شحن%' AND post_title NOT LIKE '%جوي%'\"",
        write=False,
    )
    run("cache purge")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
