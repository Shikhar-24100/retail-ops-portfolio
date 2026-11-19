# Historical business review

**Scope:** all markets, 1 December 2009–30 November 2011. Currency: GBP. Source: UCI Online Retail II. These are historical observations and proposed actions, not realized business improvements. Reproduce the figures with `python -m retail_ops.pipeline` and `python -m retail_ops.validate`.

## Trading snapshot

| Measure | Historical result |
|---|---:|
| Gross merchandise sales | £19,084,294.99 |
| Positive merchandise orders | 38,700 |
| Gross average order value | £493.13 |
| Paid merchandise units | 10,908,388 |
| Identified customers | 5,824 |
| Window repeat purchase rate | 71.7% |
| Sales linked to an identified customer | 87.0% |
| Recorded merchandise reversals | £545,529.58 |
| Net recorded merchandise value | £18,538,765.41 |
| Weighted 90-day repeat rate | 46.6% of 5,227 eligible customers |

The 71.7% rate describes repeat purchasing within the full reporting window. The 46.6% rate gives each eligible first-observed buyer exactly 90 days to repeat. These measures have different populations and follow-up periods and should not be read as contradictory.

Source tables: [KPIs](../reports/kpis.csv), [cohorts](../reports/cohorts.csv). AOV is influenced by the source retailer's wholesale activity and is not a consumer-fashion benchmark.

## Five proposed decisions

### 1. Prioritize a broad set of important SKUs for availability review

**Evidence:** 4,876 SKUs have positive sales. The top 20 represent only **11.0%** of gross sales. It takes **1,047 SKUs**, approximately 21.5% of selling SKUs, to reach 80% of gross sales. The highest-sales SKU is `22423`, Regency Cakestand 3 Tier, at **£325,077.40**.

**Action:** start a replenishment review with a cumulative-sales tier rather than assuming a handful of bestsellers dominates the business. Add variability, margin, supplier lead time and availability before assigning stock targets.

**Next measurement:** project 2 should compare forecast error and simulated fill rate/average stock across selected SKU groups. This analysis does not establish the right inventory quantity or a stockout reduction.

Source: [SKU results](../reports/products.csv), sorted by gross sales. The 80% boundary includes the first SKU that crosses the threshold.

### 2. Test retention interventions with clearly defined customer groups

**Evidence:** **2,120 frequent recent buyers** are 36.4% of identified customers and account for **£12,888,198.36**, or **67.5% of all gross sales**. There are **386 recent one-time buyers** and **2,979 buyers last observed more than 90 days before the reporting end**.

**Action:** investigate service needs among frequent buyers and test a follow-up intervention for a well-defined one-time-buyer cohort. Evaluate a separate, consent-based reactivation test for lapsed buyers after checking normal reorder intervals. Avoid assuming all lapsed customers are lost or that blanket discounts are profitable.

**Next measurement:** incremental 90-day contribution margin and repeat rate versus randomly assigned controls. Costs and campaign exposure must be collected first. Past high spending does not demonstrate a treatment effect.

Source: [Segments](../reports/segments.csv). Segment thresholds are descriptive analyst rules, not a trained churn model.

### 3. Build peak fulfilment plans from the trading calendar

**Evidence:** November 2011 records **£1,457,742.24** and **2,751 orders**, versus February 2011's **£508,869.75** and **1,093 orders**. November sales are **2.86×** February sales, while order volume is **2.52×**. November sales rise only **1.55% year on year** from November 2010.

**Action:** review peak-period staffing, picking and replenishment capacity using order/unit workloads as well as sales value. Examine daily peaks before making a staffing plan. Avoid treating a peak-to-trough comparison as annual business growth.

**Next measurement:** use rolling-origin forecasts and explicit forecast horizons in project 2. Two years of giftware seasonality do not establish future fashion demand.

Source: [Monthly trading](../reports/monthly.csv). The partial December 2011 is excluded from these comparisons.

### 4. Investigate extreme sales/reversal pairs before promoting a bestseller

**Evidence:** SKU `23166`, Medium Ceramic Top Storage Jar, ranks seventh by gross sales at **£81,448.21**, but has **£77,479.64** in recorded reversals and only **£3,968.57** in net recorded value in the same reporting window.

**Action:** inspect the large invoices, cancellation timing and operational reason codes before using the gross ranking in merchandising or replenishment decisions. Add a gross-versus-net exception review to product reporting.

**Next measurement:** quantify confirmed entry corrections separately from physical returns once order-status history is available. The figures above are not a 95% matched return rate, because reversals are not linked to the original sale cohort.

Source: [SKU results](../reports/products.csv), row `23166`.

### 5. Improve customer identification and promotion instrumentation

**Evidence:** **13.0%** of gross sales cannot be assigned to a known customer in the reporting window. No reliable campaign exposure, list price, discount depth, or unit cost appears in the source. Observed price variation therefore cannot establish promotion effectiveness.

**Action:** monitor customer-ID coverage by market/channel and collect consistent campaign eligibility, exposure and cost fields. Preserve anonymous sales in trading KPIs while keeping them outside customer-history metrics. Use permitted stable identifiers, not guessed identity links.

**Next measurement:** identified sales coverage and campaign-data completeness. Once data exists, run an offer/control experiment and evaluate incremental contribution margin per eligible customer rather than only gross sales.

Source: [KPIs](../reports/kpis.csv), [observed price variation](../reports/price_variation.csv).

## Quality findings that materially affect interpretation

- The source contains **1,067,371 rows**. **22,523 rows** are proven repeated invoice copies across sheets and are removed.
- **11,812 exact repeated-line candidates** remain after overlap resolution. They are retained because their business meaning is ambiguous. Over **all observed source dates**, removing flagged sale-line candidates would reduce gross merchandise sales by **£57,092.82**, approximately **0.29%**. This sensitivity uses a wider date range than the trading snapshot.
- The original final month ends on 9 December 2011. It must not be compared directly with complete-month totals.
- Free goods, non-merchandise codes and adjustments are audited separately. Net recorded merchandise value is not financial profit.

Source: [Full-source data audit](../reports/data_quality.json). All nine headline metrics, 4,876 SKU sales totals, and 22 cohort-month results are independently reconciled by the [validator](../reports/validation.json).

## Resume wording after reproducing the work

“Built a reproducible Python/SQLite retail analytics pipeline for 1.07M public transaction rows and an interactive dashboard covering sales, customer repeat behaviour and SKU performance; reconciled metrics independently and developed five evidence-based business recommendations.”

Do not add revenue growth, inventory savings, campaign uplift, Myntra adoption, or production-use claims to this bullet.
