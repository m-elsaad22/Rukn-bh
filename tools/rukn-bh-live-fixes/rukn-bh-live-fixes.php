<?php
/**
 * Plugin Name: Rukn BH Live Fixes
 * Description: Bahrain localization, hide call buttons, keep UAE WhatsApp temporarily, restore nav, robots.txt, stop CPT archive 500s, schema.
 * Version: 1.1.0
 * Author: ركن التطور
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! defined( 'RUKN_BH_WA' ) ) {
	define( 'RUKN_BH_WA', '971586634710' );
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
		if ( get_option( 'rukn_hide_call_global' ) !== 'on' ) {
			update_option( 'rukn_hide_call_global', 'on', false );
		}
		if ( get_option( 'whatsapp_number' ) !== '+971586634710' ) {
			update_option( 'whatsapp_number', '+971586634710', false );
		}
		if ( get_option( 'phonenumber' ) ) {
			update_option( 'phonenumber', '', false );
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

add_filter(
	'wp_robots',
	static function ( $robots ) {
		if ( is_post_type_archive( array( 'services', 'reviews', 'faqs', 'pricing', 'portfolio', 'before_after' ) ) ) {
			$robots['noindex']  = true;
			$robots['nofollow'] = true;
		}
		return $robots;
	}
);

add_filter(
	'rank_math/opengraph/facebook/og_locale',
	static function () {
		return 'ar_BH';
	}
);

function rukn_bh_request_path() {
	$path = wp_parse_url( $_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH );
	$path = is_string( $path ) ? $path : '/';
	return untrailingslashit( $path );
}

function rukn_bh_home_path() {
	$path = wp_parse_url( home_url( '/' ), PHP_URL_PATH );
	$path = is_string( $path ) ? $path : '/';
	return untrailingslashit( $path );
}

add_action(
	'template_redirect',
	static function () {
		if ( is_admin() || wp_doing_ajax() || wp_doing_cron() ) {
			return;
		}

		$path = rukn_bh_request_path();

		if ( preg_match( '#/robots\.txt$#', $path ) ) {
			status_header( 200 );
			header( 'Content-Type: text/plain; charset=utf-8' );
			echo "User-agent: *\nAllow: /\nDisallow: /wp-admin/\nAllow: /wp-admin/admin-ajax.php\n\nSitemap: https://rukn-eltatawer.com/bh/sitemap_index.xml\n";
			exit;
		}

		$rukn_cpts = array( 'services', 'reviews', 'faqs', 'pricing', 'portfolio', 'before_after' );
		if ( is_post_type_archive( $rukn_cpts ) ) {
			global $wp_query;
			$wp_query->set_404();
			status_header( 404 );
			nocache_headers();
			header( 'Content-Type: text/html; charset=utf-8' );
			$home = esc_url( home_url( '/' ) );
			$wa   = esc_attr( RUKN_BH_WA );
			echo '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><title>الصفحة غير موجودة</title></head><body>';
			echo '<h1>الصفحة غير موجودة</h1><p>هذا القسم غير مفعّل حالياً على موقع ركن التطور البحرين.</p>';
			echo '<p><a href="' . $home . '">العودة للرئيسية</a> — <a href="https://wa.me/' . $wa . '">واتساب</a></p></body></html>';
			exit;
		}

		if ( preg_match( '#/language/en/?$#', $path ) ) {
			wp_safe_redirect( home_url( '/home-services-bahrain/' ), 301 );
			exit;
		}

		$home_path    = rukn_bh_home_path();
		$is_home_path = ( $path === $home_path || $path === '' || $path === '/' );

		if ( ( is_front_page() || is_home() ) && ! $is_home_path && ! is_paged() && ! is_feed() ) {
			if ( function_exists( 'kayan_stabilization_homepage_v3_redirect' ) ) {
				remove_action( 'template_redirect', 'kayan_stabilization_homepage_v3_redirect', 0 );
			}
			global $wp_query;
			$wp_query->set_404();
			status_header( 404 );
			nocache_headers();
			$tpl = get_query_template( '404' );
			if ( $tpl ) {
				include $tpl;
			} else {
				echo '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>الصفحة غير موجودة</title></head><body><h1>الصفحة غير موجودة</h1><p>عذراً، هذا الرابط غير موجود على موقع ركن التطور البحرين.</p><p><a href="' . esc_url( home_url( '/' ) ) . '">العودة للرئيسية</a> — أو راسلنا واتساب: <a href="https://wa.me/' . esc_attr( RUKN_BH_WA ) . '">واتساب</a></p></body></html>';
			}
			exit;
		}
	},
	-1
);

function rukn_bh_menu_links() {
	$home = 'https://rukn-eltatawer.com/bh';
	return array(
		array( 'الرئيسية', $home . '/' ),
		array( 'خدماتنا', $home . '/our-services/' ),
		array( 'المدن', $home . '/cities/' ),
		array( 'من نحن', $home . '/about-us/' ),
		array( 'تواصل معنا', $home . '/contact-us/' ),
		array( 'English', $home . '/home-services-bahrain/' ),
		array( 'خريطة الموقع', $home . '/html-sitemap/' ),
	);
}

function rukn_bh_menu_html() {
	$html = '';
	foreach ( rukn_bh_menu_links() as $item ) {
		$html .= '<a href="' . esc_url( $item[1] ) . '">' . esc_html( $item[0] ) . '</a>';
	}
	return $html;
}

function rukn_bh_schema_json() {
	$wa   = RUKN_BH_WA;
	$data = array(
		'@context'     => 'https://schema.org',
		'@type'        => 'HomeAndConstructionBusiness',
		'name'         => 'ركن التطور - البحرين',
		'url'          => 'https://rukn-eltatawer.com/bh',
		'image'        => 'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp',
		'telephone'    => '+971586634710',
		'address'      => array(
			'@type'           => 'PostalAddress',
			'streetAddress'   => 'المنامة',
			'addressLocality' => 'المنامة',
			'addressRegion'   => 'العاصمة',
			'addressCountry'  => 'BH',
		),
		'areaServed'   => 'Bahrain',
		'contactPoint' => array(
			'@type'             => 'ContactPoint',
			'contactType'       => 'customer support',
			'url'               => 'https://wa.me/' . $wa,
			'availableLanguage' => array( 'ar', 'en' ),
		),
	);
	return '<script type="application/ld+json" id="rukn-bh-local-schema">' . wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . '</script>';
}

function rukn_bh_fix_html( $html ) {
	if ( ! is_string( $html ) || $html === '' ) {
		return $html;
	}

	$wa  = RUKN_BH_WA;
	$img = 'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp';

	$html = str_replace(
		array(
			'دبي، الإمارات العربية المتحدة',
			'Dubai, United Arab Emirates',
			'اختر الإمارة',
			'https://www.rukn-eltatawer.com/bh/index.php/',
			'https://rukn-eltatawer.com/bh/index.php/',
			'https://www.rukn-eltatawer.com/bh/index.php',
			'https://rukn-eltatawer.com/bh/index.php',
			'https://www.rukn-eltatawer.com/bh/',
			'اتصل أو أرسل واتساب على [[رقم الهاتف/واتساب]] ونرد عليك لتحديد الموعد.',
			'اتصل أو أرسل واتساب على [[رقم الهاتف/واتساب]]',
			'اتصل أو أرسل واتساب على +971586634710 ونرد عليك لتحديد الموعد.',
			'اتصل أو أرسل واتساب على +971586634710',
			'{PHONE_RUKN_BAHRAIN}',
			'{WHATSAPP_RUKN_BAHRAIN}',
			'[[رقم الهاتف/واتساب]]',
			'كل مدن المملكة',
			'مدن المملكة',
			'داخل المملكة',
			'يغطي المملكة',
			'rukn-eltatawer.com/bhbh',
			'rukn-eltatawer.com/bh/bh/',
			'Search Now',
			'"Search"',
			'للتواصل: صفحة الاتصال أو +971586634710',
			'يمكنك طلب حذف بياناتك عبر +971586634710',
			'og:locale" content="ar_AR"',
			'content="ar_AR"',
		),
		array(
			'المنامة، مملكة البحرين',
			'Manama, Kingdom of Bahrain',
			'اختر المدينة',
			'https://rukn-eltatawer.com/bh/',
			'https://rukn-eltatawer.com/bh/',
			'https://rukn-eltatawer.com/bh',
			'https://rukn-eltatawer.com/bh',
			'https://rukn-eltatawer.com/bh/',
			'أرسل واتساب وسنحدد موعد المعاينة.',
			'أرسل واتساب وسنحدد موعد المعاينة',
			'أرسل واتساب وسنحدد موعد المعاينة.',
			'أرسل واتساب وسنحدد موعد المعاينة',
			$wa,
			$wa,
			$wa,
			'كل مدن البحرين',
			'مدن البحرين',
			'داخل مملكة البحرين',
			'يغطي مملكة البحرين',
			'rukn-eltatawer.com/bh',
			'rukn-eltatawer.com/bh/',
			'ابحث في الموقع',
			'"بحث"',
			'للتواصل: أرسل واتساب وسنحدد موعد المعاينة',
			'يمكنك طلب حذف بياناتك عبر واتساب',
			'og:locale" content="ar_BH"',
			'content="ar_BH"',
		),
		$html
	);

	$html = preg_replace( '/src="service-\d+(?:-\d+)?\.webp"/', 'src="' . $img . '"', $html );

	$html = preg_replace( '/<a\b[^>]*href=["\']tel:[^"\']*["\'][^>]*>.*?<\/a>/is', '', $html );
	$html = preg_replace( '/href=["\']tel:[^"\']*["\']/', 'href="#rukn-no-call" data-rukn-call="1"', $html );
	$html = preg_replace( '/<a\b[^>]*class="[^"]*fab-call[^"]*"[^>]*>.*?<\/a>/is', '', $html );
	$html = preg_replace( '/<a\b[^>]*class="[^"]*btn-call[^"]*"[^>]*>.*?<\/a>/is', '', $html );

	$html = preg_replace(
		'/<a\b[^>]*href=["\']https?:\/\/wa\.me\/201151481000[^"\']*["\'][^>]*>.*?<\/a>/is',
		'<span class="kayan-credit">KAYAN WEB</span>',
		$html
	);

	$html = preg_replace(
		'#https://wa\.me/\+?971586634710#',
		'https://wa.me/' . $wa,
		$html
	);

	if ( strpos( $html, '<nav class="menu"></nav>' ) !== false ) {
		$html = str_replace( '<nav class="menu"></nav>', '<nav class="menu">' . rukn_bh_menu_html() . '</nav>', $html );
	}

	if ( strpos( $html, 'id="ruknMob"' ) !== false && strpos( $html, 'our-services/' ) === false ) {
		$html = str_replace(
			'<a href="https://wa.me/' . $wa . '" target="_blank" rel="nofollow noopener noreferrer" rel="noopener" class="btn btn-wa"><i class="fab fa-whatsapp"></i> تواصل عبر واتساب</a></div>',
			'<a href="https://wa.me/' . $wa . '" target="_blank" rel="noopener" class="btn btn-wa"><i class="fab fa-whatsapp"></i> تواصل عبر واتساب</a>' . rukn_bh_menu_html() . '</div>',
			$html
		);
		$html = str_replace(
			'<a href="https://wa.me/' . $wa . '" target="_blank" rel="noopener" class="btn btn-wa"><i class="fab fa-whatsapp"></i> تواصل عبر واتساب</a></div>',
			'<a href="https://wa.me/' . $wa . '" target="_blank" rel="noopener" class="btn btn-wa"><i class="fab fa-whatsapp"></i> تواصل عبر واتساب</a>' . rukn_bh_menu_html() . '</div>',
			$html
		);
	}

	if ( strpos( $html, '"@type": "LocalBusiness"' ) !== false && strpos( $html, '"name": ""' ) !== false ) {
		$html = preg_replace(
			'#<script type="application/ld\+json">\{"@context": "http://schema.org","@type": "LocalBusiness".*?</script>#s',
			rukn_bh_schema_json(),
			$html,
			1
		);
	}

	if ( strpos( $html, 'id="rukn-bh-local-schema"' ) === false && strpos( $html, '</head>' ) !== false ) {
		$html = str_replace( '</head>', rukn_bh_schema_json() . '</head>', $html );
	}

	return $html;
}

add_filter( 'the_content', 'rukn_bh_fix_html', 5 );
add_filter( 'the_excerpt', 'rukn_bh_fix_html', 5 );

add_action(
	'wp_head',
	static function () {
		echo '<style id="rukn-wa-only">body.rukn-hide-call a[href^="tel:"],body.rukn-wa-only a[href^="tel:"],body.rukn-wa-only .btn-call,body.rukn-wa-only .-callbutton--post-card,body.rukn-wa-only .fab-call,body.rukn-wa-only [data-rukn-call],body.rukn-wa-only .header-phone,body.rukn-wa-only .phone-number,a.fab-call,.btn-call,a[href="tel:"],a[href="#rukn-no-call"]{display:none!important}nav.menu{display:flex;flex-wrap:wrap;gap:14px;align-items:center}nav.menu a{color:#fff;font-family:Cairo,sans-serif;font-weight:700;font-size:14.5px;text-decoration:none;white-space:nowrap}#ruknMob a{display:block;color:#fff;padding:10px 0;font-family:Cairo,sans-serif;font-weight:700}</style>';
	},
	99
);

add_action(
	'template_redirect',
	static function () {
		ob_start( 'rukn_bh_fix_html' );
	},
	-5
);
