# Forecasting and inventory methodology

## Scope and calendar

Use the same audited UCI source as project 1, restricted to **United Kingdom paid merchandise sales**. Form Monday–Sunday weeks. Exclude the partial first week (source starts Tuesday 1 December 2009) and partial final week (source ends Friday 9 December 2011). The study has 104 full weeks, beginning 7 December 2009 and ending 4 December 2011.

Missing SKU-weeks are filled with zero **recorded paid units**. This is a modelling assumption about the transaction record. It cannot distinguish no demand, unavailable stock, a product not listed, or missing records. Free units and reversed quantities do not enter the target. Gross paid sales may include invoices later cancelled; this is not unconstrained or net customer demand.

| Stage | Week starts | Weeks | Purpose |
|---|---|---:|---|
| Training | 2009-12-07–2011-01-24 | 60 | Eligibility, ranking, initial fitting |
| Validation | 2011-01-31–2011-05-16 | 16 | Rolling-origin model choice and buffer calibration |
| Warm-up | 2011-05-23–2011-07-11 | 8 | Allow both inventory policies to establish pipelines |
| Holdout | 2011-07-18–2011-11-28 | 20 | Final historical evaluation; last week ends 4 December |

## Training-only product selection

Eligible SKUs have recorded sales in at least 40 of the first 60 weeks and at least six of their final eight weeks. Rank eligible SKUs by total training units, breaking ties by SKU code; take the top 50. There are 789 eligible SKUs. The selected 50 cover 20.9% of UK training paid units. This intentionally studies active products, not the entire assortment, intermittent-demand products, or new launches.

All future units can change without changing this selection. Training-only rankings and active-week counts are saved in `reports/forecasting/selected_skus.csv`.

## Baselines and candidate models

**Four-week moving average:** forecast every horizon with the mean of the four most recently observed weeks. Multi-step forecasts are flat, not recursively averaged.

**52-week seasonal naive:** use units from exactly 52 weeks before each target week. This is a fixed weekly seasonal lag; annual calendar alignment can drift and only one prior cycle is available.

**Seasonal blends:** combine the seasonal naive and four-week mean with seasonal weights 25%, 50%, and 75%. Both endpoints are already represented by the baselines.

**Pooled log-ridge:** fit a shared regularized linear model to `log(1 + units)` across the selected SKUs, using NumPy. Candidate penalties are 1, 10 and 100. Features are log-transformed lags 1/2/4/8, trailing four/eight-week means, trailing four-week standard deviation, known annual sine/cosine features, and SKU indicators. Start training rows only after eight observed weeks. Fit feature centering/scaling and coefficients on past rows only. The target is centered; the ridge penalty applies to the standardized feature coefficients.

For multi-step ridge forecasts, append the preceding prediction to history before constructing the next step. Back-transform with `exp(prediction) − 1`, clip below zero, and apply a numerical overflow guard far beyond observed units. There is no fitted bias correction. Exponentiating a log-scale point prediction can underestimate mean unit demand, especially for order spikes; the study reports signed bias rather than concealing this limitation.

All models forecast five weeks ahead at each origin. Models may refit weekly using observations available before that origin. This is a sequential rolling forecast, not a single fixed 20-week forecast. Hyperparameters, SKU scope and buffers are not retuned on holdout data.

## Selection and error metrics

Evaluate eight configurations at 16 expanding validation origins. Select the strongest baseline and best candidate **separately**, using pooled one-week validation WAPE. Break ties by method name. Save those choices before running the later evaluation. Do not replace the selected candidate after seeing holdout outcomes.

For evaluated SKU-week points, with recorded units `y` and forecast `f`:

```
MAE = sum(abs(f − y)) / number of points
WAPE = sum(abs(f − y)) / sum(y)
Bias = sum(f − y) / sum(y)
```

WAPE includes zero-unit weeks in absolute error. If the total denominator is zero, the rate is unavailable. It is not the average of per-SKU percentages and not error calculated from an aggregated portfolio curve. Positive bias means overforecasting. Later horizons are scored only when targets fall inside the same evaluation stage, so their sample sizes decrease. The one-week holdout has 1,000 SKU-week points.

## Safety buffers

For a fixed supplier lead time `L` and a weekly review, protection is `H = L + 1` weeks. From validation origins with **all H targets observed inside validation**, calculate:

```
normalised_shortfall = (sum(recorded units over H) − sum(forecasts over H))
                       / SKU mean weekly training units
buffer_factor = max(0, empirical quantile(normalised_shortfall))
SKU safety units = buffer_factor × SKU mean weekly training units
```

Pool normalised errors across SKUs and use the conservative empirical `higher` quantile. Compare 90%, 95% and 99% settings. A three-week protection window has 700 complete validation SKU-windows. They overlap in time and are dependent; these are empirical buffers, not calibrated independent confidence guarantees. Pooling assumes normalisation makes errors comparable and can misallocate stock across heterogeneous products.

Buffer parameters are calibrated separately for each model and protection horizon, then frozen. A 95% calibration setting is **not** a promised 95% unit fill rate.

## Inventory decision framework

Replay both policies against the same recorded weekly units. Review once per week. Supplier lead times are fixed at 1, 2 or 4 weeks; supply is unlimited. Quantities are rounded upward to integer units. No minimum order quantity, order fee, expiry, substitution, backorders, or return-to-stock flow is modelled.

At the start of each week:

1. Receive orders due this week.
2. Calculate stock position as available on-hand stock plus all outstanding orders.
3. Set target `S = ceil(sum(forecasts over L + 1 weeks) + safety units)`.
4. Order `max(0, S − stock position)`, arriving at the beginning of week `t + L`.
5. Fulfil demand from available stock; unmet units are lost, not backlogged. Carry closing stock forward.

Both policies begin the eight-week warm-up with the same stock, `ceil((L + 1) × mean observed units in the final eight validation weeks)`, and no outstanding orders. Warm-up losses/costs are excluded from holdout results, but its resulting stock and pipelines carry into evaluation. The warm-up is twice the longest lead time. No orders are accelerated at the end of the evaluation.

Assume units arrive at week start and demand occurs uniformly within each week for holding-cost accounting. If available stock `A` covers weekly demand `D`, average on-hand stock is `A − D/2`. If `0 ≤ A < D`, stock is depleted early and its time average is `A²/(2D)`. With zero demand, average stock is `A`.

## Simulation outcomes and cost sensitivity

Report unit fill rate (fulfilled/replayed units), unserved units, stockout SKU-weeks, portfolio mean on-hand units, ordered units, and ending on-hand/pipeline stock. A stockout SKU-week has at least one unserved unit; it is not a calendar day count.

Default hypothetical holding cost is **£0.05 per unit per week** and unmet-unit penalty is **£1 per unit**, identical across products. Cost is holding rate × stock-unit-weeks plus penalty × unserved units. Procurement costs, fixed ordering fees and disposal costs are absent. Ending pipeline is disclosed; no liquidation value is assumed. These are decision-support cost assumptions, not actual retailer costs or realized savings.

The dashboard reprices fixed replays when cost inputs change. It does not optimize stock targets from those new costs. The nine settings are a prespecified sensitivity grid, not proof of a globally optimal policy or a holdout-selected deployment configuration.

## Verification and sources

Unit tests perturb future targets, verify selection cutoffs and hand-calculate baseline/error/inventory cases. An independent validator reconciles weekly units against SQL, recomputes error metrics, verifies calibration/selection restrictions, and checks every receipt, stock balance and order equation. Saved artefacts have source/input checksums.

Method references: Hyndman and Athanasopoulos, [time-series cross-validation](https://otexts.com/fpp3/tscv.html), and MIT OpenCourseWare, [inventory review policies](https://ocw.mit.edu/courses/esd-260j-logistics-systems-fall-2006/8b53c45fd26ffff706d815131e8d177e_lect11.pdf). The implementation choices, numerical results and simulation assumptions above are specific to this portfolio.
