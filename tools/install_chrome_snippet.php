<?php
/**
 * Upsert Code Snippets row "Rukn BH Chrome SEO" without touching snippet 5.
 */
if ( ! defined( 'ABSPATH' ) ) {
	fwrite( STDERR, "Run via wp eval-file\n" );
	return;
}

global $wpdb;
$table = $wpdb->prefix . 'snippets';
$path  = dirname( __FILE__ ) . '/bh_chrome_snippet.php';
$code  = file_get_contents( $path );
if ( ! is_string( $code ) || $code === '' ) {
	fwrite( STDERR, "missing snippet file\n" );
	return;
}
$code = preg_replace( '/^<\?php\s*/', '', $code );

$exists = (int) $wpdb->get_var(
	$wpdb->prepare( "SELECT id FROM {$table} WHERE name = %s LIMIT 1", 'Rukn BH Chrome SEO' )
);

$row = array(
	'name'         => 'Rukn BH Chrome SEO',
	'description'  => 'Homepage counters, WhatsApp-only chrome, hide empty ratings. Companion to snippet 5.',
	'code'         => $code,
	'tags'         => 'bahrain,seo',
	'scope'        => 'global',
	'condition_id' => 0,
	'priority'     => 2,
	'active'       => 1,
	'modified'     => current_time( 'mysql' ),
);

if ( $exists ) {
	$wpdb->update( $table, $row, array( 'id' => $exists ) );
	echo "updated snippet {$exists}\n";
} else {
	$row['revision'] = 1;
	$wpdb->insert( $table, $row );
	echo 'inserted snippet ' . (int) $wpdb->insert_id . "\n";
}
