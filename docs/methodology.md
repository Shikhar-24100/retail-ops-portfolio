# Metric and data contracts

## Reporting population

Online Retail II has two workbook sheets, 1,067,371 original rows, and transactions observed from December 2009 through 9 December 2011. The retailer sells giftware and has wholesale customers. Order sizes, customer behaviour and seasonality may not transfer to Indian fashion retail.

All original dates remain available. Published report CSVs use 2009-12-01 through 2011-11-30 to avoid comparing the partial final month against full months. Filters apply inclusively to date, and optionally exactly to country. Every query uses bound parameters.

## Cleaning decisions

1. Normalize invoice and SKU strings without converting product codes to numbers. Convert timestamps and customer identifiers explicitly.
2. Find invoices present in both sheets. Compare the complete multiset of business fields. Remove earlier-sheet copies only if they match exactly. A conflict stops the pipeline instead of silently choosing a version.
3. Retain exact repeated line candidates within the retained source. A repeated line could be a genuine split entry. Record a duplicate flag and publish a gross-sales sensitivity excluding these candidates. This is uncertainty, not proof of erroneous duplication.
4. Classify every retained row into exactly one disposition: invalid, non-merchandise, nonpositive price, sale, return/cancellation, or other adjustment. The audit reports every row count, including exclusions.
5. Merchandise codes match five digits with zero to two letters. This transparent heuristic excludes postage, bank charges, manual adjustments and other special codes. Some real items may be excluded; the source has no authoritative product taxonomy.
6. A sale has positive integer quantity, positive price and an invoice not beginning `C`. A reversal has negative quantity and positive price. A positive-quantity cancellation is an other adjustment. Free goods are excluded from paid merchandise metrics and the forecast handoff.
7. Use integer thousandths of GBP (`mills`) for amounts. This preserves three-decimal source unit prices and avoids floating-point accumulation in SQL. Monetary display is rounded only at presentation.
8. Assert that invoice date, country and customer are consistent before aggregating to orders. Keep anonymous orders in sales. Never invent customer IDs or link unrelated anonymous transactions.

## KPI definitions

| Metric | Definition | Important limit |
|---|---|---|
| Gross merchandise sales | Sum of positive merchandise quantity × unit price | Excludes fees, free goods and cancellations |
| Orders | Distinct invoices containing a positive merchandise sale | A mixed invoice is represented by its eligible merchandise lines |
| AOV | Gross merchandise sales / orders | Gross basis, not net of later returns |
| Identified customers | Distinct non-null customer IDs with eligible orders in window | Does not cover anonymous buyers |
| Repeat purchase rate | Identified buyers with 2+ eligible invoices / identified buyers in window | Window length changes interpretation |
| Identified revenue share | Identified buyers' gross merchandise sales / all gross merchandise sales | A coverage measure, not an imputation |
| Recorded reversals | Absolute value of negative-quantity merchandise rows dated in window | Includes cancellations; not matched back to original purchases |
| Net recorded value | Gross merchandise sales minus recorded reversals | Not profit, not recognized financial-statement revenue |
| Top 20 concentration | Gross merchandise sales of highest-sales 20 SKUs / all gross merchandise sales | Does not imply an optimal inventory allocation |

## Customer segmentation

RFM-inspired descriptive rules use recency at the selected end date and frequency/monetary value inside the selected reporting window. Monetary value is gross identified sales. Segments partition identified customers:

- More than 90 days since last order: lapsed.
- Within 90 days, with 3+ orders: frequent recent buyers.
- Within 90 days, with exactly 2 orders: repeat recent buyers.
- Within 90 days, with exactly 1 order: recent one-time buyers.

The 90-day threshold is an analyst assumption for readable comparisons. It is not a validated churn threshold. Segment sales differences reflect past behaviour and do not prove a response to a marketing action.

## Cohort design

Determine each identified customer's first observed order in the selected market using all history up to the selected end date. Do not reset acquisition when the user changes the report start. Include only customers whose first observed date falls inside the window and has at least 90 days of observable follow-up. A repeat means a second distinct eligible invoice within 0–90 calendar days of first purchase; same-day distinct invoices count.

Aggregate by first-observed acquisition month and report eligible counts alongside rates. Weight the overall rate by customers, not by an average of monthly percentages. The latest eligible acquisition month can be partial because eligibility is customer-specific. Purchases before the source starts are unknown, so early cohorts are left censored. This is repeat purchasing, not month-by-month retention or true new-customer acquisition.

## Promotion effectiveness

It cannot be estimated credibly here. The source lacks promotion eligibility/exposure, campaign IDs, a reference list price, marketing cost, product cost and randomized controls. The dashboard reports price dispersion for SKUs with at least 30 distinct orders as an observational diagnostic only. Differences can reflect quantity breaks, wholesale mix, timing and errors.

To test an offer, predefine eligible customers, assign treatment/control randomly, track the same follow-up window and calculate incremental contribution margin per eligible customer. Include returns, fulfilment and campaign cost. Confirm sample size and uncertainty. No uplift or savings is claimed in this project.

## Forecast handoff

The local daily SKU-market table contains observed positive paid units. These are sales, not unconstrained demand. Stock availability, lost sales, lead times, unit costs, shelf lives and supplier minimums are absent. Missing dates remain absent at this stage; the forecasting methodology explains its calendar treatment and labels all inventory assumptions and simulated outcomes.
