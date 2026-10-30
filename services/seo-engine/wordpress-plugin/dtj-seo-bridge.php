<?php
/**
 * Plugin Name: DTJ SEO Bridge
 * Description: Lets DTJ's SEO engine read and change ONLY a page's Yoast title, Yoast description and "hide from Google"
 *              setting, plus the site's business details (JSON-LD), after a person approved the change. Nothing else.
 * Version: 1.0.0
 * Requires PHP: 7.4
 *
 * Install once (an administrator; Tier 2): Plugins > Add New > Upload, or copy to wp-content/plugins/ and activate.
 * Test it on a staging copy first. Every route needs a logged-in user (the engine uses an Editor's application password).
 * Remove it any time: deactivating it stops all access; the values already written stay as normal Yoast settings.
 */

if (!defined('ABSPATH')) {
    exit;
}

const DTJ_SEO_FIELDS = array(
    // field name used by the engine => Yoast key (without the "_yoast_wpseo_" prefix)
    'metadesc' => 'metadesc',
    'title'    => 'title',
    'noindex'  => 'meta-robots-noindex',
);
const DTJ_SEO_OPTION = 'dtj_seo_jsonld';

function dtj_seo_get($post_id, $field) {
    $key = DTJ_SEO_FIELDS[$field];
    if (class_exists('WPSEO_Meta')) {
        return (string) WPSEO_Meta::get_value($key, $post_id);
    }
    return (string) get_post_meta($post_id, '_yoast_wpseo_' . $key, true);
}

function dtj_seo_set($post_id, $field, $value) {
    $key = DTJ_SEO_FIELDS[$field];
    if (class_exists('WPSEO_Meta')) {
        WPSEO_Meta::set_value($key, $value, $post_id);  // Yoast's own setter
    } else {
        update_post_meta($post_id, '_yoast_wpseo_' . $key, $value);
    }
    clean_post_cache($post_id);
}

function dtj_seo_snapshot($post_id) {
    $out = array('post_id' => $post_id, 'post_type' => get_post_type($post_id), 'status' => get_post_status($post_id));
    foreach (array_keys(DTJ_SEO_FIELDS) as $f) {
        $out[$f] = dtj_seo_get($post_id, $f);
    }
    return $out;
}

add_action('rest_api_init', function () {
    // Which post is this public URL, and what are its SEO fields now?
    register_rest_route('dtj-seo/v1', '/resolve', array(
        'methods'             => 'GET',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
        'args'                => array('url' => array('required' => true, 'sanitize_callback' => 'esc_url_raw')),
        'callback'            => function (WP_REST_Request $req) {
            $url = $req->get_param('url');
            $id  = url_to_postid($url);
            if (!$id) {
                $path = trim((string) wp_parse_url($url, PHP_URL_PATH), '/');
                $post = get_page_by_path(basename($path), OBJECT, get_post_types(array('public' => true)));
                $id   = $post ? $post->ID : 0;
            }
            if (!$id) {
                return new WP_Error('dtj_seo_not_found', 'No post for this URL', array('status' => 404));
            }
            if (!current_user_can('edit_post', $id)) {
                return new WP_Error('dtj_seo_forbidden', 'Not allowed', array('status' => 403));
            }
            return dtj_seo_snapshot($id);
        },
    ));

    // Change ONE field of ONE post. Only the three fields above; anything else is refused.
    register_rest_route('dtj-seo/v1', '/meta', array(
        'methods'             => 'POST',
        'permission_callback' => function (WP_REST_Request $req) { return current_user_can('edit_post', (int) $req->get_param('post_id')); },
        'args'                => array(
            'post_id' => array('required' => true, 'validate_callback' => function ($v) { return is_numeric($v) && (int) $v > 0; }),
            'field'   => array('required' => true, 'validate_callback' => function ($v) { return isset(DTJ_SEO_FIELDS[$v]); }),
            'value'   => array('required' => true),
        ),
        'callback'            => function (WP_REST_Request $req) {
            $id    = (int) $req->get_param('post_id');
            $field = $req->get_param('field');
            $value = sanitize_text_field((string) $req->get_param('value'));
            if ($field === 'noindex' && !in_array($value, array('', '0', '1', '2'), true)) {
                return new WP_Error('dtj_seo_bad_value', 'noindex must be "", 0, 1 or 2', array('status' => 400));
            }
            $before = dtj_seo_get($id, $field);
            dtj_seo_set($id, $field, $value);
            return array('post_id' => $id, 'field' => $field, 'before' => $before, 'after' => dtj_seo_get($id, $field));
        },
    ));

    // The site's business details (Organization + offices), printed on the home page.
    register_rest_route('dtj-seo/v1', '/jsonld', array(
        array(
            'methods'             => 'GET',
            'permission_callback' => function () { return current_user_can('edit_pages'); },
            'callback'            => function () { return array('jsonld' => json_decode((string) get_option(DTJ_SEO_OPTION, ''), true)); },
        ),
        array(
            'methods'             => 'POST',
            'permission_callback' => function () { return current_user_can('edit_pages'); },
            'callback'            => function (WP_REST_Request $req) {
                $data = $req->get_json_params();
                $data = is_array($data) ? ($data['jsonld'] ?? null) : null;
                if ($data !== null && (!is_array($data) || ($data['@context'] ?? '') !== 'https://schema.org')) {
                    return new WP_Error('dtj_seo_bad_jsonld', 'Expected a schema.org object or null', array('status' => 400));
                }
                $before = json_decode((string) get_option(DTJ_SEO_OPTION, ''), true);
                if ($data === null) {
                    delete_option(DTJ_SEO_OPTION);
                } else {
                    update_option(DTJ_SEO_OPTION, wp_json_encode($data), false);
                }
                return array('before' => $before, 'after' => $data);
            },
        ),
    ));
});

// Print the business details on the home page. Re-encoded from stored data, so it can only ever be JSON.
add_action('wp_head', function () {
    if (!is_front_page()) {
        return;
    }
    $data = json_decode((string) get_option(DTJ_SEO_OPTION, ''), true);
    if (is_array($data)) {
        echo "\n<script type=\"application/ld+json\" class=\"dtj-seo-bridge\">"
            . wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG)
            . "</script>\n";
    }
}, 30);
