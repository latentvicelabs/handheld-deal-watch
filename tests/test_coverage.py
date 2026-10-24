import unittest
from pathlib import Path
import monitor as m

class CoverageTests(unittest.TestCase):
    def test_documented_table_matches_every_configured_model(self):
        self.assertEqual(set(m.MODEL_SCOPE), set(m.MODELS))
        self.assertIn(m.scope_table(), (Path(m.__file__).parent / 'README.md').read_text())
        message = m.notification_scope()
        for scope in m.MODEL_SCOPE.values():
            self.assertIn(scope['short'], message)

    def test_unreachable_and_reachable_without_evidence_are_distinct(self):
        spec = next(s for s in m.SHOPS if s['seller'] == 'ASUS official')
        data = {'merchants': [{'url': spec['url'], 'matched_variants': []}], 'offers': [], 'errors': []}
        rows = {r['model']: r for r in m.coverage_rows(data)}
        self.assertEqual(rows['rog_xbox_ally_x20']['status'], 'page reached; no matched evidence')
        data = {'merchants': [], 'offers': [], 'errors': [{'url':spec['url'], 'error':'timeout'}]}
        rows = {r['model']: r for r in m.coverage_rows(data)}
        self.assertEqual(rows['rog_xbox_ally_x20']['status'], 'unreachable')
        self.assertFalse(rows['rog_xbox_ally_x20']['push_capable'])

    def test_sold_out_stock_check_counts_as_evidence_not_available_offer(self):
        spec = next(s for s in m.SHOPS if s['seller'] == 'ZOTAC official')
        data = {'merchants': [{'url':spec['url'], 'matched_variants':[{'model':'zotac_zone', 'in_stock':False}]}], 'offers':[], 'errors':[]}
        row = next(r for r in m.coverage_rows(data) if r['model'] == 'zotac_zone')
        self.assertEqual(row['status'], 'matched stock/offer evidence')
        self.assertEqual(data['offers'], [])

    def test_three_current_adapters_remain_report_only_at_low_prices(self):
        for seller, title in [('Best Buy','Legion Go 2 Z2 Extreme 32GB'), ('ASUS official','ROG Xbox Ally X20 OLED'), ('Valve official','Steam Deck OLED 512GB')]:
            spec = next(s for s in m.SHOPS if s['seller'] == seller)
            entry = m.deal(spec, title, 100, True)
            self.assertEqual(entry['level'], 'seen')
            self.assertIsNone(entry['before_tax'])

    def test_deal_push_identifies_device_and_limits_coverage_claim(self):
        spec = next(s for s in m.SHOPS if s['seller'] == 'DROIX')
        entry = m.deal(spec, 'OneXFly F1 Pro HX 370 32GB', 800, True)
        title, body = m.notification_content(entry)
        self.assertIn('F1 Pro', title)
        self.assertIn('review candidate', title)
        self.assertIn('VERIFY SHIPPING/IMPORT COSTS', body)
        self.assertIn('this seller offer only', body)
        self.assertIn('DROIX', body)
