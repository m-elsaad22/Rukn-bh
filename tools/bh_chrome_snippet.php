/**
 * Rukn BH Chrome SEO — Code Snippets companion (do not disable id 5).
 * Honest homepage stats, WhatsApp-only chrome, hide empty ratings.
 */
if ( ! defined( 'ABSPATH' ) ) {
	return;
}

if ( ! function_exists( 'rukn_bh_chrome_html' ) ) {
	function rukn_bh_chrome_html( $html ) {
		if ( ! is_string( $html ) || $html === '' ) {
			return $html;
		}
		$lead = ltrim( $html );
		if ( stripos( $lead, '<html' ) === false && stripos( $lead, '<!doctype html' ) === false ) {
			return $html;
		}

		$wa = defined( 'RUKN_BH_WA' ) ? RUKN_BH_WA : '971586634710';

		$html = str_replace(
			array(
				'[[عدد المشاريع]]',
				'مشروع منفّذ',
				'[[سنة التأسيس]]',
				'في البحرين منذ',
				'اتصال أو واتساب',
				'اتصل أو واتساب',
				'اتصال أو واتساب على مدار الأسبوع',
				'تواصل وتشخيصاتصال أو واتساب',
				'معتمدون من الجهات المختصة',
				'تغطية 12 مدينة',
				'نطاق التغطية 12 مدن',
				'12 مدن منطقة',
				'لا نسعّر عبر الهاتف',
				'من أول اتصال حتى إغلاق المشكلة',
			),
			array(
				'1648',
				'صفحة مدينة×خدمة',
				'محلي',
				'فريق داخل البحرين',
				'واتساب',
				'واتساب',
				'واتساب على مدار الأسبوع',
				'تواصل وتشخيص عبر واتساب',
				'فريق يعمل داخل البحرين',
				'صفحات تفصيلية لـ 8 مدن',
				'8 مدن بصفحات تفصيلية',
				'8 مدن بصفحات',
				'لا نسعّر من الرسالة دون معاينة',
				'من أول واتساب حتى إغلاق المشكلة',
			),
			$html
		);

		$html = preg_replace(
			'/(<(?:b|div)[^>]*data-count="(\d+)"[^>]*)>0(<\/(?:b|div)>)/i',
			'$1>$2$3',
			$html
		);
		$html = str_replace( 'data-count="12"', 'data-count="8"', $html );
		$html = preg_replace(
			'/(<(?:b|div)[^>]*data-count="8"[^>]*)>12(<\/(?:b|div)>)/i',
			'$1>8$2',
			$html
		);

		$html = preg_replace(
			'#<script type="application/ld\+json">\s*\{[^{}]*"@type"\s*:\s*"LocalBusiness"[^{}]*"aggregateRating"[^{}]*\}\s*</script>#is',
			'',
			$html
		);
		$html = preg_replace(
			'#,"aggregateRating":\{"@type":"AggregateRating","ratingValue":"","reviewCount":""\}#',
			'',
			$html
		);

		$html = preg_replace(
			'/<a\b([^>]*?)href=["\']tel:[^"\']+["\']([^>]*)>/i',
			'<a$1href="https://wa.me/' . $wa . '" data-rukn-wa="1"$2>',
			$html
		);

		if ( strpos( $html, 'id="rukn-bh-chrome-css"' ) === false ) {
			$css = '<style id="rukn-bh-chrome-css">'
				. '.fab-call,.btn-call,a[href^="tel:"],.kayan-customer-ratings,.--rating--widgets--box,.--YC-single-rating-box--{display:none!important}'
				. 'body.rukn-hide-call .fab-call,body.rukn-wa-only .fab-call{display:none!important}'
				. '</style>';
			if ( strpos( $html, '</head>' ) !== false ) {
				$html = str_replace( '</head>', $css . '</head>', $html );
			} else {
				$html = $css . $html;
			}
		}

		return $html;
	}
}

add_action(
	'template_redirect',
	static function () {
		if ( is_admin() || wp_doing_ajax() || wp_doing_cron() ) {
			return;
		}
		ob_start( 'rukn_bh_chrome_html' );
	},
	-20
);
