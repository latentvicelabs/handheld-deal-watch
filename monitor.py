#!/usr/bin/env python3
"""Conservative US OLED handheld deals watcher. Python 3.11+, stdlib only.

Never treats a search snippet, RSS headline, crossed-out price or variant's
starting price as a purchasable offer. Only merchant-confirmed SKU/variant,
USD price and stock can generate an exceptional deal alert.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
from expanded_sources import SOURCES, scan_source
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

TIMEOUT = 15
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; LatentViceHandheldDealWatch/1.0; personal-price-monitor)', 'Accept': 'application/json,text/html,application/xml;q=0.8,*/*;q=0.6'}
TAX = 0.08  # NY estimate only; NOT a tax quote
END = dt.date(2026, 11, 15)
MODELS = {
    'legion_go_2_z2e_32': {'label': 'Legion Go 2 Z2 Extreme 32GB', 'watch': 1100, 'exceptional': 1000},
    'onexfly_f1_pro_hx370_32': {'label': 'OneXFly F1 Pro HX 370 32GB+', 'watch': 925, 'exceptional': 850},
    'rog_xbox_ally_x20': {'label': 'ROG Xbox Ally X20 (2026 OLED, 24GB)', 'watch': 1100, 'exceptional': 1000},
    'zotac_zone': {'label': 'ZOTAC Zone OLED', 'watch': 550, 'exceptional': 500},
    'steam_deck_oled_512': {'label': 'Steam Deck OLED 512GB', 'watch': 625, 'exceptional': 550},
}
# Deterministic first-party stores, not search-result redirects or marketplace sellers.
SHOPS = [
    {'kind': 'shopify', 'url': 'https://onexplayerstore.com/products/onexfly-f1-pro-wolrd-s-first-amd-ai-370-oled-144hz-gaming-handheld-console', 'seller': 'ONEXPLAYER official', 'condition': 'new', 'shipping': 0},
    {'kind': 'shopify', 'url': 'https://onexplayerstore.com/collections/all-products/products/refurbish-onexfly-f1-pro-oled-144hz-ultimate-gaming-handheld-console-us-stocks', 'seller': 'ONEXPLAYER official', 'condition': 'manufacturer refurbished', 'shipping': 0},
    {'kind': 'html', 'url': 'https://www.bestbuy.com/product/legion-go-2-8-8-144hz-2k-oled-gaming-handheld-amd-ryzen-z2-extreme-32gb-1tb-windows/JJGH3YZPLW/sku/6643145', 'seller': 'Best Buy', 'condition': 'new', 'shipping': None},
    {'kind': 'html', 'url': 'https://www.bestbuy.com/product/legion-go-2-8-8-144hz-2k-oled-gaming-handheld-amd-ryzen-z2-extreme-32gb-1tb/JJGH3YZPLW/sku/6643145/openbox?condition=excellent', 'seller': 'Best Buy', 'condition': 'open-box excellent', 'shipping': None},
    {'kind': 'html', 'url': 'https://www.bestbuy.com/product/legion-go-2-8-8-144hz-2k-oled-gaming-handheld-amd-ryzen-z2-extreme-32gb-1tb/JJGH3YZPLW/sku/6643145/openbox?condition=good', 'seller': 'Best Buy', 'condition': 'open-box good', 'shipping': None},
    {'kind': 'html', 'url': 'https://www.bestbuy.com/product/legion-go-2-8-8-144hz-2k-oled-gaming-handheld-amd-ryzen-z2-extreme-32gb-1tb/JJGH3YZPLW/sku/6643145/openbox?condition=fair', 'seller': 'Best Buy', 'condition': 'open-box fair', 'shipping': None},
    {'kind': 'html', 'url': 'https://rog.asus.com/us/gaming-handhelds/rog-ally/rog-xbox-ally-x20-2026/', 'seller': 'ASUS official', 'condition': 'new', 'shipping': None},
    {'kind': 'html', 'url': 'https://www.zotacstore.com/us/gaming-console', 'seller': 'ZOTAC official', 'condition': 'open-box', 'shipping': None},
    {'kind': 'html', 'url': 'https://store.steampowered.com/steamdeck', 'seller': 'Valve official', 'condition': 'new', 'shipping': None},
]
SHOPS = [s for s in SHOPS if s['seller'] != 'ZOTAC official'] + SOURCES
FEEDS = [
    'https://slickdeals.net/newsearch.php?' + urlencode({'q': q, 'searcharea': 'deals', 'rss': '1'})
    for q in ['legion go 2', 'onexfly f1 pro', 'xbox ally x20', 'zotac zone', 'steam deck oled']
] + ['https://www.reddit.com/r/buildapcsales/new/.rss', 'https://www.reddit.com/r/SteamDeck/new/.rss']
BAD_TERMS = re.compile(r'\b(case|shell|screen protector|charger|replacement part|motherboard|repair|for parts|not working|broken|display only)\b', re.I)


def fetch(url: str) -> str:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=TIMEOUT) as res:
        if res.status != 200:
            raise RuntimeError(f'HTTP {res.status}')
        return res.read(2_000_000).decode('utf-8', errors='replace')


def product_model(s: str) -> str | None:
    s = re.sub(r'[_‐‑–—]', ' ', s.casefold())
    if BAD_TERMS.search(s):
        return None
    if ('legion go 2' in s or 'legion go gen 2' in s) and ('z2 extreme' in s or '83n0000bus' in s) and re.search(r'\b32\s?g(?:b)?\b', s):
        return 'legion_go_2_z2e_32'
    if re.search(r'one\s?x\s?fly\s*f1\s*pro', s) and re.search(r'(?:hx\s?370|ai\s?9\s*370)', s) and re.search(r'\b(?:32|64)\s?g(?:b)?\b', s):
        return 'onexfly_f1_pro_hx370_32'
    if ('ally x20' in s or 'rc74xa' in s) and ('oled' in s or 'rc74xa' in s):
        return 'rog_xbox_ally_x20'
    if ('zotac' in s and 'zone' in s) and ('oled' in s or '8840u' in s):
        return 'zotac_zone'
    if 'steam deck' in s and 'oled' in s and re.search(r'\b512\s?g(?:b)?\b', s):
        return 'steam_deck_oled_512'
    return None


def deal(spec: dict, name: str, price: float, availability: bool, *, variant: str = '') -> dict | None:
    if not availability or price <= 0:
        return None
    model = product_model(f'{name} {variant}')
    if not model:
        return None
    # Product model identity is strongest only for complete SKU / variant.
    shipping = spec['shipping']
    total = round(price + shipping, 2) if shipping is not None else None
    basis = total if total is not None else price
    level = ('exceptional' if total is not None and total <= MODELS[model]['exceptional'] else
             'watch' if total is not None and total <= MODELS[model]['watch'] else
             'review' if total is None and spec['seller'] in ('DROIX', 'WhatGeek') and price <= MODELS[model]['watch'] else 'seen')
    return {'model': model, 'label': MODELS[model]['label'], 'title': (name + ' ' + variant).strip(),
            'seller': spec['seller'], 'condition': spec['condition'], 'price': round(price, 2),
            'shipping': shipping, 'before_tax': total, 'estimated_total': round(total * (1 + TAX), 2) if total is not None else None,
            'alert_price': total if total is not None else round(price, 2),
            'review_required': shipping is None,
            'in_stock': True, 'url': spec['url'], 'level': level, 'evidence': spec['kind']}


def scan_shopify(spec: dict, body: str) -> list[dict]:
    data = json.loads(body)
    title = str(data.get('title') or '')
    # A Shopify "from $999" product price is never used; actual variants only.
    if 'f1 pro' not in title.lower() and 'onexfly' not in title.lower():
        return []
    ret = []
    for v in data.get('variants', []):
        variant = str(v.get('public_title') or v.get('title') or '')
        price = v.get('price')
        if not isinstance(price, (int, float)) or isinstance(price, bool):
            continue
        entry = deal(spec, title, price / 100, v.get('available') is True, variant=variant)
        if entry:
            # Link to actual variant, not default 8840U/HX365 selection.
            entry['url'] = spec['url'].split('?')[0] + '?variant=' + str(v['id'])
            entry['evidence'] = 'shopify variant ID and available=true'
            ret.append(entry)
    return ret


def jsonld_objects(body: str):
    for m in re.finditer(r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, flags=re.I | re.S):
        try:
            data = json.loads(m.group(1).strip())
            stack = [data]
            while stack:
                obj = stack.pop()
                if isinstance(obj, list):
                    stack.extend(obj)
                elif isinstance(obj, dict):
                    yield obj
                    stack.extend(obj.get('@graph', []) if isinstance(obj.get('@graph'), list) else [])
        except (ValueError, TypeError):
            continue


def scan_html(spec: dict, body: str) -> list[dict]:
    ret = []
    for p in jsonld_objects(body):
        typ = p.get('@type', '')
        if not (typ == 'Product' or (isinstance(typ, list) and 'Product' in typ)):
            continue
        title = str(p.get('name', ''))
        sku = str(p.get('sku') or p.get('mpn') or '')
        for offer in (p.get('offers') if isinstance(p.get('offers'), list) else [p.get('offers')]):
            if not isinstance(offer, dict):
                continue
            if str(offer.get('priceCurrency', '')).upper() != 'USD':
                continue
            # Don't infer available from a buy button. Explicit schema InStock only.
            if not str(offer.get('availability', '')).rstrip('/').lower().endswith('/instock'):
                continue
            if 'bestbuy.com' in urlparse(spec['url']).hostname and sku and sku not in ('6643145', '83N0000BUS'):
                continue
            try:
                price = float(offer['price'])
            except (KeyError, TypeError, ValueError):
                continue
            entry = deal(spec, spec['seller'] + ' ' + title + ' ' + sku, price, True)
            if entry:
                # Shipping not confirmed at checkout for these retailers: log for review, never auto-alert.
                ret.append(entry)
    return ret


def feed_discovery(url: str, body: str) -> list[dict]:
    root = ET.fromstring(body)
    results = []
    for item in list(root.findall('.//item')) + list(root.findall('{http://www.w3.org/2005/Atom}entry')):
        title = (item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
        if not re.search(r'legion\s+go\s*2|onexfly|ally\s*x20|zotac\s+zone|steam\s+deck\s+oled', title, re.I):
            continue
        link = item.findtext('link') or ''
        if not link:
            e = item.find('{http://www.w3.org/2005/Atom}link')
            link = e.get('href', '') if e is not None else ''
        results.append({'title': title[:200], 'url': link, 'source': urlparse(url).hostname,
                        'status': 'unverified discovery only, never auto-notify'})
    return results[:25]


def issue_marker(entry: dict) -> str:
    canonical = f"{entry['model']}|{entry['url']}|{entry['condition']}"
    return hashlib.sha256(canonical.encode()).hexdigest()[:20]


def api_request(url: str, method: str = 'GET', payload: dict | None = None):
    token = os.environ['GITHUB_TOKEN']
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'LatentViceDealWatch'}
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, method=method, data=data, headers=headers)
    with urlopen(req, timeout=TIMEOUT) as res:
        return json.loads(res.read().decode())


def send_ntfy(entry: dict):
    topic = os.getenv('NTFY_TOPIC', '').strip()
    if not topic:
        return False
    if not re.fullmatch(r'[a-zA-Z0-9_-]{16,100}', topic):
        raise ValueError('Invalid NTFY_TOPIC')
    amount = entry['alert_price']
    qualifier = 'LISTED PRICE; VERIFY SHIPPING/IMPORT COSTS' if entry['review_required'] else 'including shipping, before tax'
    text = f"{entry['label']} ${amount:.2f} {qualifier}; {entry['condition']}; {entry['seller']}. Verify condition, checkout and warranty."
    title = 'OLED handheld: review candidate' if entry['review_required'] else 'OLED handheld: ' + entry['level'] + ' price'
    req = Request(f'https://ntfy.sh/{topic}', data=text.encode(), method='POST',
                  headers={'Title': title, 'Priority': 'high' if entry['level'] == 'exceptional' else 'default', 'Click': entry['url']})
    with urlopen(req, timeout=TIMEOUT) as response:
        if response.status not in (200, 201, 202):
            raise RuntimeError('ntfy failed')
    return True


def report_issue(entry: dict) -> str:
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    if not repo or not os.environ.get('GITHUB_TOKEN'):
        return 'not sent (missing GitHub runtime or token)'
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise ValueError('Invalid GITHUB_REPOSITORY')
    base = f'https://api.github.com/repos/{repo}'
    marker = issue_marker(entry)
    cents = round(entry['alert_price'] * 100)
    issues = api_request(base + '/issues?' + urlencode({'state': 'all', 'per_page': '100'}))
    existing = next((i for i in issues if f'<!-- handheld-deal:{marker} -->' in (i.get('body') or '')), None)
    pending = False
    if existing:
        oldbody = existing.get('body') or ''
        m = re.search(r'<!-- last-cents:(\d+) -->', oldbody)
        old = int(m.group(1)) if m else 10**10
        pending = '<!-- push-pending -->' in oldbody
        if cents >= old - 2500 and not pending:
            return 'already alerted at this or similar price'
    qualifier = 'Listed price only — shipping/import costs need review' if entry['review_required'] else 'Including shipping, before tax'
    title = f"[Handheld {'review' if entry['review_required'] else 'deal'}] {entry['label']} ${entry['alert_price']:.2f} - {entry['seller']}"
    body = (f"<!-- handheld-deal:{marker} -->\n<!-- last-cents:{cents} -->\n<!-- push-pending -->\n"
            f"## {entry['level'].title()} price\n\n**Price:** ${entry['alert_price']:.2f} — {qualifier}\n\n"
            f"**Exact configuration:** {entry['title']}\n\n**Seller:** {entry['seller']}\n\n"
            f"**Condition:** {entry['condition']}\n\n**Listing:** {entry['url']}\n\n"
            f"**Evidence:** {entry['evidence']}\n\nCheck checkout total, condition, returns and warranty. No purchase made.")
    if existing:
        issue = existing
        api_request(base + f"/issues/{issue['number']}", 'PATCH', {'title': title, 'body': body, 'state': 'open'})
        if not pending:
            api_request(base + f"/issues/{issue['number']}/comments", 'POST', {'body': f"Price improved: ${entry['alert_price']:.2f}. {qualifier}. {entry['url']}"})
    else:
        issue = api_request(base + '/issues', 'POST', {'title': title, 'body': body})
    # Leave a pending marker if delivery fails so a later scan retries the push.
    if send_ntfy(entry):
        api_request(base + f"/issues/{issue['number']}", 'PATCH', {'body': body.replace('<!-- push-pending -->', '<!-- push-sent -->')})
    return f"recorded issue #{issue['number']}"


def scan() -> dict:
    result = {'checked_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'merchants': [],
              'offers': [], 'discovery': [], 'errors': [], 'alerts': []}
    def merchant(spec):
        if spec['kind'] in ('shopify_search', 'zotac', 'woo', 'paymore'):
            try:
                found, checks = scan_source(spec, fetch, deal, product_model, scan_shopify, scan_html)
                return {'merchant': spec['seller'], 'url': spec['url'], 'verified': len(found), 'matched_variants': checks, 'coverage_verified': bool(checks or found)}, found, None
            except Exception as exc:
                return None, [], {'url': spec['url'], 'error': str(exc)[:180]}
        url = spec['url'].split('?')[0] + '.js' if spec['kind'] == 'shopify' else spec['url']
        try:
            body = fetch(url)
            candidates = []
            if spec['kind'] == 'shopify':
                origin = 'https://' + urlparse(spec['url']).netloc
                currency = json.loads(fetch(origin + '/cart.js')).get('currency')
                if currency != 'USD':
                    raise ValueError(f'Unverified USD currency: {currency!r}')
                product = json.loads(body)
                for variant in product.get('variants', []):
                    model = product_model(str(product.get('title', '')) + ' ' + str(variant.get('title', '')))
                    if model:
                        candidates.append({'model': model, 'variant': variant.get('title'), 'in_stock': variant.get('available') is True,
                                           'price': variant.get('price', 0) / 100})
            found = scan_shopify(spec, body) if spec['kind'] == 'shopify' else scan_html(spec, body)
            return {'merchant': spec['seller'], 'url': spec['url'], 'verified': len(found),
                    'matched_variants': candidates, 'coverage_verified': bool(candidates or found)}, found, None
        except Exception as exc:
            return None, [], {'url': spec['url'], 'error': str(exc)[:180]}

    def feed(url):
        try:
            return feed_discovery(url, fetch(url)), None
        except Exception as exc:
            return [], {'url': url, 'error': str(exc)[:180]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        for status, found, error in pool.map(merchant, SHOPS):
            if status:
                result['merchants'].append(status)
            result['offers'].extend(found)
            if error:
                result['errors'].append(error)
        for found, error in pool.map(feed, FEEDS):
            result['discovery'].extend(found)
            if error:
                result['errors'].append(error)
    return result


def main():
    output = Path(os.getenv('REPORT_FILE', 'report.json'))
    if dt.datetime.now(ZoneInfo('America/New_York')).date() > END:
        print('Tracker window ended 2026-11-15. Exiting.'); return 0
    data = scan()
    data['offers'].sort(key=lambda d: (d['level'] != 'exceptional', d['before_tax'] or 9e9))
    for entry in data['offers']:
        if entry['level'] in ('exceptional', 'watch', 'review'):
            try:
                status = report_issue(entry)
                data['alerts'].append({'title': entry['title'], 'status': status})
            except Exception as exc:
                # Do not silently swallow failures that prevent alerts.
                data['alerts'].append({'title': entry['title'], 'status': 'FAILED', 'error': str(exc)})
                print(f'ERROR: could not alert: {exc}', file=sys.stderr)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for o in data['offers']:
        if o['level'] in ('exceptional', 'watch', 'review'):
            print(f"{o['level'].upper()}: {o['label']} {o['seller']} ${o['alert_price']:.2f} {o['url']}")
    print(f"Scanned {len(SHOPS)} direct merchant pages and {len(FEEDS)} RSS feeds; "
          f"{len(data['offers'])} stock-confirmed matched variants; "
          f"{len(data['discovery'])} unverified discoveries; {len(data['errors'])} failures")
    for error in data['errors']:
        print(f"SOURCE FAILED: {error['url']} — {error['error']}")
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        lines = ['## OLED handheld scan', f"Matched offers: {len(data['offers'])}; source failures: {len(data['errors'])}.", '',
                 '| Model | Seller | Price | Shipping | Classification |', '|---|---|---:|---:|---|']
        for offer in data['offers']:
            lines.append(f"| {offer['label']} | {offer['seller']} | ${offer['price']:.2f} | {offer['shipping']} | {offer['level']} |")
        lines.extend(['', '### Stock checks'] + [f"- {m['merchant']}: {v['variant']} — {'in stock' if v['in_stock'] else 'out of stock'} (${v['price']:.2f})" for m in data['merchants'] for v in m.get('matched_variants', [])])
        lines.extend(['', '### Source failures'] + [f"- {e['url']}: {e['error']}" for e in data['errors']])
        with open(summary, 'a', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')
    if not any(m.get('coverage_verified') for m in data['merchants']):
        print('ERROR: no validated merchant coverage.', file=sys.stderr)
        return 1
    return 1 if any(a['status'] == 'FAILED' for a in data['alerts']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
