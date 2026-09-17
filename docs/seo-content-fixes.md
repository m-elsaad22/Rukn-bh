# إصلاحات محتوى SEO عبر REST

السكربت: `tools/wp_seo_content_fixes.py`

نُفِّذ على الموقع الحي في 17 سبتمبر 2026. **0 فشل.** كاش LiteSpeed أُفرغ بعد التحديث.

## النتائج

| مهمة | النتيجة |
|---|---|
| تنظيف FAQ المكرر | 1648 مقالاً منشوراً — عناصر الأكورديون الفريدة فقط (عيّنة: 9 → 4) |
| صورة بارزة | `featured_media = 1587` (`rukn-eltatawer-picture.webp`) |
| تآكل الكلمات | 16 مقالاً → `draft` — المنشور الآن **1648** |
| PUT فاشل | 0 |

## قواعد 301 — Rank Math أو .htaccess

الصق هذا في Rank Math → Redirections، أو في `.htaccess`:

```
Redirect 301 /bh/grass-wall-manama/ https://rukn-eltatawer.com/bh/wall-grass-manama/
Redirect 301 /bh/grass-wall-muharraq/ https://rukn-eltatawer.com/bh/wall-grass-muharraq/
Redirect 301 /bh/grass-wall-riffa/ https://rukn-eltatawer.com/bh/wall-grass-riffa/
Redirect 301 /bh/grass-wall-hamad-town/ https://rukn-eltatawer.com/bh/wall-grass-hamad-town/
Redirect 301 /bh/grass-wall-isa-town/ https://rukn-eltatawer.com/bh/wall-grass-isa-town/
Redirect 301 /bh/grass-wall-aali/ https://rukn-eltatawer.com/bh/wall-grass-aali/
Redirect 301 /bh/grass-wall-sitra/ https://rukn-eltatawer.com/bh/wall-grass-sitra/
Redirect 301 /bh/grass-wall-budaiya/ https://rukn-eltatawer.com/bh/wall-grass-budaiya/
Redirect 301 /bh/artificial-grass-grdn-manama/ https://rukn-eltatawer.com/bh/artificial-grass-manama/
Redirect 301 /bh/artificial-grass-grdn-muharraq/ https://rukn-eltatawer.com/bh/artificial-grass-muharraq/
Redirect 301 /bh/artificial-grass-grdn-riffa/ https://rukn-eltatawer.com/bh/artificial-grass-riffa/
Redirect 301 /bh/artificial-grass-grdn-hamad-town/ https://rukn-eltatawer.com/bh/artificial-grass-hamad-town/
Redirect 301 /bh/artificial-grass-grdn-isa-town/ https://rukn-eltatawer.com/bh/artificial-grass-isa-town/
Redirect 301 /bh/artificial-grass-grdn-aali/ https://rukn-eltatawer.com/bh/artificial-grass-aali/
Redirect 301 /bh/artificial-grass-grdn-sitra/ https://rukn-eltatawer.com/bh/artificial-grass-sitra/
Redirect 301 /bh/artificial-grass-grdn-budaiya/ https://rukn-eltatawer.com/bh/artificial-grass-budaiya/
```

الملفات الجاهزة: `reports/seo-301-htaccess.txt` و`reports/seo-301-rankmath.csv` و`reports/seo-301-redirects.txt`.

## تشغيل لاحق

```bash
python3 tools/wp_seo_content_fixes.py --dry-run
python3 tools/wp_seo_content_fixes.py --apply
```
