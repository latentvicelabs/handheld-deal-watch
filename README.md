# OLED handheld deal watch — Latent Vice Labs

This is a **five-device scanner with partial coverage**. All five models below are configured and scanned. Two have live-validated, push-capable adapters; three remain report-only with their current adapters. A successful workflow or delivery test does not mean every model or source is covered.

Runs on GitHub Actions at `3,13,23,33,43,53` minutes each hour. GitHub can delay or skip scheduled runs; this is not a guaranteed 10-minute service. Scanning ends November 15, 2026. No purchases are made.

## All configured devices and thresholds

<!-- This table is generated from monitor.MODELS and MODEL_SCOPE; tests check it stays in sync. -->
| Configured device | Good-price threshold | Exceptional threshold | Current notification coverage |
|---|---:|---:|---|
| Legion Go 2 Z2 Extreme 32GB | $1,100 | $1,000 | Report-only with current adapters |
| OneXFly F1 Pro HX 370 32/64GB | $925 | $850 | Push-capable; partial seller coverage |
| ROG Xbox Ally X20 / RC74XA OLED | $1,100 | $1,000 | Report-only with current adapters |
| ZOTAC Zone OLED | $550 | $500 | Push-capable; partial seller coverage |
| Steam Deck OLED 512GB | $625 | $550 | Report-only with current adapters |

All thresholds are USD, before tax. The thresholds for the three report-only devices are configured values, **not a promise of phone alerts**. Their current source specifications have unknown shipping, and their sellers are not eligible for shipping-unverified review alerts, so extracted offers remain `seen` regardless of price.

## Coverage by device

**Legion Go 2 Z2 Extreme 32GB** — Scanned; Best Buy has timed out in live runs. Unknown shipping keeps extracted offers report-only.

**OneXFly F1 Pro HX 370 32/64GB** — Live-validated adapters; availability varies by seller. WhatGeek/DROIX can send shipping-unverified review candidates.

**ROG Xbox Ally X20 / RC74XA OLED** — Scanned; no verified offers extracted in live checks. Unknown shipping keeps offers report-only; matcher does not require a RAM capacity.

**ZOTAC Zone OLED** — Live-validated official open-box product adapter; stock and shipping evidence are checked each run.

**Steam Deck OLED 512GB** — Scanned; no verified offers extracted in live checks. Unknown shipping keeps offers report-only.

The F1 matcher accepts HX 370 with 32GB or 64GB; it rejects HX 365 and 8840U variants. Steam Deck matching requires OLED and 512GB. X20 matching accepts the X20/OLED name or RC74XA identifier; it does not independently require 24GB RAM.

## F1 Pro sources

- **ONEXPLAYER official:** new and manufacturer refurbished; exact Shopify variants and USD currency.
- **ItsWorthMore:** searches the live store for newly listed F1 Pro products every scan, then checks exact condition/stock variants. Free US standard shipping per https://buy.itsworthmore.com/policies/shipping-policy . This can find replacement listing URLs, unlike a fixed sold-out link.
- **PayMore Seven Oaks:** the verified exact product listing at https://paymore.com/shop/product/15362360082646/ . Explicit USD/stock schema and free shipping; fixed-listing coverage, not all PayMore stores. Out of stock in the October 23 validation.
- **WhatGeek:** exact US F1 Pro variants; store currency must be USD. Shipping is unverified, so qualifying offers produce review candidates.
- **DROIX:** exact CPU/RAM/condition variants, explicit USD currency and inventory. Uses full `display_price`, never the advertised deposit. Shipping/import costs are unverified, so qualifying offers produce review candidates.

HX 365 and 8840U F1 variants are excluded. 64GB configurations qualify at the same ceilings; extra RAM does not raise the budget.

## ZOTAC alternative

Uses the **actual open-box product page**, https://www.zotacstore.com/us/open-box/zone-handheld/gaming-console , rather than the old category-page adapter. Requires exact ZGC-G1A1W-01 identity, current USD price, explicit product stock status, and free-shipping evidence. Tracks current price, not crossed-out MSRP. Checked October 23, 2026: in stock at $639.99, above the alert ceiling.


## Source failures and discovery feeds

Best Buy's Legion Go 2 pages have repeatedly timed out on GitHub runners. The ASUS X20 and Valve pages have not yielded verified offers in live checks. They remain scheduled scans, not disabled or removed models. Other sources can also fail or return out-of-stock listings.

Slickdeals searches cover all five device names. Reddit RSS adds discovery candidates. RSS entries are unverified, saved for review, and **never send phone pushes**. eBay remains excluded.

Each `report.json` and Actions summary lists every configured device, sources reached/failed, whether matching evidence was extracted, and its current notification mode. Reachable HTML without matching evidence is explicitly unverified; an out-of-stock matching variant is working stock-check evidence, not an available deal. The workflow fails on total loss of validated merchant coverage, but can succeed with partial failures.

## What notifications mean

- **Good-price offer:** model/stock/USD price verified and known shipping included; at or below the configured good-price threshold. Normal-priority push.
- **Exceptional-price offer:** the same checks, at or below the exceptional threshold. High-priority push.
- **Review candidate:** qualifying listed price with unverified shipping/import costs. Currently enabled only for WhatGeek and DROIX. Normal-priority push explicitly marked `VERIFY SHIPPING/IMPORT COSTS`; not a confirmed delivered-price bargain.
- **Delivery test:** names all five configured models and distinguishes push-capable from report-only adapters. Tests transport only; not a deal or proof of retailer coverage.

Real deal pushes identify the device, seller, condition, price basis and this offer's limited scope. GitHub Issue alerts include the source evidence and device coverage note. No search snippet, crossed-out MSRP, advertised deposit, assumed coupon or unavailable variant is treated as a buyable bargain.

`NTFY_TOPIC` is stored in GitHub Actions Secrets and omitted from source/docs. The owner's phone subscription has been tested. Issues suppress repeats; a drop of more than $25 updates an alert. Failed pushes retry on a later scan while the listing still qualifies.

Actions → OLED handheld deal watch → Run workflow → check `test_notification` for a labeled delivery test. Inspect `report.json` or the Actions summary for actual coverage.

```sh
python -m unittest discover -s tests -v
python monitor.py  # no notifications without GitHub runtime credentials
```

The repository is public; this workflow uses standard GitHub-hosted runners. The existing schedule, model eligibility and alert thresholds are unchanged by the documentation/notification clarification.
