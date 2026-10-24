import json
import unittest
from unittest.mock import patch
import expanded_sources as x
import monitor as m

class ExpandedTests(unittest.TestCase):
    def test_better_ram_configuration_is_included(self):
        self.assertEqual(m.product_model('OneXFly F1 Pro HX 370 64GB 4TB'), 'onexfly_f1_pro_hx370_32')
        self.assertIsNone(m.product_model('OneXFly F1 Pro HX 365 64GB'))

    def test_good_price_and_review_are_distinct(self):
        spec = dict(x.SOURCES[1])
        offer = m.deal(spec, 'OneXFly F1 Pro HX 370 32GB', 900, True)
        self.assertEqual(offer['level'], 'review')
        self.assertIsNone(offer['before_tax'])
        self.assertEqual(offer['alert_price'], 900)
        offer = m.deal(dict(spec, shipping=0), 'OneXFly F1 Pro HX 370 32GB', 900, True)
        self.assertEqual(offer['level'], 'watch')
        self.assertFalse(offer['review_required'])

    def test_zotac_current_price_not_crossed_out_price(self):
        body = '''<h1>ZOTAC ZONE</h1><div>ZGC-G1A1W-01 (O)</div>
        <meta itemprop="price" content="539.99"><meta itemprop="priceCurrency" content="USD">
        <span data-price-type="oldPrice">799.99</span><div class="stock available" title="Availability">In stock</div>Free Shipping'''
        offers, checks = x.scan_zotac(x.SOURCES[-1], body, m.deal)
        self.assertEqual(offers[0]['level'], 'watch')
        self.assertEqual(offers[0]['price'], 539.99)
        offers, checks = x.scan_zotac(x.SOURCES[-1], body.replace('stock available', 'stock unavailable'), m.deal)
        self.assertEqual(offers, [])
        self.assertFalse(checks[0]['in_stock'])

    def test_dynamic_search_reads_actual_variant(self):
        product = {'title':'OneXFly F1 Pro HX 370 32GB', 'variants':[
            {'id':1,'title':'Excellent','price':84900,'available':False},
            {'id':2,'title':'Good','price':89900,'available':True}]}
        def fetch(url):
            if '/cart.js' in url:return '{"currency":"USD"}'
            if '/search/' in url:return json.dumps({'resources':{'results':{'products':[{'title':product['title'],'handle':'f1-pro'}]}}})
            return json.dumps(product)
        offers, checks = x.scan_search(x.SOURCES[0], fetch, m.scan_shopify, m.product_model)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]['price'], 899)
        self.assertTrue(offers[0]['url'].endswith('?variant=2'))
        self.assertEqual(len(checks), 2)

    def test_woo_never_uses_deposit_or_other_cpu(self):
        import html
        variants=[{'attributes':{'cpu':'ryzen-ai-9-hx-370','ram':'32gb','condition':'refurbished'},'display_price':899,'is_in_stock':True,'is_purchasable':True,'variation_id':1,'deposit':45},
                  {'attributes':{'cpu':'ryzen-ai-9-hx-365','ram':'32gb'},'display_price':500,'is_in_stock':True,'is_purchasable':True,'variation_id':2}]
        body='<script>{"currency":"USD"}</script><form data-product_variations="'+html.escape(json.dumps(variants),quote=True)+'"></form>'
        offers, checks=x.scan_woo(x.SOURCES[3], body, m.deal, m.product_model)
        self.assertEqual(len(offers),1)
        self.assertEqual(offers[0]['alert_price'],899)
        self.assertEqual(offers[0]['level'],'review')

    def test_push_failure_retries_existing_issue(self):
        entry=m.deal(dict(x.SOURCES[2]),'OneXFly F1 Pro HX 370 32GB',800,True)
        issue={'number':9,'body':f"<!-- handheld-deal:{m.issue_marker(entry)} -->\n<!-- last-cents:80000 -->\n<!-- push-pending -->"}
        with patch.dict(m.os.environ,{'GITHUB_REPOSITORY':'latentvicelabs/handheld-deal-watch','GITHUB_TOKEN':'test'}), patch.object(m,'api_request',side_effect=lambda u,method='GET',payload=None: [issue] if method=='GET' else {}), patch.object(m,'send_ntfy',return_value=True) as push:
            m.report_issue(entry)
            push.assert_called_once()
