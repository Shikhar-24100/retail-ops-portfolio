# Forecasting and inventory interview walkthrough

## A 60-second explanation

“I extended my retail analytics warehouse into a forecasting and inventory study. I selected 50 active products using past data only, compared two simple baselines with seasonal blends and a pooled ridge model, and evaluated the frozen choices on 20 later weeks. The candidate reduced one-week WAPE from 55.1% to 52.0%, but had substantial underforecast bias. When I connected it to a simulated replenishment policy, it performed worse than the moving-average baseline. I kept that finding because the business decision should depend on service and inventory outcomes, not only a forecasting metric.”

## What to demonstrate

1. Open **Forecast & inventory**. Explain the training, validation, warm-up and holdout windows.
2. Show both baselines. Explain why comparing only with seasonal naive would exaggerate the candidate's value.
3. Select a SKU, then contrast its weekly curve with the all-SKU WAPE. Errors in an aggregate curve can cancel across products.
4. Show signed bias and horizon-specific errors. Explain that one-week absolute error is different from lead-time inventory risk.
5. Open **Inventory scenarios**. Explain receive → review/order → fulfil → carry stock. Orders arrive after the stated lead time, not immediately.
6. Change lead time and buffer quantile. Explain why a 95% buffer setting does not imply a guaranteed 95% unit fill rate.
7. Change assumed holding cost or unmet-unit penalty. These reprice a fixed simulation; they do not retune its order decisions.
8. Open the ledger and methodology. End with the default result and the decision to keep the baseline as the study reference.

## Questions to practise

**Why a chronological split?** Randomly mixing weeks can let future patterns influence training. I selected SKUs and model settings from earlier periods, calibrated buffers on validation residuals, then replayed later weeks sequentially.

**Does weekly refitting violate the holdout?** No. Each new forecast uses only observations that would already be known at that point. The hyperparameters and buffer rules remain frozen. This is a rolling-origin evaluation, not one forecast made 20 weeks in advance.

**What is WAPE?** Sum of absolute SKU-week errors divided by total recorded units. It includes errors on zero-demand weeks and weights high-volume units more heavily. It is not an average of per-SKU percentage errors and is not 1 minus “accuracy.”

**Why did the better forecast make worse inventory decisions?** Absolute-error improvement does not ensure unbiased unit forecasts. The log-ridge underpredicts total units by 28.7% and can miss large spikes. Inventory needs a multi-week path and a suitable stock allocation. The pooled validation buffer gives the candidate more total safety units but does not fix SKU/week mismatches. The simulation demonstrates the result; a causal explanation about real stockouts is not established.

**How is safety stock calculated?** For each validation protection window, compare summed recorded units with summed forecasts. Divide the shortfall by that SKU's training mean to pool scales, take an empirical upper quantile, and multiply it back by each SKU's mean. This is simple and reviewable, but assumes comparable normalized errors. Overlapping windows are not independent.

**What is the order-up-to rule?** Target the next lead-time-plus-one weeks of predicted units plus a safety buffer. Subtract on-hand stock after receipts and outstanding orders. Order the positive remainder, rounded up. Lost sales are not backlogged.

**What counts as a result here?** Forecast errors are historical held-out measurements. Fill rate, stock and costs are hypothetical simulation outputs. No actual retailer stockout reduction or monetary saving has been measured.

**Why did you not improve the candidate after seeing these numbers?** Changing it now and continuing to describe the same period as untouched would be misleading. A new model iteration needs a new evaluation period or a clearly labelled exploratory analysis.

**What is missing for Myntra?** Stock availability, style/colour/size hierarchies, launch/de-list dates, promotion exposure, supplier lead-time variability, costs, return flows and lost-demand signals. These would change both target construction and policy constraints.

## Resume wording you can defend

“Evaluated retail demand forecasts on 1,000 unseen SKU-weeks, reducing one-week WAPE from 55.1% to 52.0% versus the stronger simple baseline; built and audited 18 inventory policy/scenario replays, identifying why the forecast gain did not improve service or assumed cost.”

This project was built with coding-assistant support. Reproduce the outputs, explain the SQL-to-forecast data flow, and practise hand-calculating one stock week before an interview. Do not claim production use, actual savings, or ownership of techniques you cannot explain.
