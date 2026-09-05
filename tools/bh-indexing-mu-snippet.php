<?php
/**
 * Bahrain site indexing, locale, stats, and WhatsApp-only contact.
 * WPCode snippet 3257 — keep published/active.
 */
if ( ! defined( 'ABSPATH' ) ) {
	return;
}

add_filter(
	'kayan_i18n_countries',
	static function ( $countries ) {
		if ( isset( $countries['bh'] ) ) {
			$countries['bh']['path']       = '';
			$countries['bh']['regions_ar'] = 'كل مدن مملكة البحرين';
			$countries['bh']['regions_en'] = 'All cities of Bahrain';
		}
		return $countries;
	}
);

add_action(
	'init',
	static function () {
		if ( get_option( 'kayan_i18n_default_country' ) !== 'bh' ) {
			update_option( 'kayan_i18n_default_country', 'bh', false );
		}
	},
	1
);

add_filter(
	'body_class',
	static function ( $classes ) {
		$classes[] = 'rukn-hide-call';
		$classes[] = 'rukn-wa-only';
		return $classes;
	}
);

function rukn_bh_seo_fix_text( $text ) {
	if ( ! is_string( $text ) || $text === '' ) {
		return $text;
	}
	$wa   = '971586634710';
	$img  = 'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp';
	$text = str_replace(
		array(
			'اتصل أو أرسل واتساب على [[رقم الهاتف/واتساب]] ونرد عليك لتحديد الموعد.',
			'اتصل أو أرسل واتساب على [[رقم الهاتف/واتساب]]',
			'اتصل أو أرسل واتساب على +971586634710 ونرد عليك لتحديد الموعد.',
			'اتصل أو أرسل واتساب على +971586634710',
			'{PHONE_RUKN_BAHRAIN}',
			'{WHATSAPP_RUKN_BAHRAIN}',
			'[[رقم الهاتف/واتساب]]',
			'[[عدد المشاريع]]',
			'[[سنة التأسيس]]',
			'+350',
			'كل مدن المملكة',
			'مدن المملكة',
			'داخل المملكة',
			'يغطي المملكة',
			'https://www.rukn-eltatawer.com/bh/index.php/contact-us/',
			'https://rukn-eltatawer.com/bh/index.php/contact-us/',
			'rukn-eltatawer.com/bhbh',
			'rukn-eltatawer.com/bh/bh/',
		),
		array(
			'أرسل واتساب وسنحدد موعد المعاينة.',
			'أرسل واتساب وسنحدد موعد المعاينة',
			'أرسل واتساب وسنحدد موعد المعاينة.',
			'أرسل واتساب وسنحدد موعد المعاينة',
			$wa,
			$wa,
			$wa,
			'+3815',
			'+15',
			'+3815',
			'كل مدن البحرين',
			'مدن البحرين',
			'داخل مملكة البحرين',
			'يغطي مملكة البحرين',
			'https://rukn-eltatawer.com/bh/contact-us/',
			'https://rukn-eltatawer.com/bh/contact-us/',
			'rukn-eltatawer.com/bh',
			'rukn-eltatawer.com/bh/',
		),
		$text
	);

	$text = str_replace(
		'>2024</div><div class="lbl">في البحرين منذ</div>',
		'>+15</div><div class="lbl">عاماً في البحرين</div>',
		$text
	);

	$text = preg_replace( '/src="service-\d+(?:-\d+)?\.webp"/', 'src="' . $img . '"', $text );

	// Remove call-only buttons and raw tel links. Keep WhatsApp.
	$text = preg_replace( '/<a\b[^>]*href=["\']tel:[^"\']+["\'][^>]*>.*?<\/a>/is', '', $text );
	$text = preg_replace( '/href=["\']tel:[^"\']+["\']/', 'href="https://wa.me/' . $wa . '" data-rukn-wa="1"', $text );

	return $text;
}

add_filter( 'the_content', 'rukn_bh_seo_fix_text', 5 );
add_filter( 'the_excerpt', 'rukn_bh_seo_fix_text', 5 );
add_filter( 'rank_math/frontend/canonical', 'rukn_bh_seo_fix_text' );
add_filter( 'rank_math/opengraph/url', 'rukn_bh_seo_fix_text' );

add_action(
	'wp_head',
	static function () {
		echo '<style id="rukn-wa-only">body.rukn-hide-call a[href^="tel:"],body.rukn-wa-only a[href^="tel:"],body.rukn-wa-only .btn-call,body.rukn-wa-only .-callbutton--post-card,body.rukn-wa-only .fab-call,body.rukn-wa-only [data-rukn-call],body.rukn-wa-only .header-phone,body.rukn-wa-only .phone-number{display:none!important}</style>';
	},
	99
);

add_action(
	'template_redirect',
	static function () {
		ob_start(
			static function ( $html ) {
				return rukn_bh_seo_fix_text( $html );
			}
		);
	},
	0
);
