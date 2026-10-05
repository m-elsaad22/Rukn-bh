#!/usr/bin/env python3
"""Homepage trust chrome + shipping-log leak scrub (live-safe write paths)."""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rewrite_bh_kayan import cli, req  # noqa: E402

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

HEADER_CODES = r"""<style id="rukn-bh-ui">#ruknFab.fab-stack,.fab-stack{opacity:1!important;visibility:visible!important;transform:none!important}#ruknMob a.rukn-nav-link{display:block;padding:12px 0;font-family:Cairo,sans-serif;font-weight:700;color:#fff}html,body{background:#0A1F4E}header,header#hdr,header.fixedintro{left:0!important;right:0!important;inset-inline:0!important;width:100%!important;max-width:none!important;flex-wrap:nowrap!important;background:transparent!important}header:before,header::before,header#hdr:before,header#hdr::before,header.fixedintro:before,header.fixedintro::before{content:none!important;display:none!important;opacity:0!important;visibility:hidden!important;background:transparent!important;width:0!important;height:0!important}header#hdr .logo .mark,header#hdr .logo b{display:none!important}header#hdr .logo img{display:block!important;max-height:52px!important;max-width:min(58vw,220px)!important;width:auto!important;height:auto!important;opacity:1!important;visibility:visible!important;object-fit:contain!important;background:transparent!important;margin-inline:8px}header#hdr.scrolled{background:rgba(255,255,255,.78)!important}header#hdr.scrolled .logo img{mix-blend-mode:normal}@media(max-width:768px){header#hdr nav.menu,header#hdr nav.menu a{display:none!important;visibility:hidden!important}header#hdr .nav-cta .btn{display:none!important}}</style>
<style id="rukn-bh-chrome-css">.fab-call,.btn-call,a[href^="tel:"],.kayan-customer-ratings,.--rating--widgets--box,.--YC-single-rating-box--{display:none!important}body.rukn-hide-call .fab-call,body.rukn-wa-only .fab-call,html.rukn-wa-only .fab-call{display:none!important}</style>
<script>
(function(){
 var WA='971586634710';
 var HOME='https://rukn-eltatawer.com/bh';
 var links=[['الرئيسية',HOME+'/'],['خدماتنا',HOME+'/our-services/'],['المدن',HOME+'/cities/'],['من نحن',HOME+'/about-us/'],['تواصل معنا',HOME+'/contact-us/'],['English',HOME+'/home-services-bahrain/']];
 var TEXT=[
  ['[[عدد المشاريع]]','1648'],
  ['[[سنة التأسيس]]','محلي'],
  ['مشروع منفّذ','صفحة مدينة×خدمة'],
  ['في البحرين منذ','فريق داخل البحرين'],
  ['مدن تغطية','مدن بصفحات'],
  ['تغطية 12 مدينة','صفحات تفصيلية لـ 8 مدن'],
  ['نطاق التغطية 12 مدن','8 مدن بصفحات تفصيلية'],
  ['12 مدن منطقة','8 مدن بصفحات'],
  ['من أول اتصال حتى إغلاق المشكلة','من أول واتساب حتى إغلاق المشكلة'],
  ['تواصل وتشخيصاتصال أو واتساب','تواصل وتشخيص عبر واتساب'],
  ['اتصال أو واتساب على مدار الأسبوع','واتساب على مدار الأسبوع'],
  ['اتصال أو واتساب','واتساب'],
  ['اتصل أو واتساب','واتساب'],
  ['لا نسعّر عبر الهاتف','لا نسعّر من الرسالة دون معاينة'],
  ['قبل ما تتصل','قبل ما تراسل'],
  ['نغطي المنامة والمحرق والرفاع ومدينة حمد ومدينة عيسى وعالي وسترة وجدحفص والبديع وسار وتوبلي والحد.','صفحات تفصيلية لـ 8 مدن: المنامة والمحرق والرفاع ومدينة حمد ومدينة عيسى وعالي وسترة والبديع. ونصل للمعاينة في أحياء مجاورة مثل الحد وسار وجدحفص وتوبلي.']
 ];
 function menuHtml(){var h='';for(var i=0;i<links.length;i++){h+='<a class="rukn-nav-link" href="'+links[i][1]+'">'+links[i][0]+'</a>';}return h;}
 function ensureFabs(){
  var stack=document.getElementById('ruknFab');
  if(!stack){
   stack=document.createElement('div');
   stack.className='fab-stack show';
   stack.id='ruknFab';
   (document.body||document.documentElement).appendChild(stack);
  }
  stack.classList.add('show');
  var calls=stack.querySelectorAll('a.fab-call,a[href^="tel:"]');
  for(var i=0;i<calls.length;i++){calls[i].remove();}
  if(!stack.querySelector('a.fab-wa')){
   var w=document.createElement('a');
   w.href='https://wa.me/'+WA;
   w.target='_blank';
   w.rel='noopener';
   w.className='fab-btn fab-wa';
   w.setAttribute('aria-label','واتساب');
   w.innerHTML='<i class="fab fa-whatsapp"></i>';
   stack.appendChild(w);
  }
 }
 function fillCounts(){
  var els=document.querySelectorAll('[data-count]');
  for(var i=0;i<els.length;i++){
   var el=els[i];
   var n=el.getAttribute('data-count')||'';
   if(n==='12'){n='8';el.setAttribute('data-count','8');}
   var t=(el.textContent||'').replace(/\s+/g,'');
   if(t===''||t==='0'||t==='12'){el.textContent=n;}
  }
 }
 function replaceText(){
  if(!document.body)return;
  var walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null);
  var n;
  while(n=walk.nextNode()){
   var v=n.nodeValue;
   if(!v)continue;
   if(v.indexOf('اختر الإمارة')!==-1){v=v.replace(/اختر الإمارة/g,'اختر المدينة');}
   if(v.indexOf('دبي، الإمارات')!==-1){v=v.replace(/دبي، الإمارات العربية المتحدة/g,'المنامة، مملكة البحرين').replace(/دبي، الإمارات/g,'المنامة، مملكة البحرين');}
   for(var i=0;i<TEXT.length;i++){
    if(v.indexOf(TEXT[i][0])!==-1){v=v.split(TEXT[i][0]).join(TEXT[i][1]);}
   }
   n.nodeValue=v;
  }
 }
 function stripEmptyRating(){
  var scripts=document.querySelectorAll('script[type="application/ld+json"]');
  for(var i=0;i<scripts.length;i++){
   var t=scripts[i].textContent||'';
   if(t.indexOf('"aggregateRating"')!==-1 && t.indexOf('"ratingValue":""')!==-1){
    t=t.replace(/,"aggregateRating":\{"@type":"AggregateRating","ratingValue":"","reviewCount":""\}/g,'');
    if(t.indexOf('"name": ""')!==-1){scripts[i].remove();}
    else {scripts[i].textContent=t;}
   }
  }
 }
 function retargetTel(){
  var as=document.querySelectorAll('a[href^="tel:"]');
  for(var i=0;i<as.length;i++){
   as[i].href='https://wa.me/'+WA;
   as[i].setAttribute('data-rukn-wa','1');
  }
 }
 function fix(){
  document.documentElement.classList.add('rukn-wa-only','rukn-hide-call');
  if(document.body){document.body.classList.add('rukn-wa-only','rukn-hide-call');}
  var nav=document.querySelector('nav.menu');
  if(nav&&!nav.querySelector('a')){nav.innerHTML=menuHtml();}
  var mob=document.querySelector('#ruknMob');
  if(mob&&!mob.querySelector('a.rukn-nav-link')){
   var wa=mob.querySelector('a.btn-wa');
   var box=document.createElement('div');box.innerHTML=menuHtml();
   while(box.firstChild){if(wa){mob.insertBefore(box.firstChild,wa);}else{mob.appendChild(box.firstChild);}}
  }
  var imgs=document.querySelectorAll('header .logo img[data-loader-src]');
  for(var i=0;i<imgs.length;i++){if(!imgs[i].getAttribute('src')) imgs[i].src=imgs[i].getAttribute('data-loader-src');}
  var ix=document.querySelectorAll('a[href*="index.php/"]');
  for(var x=0;x<ix.length;x++){ix[x].href=ix[x].href.replace('/index.php/','/');}
  var labels=document.querySelectorAll('[aria-label="اختر الإمارة"]');
  for(var l=0;l<labels.length;l++){labels[l].setAttribute('aria-label','اختر المدينة');}
  var eg=document.querySelectorAll('a[href*="wa.me/201151481000"]');
  for(var e=0;e<eg.length;e++){eg[e].outerHTML='<span class="kayan-credit">KAYAN WEB</span>';}
  replaceText();
  fillCounts();
  stripEmptyRating();
  retargetTel();
  ensureFabs();
 }
 if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',fix);}else{fix();}
 setTimeout(fillCounts,400);
 setTimeout(fillCounts,1400);
})();
</script>
"""


def run(cmd: str, write: bool = True, timeout: int = 90) -> dict:
    out = cli(cmd, write=write, timeout=timeout)
    print(cmd[:120], "exit", out.get("exit_code"), (out.get("stdout") or out.get("stderr") or out.get("message") or "")[:220], flush=True)
    return out


def option_update(key: str, value: str) -> dict:
    cmd = f"option update {key} --format=json {json.dumps(value, ensure_ascii=False)}"
    return run(cmd, write=True, timeout=120)


def leak_ids() -> list[int]:
    likes = " OR ".join(f"post_content LIKE '%{old}%'" for old, _ in REPLACES)
    sql = (
        "SELECT ID FROM 2GGpPu6Sy_posts WHERE post_status='publish' AND post_type='post' AND ("
        + likes
        + ") ORDER BY ID"
    )
    out = cli(f'db query "{sql}" --limit=500', write=False, timeout=60)
    rows = []
    raw = out.get("stdout") or ""
    try:
        data = json.loads(raw)
        rows = data.get("results") or data
    except json.JSONDecodeError:
        print("leak id parse", raw[:300])
        return []
    ids = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("ID"):
                ids.append(int(row["ID"]))
            elif isinstance(row, (int, str)):
                ids.append(int(row))
    print("leak ids", len(ids), flush=True)
    return ids


def scrub_post(pid: int) -> str:
    code, data = req("GET", f"/wp/v2/posts/{pid}&context=edit&_fields=id,content", timeout=60)
    if code != 200:
        return f"{pid} get-{code}"
    raw = ((data.get("content") or {}).get("raw")) or ""
    new = raw
    for old, repl in REPLACES:
        new = new.replace(old, repl)
    if new == raw:
        return f"{pid} skip"
    code, out = req("POST", f"/wp/v2/posts/{pid}", {"content": new}, timeout=90)
    if code not in (200, 201):
        return f"{pid} post-{code}:{str(out)[:80]}"
    return f"{pid} ok"


def scrub_leaks() -> None:
    ids = leak_ids()
    if not ids:
        print("no leak ids", flush=True)
        return
    ok = skip = err = 0
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(scrub_post, pid): pid for pid in ids}
        for fut in as_completed(futs):
            try:
                msg = fut.result()
            except Exception as exc:  # noqa: BLE001
                msg = f"{futs[fut]} exc:{exc}"
            print(msg, flush=True)
            if msg.endswith(" ok"):
                ok += 1
            elif msg.endswith(" skip"):
                skip += 1
            else:
                err += 1
            time.sleep(0.05)
    print(f"leaks ok={ok} skip={skip} err={err}", flush=True)


def main() -> int:
    if not os.environ.get("WP_APP_PASSWORD"):
        print("WP_APP_PASSWORD missing", file=sys.stderr)
        return 1

    print("=== header chrome ===", flush=True)
    option_update("header___codes", HEADER_CODES)

    run(
        "option patch update rank-math-options-titles homepage_description "
        "'خدمات منزلية متكاملة في مملكة البحرين: كشف تسربات، عزل، صيانة، تكييف، سباكة، تنظيف ومكافحة حشرات. "
        "صفحات تفصيلية لـ 8 مدن وتواصل واتساب.'"
    )
    run(
        "option update blogdescription "
        "'ركن التطور البحرين: خدمات منزلية في المنامة والمحرق والرفاع و5 مدن بصفحات تفصيلية. تواصل واتساب.'"
    )
    run(f"option patch update HomeIntro slider_intro_v1 hide_call_button on")
    run("option delete _rukn_chrome_probe", write=True)

    print("=== leak scrub ===", flush=True)
    scrub_leaks()

    likes = " OR ".join(f"post_content LIKE '%{old}%'" for old, _ in REPLACES)
    run(
        'db query "SELECT COUNT(*) AS leak_left FROM 2GGpPu6Sy_posts WHERE post_status=\'publish\' '
        f"AND post_type='post' AND ({likes})\"",
        write=False,
    )
    run(
        'db query "SELECT COUNT(*) AS air_left FROM 2GGpPu6Sy_posts WHERE post_status=\'publish\' '
        "AND post_type='post' AND post_content LIKE '%الشحن الجوي%' "
        "AND post_title NOT LIKE '%شحن%' AND post_title NOT LIKE '%جوي%'\"",
        write=False,
    )
    run("cache purge --url=https://www.rukn-eltatawer.com/bh/,https://www.rukn-eltatawer.com/bh/home-cleaning-muharraq/")
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
