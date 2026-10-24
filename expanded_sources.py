"""Merchant-specific public product adapters; no carts or purchases."""
import html
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlencode, urlparse, urljoin

SOURCES = [
    {'kind': 'shopify_search', 'url': 'https://buy.itsworthmore.com', 'seller': 'ItsWorthMore', 'condition': 'refurbished', 'shipping': 0},
    {'kind': 'shopify', 'url': 'https://www.whatgeek.com/products/one-netbook-onexfly-f1-pro-handheld-game-console', 'seller': 'WhatGeek', 'condition': 'new', 'shipping': None},
    {'kind': 'paymore', 'url': 'https://paymore.com/shop/product/15362360082646/', 'seller': 'PayMore Seven Oaks', 'condition': 'used', 'shipping': 0},
    {'kind': 'woo', 'url': 'https://droix.net/product/onexplayer-onexfly-f1-pro/', 'seller': 'DROIX', 'condition': 'per variant', 'shipping': None},
    {'kind': 'zotac', 'url': 'https://www.zotacstore.com/us/open-box/zone-handheld/gaming-console', 'seller': 'ZOTAC official', 'condition': 'open-box', 'shipping': 0},
]

class Page(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(body)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
    def meta(self, prop):
        return [a.get('content', '') for t, a in self.tags if t == 'meta' and a.get('itemprop') == prop]

def scan_zotac(spec, body, deal):
    page = Page(body)
    # Exact product SKU + explicit product stock status, not an enabled JS button.
    if 'ZGC-G1A1W-01' not in body or 'ZOTAC ZONE' not in body.upper():
        raise ValueError('ZOTAC product identity missing')
    price, currency = page.meta('price'), page.meta('priceCurrency')
    if not price or currency != ['USD']:
        raise ValueError('ZOTAC USD product price missing or ambiguous')
    stock = [a for _, a in page.tags if a.get('title') == 'Availability' and 'stock' in a.get('class', '').split()]
    if len(stock) != 1:
        raise ValueError('ZOTAC stock evidence missing')
    available = 'available' in stock[0].get('class', '').split()
    if 'Free Shipping' not in body:
        spec = dict(spec, shipping=None)
    entry = deal(spec, 'ZOTAC Zone OLED 8840U', float(price[0]), available)
    return ([entry] if entry else []), [{'model': 'zotac_zone', 'variant': 'ZGC-G1A1W-01 open-box', 'in_stock': available, 'price': float(price[0])}]

def scan_woo(spec, body, deal, product_model):
    page = Page(body)
    forms = [a for t, a in page.tags if t == 'form' and 'data-product_variations' in a]
    if len(forms) != 1:
        raise ValueError('DROIX variation data missing')
    # USD must be explicit in page data; a dollar symbol alone is insufficient.
    if not re.search(r'"(?:currency|priceCurrency)"\s*:\s*"USD"', body):
        raise ValueError('DROIX USD currency not verified')
    offers, checks = [], []
    for v in json.loads(forms[0]['data-product_variations']):
        attrs = v.get('attributes', {})
        variant = ' '.join(str(x).replace('-', ' ') for x in attrs.values())
        model = product_model('OneXFly F1 Pro ' + variant)
        if not model:
            continue
        price = float(v['display_price'])  # full device price; never the deposit
        available = v.get('is_in_stock') is True and v.get('is_purchasable') is True
        checks.append({'model': model, 'variant': variant, 'price': price, 'in_stock': available})
        condition = str(attrs.get('attribute_pa_condition', 'unknown')).replace('-', ' ')
        url = spec['url'] + '?' + urlencode(attrs)
        entry = deal(dict(spec, condition=condition, url=url), 'OneXFly F1 Pro', price, available, variant=variant)
        if entry:
            entry['evidence'] = 'WooCommerce exact variant, full price and explicit stock; shipping/import costs unverified'
            offers.append(entry)
    return offers, checks

def scan_search(spec, fetch, scan_shopify, product_model):
    origin = spec['url'].rstrip('/')
    if json.loads(fetch(origin + '/cart.js')).get('currency') != 'USD':
        raise ValueError('ItsWorthMore store currency is not USD')
    query = urlencode({'q': 'onexfly', 'resources[type]': 'product', 'resources[limit]': 10})
    results = json.loads(fetch(origin + '/search/suggest.json?' + query))['resources']['results']['products']
    offers, checks = [], []
    for p in results:
        if not product_model(p.get('title', '')):
            continue
        handle = p.get('handle', '')
        if not re.fullmatch(r'[a-zA-Z0-9-]+', handle):
            raise ValueError('Invalid merchant product handle')
        url = origin + '/products/' + handle
        body = fetch(url + '.js')
        data = json.loads(body)
        for v in data.get('variants', []):
            checks.append({'model': product_model(data['title']), 'variant': data['title'] + ' / ' + v['title'], 'price': v['price'] / 100, 'in_stock': v.get('available') is True})
        found = scan_shopify(dict(spec, kind='shopify', url=url), body)
        for entry in found:
            entry['condition'] = 'refurbished / ' + entry['title'].split(data['title'], 1)[-1].strip()
        offers.extend(found)
    return offers, checks

def scan_source(spec, fetch, deal, product_model, scan_shopify, scan_html):
    if spec['kind'] == 'shopify_search':
        return scan_search(spec, fetch, scan_shopify, product_model)
    body = fetch(spec['url'])
    if spec['kind'] == 'zotac':
        return scan_zotac(spec, body, deal)
    if spec['kind'] == 'woo':
        return scan_woo(spec, body, deal, product_model)
    if spec['kind'] == 'paymore':
        if 'Free Shipping' not in body:
            spec = dict(spec, shipping=None)
        offers = scan_html(spec, body)
        checks = []
        # Product schema remains valid coverage even when out of stock.
        for text in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', body, re.S):
            p = json.loads(text)
            if p.get('@type') != 'Product' or not product_model(p.get('name', '')):
                continue
            o = p.get('offers', {})
            if o.get('priceCurrency') == 'USD' and o.get('availability'):
                checks.append({'model': product_model(p['name']), 'variant': p['name'], 'price': float(o['price']), 'in_stock': str(o['availability']).endswith('/InStock')})
        if not checks:
            raise ValueError('PayMore product/stock schema missing')
        return offers, checks
    raise ValueError('Unknown source adapter')
