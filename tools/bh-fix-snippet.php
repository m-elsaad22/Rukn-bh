/**
 * Bahrain live fixes — Code Snippets id 5.
 * Call-main page shapes + header overlay kill + UAE leftovers.
 * Floating call + WhatsApp stay visible. UAE +971586634710 is temporary.
 * Theme files are locked (DISALLOW_FILE_EDIT); this snippet is the live patch path.
 */

if ( ! defined( 'ABSPATH' ) ) {
	return;
}

if ( ! defined( 'RUKN_BH_WA' ) ) {
	define( 'RUKN_BH_WA', '971586634710' );
}

if ( ! defined( 'RUKN_BH_TEL' ) ) {
	define( 'RUKN_BH_TEL', '+971586634710' );
}

if ( ! defined( 'RUKN_BH_HOME' ) ) {
	define( 'RUKN_BH_HOME', 'https://www.rukn-eltatawer.com/bh' );
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

if ( ! function_exists( 'rukn_bh_rel_path' ) ) {
	function rukn_bh_rel_path() {
		$home = rukn_bh_home_path();
		$path = rukn_bh_request_path();
		if ( $home !== '' && strpos( $path, $home ) === 0 ) {
			$path = substr( $path, strlen( $home ) );
		}
		$path = $path === '' ? '/' : $path;
		return $path[0] === '/' ? $path : '/' . $path;
	}
}

if ( ! function_exists( 'rukn_bh_city_map' ) ) {
	function rukn_bh_city_map() {
		return array(
			'manama'     => 'المنامة',
			'muharraq'   => 'المحرق',
			'riffa'      => 'الرفاع',
			'hamad-town' => 'مدينة حمد',
			'isa-town'   => 'مدينة عيسى',
			'aali'       => 'عالي',
			'sitra'      => 'سترة',
			'budaiya'    => 'البديع',
			'hidd'       => 'الحد',
			'saar'       => 'سار',
			'jidhafs'    => 'جدحفص',
			'tubli'      => 'توبلي',
		);
	}
}

add_action(
	'template_redirect',
	static function () {
		if ( is_admin() || wp_doing_ajax() || wp_doing_cron() ) {
			return;
		}

		$path = rukn_bh_request_path();
		$rel  = rukn_bh_rel_path();

		if ( preg_match( '#/robots\.txt$#', $path ) ) {
			status_header( 200 );
			header( 'Content-Type: text/plain; charset=utf-8' );
			echo "User-agent: *\nAllow: /\nDisallow: /wp-admin/\nAllow: /wp-admin/admin-ajax.php\n\nSitemap: https://www.rukn-eltatawer.com/bh/sitemap_index.xml\n";
			exit;
		}

		if ( preg_match( '#^/grass-wall-([a-z0-9-]+)$#', $rel, $m ) ) {
			wp_safe_redirect( home_url( '/wall-grass-' . $m[1] . '/' ), 301 );
			exit;
		}
		if ( preg_match( '#^/artificial-grass-grdn-([a-z0-9-]+)$#', $rel, $m ) ) {
			wp_safe_redirect( home_url( '/artificial-grass-' . $m[1] . '/' ), 301 );
			exit;
		}

		if ( $rel === '/en' || $rel === '/language/en' || preg_match( '#/language/en$#', $path ) ) {
			wp_safe_redirect( home_url( '/home-services-bahrain/' ), 301 );
			exit;
		}
		if ( $rel === '/ar' || $rel === '/language/ar' ) {
			wp_safe_redirect( home_url( '/' ), 301 );
			exit;
		}

		$rukn_cpts = array( 'services', 'reviews', 'faqs', 'pricing', 'portfolio', 'before_after' );
		if ( is_post_type_archive( $rukn_cpts ) ) {
			rukn_bh_render_404( 'هذا القسم غير مفعّل حالياً على موقع ركن التطور البحرين.' );
			exit;
		}

		if ( is_tax( 'cities' ) ) {
			rukn_bh_render_city_archive();
			exit;
		}

		$home_path    = rukn_bh_home_path();
		$is_home_path = ( $path === $home_path || $path === '' || $path === '/' );

		if ( is_404() || ( ( is_front_page() || is_home() ) && ! $is_home_path && ! is_paged() && ! is_feed() ) ) {
			if ( function_exists( 'kayan_stabilization_homepage_v3_redirect' ) ) {
				remove_action( 'template_redirect', 'kayan_stabilization_homepage_v3_redirect', 0 );
			}
			global $wp_query;
			$wp_query->set_404();
			rukn_bh_render_404( 'يبدو أن الرابط الذي وصلت منه غير صحيح أو أن الصفحة نُقلت.' );
			exit;
		}
	},
	-1
);

add_action(
	'wp',
	static function () {
		if ( ! is_singular() ) {
			return;
		}
		$post = get_post();
		if ( $post && is_string( $post->post_content ) && strpos( $post->post_content, 'rukn-shape' ) !== false ) {
			remove_filter( 'the_content', 'wpautop' );
			remove_filter( 'the_content', 'shortcode_unautop' );
		}
	}
);

add_filter(
	'ez_toc_maybe_apply_the_content_filter',
	static function ( $run ) {
		$post = get_post();
		if ( $post && is_string( $post->post_content ) && strpos( $post->post_content, 'rukn-shape' ) !== false ) {
			return false;
		}
		return $run;
	}
);

if ( ! function_exists( 'rukn_bh_menu_links' ) ) {
	function rukn_bh_menu_links() {
		$home = RUKN_BH_HOME;
		return array(
			array( 'الرئيسية', $home . '/' ),
			array( 'خدماتنا', $home . '/our-services/' ),
			array( 'المدن', $home . '/cities/' ),
			array( 'من نحن', $home . '/about-us/' ),
			array( 'تواصل معنا', $home . '/contact-us/' ),
			array( 'الأسئلة الشائعة', $home . '/faq/' ),
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
		return '#ruknFab.fab-stack,.fab-stack{opacity:1!important;visibility:visible!important;transform:none!important;pointer-events:auto!important}'
			. '#ruknFab.fab-stack.show,.fab-stack.show{display:flex!important}'
			. '#ruknMob a.rukn-nav-link{display:block;padding:12px 0;font-family:Cairo,sans-serif;font-weight:700;color:#fff}'
			. 'header,header#hdr,header.fixedintro{position:fixed!important;top:0!important;left:0!important;right:0!important;inset-inline:0!important;width:100vw!important;max-width:100vw!important;min-width:100%!important;height:80px!important;display:flex!important;align-items:center!important;z-index:1000!important;overflow:visible!important;flex-wrap:nowrap!important;background:transparent!important;transform:none!important;margin:0!important}'
			. 'header .wrap,header#hdr .wrap.nav,header.fixedintro .wrap{width:100%!important;max-width:1400px!important;margin:0 auto!important}'
			. 'header:before,header::before,header#hdr:before,header#hdr::before,header.fixedintro:before,header.fixedintro::before{content:none!important;display:none!important;opacity:0!important;visibility:hidden!important;background:transparent!important;width:0!important;height:0!important;pointer-events:none!important}'
			. '@media(max-width:768px){header,header#hdr,header.fixedintro{width:100vw!important;left:0!important;right:0!important;inset-inline:0!important}header:before,header::before,header#hdr::before,header.fixedintro::before{content:none!important;display:none!important}}'
			. 'header#hdr .logo .mark,header#hdr .logo b,header#hdr .kayan-logo-fallback{display:none!important}'
			. 'header#hdr .logo img{display:block!important;max-height:52px!important;max-width:min(58vw,220px)!important;width:auto!important;height:auto!important;opacity:1!important;visibility:visible!important;object-fit:contain!important;background:transparent!important;margin-inline:8px;mix-blend-mode:normal}'
			. 'header#hdr.scrolled{background:rgba(255,255,255,.78)!important;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px)}'
			. 'header#hdr.scrolled .logo img{mix-blend-mode:normal}'
			. '.rukn-lc-langico{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;overflow:hidden;font-size:11px;font-weight:800;font-family:Cairo,sans-serif;line-height:1}'
			. '.rukn-lc-langico.en{letter-spacing:-0.5px;font-size:10px;width:28px;height:28px}'
			. '.kayan-header-lang:not(.open) .rukn-lc-menu{display:none!important;visibility:hidden!important;pointer-events:none!important}'
			. 'html,body{overflow-x:hidden}'
			. '.uae-svg,svg.uae-svg,.area-map .uae-svg{display:none!important}'
			. '.rukn-shape #ez-toc-container,.rukn-shape .ez-toc-container,.rukn-shape .ez-toc-title-container{display:none!important}'
			. 'body:has(.rukn-shape) .article-layout{display:block!important;grid-template-columns:1fr!important}'
			. 'body:has(.rukn-shape) .article-body{max-width:1400px;margin:0 auto;background:transparent!important;border:none!important;box-shadow:none!important;padding:20px 0 60px!important}'
			. '#ez-toc-container{display:none!important}'
			. '@media(max-width:768px){header#hdr nav.menu,header#hdr nav.menu a{display:none!important;visibility:hidden!important}header#hdr .nav-cta .btn{display:none!important}}';
	}
}

if ( ! function_exists( 'rukn_bh_page_css' ) ) {
	function rukn_bh_page_css() {
		return ':root{--navy:#0A1F4E;--navy2:#1A3A6B;--blue:#2980D4;--turq:#2E9DF7;--aqua:#4FA8FF;--gold:#C9A227;--gold2:#F0CE73;--success:#18C96A;--wa:#25D366;--bg:#F4F8FD;--text:#1C2E44;--text2:#3A5068;--border:#E2EAF5;--white:#fff;--r-s:16px;--r-m:24px;--r-l:32px;--sh-s:0 4px 16px rgba(10,31,78,.06);--sh-m:0 12px 32px rgba(10,31,78,.10);--sh-l:0 24px 60px rgba(10,31,78,.16);--sh-glow:0 16px 48px rgba(46,157,247,.28);--grad:linear-gradient(135deg,#0A1F4E 0%,#1A3A6B 45%,#2E9DF7 100%);--grad-cta:linear-gradient(135deg,#2980D4,#2E9DF7)}'
			. '.rukn-shape{font-family:Tajawal,Cairo,sans-serif;color:var(--text);line-height:1.7}'
			. '.rukn-shape .wrap{max-width:1400px;margin:0 auto;padding:0 24px}'
			. '.rukn-shape .sec{padding:80px 0}'
			. '.rukn-shape .shead{text-align:center;max-width:760px;margin:0 auto 48px}'
			. '.rukn-shape .shead .tag{display:inline-block;font-weight:800;font-size:14px;color:var(--turq);background:rgba(46,157,247,.10);padding:8px 18px;border-radius:999px;margin-bottom:14px}'
			. '.rukn-shape .shead h2 span{background:var(--grad-cta);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}'
			. '.rukn-shape .shead p{color:var(--text2);margin-top:12px}'
			. '.rukn-shape .btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;font-family:Cairo,sans-serif;font-weight:700;font-size:16px;padding:15px 28px;border-radius:14px;border:none;cursor:pointer;text-decoration:none}'
			. '.rukn-shape .btn-wa{background:var(--wa);color:#fff}'
			. '.rukn-shape .btn-call{background:var(--turq);color:#fff}'
			. '.rukn-shape .btn-quote{background:linear-gradient(120deg,var(--gold),var(--gold2));color:var(--navy)}'
			. '.rukn-shape .phero{position:relative;padding:145px 0 60px;background:var(--grad);overflow:hidden}'
			. '.rukn-shape .phero .wrap{position:relative;z-index:2}'
			. '.rukn-shape .crumb{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:14px;font-weight:600;color:rgba(255,255,255,.68);margin-bottom:18px}'
			. '.rukn-shape .crumb a{color:rgba(255,255,255,.68)}'
			. '.rukn-shape .crumb span{color:#fff}'
			. '.rukn-shape .phero h1{color:#fff;max-width:820px;font-family:Cairo,sans-serif;font-weight:900;font-size:clamp(32px,4.4vw,52px);line-height:1.25}'
			. '.rukn-shape .phero h1 em{font-style:normal;background:linear-gradient(120deg,var(--aqua),var(--gold));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}'
			. '.rukn-shape .phero .psub{color:rgba(255,255,255,.86);font-size:clamp(15px,1.3vw,19px);margin-top:16px;max-width:700px}'
			. '.rukn-shape .hero-proof{display:flex;flex-wrap:wrap;gap:10px;margin-top:26px}'
			. '.rukn-shape .chip{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);color:#fff;font-size:14px;font-weight:600;padding:9px 14px;border-radius:999px}'
			. '.rukn-shape .city-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:22px}'
			. '.rukn-shape .citycard{position:relative;border-radius:var(--r-m);overflow:hidden;min-height:200px;display:flex;align-items:flex-end;padding:22px;color:#fff;background:var(--grad);text-decoration:none}'
			. '.rukn-shape .citycard .cc-in{position:relative;z-index:2;width:100%}'
			. '.rukn-shape .citycard h3{color:#fff;font-size:22px;margin:0 0 4px}'
			. '.rukn-shape .citycard small{color:rgba(255,255,255,.78)}'
			. '.rukn-shape .citycard .ccbadge{position:absolute;top:16px;inset-inline-end:16px;z-index:2;background:rgba(255,255,255,.16);color:#fff;font-size:12px;font-weight:800;padding:5px 12px;border-radius:999px}'
			. '.rukn-shape .services-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}'
			. '.rukn-shape .svc{background:#fff;border:1px solid var(--border);border-radius:var(--r-m);padding:28px}'
			. '.rukn-shape .svc-ic{width:62px;height:62px;border-radius:17px;background:var(--grad-cta);display:grid;place-items:center;color:#fff;font-size:26px;margin-bottom:16px}'
			. '.rukn-shape .svc .desc{color:var(--text2);margin:8px 0 14px}'
			. '.rukn-shape .svc ul{list-style:none;padding:0;margin:0 0 16px;display:grid;gap:8px}'
			. '.rukn-shape .svc li{color:var(--text2);font-size:14.5px}'
			. '.rukn-shape .svc-cta{color:var(--turq);font-weight:700;font-family:Cairo,sans-serif}'
			. '.rukn-shape .about-grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}'
			. '.rukn-shape .abcard{background:#fff;border:1px solid var(--border);border-radius:var(--r-l);padding:34px}'
			. '.rukn-shape .aic{width:58px;height:58px;border-radius:15px;background:var(--grad-cta);color:#fff;display:grid;place-items:center;font-size:24px;margin-bottom:18px}'
			. '.rukn-shape .stats-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}'
			. '.rukn-shape .stat{text-align:center;background:#fff;border:1px solid var(--border);border-radius:var(--r-m);padding:28px 16px}'
			. '.rukn-shape .stat .num{font-family:Cairo,sans-serif;font-weight:900;font-size:36px;color:var(--navy)}'
			. '.rukn-shape .timeline-h{display:grid;gap:22px;max-width:760px;margin:0 auto}'
			. '.rukn-shape .th-item b{color:var(--turq);font-family:Cairo,sans-serif}'
			. '.rukn-shape .contact-layout{display:grid;grid-template-columns:1fr 1.3fr;gap:40px}'
			. '.rukn-shape .cinfo-card{background:var(--grad);color:#fff;border-radius:var(--r-l);padding:34px}'
			. '.rukn-shape .cinfo-item{display:flex;gap:14px;align-items:flex-start;margin-bottom:22px}'
			. '.rukn-shape .cinfo-item i{width:46px;height:46px;border-radius:13px;background:rgba(255,255,255,.14);display:grid;place-items:center;flex:none}'
			. '.rukn-shape .cinfo-item b{display:block;font-family:Cairo,sans-serif}'
			. '.rukn-shape .cinfo-item small{color:rgba(255,255,255,.78)}'
			. '.rukn-shape .form-card{background:#fff;border:1px solid var(--border);border-radius:var(--r-l);padding:38px}'
			. '.rukn-shape .form-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}'
			. '.rukn-shape .fld{display:flex;flex-direction:column;gap:8px}'
			. '.rukn-shape .fld.full{grid-column:1/-1}'
			. '.rukn-shape .fld label{font-family:Cairo,sans-serif;font-weight:700;font-size:14.5px;color:var(--navy)}'
			. '.rukn-shape .fld input,.rukn-shape .fld select,.rukn-shape .fld textarea{font-family:Tajawal,sans-serif;font-size:15.5px;padding:14px 16px;border-radius:13px;border:1.5px solid var(--border);background:var(--bg);width:100%}'
			. '.rukn-shape .article-layout{display:grid;grid-template-columns:2.1fr 1fr;gap:40px}'
			. '.rukn-shape .article-body{background:#fff;border:1px solid var(--border);border-radius:var(--r-l);padding:44px}'
			. '.rukn-shape .prose h2{margin:28px 0 12px;color:var(--navy)}'
			. '.rukn-shape .prose p{margin-bottom:16px;color:var(--text2)}'
			. '.rukn-shape .side-w{background:#fff;border:1px solid var(--border);border-radius:var(--r-m);padding:24px;margin-bottom:22px}'
			. '.rukn-shape .side-w.cta{background:var(--grad);color:#fff}'
			. '.rukn-shape .legal-toc{display:grid;gap:8px}'
			. '.rukn-shape .faq-list{max-width:860px;margin:0 auto;display:grid;gap:14px}'
			. '.rukn-shape .faq-item{background:#fff;border:1px solid var(--border);border-radius:16px;overflow:hidden}'
			. '.rukn-shape .faq-q{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 24px;cursor:pointer;font-family:Cairo,sans-serif;font-weight:700;color:var(--navy)}'
			. '.rukn-shape .faq-a{display:none;padding:0 24px 22px;color:var(--text2)}'
			. '.rukn-shape .faq-item.open .faq-a{display:block}'
			. '.rukn-shape .err-wrap{min-height:70vh;display:flex;align-items:center;justify-content:center;text-align:center;padding:140px 0 80px;background:var(--grad);color:#fff}'
			. '.rukn-shape .err-num{font-family:Cairo,sans-serif;font-weight:900;font-size:clamp(90px,16vw,160px);line-height:1}'
			. '.rukn-shape .err-actions{display:flex;flex-wrap:wrap;gap:14px;justify-content:center;margin:24px 0}'
			. '.rukn-shape .err-links a{color:#fff;background:rgba(255,255,255,.12);padding:8px 16px;border-radius:999px;margin:4px;display:inline-block}'
			. '@media(max-width:1024px){.rukn-shape .city-grid,.rukn-shape .services-grid{grid-template-columns:repeat(2,1fr)}.rukn-shape .article-layout,.rukn-shape .contact-layout,.rukn-shape .about-grid{grid-template-columns:1fr}.rukn-shape .form-grid{grid-template-columns:1fr}}'
			. '@media(max-width:640px){.rukn-shape .city-grid,.rukn-shape .services-grid,.rukn-shape .stats-grid{grid-template-columns:1fr}.rukn-shape .article-body,.rukn-shape .form-card{padding:24px}.rukn-shape .sec{padding:56px 0}}';
	}
}

if ( ! function_exists( 'rukn_bh_schema_json' ) ) {
	function rukn_bh_schema_json() {
		$wa   = RUKN_BH_WA;
		$data = array(
			'@context'     => 'https://schema.org',
			'@type'        => 'HomeAndConstructionBusiness',
			'name'         => 'ركن التطور - البحرين',
			'url'          => RUKN_BH_HOME,
			'image'        => RUKN_BH_HOME . '/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp',
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
		$img = RUKN_BH_HOME . '/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp';
		$en  = RUKN_BH_HOME . '/home-services-bahrain/';

		$html = str_replace(
			array(
				'دبي، الإمارات العربية المتحدة',
				'دبي، الإمارات',
				'Dubai, United Arab Emirates',
				'اختر الإمارة',
				'اختر الامارة',
				'جميع إمارات الدولة السبع',
				'جميع إمارات الدولة',
				'إمارات الدولة السبع',
				'7 إمارات',
				'كل إمارة',
				'بلدية دبي',
				'دبي مارينا',
				'https://www.rukn-eltatawer.com/bh/en/',
				'https://rukn-eltatawer.com/bh/en/',
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
				'grass-wall-',
				'artificial-grass-grdn-',
			),
			array(
				'المنامة، مملكة البحرين',
				'المنامة، مملكة البحرين',
				'Manama, Kingdom of Bahrain',
				'اختر المدينة',
				'اختر المدينة',
				'جميع مدن مملكة البحرين',
				'جميع مدن مملكة البحرين',
				'مدن مملكة البحرين',
				'8 مدن',
				'كل مدينة',
				'بلدية البحرين',
				'المنامة',
				$en,
				$en,
				RUKN_BH_HOME . '/',
				RUKN_BH_HOME . '/',
				RUKN_BH_HOME,
				RUKN_BH_HOME,
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
				'wall-grass-',
				'artificial-grass-',
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
			array(
				'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/20260417_163942_٠٠٠١-90x23.webp',
				'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/20260417_163942_٠٠٠١.webp',
				'https://www.rukn-eltatawer.com/bh/wp-content/uploads/2026/08/20260417_163942_٠٠٠١-90x23.webp',
				'https://www.rukn-eltatawer.com/bh/wp-content/uploads/2026/08/20260417_163942_٠٠٠١.webp',
				'<b>ركن التطور</b>',
			),
			array(
				'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/09/rukn-logo-transparent.webp',
				'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/09/rukn-logo-transparent.webp',
				'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/09/rukn-logo-transparent.webp',
				'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/09/rukn-logo-transparent.webp',
				'',
			),
			$html
		);

		$html = str_replace( '<header id="hdr">', '<header id="hdr" class="fixedintro">', $html );
		if ( strpos( $html, 'id="hdr"' ) !== false && strpos( $html, 'fixedintro' ) === false ) {
			$html = str_replace( '<header id="hdr" class="', '<header id="hdr" class="fixedintro ', $html );
		}

		return $html;
	}
}

if ( ! function_exists( 'rukn_bh_strip_article_css' ) ) {
	function rukn_bh_strip_article_css( $content ) {
		if ( ! is_string( $content ) || $content === '' ) {
			return $content;
		}
		$content = preg_replace( '#<style\b[^>]*>.*?</style>#is', '', $content );
		return $content;
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

if ( ! function_exists( 'rukn_bh_render_404' ) ) {
	function rukn_bh_render_404( $message ) {
		status_header( 404 );
		nocache_headers();
		header( 'Content-Type: text/html; charset=utf-8' );
		$home = esc_url( home_url( '/' ) );
		$wa   = esc_attr( RUKN_BH_WA );
		$msg  = esc_html( $message );
		echo '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>الصفحة غير موجودة | ركن التطور البحرين</title><style>' . rukn_bh_page_css() . '</style></head><body>';
		echo '<div class="rukn-shape"><section class="err-wrap"><div class="wrap"><div class="err-num">404</div><h2>عذراً، هذه الصفحة غير موجودة</h2><p>' . $msg . '</p>';
		echo '<div class="err-actions"><a class="btn btn-quote" href="' . $home . '">العودة للرئيسية</a><a class="btn btn-wa" href="https://wa.me/' . $wa . '">تحدث معنا</a></div>';
		echo '<div class="err-links"><a href="' . esc_url( home_url( '/our-services/' ) ) . '">جميع الخدمات</a><a href="' . esc_url( home_url( '/cities/' ) ) . '">المدن</a><a href="' . esc_url( home_url( '/blog/' ) ) . '">المدونة</a><a href="' . esc_url( home_url( '/contact-us/' ) ) . '">اتصل بنا</a><a href="' . esc_url( home_url( '/faq/' ) ) . '">الأسئلة الشائعة</a></div>';
		echo '</div></section></div></body></html>';
	}
}

if ( ! function_exists( 'rukn_bh_render_city_archive' ) ) {
	function rukn_bh_render_city_archive() {
		$term = get_queried_object();
		$name = ( $term && ! empty( $term->name ) ) ? $term->name : 'مدن البحرين';
		$slug = ( $term && ! empty( $term->slug ) ) ? $term->slug : '';
		status_header( 200 );
		nocache_headers();
		header( 'Content-Type: text/html; charset=utf-8' );

		$home = esc_url( home_url( '/' ) );
		$wa   = esc_attr( RUKN_BH_WA );
		$q    = new WP_Query(
			array(
				'post_type'      => 'post',
				'post_status'    => 'publish',
				'posts_per_page' => 8,
				'tax_query'      => array(
					array(
						'taxonomy' => 'cities',
						'field'    => 'slug',
						'terms'    => $slug,
					),
				),
			)
		);

		echo '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">';
		echo '<title>خدمات ركن التطور في ' . esc_html( $name ) . '</title>';
		echo '<style>' . rukn_bh_ui_css() . rukn_bh_page_css() . '</style></head><body>';
		echo '<div class="rukn-shape">';
		echo '<section class="phero compact"><div class="wrap"><div class="crumb"><a href="' . $home . '">الرئيسية</a><span> / المدن / ' . esc_html( $name ) . '</span></div>';
		echo '<h1>خدمات منزلية في <em>' . esc_html( $name ) . '</em></h1>';
		echo '<p class="psub">فريق ركن التطور يصل إلى ' . esc_html( $name ) . ' داخل مملكة البحرين. أرسل واتساب لتحديد موعد المعاينة.</p>';
		echo '<div class="hero-proof"><a class="btn btn-wa" href="https://wa.me/' . $wa . '">واتساب</a></div></div></section>';
		echo '<section class="sec"><div class="wrap">';
		if ( $q->have_posts() ) {
			echo '<div class="shead"><span class="tag">مقالات ' . esc_html( $name ) . '</span><h2>خدمات متوفرة في <span>' . esc_html( $name ) . '</span></h2></div>';
			echo '<div class="services-grid">';
			while ( $q->have_posts() ) {
				$q->the_post();
				echo '<article class="svc"><h3>' . esc_html( get_the_title() ) . '</h3><p class="desc">' . esc_html( wp_trim_words( wp_strip_all_tags( get_the_excerpt() ), 24 ) ) . '</p><a class="svc-cta" href="' . esc_url( get_permalink() ) . '">اقرأ المزيد</a></article>';
			}
			echo '</div>';
			wp_reset_postdata();
		} else {
			echo '<div class="shead"><p>نصل إلى ' . esc_html( $name ) . ' عبر فرق البحرين. تواصل واتساب لحجز المعاينة.</p><p><a class="btn btn-wa" href="https://wa.me/' . $wa . '">واتساب</a> <a class="btn btn-quote" href="' . esc_url( home_url( '/cities/' ) ) . '">كل المدن</a></p></div>';
		}
		echo '</div></section></div>';
		echo '<div class="fab-stack show" id="ruknFab"><a href="tel:' . esc_attr( RUKN_BH_TEL ) . '" class="fab-btn fab-call" aria-label="اتصال"><i class="fas fa-phone"></i></a><a href="https://wa.me/' . $wa . '" class="fab-btn fab-wa" aria-label="واتساب"><i class="fab fa-whatsapp"></i></a></div>';
		echo '</body></html>';
	}
}

add_filter( 'the_content', 'rukn_bh_strip_article_css', 1 );
add_filter( 'the_content', 'rukn_bh_apply_markup_fixes', 5 );
add_filter( 'the_excerpt', 'rukn_bh_apply_markup_fixes', 5 );

add_action(
	'wp_head',
	static function () {
		echo '<style id="rukn-bh-ui">' . rukn_bh_ui_css() . '</style>';
		echo '<style id="rukn-bh-pages">' . rukn_bh_page_css() . '</style>';
	},
	99
);

add_action(
	'wp_footer',
	static function () {
		echo '<style id="rukn-bh-ui-footer">' . rukn_bh_ui_css() . '</style>';
		$wa = esc_js( RUKN_BH_WA );
		echo '<script id="rukn-bh-ui-js">(function(){var s=document.createElement("style");s.id="rukn-bh-header-kill";s.textContent="header#hdr,header.fixedintro,header{width:100vw!important;max-width:100vw!important;left:0!important;right:0!important;inset-inline:0!important;background:transparent!important}header::before,header#hdr::before,header.fixedintro::before{content:none!important;display:none!important;opacity:0!important;background:transparent!important;width:0!important;height:0!important}";document.documentElement.appendChild(s);var h=document.getElementById("hdr");if(h){h.style.setProperty("width","100vw","important");h.style.setProperty("max-width","100vw","important");h.style.setProperty("left","0","important");h.style.setProperty("right","0","important");h.style.setProperty("inset-inline","0","important");h.style.setProperty("background","transparent","important");var on=function(){if(window.scrollY>12){h.classList.add("scrolled");h.style.setProperty("background","rgba(255,255,255,.78)","important");}else{h.classList.remove("scrolled");h.style.setProperty("background","transparent","important");}};on();window.addEventListener("scroll",on,{passive:true});}document.querySelectorAll(".rukn-shape .faq-q").forEach(function(q){q.addEventListener("click",function(){var it=q.closest(".faq-item");if(it)it.classList.toggle("open");});});document.querySelectorAll("form.rukn-wa-form").forEach(function(f){f.addEventListener("submit",function(e){e.preventDefault();var fd=new FormData(f);var parts=[];fd.forEach(function(v,k){if(v)parts.push(k+": "+v);});var url="https://wa.me/' . $wa . '?text="+encodeURIComponent("طلب من موقع ركن التطور البحرين\\n"+parts.join("\\n"));window.open(url,"_blank");});});})();</script>';
	},
	9999
);

add_action(
	'loop_start',
	static function ( $query ) {
		if ( ! $query instanceof WP_Query || ! $query->is_main_query() ) {
			return;
		}
		if ( is_home() && ! is_front_page() ) {
			$home = esc_url( home_url( '/' ) );
			echo '<div class="rukn-shape"><section class="phero compact"><div class="wrap"><div class="crumb"><a href="' . $home . '">الرئيسية</a><span> / المدونة</span></div><h1>مدونة <em>ركن التطور</em> في البحرين</h1><p class="psub">أدلة عملية لخدمات المنزل في المنامة وباقي مدن مملكة البحرين.</p></div></section></div>';
		}
	}
);

add_action(
	'template_redirect',
	static function () {
		ob_start( 'rukn_bh_fix_html' );
	},
	-5
);

add_action(
	'template_redirect',
	static function () {
		if ( is_admin() || wp_doing_ajax() || wp_doing_cron() || is_feed() ) {
			return;
		}
		if ( defined( 'REST_REQUEST' ) && REST_REQUEST ) {
			return;
		}
		if ( is_404() ) {
			rukn_bh_render_404( 'يبدو أن الرابط الذي وصلت منه غير صحيح أو أن الصفحة نُقلت.' );
			exit;
		}
	},
	99
);
