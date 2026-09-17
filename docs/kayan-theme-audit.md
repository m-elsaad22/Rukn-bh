# تدقيق قالب KAYAN Theme — نسخة موقع البحرين

**الموقع:** https://www.rukn-eltatawer.com/bh  
**القالب الحي:** `kayan-theme` — **KAYAN Theme 1.4.12**  
**ووردبريس / PHP:** 7.1 / 8.3.33  
**تاريخ الفحص:** 17 سبتمبر 2026  
**النطاق:** قراءة مباشرة لملفات القالب عبر WPVibe (`file/list` + `file/search` + `file/read`) + تحقق حي من HTML. **لم يُعدَّل القالب.**

هذا تقرير أخطاء ونواقص في **القالب نفسه** (لا المحتوى ولا إعدادات الاستضافة إلا حيث يتداخل القالب معها).

---

## الخلاصة التنفيذية

القالب ليس قالب ووردبريس تقليدياً. هو محرّك مخصّص (`ThemeStatic` / «Blade» داخل `syntax.php`) يلتهم الطلب في `template_redirect` ثم `die()`. لذلك اختفت قوالب ووردبريس القياسية (`404.php`, `single.php`, `page.php`, `search.php`, `archive.php`)، وتعطّلت سلوكيات جوهرية: robots.txt، أرشيف الأنواع المخصصة، لغة HTML، وإخراج Rank Math.

النسخة 1.4.12 أصلها **خليجي/إماراتي** (YourColor / Rukn v3) رُكّبت على موقع بحريني في مجلد فرعي `/bh/`. طبقة `kayan-i18n` فيها دولة بحرين، لكن الواجهة والودجات والـ Schema ما زالت تحمل الإمارات كافتراضي هندسي.

أرقام سريعة:

| مؤشر | القيمة |
|---|---|
| ملفات القالب | 574 مسار / 441 ملفاً (327 PHP، 54 CSS، 17 JS) |
| قوالب WP القياسية الموجودة | `index.php` + `functions.php` + `style.css` فقط |
| قوالب WP الناقصة | `single.php` `page.php` `archive.php` `404.php` `search.php` `header.php` `footer.php` `comments.php` `sidebar.php` |
| أرشيف CPT (`/services/` `/reviews/` `/faqs/` `/pricing/` `/portfolio/` `/before-after/`) | **HTTP 500** كلها، وعدد المنشورات = 0 |
| صفحة 404 | الحالة **404** صارت تُرسل، لكن `robots.txt` أيضاً HTML 404 |
| `<nav class="menu">` في الرئيسية | **فارغ** (0 أحرف) رغم وجود قائمة في ووردبريس |
| بقايا الإمارات في الرئيسية الحية | `uae-svg` ×3، `اختر الإمارة` ×5، `passowrd` ×5، `2font-family` / `1font-family` |
| LocalBusiness JSON-LD | حقول فارغة + `aggregateRating` فارغ |
| نطاق الترجمة | `yourcolor` — **لا** `load_theme_textdomain` |

---

## 1) معمارية القالب — ماذا يعمل فعلاً؟

```
kayan-theme/
  style.css          ← الهوية فقط + إصلاح أوزان Font Awesome
  functions.php      ← ThemeTree + تحميل كل حزمة بلا @ و #
  syntax.php         ← ThemeStatic::Locate() يرسم الصفحة ثم die()
  index.php          ← احتياطي نادراً ما يُستدعى
  components/packs/  ← ~80 حزمة (ودجات، Ajax، SEO، حجز، تتبع، سكيما…)
  components/styles/ ← CSS يُحقن inline داخل <style> في الهيدر
```

مسار الطلب:

1. `kayan-stabilization/lockdown.php` يفتح output buffer عند `template_redirect` بأولوية `-1`.
2. `kayan-stabilization/homepage.php` يحاول اعتراض الرئيسية بأولوية `0` عبر `kayan_homepage_v3_render()` — **الدالة غير معرّفة داخل القالب** (نداء ميت / بقايا نظام حُذف في 1.4.10 حسب `readme.txt`).
3. `ThemeStatic::Locate()` يختار `@index` / `@single` / `@page` / `@archive` / `@search` / `@404` ثم **`die()` حتى لو لم يطابق أي شرط**.
4. الهيدر `#header/part.php` والفوتير `#footer/part.php` ليسا `header.php`/`footer.php`.

النتيجة: ووردبريس «الرسمي» (القالب الهرمي، `wp_body_open`، `language_attributes()`، `get_header()`) شبه معطّل. أي خلل في المحرّك = الموقع كله.

---

## 2) أخطاء كبيرة (حرجة)

### 2.1 أرشيفات الأنواع المخصصة تنهار بـ 500

القالب يسجّل في `kayan-cpt/setup.php` ستة أنواع عامة قابلة للفهرسة:

`services` · `reviews` · `faqs` · `pricing` · `portfolio` · `before_after`

التحقق الحي: **كل** المسارات التالية ترجع صفحة خطأ ووردبريس الحرجة (500):

- `/bh/services/`
- `/bh/reviews/`
- `/bh/faqs/`
- `/bh/pricing/`
- `/bh/portfolio/`
- `/bh/before-after/`

وعدد المنشورات عبر REST = **0** لكل نوع. أرشيف فارغ يجب أن يعرض حالة فارغة، لا أن يكسر PHP.

السبب التقني المرجّح داخل `@archive`:

- `shape.php` يحوّل لأرشيف النوع إن وُجد `archive-{post_type}.php`، وإلا يسقط على `default.php`.
- `default.php` يفترض أن `$obj` تصنيف: يستخدم `$obj->taxonomy` و`$obj->term_id` **بدون فحص**. على أرشيف CPT يكون `$obj` من نوع `WP_Post_Type` (لا `taxonomy` ولا `term_id`) → تحذير/خطأ PHP 8.3 داخل `tax_query`.
- حتى قوالب `archive-services.php` وغيرها تستدعي `kayan_kit_hero()` / `kayan_kit_empty()` على كائن نوع المنشور؛ أي خاصية ناقصة أو دالة غير محمّلة في هذا المسار تُسقط الصفحة.

جوجل إن زحف هذه الأرشيفات (مفعّلة في Rank Math كـ `pt_services_sitemap`) سيرى 500 أو يفهرس خطأ.

**ما يحتاجه القالب:** `has_archive => false` ما دامت فارغة، أو قالب أرشيف يفرّق بين `WP_Term` و`WP_Post_Type` ويتحمّل القائمة الفارغة. إصلاح 500 أولوية قصوى.

### 2.2 لا يوجد قالب 404 ووردبريس — والـ robots خُطف

- لا ملف `404.php` في جذر القالب. يوجد فقط `components/packs/@404/shape.php`.
- `kayan_send_404_status()` في `functions.php` يرسل `status_header(404)` إذا `is_404()` — وهذا يعمل الآن على رابط وهمي.
- لكن `/bh/robots.txt` أيضاً **404 HTML** (`text/html` ~198 ك.ب) وليس `text/plain`. الزاحف لا يجد تعليمات الفهرسة لموقع `/bh/`.
- `Locate()` بعد فروع home/archive/single/search/page/404 يستدعي `die()` بلا محتوى إن لم يُطابق شيئاً (feeds تُستثنى فقط).
- صفحة 404 نفسها بلا `<title>` ظاهر، وبلا نص «الصفحة غير موجودة» في العيّنة المقروءة رغم وجود `.err-wrap` / `.err-num` — تجربة ضعيفة + إشارة SEO ضعيفة.

**ما يحتاجه:** `404.php` حقيقي + استثناء `robots.txt` / `sitemap.xml` / `favicon.ico` من محرّك Blade + عنوان ووصف 404.

### 2.3 القائمة الرئيسية تُرسم فارغة

في `#header/part.php` القائمة تُبنى يدوياً من `wp_get_nav_menu_items()` وليس `wp_nav_menu()`:

```php
echo '<nav class="menu">';
foreach ( $rukn_menu_tree as $branch ) { ... }
echo '</nav>';
```

في HTML الحية للرئيسية: **`<nav class="menu"></nav>` بطول 0**.  
`MenuField/setup.php` يفلتر `wp_get_nav_menu_items` لإخفاء عناصر في الرئيسية. Polylang أيضاً يفرّغ عناصر لغة أخرى. النتيجة: زائر البحرين لا يرى روابط الصفحات في الهيدر إلا إذا حقن JS خارجي (`header___codes`) ملأها لاحقاً.

الروابط داخل الحلقة **غير مُهرَّبة**: `href="'.$item->url.'"` — ثغرة XSS مخزّنة عبر عنصر قائمة.

`nav-menus/setup.php` يسجّل موقعاً واحداً فقط: `main-menu`. قوائم الفوتر تُختار بمعرّف خيار لا بموقع قياسي.

### 2.4 تعطيل Rank Math على الواجهة ثم Schema القالب الفارغ

ثلاث طبقات متعارضة:

| الطبقة | ماذا تفعل |
|---|---|
| `kayan-seo/compatibility.php` | `rank_math/frontend/disable` = true، يحذف JSON-LD وOpenGraph من Rank Math |
| `lockdown.php` تعليقات v1.4.2 | «Rank Math مفعّل بالكامل» — **الكود لا يطابق التعليق** |
| `schema/setup.php` + `LocalBusiness.php` | يطبع JSON-LD يدوياً |

الحي على الرئيسية:

```json
"@type": "LocalBusiness",
"name": "", "telephone": "", "image": "",
"address": { "streetAddress": "", "addressLocality": "", "addressCountry": "" },
"aggregateRating": { "ratingValue": "", "reviewCount": "" }
```

أخطاء Schema إضافية:

- `"@context": "http://schema.org"` (HTTP) لا HTTPS.
- `aggregateRating` فارغ = بيانات منظّمة غير صالحة وقد تُرفض.
- في `LocalBusiness.php`: `"Youtube": "...";` **فاصلة منقوطة** تكسر JSON؛ خاصية `socialMedia` ليست من schema.org.
- اسم الخيار `YourColoe_Schema_business` (خطأ إملائي Color→Coloe) والخيار على الموقع **فارغ**.
- `hide_schema_business` بشرط `empty()` يعني المخطط يُطبع حتى لو المصفوفة فارغة.
- سكيما المقال: شرط خاطئ `hide_schema_Service` بدل `hide_schema_Article` (نسخ/لصق).
- `defualt_*` مكررة في السكيما (typo default).
- القالب يطبع عدة كتل `<script type="application/ld+json">` متتالية؛ بعضها قد يخرج `{}` فارغاً.
- `readme.txt` يقول «القالب لا يُخرج أي meta مكررة» بينما يعطّل Rank Math ثم يطبع سكيما يدوية سيئة.

**ما يحتاجه:** مصدر واحد للـ SEO (Rank Math أو KAYAN لا الاثنان). ملء LocalBusiness بحريني أو حذف الكتلة. لا `AggregateRating` إلا بأرقام حقيقية.

### 2.5 بقايا الإمارات داخل القالب (ليست إعدادات الموقع فقط)

حتى بعد ضبط خيارات البحرين، القالب نفسه ما زال إماراتياً في الكود:

| الملف | المشكلة |
|---|---|
| `city__widget.php` | عنوان افتراضي «خدماتنا في جميع إمارات الدولة»؛ كروت دبي/أبوظبي/الشارقة…؛ SVG كلاس `.uae-svg` **ثابت في القالب** حتى لو المدن بحرينية |
| `city__widget.css` | `.uae-svg` |
| `Faqs__simple2.php` | «هل تعملون في جميع إمارات الدولة؟» + قائمة السبع إمارات |
| `rukn_cases.php` / `works.php` / `rukn_reviews.php` / `rukn_results.php` | عيّنات «دبي مارينا» |
| `rukn_stats.php` | «ثقة الآلاف … الإمارات» |
| `rukn_certs.php` | «المعايير المعتمدة في دولة الإمارات» |
| `blog_v1.php` | عناوين مقالات إماراتية |
| `slider_intro_v1.php` | «معتمد من بلدية دبي» |
| `rukn_finder.php` | التعليقات والحقول ما زالت «الإمارة» رغم أن الواجهة صارت «اختر المدينة» |
| `kayan-booking.js` | حقل `emirate` / «الإمارة / المنطقة الرئيسية» |
| `kayan-seed/setup.php` | بذور أبوظبي و«كل إمارة» |
| `kayan-i18n/helpers.php` | الدولة الافتراضية إن فشل الرصد = **`ae`** |
| `kayan-i18n/countries.php` | الإمارات `path => ''` (الجذر)، البحرين `path => '/bh'` — على تثبيت أصلاً داخل `/bh/` هذا يولّد مسارات مزدوجة `/bh/bh/...` |

التحقق الحي للرئيسية: `uae-svg` موجود، «اختر الإمارة» **5 مرات**، «اختر المدينة» مرتين، كلمة «دبي» مرتين.

`style.css` و`readme` يدّعيان «لا يفرض مدناً أو محتوى تجريبي» و«لا خريطة دبي» — هذا صحيح **فقط** إذا أُطفئ «المحتوى الافتراضي». خريطة الإمارات (SVG) ليست خياراً: هي HTML ثابت.

### 2.6 لغة HTML ثابتة عربي/RTL — نظاما ترجمة متوازيان

`#header/part.php` يطبع:

```html
<html lang="ar" dir="rtl">
```

ولا يستدعي `language_attributes()`.  
`kayan_i18n_filter_language_attributes()` موجودة لكن **لا تُطبَّق** لأن الوسم لا يمر من ووردبريس.

في الوقت نفسه:

- Polylang مفعّل (`ar`/`en`).
- `kayan-i18n` يسجّل قواعد `^en/` و`^bh/en/` ويحوّل الطلب إلى `is_home` إذا وُجدت دولة/لغة بلا slug — هذا مصدر محتمل لصفحات إنجليزية وهمية أو soft-home.
- لا ملفات `.po/.mo`، ولا `load_theme_textdomain('yourcolor')`.
- نطاق النص مخلوط: `yourcolor` / `YourColor` / `'yourcolor'` داخل `__()` بثلاث وسائط **غير صالحة** في `functions.php` (`__($name, 'yourcolor', 'post type general name')` — ووردبريس يقبل وسيطين فقط).

الإنجليزية في هذا القالب على موقع البحرين غير قابلة للعمل من الهيدر أصلاً.

### 2.7 أمان: Ajax بلا nonce، تقييمات وتعليقات مفتوحة، تسريب جلسة

**AjaxCenter** (`/AjaxCenter/{action}/`) يحمّل أي ملف PHP في المجلد بعد `sanitize_key` — أفضل من LFI القديم، لكن أغلب النقاط **عامة بلا nonce**:

| الملف | الخطر |
|---|---|
| `fields-loadmore.php` | `base64_decode($_POST['args'])` ثم استعلام منشورات |
| `MenusInitialize.php` / `TabsActions.php` / `More-Ajax-objects.php` / `PopoverActions.php` | نفس النمط |
| `AddComment.php` | إدراج تعليق من `$_POST` بلا nonce ولا `sanitize_*` ولا التحقق من البريد؛ خيار `default_comments_approval` للموافقة التلقائية؛ تحديث تقييمات Woo-style |
| `RateAjax.php` | أي زائر يرفع `RatingValue_v1` على أي منشور/تصنيف بلا حد ولا nonce (تضخيم تقييمات) |
| `YC-Scrape/setup.php` | كاشط محتوى + `var_dump` + `print_r` حيّة في مسار الإنتاج |
| `export-import/.../extract.php` | `@unserialize` على بيانات مستوردة |
| `syntax.php` `UploadPhoto()` | تنزيل صورة من URL وكتابتها في uploads |
| `syntax.php` `TryToLogin()` | `wp_set_auth_cookie(..., true, false)` — كوكي غير آمن على HTTPS |
| `Custom-Setup.js:534` | `j = eval("(" + text + ")")` |
| `#header/part.php` | `echo get_option('header___codes');` HTML/JS خام في `<head>` |
| `#header/part.php` | `open_css` يخزّن **IP الزائر** في `wp_options` عبر `?open__css` |

في تذييل كل صفحة:

```js
var Currentuser_email = '';
var Currentuser_Logged = true;  // دائماً true حتى للزائر!
```

للمستخدم المسجّل تُسرَّب `first_name` و`last_name` و`email` و`ID` في HTML. `Currentuser_Logged = true` يكسر أي JS يعتمد على الحالة.

`disable_all_scripts` بأولوية `999999` يلغي تقريباً كل سكربتات الإضافات على الواجهة (ما عدا بادئات محمية). Polylang/نماذج/إضافات أخرى قد تموت بصمت.

### 2.8 أداء الواجهة: CSS inline + jQuery 3.4.1 + CDN خارجي

- كل `forms.css` + `main.css` + `hover.css` + `responsive.css` + `rukn-v3.css` + الخطوط تُحقن بـ `require` داخل `<style>` في كل طلب. الرئيسية الحية ≈ **309 ك.ب HTML**. 404 ≈ **198 ك.ب**. لا كاش للمتصفح على CSS.
- عند `?open__css` تتحول إلى روابط مع `?v='.rand()` (كسر كاش دائم) وتُسجَّل IP.
- `Enqueues/setup.php` يلغي jQuery ووردبريس ويحمّل **jquery-3.4.1.min.js** (2019، ثغرات XSS معروفة) من مجلد `#footer`.
- الخطوط من Google Fonts (fonts.googleapis.com) رغم أن readme يقول Font Awesome محلي فقط — Cairo/Tajawal خارجيان.
- PhotoSwipe من **unpkg.com** بلا تثبيت إصدار ثابت في أحد الاستيرادات.
- `<link rel="preload" as="font">` بلا `href` (تلميح أداء فارغ/خطأ).
- `meta http-equiv="Cache-control" content="public"` في الهيدر.
- عدّاد الزيارات على كل مقال مفرد: `update_post_meta` لـ `trending` في `Locate()` — كتابة DB في كل مشاهدة مقال.

### 2.9 HTML غير صالح وإتاحة ضعيفة

- وسم مخصّص `<root>` يلف الصفحة (غير HTML5 قياسي؛ قد يُكسر في بعض المتصفحات/قارئات).
- لا `wp_body_open()` ولا رابط تخطٍ (`skip-link`).
- `body mode="light"` خاصية غير قياسية.
- أزرار القائمة: `onclick="ruknToggleMob(true)"` بلا `type="button"`.
- لا `comments.php` — التعليقات عبر AjaxCenter فقط.
- لا سايدبار ووردبريس (`sidebars_widgets` غير مستخدم في التدقيق السابق).
- `orderFooter` يضيف `rel="nofollow noopener noreferrer"` على **كل** `target="_blank"` بما فيها واتساب والسووشيال — يضعف إشارات الروابط الخارجية الشرعية.

---

## 3) أدق الأخطاء الصغيرة (typos / بقايا / عدم اتساق)

هذه ليست تجميلية فقط: بعضها يكسر CSS أو يمنع حفظ الإعدادات أو يضلّل لوحة التحكم.

| الخطأ | أين | الأثر |
|---|---|---|
| `passowrd-level` بدل `password-level` | `components/styles/forms.css` (4 قواعد) + **5 ظهور** في HTML الحية | مؤشر قوة كلمة المرور في النماذج لا يتطابق مع JS إن استخدم الاسم الصحيح |
| `2font-family` و `1font-family` | CSS المضمّن الحي (التصق رقم سطر/قاعدة بـ `font-family` عند `require` ملفات بلا سطر أخير) | `@font-face` معطوب → الخطوط الاحتياطية |
| `company__adress` / `footer__company__adress_url` | الفوتر + خيارات الثيم | خطأ إملائي مزمن (address)؛ أي كود يبحث عن `address` لا يجده |
| `YourColoe_Schema_business` | `LocalBusiness.php` | Color ناقصة r؛ الخيار فارغ لأن الاسم خاطئ منذ الأصل |
| `text_Color` مقابل `site_color` | الهيدر | عدم اتساق أسماء الخيارات |
| `Configration` | مجلد `export-import/Configration-Actions` | Configuration |
| `defualt_ImageObject` / `defualt_Service` | `schema/setup.php` | default |
| `HTML_otput` | `#footer/part.php` | output |
| `attchment` | `@empty__objects/object--empty.php` | attachment |
| `hide__description_show` منطق مقلوب الاسم | kayan-seo | الاسم يعني «إخفاء» لكن يُستخدم كقاطع للوصف |
| `seo__title_showsin` | theme-seo | shows in |
| `footer('Content-type: ...')` | `#footer/part.php` وضع Ajax | الدالة الصحيحة PHP هي `header()` — تعليق المبرمج نفسه: «HERE IS THE PROBLEM» |
| `ob_get_clean()` مرتين في مسار Ajax بالفوتر | بعد `ob_get_clean()` للهيدر/الجسم يُستدعى مرة ثانية | مسار `?ajax=1` يعيد مخرجات فارغة/مكسورة |
| `Currentuser_Logged = true` دائماً | الفوتر JS | خطأ منطقي |
| `__()` بثلاث وسائط | `ThemeTree::AddTaxonomy` / `AddPType` | الترجمات لا تُحمَّل |
| `register_post_type` في `AddPType` بلا `show_in_rest` ولا `has_archive` مضبوط | functions.php | الـ CPT القديمة غير مكتملة |
| تصنيف الباحث `city` vs التسجيل `cities` | `rukn_finder.php` vs `kayan-cpt` | الوضع التلقائي للمدن لا يجد المصطلحات |
| جدول ثابت `wp_postmeta` | `syntax.php` `UploadImageCheck` | ينكسر إن تغيّر بادئة الجداول |
| `mb_convert_encoding(..., 'HTML-ENTITIES')` | YC-Scrape | deprecated في PHP 8.2+ |
| `style.css` Version **1.4.12** مقابل `readme.txt` Stable tag **1.4.10** و«Tested up to: 6.7» | الجذر | الموقع على WP **7.1** — ملف التعريف متخلف |
| Text Domain في `style.css`: `yourcolor` | الهوية | القالب يُسمّى KAYAN |
| `KAYAN-BOOKING-PHASE1-CHANGELOG.md` و`كيفية-الرفع-الصحيح-اقرأني.txt` | جذر القالب | ملفات تطوير ظاهرة إن سُمح بتصفح المجلد |
| `.php-tmp` | ملف واحد في الشجرة | بقايا رفع |
| `print_r` حي في `ThemeOptions.php:193` وفي scrape/import | الأدمن/الاستيراد | تسريب بنية الحقول |
| `console.log` في `Custom-Setup.js` | لوحة الحقول | ضجيج إنتاج |
| تعليقات `kayan-stabilization` «v2027.3.9+» | lockdown | تاريخ/إصدار غير متسق مع 1.4.12 |
| `GetCurrentURL()` يبدأ `http` ثم يضيف s | syntax.php | يعتمد على `HTTPS` فقط، يخطئ خلف proxy |
| `wp_redirect` على `?page=` و`?s=` ثم `die()` | Locate() | قد يكسر ترقيم ووردبريس/البحث |

---

## 4) ماذا ينقص القالب؟

### قوالب ووردبريس القياسية
`404.php` `single.php` `page.php` `archive.php` `search.php` `header.php` `footer.php` `home.php`/`front-page.php` `comments.php` `sidebar.php` `screenshot` موجود لكن لا child-theme.

### توطين البحرين داخل المحرّك
- خريطة/كلاس `bh-svg` بدل `uae-svg`.
- عيّنات ودجات: المنامة/المحرق/الرفاع لا دبي مارينا.
- حقل الحجز: محافظة/مدينة لا «إمارة».
- افتراضي `kayan_i18n` = `bh` في الكود لا `ae`.
- `html lang="ar-BH"` أو من Polylang، و`dir` حسب اللغة.
- رقم `wa.me` يُنظَّف من `+` والمسافات (الهيدر يمرّر الخيار كما هو؛ `kayan_wa_sanitize_number` موجودة في `kayan-ui/helpers.php` **ولا تُستخدم** في الهيدر/الفوتر).

### SEO تقني داخل القالب
- عدم تعطيل Rank Math إذا كان هو مصدر الحقيقة.
- أو العكس: إكمال KAYAN SEO (Open Graph، canonical، robots، hreflang صحيح، JSON-LD واحد).
- الآن: OG يظهر من Rank Math في العيّنة الحية (`og:` ×11) **رغم** `frontend/disable` — الطبقتان تتسابقان حسب ترتيب التحميل والكاش. هذا يفسّر أوصافاً مكررة سابقاً.
- لا معالجة `robots.txt` لمجلد فرعي.
- لا `title` على 404.
- أرشيفات CPT العامة الفارغة.

### أمان وحدود
- nonce + `current_user_can` على AjaxCenter.
- إيقاف `RateAjax` العام أو تقييده بكوكي/IP.
- حذف أو عزل `YC-Scrape` من الإنتاج.
- عدم طباعة بيانات المستخدم في JS.
- `header___codes` عبر `wp_kses` أو إيقافه (lockdown يمنع إلا إذا `kayan_lockdown_allow_header_injection=1` وهو **مفعّل** على هذا الموقع).
- إزالة `eval` و`unserialize` غير الآمن.

### جودة الواجهة
- قائمة تُرسم بـ `wp_nav_menu` مع walker أو تهريب `esc_url`/`esc_html`.
- قائمة جوال فيها نفس الشجرة (الآن تعتمد على الشجرة الفارغة نفسها).
- `type="button"`، `aria-expanded` للقائمة، skip link، معلمات `lang`.
- عدم لف الصفحة بـ `<root>`.
- jQuery من ووردبريس (3.7+) لا 3.4.1.
- CSS/JS عبر `wp_enqueue_*` مع إصدار القالب لا inline+rand.
- صورة الشعار: لا مقاس 90×23؛ `custom_logo` في theme_mods.

### محتوى القالب vs موقع المقالات
الموقع يعمل بـ 1600+ **مقالة** `post` × مدينة. القالب مصمّم لـ CPT `services`/`reviews`/`portfolio`. الهوّة تفسّر ودجات فارغة، أرشيفات 500، وبطاقات تذهب لـ `/contact-us/`.

ينقص:

- ربط الودجات بتصنيف `cities` (الموجود) لا `city`.
- أو ملء CPT وإخفاء أرشيف المقالات كواجهة خدمات.
- صفحة مدونة حقيقية: الفوتر يضع افتراضياً `home_url('/blog/')` وهو على هذا الموقع أرشيف/شبه رئيسية لا قالب مدونة.

### توثيق وإصدار
- توحيد 1.4.12 في `style.css` و`readme.txt`.
- اختبار على WP 7.1 / PHP 8.3 (التصريح «Tested up to 6.7»).
- حذف ملفات الرفع المؤقت والتعليمات من جذر القالب على الإنتاج.

---

## 5) ماذا يحتاج القالب — ترتيب عمل تقني

لا تقدير زمني؛ حسب التداخل والمخاطر:

1. **إيقاف النزيف:** `has_archive => false` للأنواع الفارغة أو إصلاح `@archive/default.php` حتى لا يمسّ خصائص تصنيف على `WP_Post_Type`. التحقق أن `/services/` لم يعد 500.
2. **404 + robots:** استثناء الملفات الخاصة من `Locate()`؛ قالب 404 بعنوان؛ `robots.txt` نصي لمسار `/bh/`.
3. **قائمة:** `wp_nav_menu` + تهريب + عدم إفراغ Polylang للعناصر المشتركة؛ قائمة جوال من نفس المصدر.
4. **سكيمة وتواصل:** مصدر SEO واحد؛ LocalBusiness باسم ركن التطور / المنامة / BH؛ حذف AggregateRating الفارغ؛ استخدام `kayan_wa_sanitize_number` في الهيدر/الفوتر/الـ FAB.
5. **توطين البحرين في المصدر:** استبدال `.uae-svg` وعيّنات دبي/إمارة؛ افتراضي i18n = `bh`؛ `lang` ديناميكي.
6. **أمن Ajax والفوتر JS:** nonce؛ `Currentuser_Logged` حقيقي؛ لا بريد في الصفحة.
7. **أصول حديثة:** إنqueue لا require؛ jQuery كور؛ إصلاح `passowrd` و`font-family` الملتصق؛ إنهاء preload الفارغ.
8. **تنظيف محرّك قديم:** YC-Scrape، eval، جدول wp_postmeta الثابت، `__()` الثلاثي، ملف `.php-tmp`.
9. **قرار منتج:** إما تشغيل CPT (خدمات/تقييمات/أعمال) وملؤها، أو إيقاف تسجيلها حتى لا تُفهرس/تنهار.

---

## 6) خريطة الحزم (للمرجع)

حزم جذر `components/packs/` ذات أثر مباشر على البحرين:

| حزمة | الدور | ملاحظة لهذا الموقع |
|---|---|---|
| `#header` / `#footer` | الهيكل الحي | قائمة فارغة، RTL ثابت، FAB هاتف، JS مستخدم |
| `@404` `@archive` `@single` `@page` `@search` `@index` | القوالب الفعلية | أرشيف CPT = 500 |
| `kayan-cpt` | تسجيل الأنواع | عامة + أرشيف مفعّل رغم صفر محتوى |
| `kayan-i18n` | دول خليجية + en | افتراضي ae؛ قواعد `/bh` فوق تثبيت `/bh` |
| `kayan-seo` | تعطيل Rank Math فرونت | يتعارض مع lockdown/readme |
| `schema` | JSON-LD يدوي | فارغ + أخطاء إملائية |
| `YourColorWidgets` | الرئيسية | بقايا الإمارات |
| `AjaxCenter` | نماذج/تحميل/تعليق/تقييم | بلا nonce في الغالب |
| `RuknContact` | أرقام هرمية مقال←تصنيف←عام | الهاتف مخفي CSS؛ واتساب من الخيار العام |
| `RuknUX` | TOC | innerHTML |
| `kayan-ui` | kit-pages + إخفاء أزرار اتصال | JS `removeCallButtons` |
| `kayan-stabilization` | lockdown + homepage v3 ميت | buffer + فلتر سكربتات |
| `kayan-performance` | preload شعار | يعتمد yc_get_option |
| `kayan-booking` / `kayan-payment` / `kayan-price-pay` | حجز ودفع | حقل إمارة |
| `kayan-track` | تتبع | DNI REST `/kayan/v1/dni` |
| `YC-Scrape` / `export-import` | كشط واستيراد | غير مناسب للإنتاج |
| `FieldsMachine` | لوحة خيارات ضخمة (123 ملفاً) | `eval` في Custom-Setup.js |
| `Enqueues` | إلغاء أصول WP | jQuery 3.4.1 |

`index.php` داخل `components/` و`components/packs/` و`components/styles/` فارغ/حماية مجلد — جيد.

---

## 7) ما الذي تغيّر منذ تدقيق الموقع السابق؟

مقارنة سريعة مع تقرير الموقع (16 سبتمبر):

| بند | السابق | القالب 1.4.12 اليوم |
|---|---|---|
| إصدار القالب | 1.4.2 في التقرير القديم | **1.4.12** |
| حالة 404 الوهمي | 200 + الرئيسية | **404** (تحسّن) لكن الصفحة بدينة وبلا title |
| robots.txt `/bh/` | HTML الرئيسية 200 | HTML **404** (ما زال غير صالح كروبوتس) |
| أرشيف `/services/` | 200 فارغ بعنوان إنجليزي | **500** (أسوأ) |
| «اختر الإمارة» في finder.php | كان في السطر 125 | صار «اختر المدينة» في PHP — **لكن النص ما زال يظهر 5 مرات** من ودجات/JS أخرى |
| رقم مصر في القالب | كان في الفوتر | **غير موجود في ملفات القالب الحالية** |
| مقر دبي كافتراضي فوتر | نص افتراضي | لا يُطبع إن فراغ الخيار؛ الخريطة SVG الإمارات ما زالت في ودجت المدن |
| قائمة HTML | فارغة | ما زالت فارغة |

أي أن ترقية القالب إلى 1.4.12 أصلحت 404 status وعبارة الباحث في ملف واحد، وكسرت أرشيفات CPT، وتركت التوطين البصري والإماراتي والـ Schema على حالها.

---

## 8) منهج الفحص

- `GET /wpvibe/v1/site-info` و`file/list` (574 مساراً، `editable: false`).
- `file/search` لعشرات الأنماط: أخطاء إملائية، الإمارات، tel/wa، eval، Ajax، Schema، القوالب، nonce.
- `file/read` للملفات الحرجة: `functions.php` `syntax.php` `style.css` الهيدر/الفوتر، lockdown، schema، CPT، i18n، SEO، AjaxCenter، الودجات، `@archive`، `@404`، Enqueues، kit-pages.
- طلبات حية: الرئيسية، 404، robots، أرشيفات CPT، REST counts.
- لم تُكتب ملفات على الخادم ولم تُغيَّر خيارات.

---

## خاتمة

القالب قوي كمنصّة خدمات خليجية (ودجات، حجز، تتبع، لوحة حقول)، لكنه **غير مكتمل كقالب ووردبريس** و**غير موطَّن للبحرين في المصدر**. أكبر عيوبه الآن ليست «نقص ديكور» بل: أرشيفات 500، محرّك يبتلع robots، قائمة فارغة، Schema فارغ، طبقتا SEO متضاربتان، Ajax مفتوح، وبقايا الإمارات في الواجهة.

إصلاح المحتوى وحده لن يكفي: الأخطاء المذكورة أعلاه في ملفات `kayan-theme` ويجب معالجتها في القالب (أو child واضح)، وهذا الموقع `DISALLOW_FILE_EDIT` لذا التعديل يتم بحزمة قالب جديدة لا من محرّر ووردبريس.
