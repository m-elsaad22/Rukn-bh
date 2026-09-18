<?php
/**
 * Plugin Name: Rukn BH Live Fixes
 * Description: Bahrain localization, restore header/hero/FABs, UAE WhatsApp + call temporarily, robots.txt, CPT archive 404s, schema.
 * Version: 1.2.2
 * Author: ركن التطور
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! defined( 'RUKN_BH_WA' ) ) {
	define( 'RUKN_BH_WA', '971586634710' );
}

if ( ! defined( 'RUKN_BH_TEL' ) ) {
	define( 'RUKN_BH_TEL', '+971586634710' );
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
		if ( get_option( 'whatsapp_number' ) !== RUKN_BH_TEL ) {
			update_option( 'whatsapp_number', RUKN_BH_TEL, false );
		}
		if ( get_option( 'phonenumber' ) !== RUKN_BH_TEL ) {
			update_option( 'phonenumber', RUKN_BH_TEL, false );
		}
		$hide_call = get_option( 'rukn_hide_call_global' );
		if ( $hide_call === 'on' || $hide_call === 'off' ) {
			delete_option( 'rukn_hide_call_global' );
		}
	},
	1
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

if ( ! function_exists( 'rukn_bh_request_path' ) ) {
	function rukn_bh_request_path() {
		$path = wp_parse_url( $_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH );
		$path = is_string( $path ) ? $path : '/';
		return untrailingslashit( $path );
	}
}

if ( ! function_exists( 'rukn_bh_home_path' ) ) {
	function rukn_bh_home_path() {
		$path = wp_parse_url( home_url( '/' ), PHP_URL_PATH );
		$path = is_string( $path ) ? $path : '/';
		return untrailingslashit( $path );
	}
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

if ( ! function_exists( 'rukn_bh_menu_links' ) ) {
	function rukn_bh_menu_links() {
		$home = 'https://rukn-eltatawer.com/bh';
		return array(
			array( 'الرئيسية', $home . '/' ),
			array( 'خدماتنا', $home . '/our-services/' ),
			array( 'المدن', $home . '/cities/' ),
			array( 'من نحن', $home . '/about-us/' ),
			array( 'تواصل معنا', $home . '/contact-us/' ),
			array( 'English', $home . '/home-services-bahrain/' ),
		);
	}
}

if ( ! function_exists( 'rukn_bh_menu_html' ) ) {
	function rukn_bh_menu_html() {
		$html = '';
		foreach ( rukn_bh_menu_links() as $item ) {
			$html .= '<a class="rukn-nav-link" href="' . esc_url( $item[1] ) . '">' . esc_html( $item[0] ) . '</a>';
		}
		return $html;
	}
}

if ( ! function_exists( 'rukn_bh_ui_css' ) ) {
	function rukn_bh_ui_css() {
		return '#ruknFab.fab-stack,.fab-stack{opacity:1!important;visibility:visible!important;transform:none!important}'
			. '#ruknMob a.rukn-nav-link{display:block;padding:12px 0;font-family:Cairo,sans-serif;font-weight:700;color:#fff}'
			. 'header#hdr,header#hdr .wrap.nav{left:0!important;right:0!important;inset-inline:0!important;width:100%!important;max-width:none!important;flex-wrap:nowrap!important}'
			. 'header#hdr{background:transparent!important}'
			. 'header#hdr::before{content:none!important;display:none!important;opacity:0!important;visibility:hidden!important;background:transparent!important;transform:translateY(-100%)!important}'
			. 'header#hdr .logo img{display:none!important}'
			. 'header#hdr .logo .mark{display:grid!important}'
			. 'header#hdr .logo b{color:#fff;font-family:Cairo,sans-serif;font-weight:900;font-size:18px;white-space:nowrap}'
			. 'header#hdr.scrolled{background:rgba(255,255,255,.78)!important}'
			. 'header#hdr.scrolled .logo b{color:var(--navy,#0A1F4E)}'
			. '@media(max-width:768px){header#hdr nav.menu,header#hdr nav.menu a{display:none!important;visibility:hidden!important}header#hdr .nav-cta .btn{display:none!important}}';
	}
}

if ( ! function_exists( 'rukn_bh_schema_json' ) ) {
	function rukn_bh_schema_json() {
		$wa   = RUKN_BH_WA;
		$data = array(
			'@context'     => 'https://schema.org',
			'@type'        => 'HomeAndConstructionBusiness',
			'name'         => 'ركن التطور - البحرين',
			'url'          => 'https://rukn-eltatawer.com/bh',
			'image'        => 'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp',
			'telephone'    => RUKN_BH_TEL,
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
				'telephone'         => RUKN_BH_TEL,
				'url'               => 'https://wa.me/' . $wa,
				'availableLanguage' => array( 'ar', 'en' ),
			),
		);
		return '<script type="application/ld+json" id="rukn-bh-local-schema">' . wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . '</script>';
	}
}

if ( ! function_exists( 'rukn_bh_apply_markup_fixes' ) ) {
	function rukn_bh_apply_markup_fixes( $html ) {
		if ( ! is_string( $html ) || $html === '' ) {
			return $html;
		}

		$wa  = RUKN_BH_WA;
		$img = 'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp';

		$html = str_replace(
			array(
				'دبي، الإمارات العربية المتحدة',
				'دبي، الإمارات',
				'Dubai, United Arab Emirates',
				'اختر الإمارة',
				'https://www.rukn-eltatawer.com/bh/index.php/',
				'https://rukn-eltatawer.com/bh/index.php/',
				'https://www.rukn-eltatawer.com/bh/index.php',
				'https://rukn-eltatawer.com/bh/index.php',
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
				'للتواصل: صفحة الاتصال أو +971586634710',
				'يمكنك طلب حذف بياناتك عبر +971586634710',
				'og:locale" content="ar_AR"',
				'content="ar_AR"',
			),
			array(
				'المنامة، مملكة البحرين',
				'المنامة، مملكة البحرين',
				'Manama, Kingdom of Bahrain',
				'اختر المدينة',
				'https://rukn-eltatawer.com/bh/',
				'https://rukn-eltatawer.com/bh/',
				'https://rukn-eltatawer.com/bh',
				'https://rukn-eltatawer.com/bh',
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
				'للتواصل: أرسل واتساب وسنحدد موعد المعاينة',
				'يمكنك طلب حذف بياناتك عبر واتساب',
				'og:locale" content="ar_BH"',
				'content="ar_BH"',
			),
			$html
		);

		$html = preg_replace( '/src="service-\d+(?:-\d+)?\.webp"/', 'src="' . $img . '"', $html );

		$html = preg_replace(
			'/<a\b[^>]*href=["\']https?:\/\/wa\.me\/201151481000[^"\']*["\'][^>]*>.*?<\/a>/is',
			'<span class="kayan-credit">KAYAN WEB</span>',
			$html
		);

		if ( strpos( $html, '<nav class="menu"></nav>' ) !== false ) {
			$html = str_replace( '<nav class="menu"></nav>', '<nav class="menu">' . rukn_bh_menu_html() . '</nav>', $html );
		}

		if ( strpos( $html, 'id="ruknMob"' ) !== false && ! preg_match( '#id="ruknMob"[^>]*>[\s\S]*?class="rukn-nav-link"#', $html ) ) {
			$html = preg_replace(
				'#(<div class="mob" id="ruknMob">[\s\S]*?class="mob-search"[\s\S]*?</button>)#',
				'$1' . rukn_bh_menu_html(),
				$html,
				1
			);
		}

		$html = preg_replace(
			'#(<img\b[^>]*class="[^"]*YourColor--Theme--image[^"]*"[^>]*?)\sdata-loader-src="([^"]+)"#',
			'$1 src="$2"',
			$html
		);
		$html = str_replace(
			'20260417_163942_٠٠٠١-90x23.webp',
			'20260417_163942_٠٠٠١.webp',
			$html
		);

		$html = str_replace( '<header id="hdr">', '<header id="hdr" class="fixedintro">', $html );
		if ( strpos( $html, 'id="hdr"' ) !== false && strpos( $html, 'fixedintro' ) === false ) {
			$html = str_replace( '<header id="hdr" class="', '<header id="hdr" class="fixedintro ', $html );
		}

		if ( strpos( $html, 'class="logo"' ) !== false && strpos( $html, '<b>ركن التطور</b>' ) === false ) {
			$html = preg_replace(
				'#(<a href="[^"]*" class="logo"[^>]*>)([\s\S]*?)(</a>)#',
				'$1$2<b>ركن التطور</b>$3',
				$html,
				1
			);
		}

		return $html;
	}
}

if ( ! function_exists( 'rukn_bh_ensure_fabs' ) ) {
	function rukn_bh_ensure_fabs( $html ) {
		$wa   = RUKN_BH_WA;
		$tel  = RUKN_BH_TEL;
		$call = '<a href="tel:' . esc_attr( $tel ) . '" class="fab-btn fab-call" aria-label="اتصال" data-call="phone"><i class="fas fa-phone"></i></a>';
		$wab  = '<a href="https://wa.me/' . esc_attr( $wa ) . '" target="_blank" rel="noopener" class="fab-btn fab-wa" aria-label="واتساب" data-call="whatsapp"><i class="fab fa-whatsapp"></i></a>';

		if ( strpos( $html, 'id="ruknFab"' ) !== false ) {
			$html = str_replace( 'class="fab-stack"', 'class="fab-stack show"', $html );
			if ( ! preg_match( '/<a\b[^>]*class="[^"]*fab-call[^"]*"/', $html ) ) {
				$html = preg_replace(
					'#(<div class="fab-stack show" id="ruknFab">)#',
					'$1' . $call,
					$html,
					1
				);
			}
			if ( ! preg_match( '/<a\b[^>]*class="[^"]*fab-wa[^"]*"/', $html ) ) {
				$html = preg_replace(
					'#(<div class="fab-stack show" id="ruknFab">)#',
					'$1' . $wab,
					$html,
					1
				);
			}
			return $html;
		}

		$stack = '<div class="fab-stack show" id="ruknFab">' . $call . $wab . '</div>';
		if ( strpos( $html, '</root>' ) !== false ) {
			return str_replace( '</root>', $stack . '</root>', $html );
		}
		if ( strpos( $html, '</body>' ) !== false ) {
			return str_replace( '</body>', $stack . '</body>', $html );
		}
		return $html . $stack;
	}
}

if ( ! function_exists( 'rukn_bh_fix_html' ) ) {
	function rukn_bh_fix_html( $html ) {
		if ( ! is_string( $html ) || $html === '' ) {
			return $html;
		}

		$lead = ltrim( $html );
		if ( stripos( $lead, '<html' ) === false && stripos( $lead, '<!doctype html' ) === false ) {
			return $html;
		}

		$parts = preg_split( '#(<(?:style|script|noscript)\b[^>]*>.*?</(?:style|script|noscript)>)#is', $html, -1, PREG_SPLIT_DELIM_CAPTURE );
		if ( is_array( $parts ) && count( $parts ) > 1 ) {
			$out = '';
			foreach ( $parts as $i => $part ) {
				$out .= ( $i % 2 === 1 ) ? $part : rukn_bh_apply_markup_fixes( $part );
			}
			$html = $out;
		} else {
			$html = rukn_bh_apply_markup_fixes( $html );
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

		$html = rukn_bh_ensure_fabs( $html );

		return $html;
	}
}

add_filter( 'the_content', 'rukn_bh_apply_markup_fixes', 5 );
add_filter( 'the_excerpt', 'rukn_bh_apply_markup_fixes', 5 );

add_action(
	'wp_head',
	static function () {
		echo '<style id="rukn-bh-ui">' . rukn_bh_ui_css() . '</style>';
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
