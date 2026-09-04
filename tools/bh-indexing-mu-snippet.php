<?php
/**
 * Bahrain site indexing, locale, and content fixes.
 * Enable in WPCode: snippet 3257 (or the latest “Bahrain SEO” draft).
 */
if ( ! defined( 'ABSPATH' ) ) {
	return;
}

/**
 * The /bh install already lives at /bh/. Kayan must not add another country prefix
 * or canonicals become /bh/bh/ and /bhbh/.
 */
add_filter(
	'kayan_i18n_countries',
	static function ( $countries ) {
		if ( isset( $countries['bh'] ) ) {
			$countries['bh']['path']        = '';
			$countries['bh']['regions_ar']  = 'كل مدن مملكة البحرين';
			$countries['bh']['regions_en']  = 'All cities of Bahrain';
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

		$htaccess = ABSPATH . '.htaccess';
		$rules    = <<<'HTA'
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /bh/
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /bh/index.php [L]
</IfModule>
# END WordPress
HTA;
		$current = is_readable( $htaccess ) ? (string) file_get_contents( $htaccess ) : '';
		if ( strpos( $current, 'RewriteBase /bh/' ) === false ) {
			@file_put_contents( $htaccess, $rules );
		}
	},
	1
);

/**
 * Shared replacements for stored content, widgets, and full HTML.
 */
function rukn_bh_seo_fix_text( $text ) {
	if ( ! is_string( $text ) || $text === '' ) {
		return $text;
	}
	$phone = '+971586634710';
	$wa    = '971586634710';
	$img   = 'https://rukn-eltatawer.com/bh/wp-content/uploads/2026/08/rukn-eltatawer-picture.webp';
	$text  = str_replace(
		array(
			'{PHONE_RUKN_BAHRAIN}',
			'{WHATSAPP_RUKN_BAHRAIN}',
			'[[رقم الهاتف/واتساب]]',
			'[[عدد المشاريع]]',
			'[[سنة التأسيس]]',
			'كل مدن المملكة',
			'مدن المملكة',
			'داخل المملكة',
			'يغطي المملكة',
			'https://www.rukn-eltatawer.com/bh/contact-us/',
			'https://rukn-eltatawer.com/bh/contact-us/',
			'rukn-eltatawer.com/bhbh',
			'rukn-eltatawer.com/bh/bh/',
		),
		array(
			$phone,
			$wa,
			$phone,
			'+350',
			'2024',
			'كل مدن البحرين',
			'مدن البحرين',
			'داخل مملكة البحرين',
			'يغطي مملكة البحرين',
			'https://rukn-eltatawer.com/bh/index.php/contact-us/',
			'https://rukn-eltatawer.com/bh/index.php/contact-us/',
			'rukn-eltatawer.com/bh',
			'rukn-eltatawer.com/bh/',
		),
		$text
	);
	$text = preg_replace( '/src="service-\d+\.webp"/', 'src="' . $img . '"', $text );
	return $text;
}

add_filter( 'the_content', 'rukn_bh_seo_fix_text', 5 );
add_filter( 'the_excerpt', 'rukn_bh_seo_fix_text', 5 );
add_filter( 'rank_math/frontend/canonical', 'rukn_bh_seo_fix_text' );
add_filter( 'rank_math/opengraph/url', 'rukn_bh_seo_fix_text' );

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
