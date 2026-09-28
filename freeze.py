"""Build the public blog into dist/ for Render static hosting."""
import os
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app import app, get_db, init_db  # noqa: E402

DIST = ROOT / 'dist'

PAGES = [
    '/',
    '/songbird-magazine',
    '/angsty-entries',
    '/quick-reads',
    '/archive',
    '/about',
    '/subscribe',
    '/admin/login',
]


class ReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in ('a', 'link') and attributes.get('href'):
            self.refs.append(attributes['href'])
        if tag in ('img', 'script') and attributes.get('src'):
            self.refs.append(attributes['src'])


def output_path(url_path):
    if url_path == '/':
        return DIST / 'index.html'
    cleaned = url_path.strip('/')
    if not cleaned or cleaned.startswith('..') or '\\' in cleaned or '//' in cleaned:
        raise ValueError(f'Unsafe path: {url_path}')
    return DIST / cleaned / 'index.html'


def page_file(url_path):
    parsed = urlparse(url_path)
    path = unquote(parsed.path)
    if path in ('', '/'):
        return DIST / 'index.html'
    return DIST / path.strip('/') / 'index.html'


def asset_file(url_path):
    parsed = urlparse(url_path)
    return DIST / unquote(parsed.path).lstrip('/')


def build():
    init_db()
    app.config['STATIC_EXPORT'] = True

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / 'static', DIST / 'static')

    conn = get_db()
    slugs = [row['slug'] for row in conn.execute('SELECT slug FROM articles')]
    covers = [row['cover_image_filename'] for row in conn.execute('SELECT cover_image_filename FROM articles')]
    about = conn.execute('SELECT author_photo_filename FROM about_page LIMIT 1').fetchone()
    conn.close()

    for filename in covers:
        warn_if_missing_image(filename)
    if about:
        warn_if_missing_image(about['author_photo_filename'])

    from flask import url_for

    paths = PAGES + [f'/article/{slug}' for slug in slugs]
    client = app.test_client()
    for path in paths:
        if path.startswith('/article/'):
            with app.test_request_context():
                request_path = url_for('article_detail', slug=path[len('/article/'):])
        else:
            request_path = path
        response = client.get(request_path)
        if response.status_code != 200:
            raise SystemExit(f'{path} returned {response.status_code}')
        destination = output_path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.data)

    missing = find_missing_references()
    if missing:
        print('Missing files referenced by the generated pages:')
        for item in missing:
            print(f'  {item}')
        raise SystemExit(1)

    print(f'Wrote {len(paths)} pages to {DIST}')


def warn_if_missing_image(filename):
    if not filename:
        return
    if filename == 'cover_image.png':
        location = ROOT / 'static' / 'graphics' / filename
    else:
        location = ROOT / 'static' / 'uploads' / filename
    if not location.exists():
        print(f'Warning: image file is missing: {location.relative_to(ROOT)}')


def find_missing_references():
    missing = []
    for html_path in DIST.rglob('*.html'):
        parser = ReferenceParser()
        parser.feed(html_path.read_text(encoding='utf-8'))
        for ref in parser.refs:
            if ref.startswith(('#', 'mailto:', 'data:', 'http://', 'https://', 'javascript:')):
                continue
            parsed = urlparse(ref)
            if parsed.scheme or parsed.netloc:
                continue
            target = asset_file(ref) if parsed.path.startswith('/static/') else page_file(parsed.path)
            if not target.exists():
                missing.append(f'{html_path.relative_to(DIST)} -> {ref}')
    return missing


def serve(port):
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DIST), **kwargs)

        def do_GET(self):
            parsed = urlparse(self.path)
            rel = unquote(parsed.path).lstrip('/')
            if rel.endswith('/'):
                rel = rel[:-1]
            direct = (DIST / rel).resolve() if rel else None
            dist_root = DIST.resolve()
            if direct and dist_root not in direct.parents and direct != dist_root:
                self.send_error(404)
                return
            if direct and direct.is_file():
                super().do_GET()
                return
            index = dist_root / 'index.html' if not rel else dist_root / rel / 'index.html'
            if dist_root not in index.parents or not index.exists():
                self.send_error(404)
                return
            self.path = '/' + index.relative_to(dist_root).as_posix()
            super().do_GET()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Preview at http://127.0.0.1:{port}/')
    server.serve_forever()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--preview':
        preview_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        if not (DIST / 'index.html').exists():
            build()
        serve(preview_port)
    else:
        build()
