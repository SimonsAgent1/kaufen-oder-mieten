from buy_vs_rent.static_urls import with_versioned_static_urls


def test_version_query_on_static_refs():
    html = '<link href="/static/styles.css"><script src="/static/app.js"></script>'
    out = with_versioned_static_urls(html, "9.8.7")
    assert 'href="/static/styles.css?v=9.8.7"' in out
    assert 'src="/static/app.js?v=9.8.7"' in out


def test_version_query_skips_existing_query():
    html = '<script src="/static/app.js?cache=1"></script>'
    assert with_versioned_static_urls(html, "1.0.0") == html
