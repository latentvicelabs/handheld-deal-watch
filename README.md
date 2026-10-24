# OLED handheld deal watch — Latent Vice Labs

Personal US deal watcher. Runs on GitHub Actions at `3,13,23,33,43,53` minutes each hour (actual scheduling can be delayed). Scanning ends November 15, 2026. Never purchases anything.

## Active phone alert targets

| Device | Good-price push | Exceptional high-priority push |
|---|---:|---:|
| OneXFly F1 Pro **HX 370, 32GB or 64GB** | $925 | $850 |
| ZOTAC Zone **8840U OLED, open-box** | $550 | $500 |

Thresholds include shipping when known and exclude tax. Unknown shipping/import costs generate **review candidate** notifications at the good-price ceiling, explicitly labeled as listed price only. These are leads to inspect, not confirmed landed-cost bargains. No assumed coupon savings.

## F1 Pro sources

- **ONEXPLAYER official:** new and manufacturer refurbished; exact Shopify variants and USD currency.
- **ItsWorthMore:** searches the live store for newly listed F1 Pro products every scan, then checks exact condition/stock variants. Free US standard shipping per https://buy.itsworthmore.com/policies/shipping-policy . This can find replacement listing URLs, unlike a fixed sold-out link.
- **PayMore Seven Oaks:** the verified exact product listing at https://paymore.com/shop/product/15362360082646/ . Explicit USD/stock schema and free shipping; fixed-listing coverage, not all PayMore stores. Currently out of stock.
- **WhatGeek:** exact US F1 Pro variants; store currency must be USD. Shipping is unverified, so qualifying offers produce review candidates.
- **DROIX:** exact CPU/RAM/condition variants, explicit USD currency and inventory. Uses full `display_price`, never the advertised deposit. Shipping/import costs are unverified, so qualifying offers produce review candidates.

HX 365 and 8840U F1 variants are excluded. 64GB configurations qualify at the same ceilings; extra RAM does not raise the budget.

## ZOTAC alternative

Uses the **actual open-box product page**, https://www.zotacstore.com/us/open-box/zone-handheld/gaming-console , rather than the old category-page adapter. Requires exact ZGC-G1A1W-01 identity, current USD price, explicit product stock status, and free-shipping evidence. Tracks current price, not crossed-out MSRP. Checked October 23, 2026: in stock at $639.99, above the alert ceiling.

## Remaining coverage

Legacy Best Buy Legion Go 2, ASUS X20 and Valve pages are still scanned, but are not validated reliable alert sources. They may time out or expose no parseable offers. Slickdeals and Reddit RSS are discovery-only and never generate phone pushes. eBay remains excluded.

Every scan records reachable sources, matching configurations (including out-of-stock ones), offers and failures. Total loss of validated merchant coverage fails the workflow. A successful run means some validated coverage exists; it does not mean every source worked.

## Notifications and operation

`NTFY_TOPIC` is stored as a GitHub Actions secret, never in source. The owner's phone subscription was tested. Good prices and review candidates use normal priority; exceptional verified deals use high priority. GitHub Issues retain alerts and suppress repeats; a drop of more than $25 updates an existing alert. Failed phone pushes leave a pending marker and retry on a future scan while the listing still qualifies.

Actions → OLED handheld deal watch → Run workflow → check `test_notification` sends a clearly labeled setup test. Inspect the run summary or `report.json` artifact for source health. The notification topic is intentionally omitted from this README.

```sh
python -m unittest discover -s tests -v
python monitor.py  # local scan, no notifications without GitHub runtime credentials
```

Private-repository Actions usage draws on the owner's allowance. Standard jobs round up to whole minutes. Repository/account visibility and billing settings are unchanged.
