# إصلاحات محتوى SEO عبر REST

السكربت: `tools/wp_seo_content_fixes.py`

يتصل بـ `/wp-json/wp/v2/` (Application Password من البيئة أو `~/.config/rukn-bh/wp.env`).

## المهام

1. **FAQ:** حذف عناصر أكورديون H2 المكررة داخل `-YC-FaqsSimple` وإبقاء نسخة واحدة، مع تنظيف `FAQPage` JSON-LD.
2. **الصورة البارزة:** تعيين مرفق `rukn-eltatawer-picture.webp`.
3. **التآكل:** تحويل السلاق الأضعف إلى `draft` وإخراج قواعد 301:
   - `grass-wall-{city}` → `wall-grass-{city}`
   - `artificial-grass-grdn-{city}` → `artificial-grass-{city}`

## تشغيل

```bash
python3 tools/wp_seo_content_fixes.py --dry-run
python3 tools/wp_seo_content_fixes.py --limit 1 --apply
python3 tools/wp_seo_content_fixes.py --apply
```

المخرجات في `reports/seo-301-redirects.txt` و`reports/seo-content-fixes-log.csv`.
