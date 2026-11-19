# Project 2: demand forecasting and inventory decisions

**Status: implemented.** This was the original scope. The completed [methodology](forecasting_methodology.md), [measured results](forecasting_review.md), and [interview guide](forecasting_interview_guide.md) document the final implementation. Forecast accuracy improves against the stronger baseline; the inventory candidate underperforms, and that result is preserved.

## Business question

Can time-based forecasts improve replenishment decisions against a simple baseline on the same retailer's observed sales, under explicit simulated inventory assumptions?

## Evaluation design

- Select a manageable set of active, sufficiently observed UK SKUs using training-period information only. Publish the eligibility rule and excluded population.
- Build a weekly calendar and justify treatment of missing sale dates, inactive products and the partial final week. Positive paid sales are a proxy for demand; historical stockouts and lost sales are unknown.
- Compare a seasonal naive baseline and a simple moving-average baseline with a candidate forecasting model. Use rolling-origin validation for model selection and a later untouched holdout for final reporting.
- Fit all preprocessing using training data only. Use the same forecast origins, SKU scope and horizons for every method.
- Report MAE, WAPE and signed bias by SKU and in aggregate. Handle zero-demand periods explicitly. Report failures and cases where the simple baseline wins.

## Inventory simulation

Specify lead time, review period, service target, starting stock, ordering rules, holding cost and lost-sale cost as assumptions. Compare baseline and forecast-driven order-up-to policies under the same simulated sales path and constraints. Estimate safety stock from training or validation residuals, never the test outcomes.

Report unit fill rate, stockout days/weeks, mean inventory, simulated holding cost, lost units and total assumed cost. Include sensitivity to lead time and cost assumptions. Run both policies on the same initial inventory and include an adequate warm-up so starting stock does not dominate results.

## Required deliverables

1. Reproducible backtesting pipeline and saved forecast errors.
2. Baseline/model comparison with an untouched holdout.
3. Explicit policy equations and simulation assumptions.
4. Inventory trade-off dashboard with comparable policies.
5. Measured historical forecast metrics and clearly labelled simulated inventory results.

No claim of reducing an actual retailer's stockouts or increasing revenue follows from a public-data simulation.
