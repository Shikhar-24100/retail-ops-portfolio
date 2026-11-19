# Forecasting and inventory business review

**Historical scope:** 50 training-selected active UK giftware SKUs; 20 held-out weeks from 18 July through 4 December 2011. **Inventory scope:** hypothetical weekly lost-sales replay, not the retailer's real stock history. No Myntra data or commercial impact is claimed.

## Main finding

The validation-selected pooled log-ridge reduces one-week WAPE from **55.11% to 52.00%** against the stronger four-week moving-average baseline, an absolute reduction of **3.11 percentage points** or **5.64% relative**. It outperforms that baseline on 36 of 50 individual SKU WAPEs.

That improvement **does not translate into better inventory decisions**. In the default two-week-lead-time, 95%-buffer replay, the candidate has a lower fill rate, more unserved units, more mean stock and higher hypothetical cost. The baseline has higher fill rate and lower assumed cost in all nine prespecified lead-time/buffer settings.

## Historical forecast evaluation

| Model | One-week MAE (units/SKU-week) | WAPE | Signed bias |
|---|---:|---:|---:|
| 4-week moving average — strongest validation baseline | 177.72 | 55.11% | −5.93% |
| Pooled log-ridge, alpha 100 — frozen candidate | 167.69 | 52.00% | −28.70% |
| 52-week seasonal naive — second baseline | 303.38 | 94.07% | +42.80% |

All methods use the same 1,000 held-out SKU-week points. The target totals 322,500 recorded paid units. Model selection used 800 earlier validation SKU-week points: candidate validation WAPE was 56.77%, versus 63.24% for the strongest baseline. The weaker seasonal naive is reported so the comparison cannot hide a stronger simple method.

The candidate's first three horizon WAPEs are better than the moving average, but its unit bias is much more negative. At five weeks, candidate WAPE is 59.45% versus baseline 58.98%. A forecast can reduce absolute error while severely underpredicting large orders; aggregate accuracy alone is insufficient for a stock policy.

Sources: [aggregate accuracy](../reports/forecasting/accuracy.csv), [SKU results](../reports/forecasting/sku_accuracy.csv), [frozen model selection](../reports/forecasting/model_selection.json).

## Default simulated inventory comparison

Assumptions: weekly review, two-week supplier lead time, 95th-percentile validation buffer, eight-week warm-up, unlimited supply, uniform within-week demand, no backorders, £0.05/unit/week holding cost and £1/unserved-unit penalty. Buffers are calibrated separately by model using earlier validation errors.

| Holdout outcome | Baseline policy | Candidate policy |
|---|---:|---:|
| Replayed units | 322,500 | 322,500 |
| Simulated unit fill rate | 93.37% | 90.38% |
| Unserved replay units | 21,396 | 31,015 |
| Stockout SKU-weeks | 50 / 1,000 | 55 / 1,000 |
| Mean portfolio on-hand units | 56,735.58 | 59,848.22 |
| Hypothetical total cost | £78,131.58 | £90,863.22 |
| Ending on-hand units | 51,045 | 45,569 |
| Ending outstanding-order units | 40,088 | 32,829 |

The candidate leaves **9,619 more units unserved** and incurs **£12,731.63 more assumed cost**. These are differences inside a simulator, not observed business losses or savings.

Two SKUs contribute 9,672 excess candidate unserved units before offsetting improvements elsewhere: `22086` (5,101) and `22197` (4,571). Inspect their time series before choosing a uniform safety buffer for the assortment. The candidate's pooled buffer allocates about 60,088 safety units versus baseline 46,672, yet delivers worse service. More total safety stock does not ensure that stock is aligned with the right SKU and week.

Sources: [inventory summaries](../reports/forecasting/inventory_summary.csv), [buffer calibration](../reports/forecasting/safety_calibration.csv), and the saved `inventory_ledger.parquet` exposed through the dashboard.

## Decisions supported by the study

1. **Keep the moving average as the replenishment reference for this study.** The candidate has not earned replacement status on service or assumed cost. Do not select it solely from the one-week WAPE gain.
2. **Evaluate replenishment over the protection horizon and by SKU.** Include signed bias, unserved units and holding stock. Review the two high-shortfall products individually rather than increasing a pooled buffer for every SKU.
3. **Make the service–stock trade-off explicit.** At two-week lead time, the baseline's 90%, 95% and 99% buffer settings produce simulated fill rates of 90.70%, 93.37% and 97.17%, with mean stock of roughly 45,990, 56,736 and 89,368 units. These are sensitivity results, not a holdout-tuned deployment recommendation.
4. **Treat a shorter supplier lead time as a scenario to investigate.** At the 95% buffer, a one-week baseline replay reaches 93.53% fill with about 47,468 mean stock, compared with 93.37% and 56,736 at two weeks. Real lead-time reduction feasibility and supplier costs are unknown.
5. **Collect availability and economics before making real inventory commitments.** Historical paid sales omit lost demand; costs and lead times are assumed. A next iteration could validate bias-aware or quantile forecasts on a new forward period, with SKU-level costs and actual stock availability. This holdout must not become a new tuning set while still being called unseen.

## Reproducibility and practical limits

The SKU sample covers **20.9% of UK training paid units**, not all retailer products. The data includes giftware and wholesale orders; fashion size/colour variants, product launches, return-to-stock behaviour and Indian retail seasonality are not represented.

The study independently verifies 53,000 saved forecast rows, 5,200 weekly SQL source cells, 25,200 inventory ledger rows and all 18 policy/scenario runs. [Validation record](../reports/forecasting/validation.json). The historical data and the uniform assumed costs do not establish financial savings, production suitability or a universal inventory optimum.
