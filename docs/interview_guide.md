# Interview walkthrough

## A 60-second explanation

“I built a retail sales and customer analytics system using two years of public transaction data. I used Python to audit and prepare the data, SQLite for the business metrics, and Streamlit for an interactive dashboard. The dashboard connects sales trends, customer repeat behaviour, and product performance to proposed operational actions. I separated historical observations from recommendations and did not claim that a recommendation produced savings. I also identified where promotion analysis was impossible without campaign and cost data.”

Use the measured values in the business review after opening the dashboard. Learn what the values mean; do not memorize unsupported impact percentages.

## A five-minute demo

1. Open **Sales overview**. Explain gross sales, order count, and AOV using their numerators and denominators. Explain why the last partial month is excluded by default.
2. Change market, apply filters, and show that all relevant metrics update. Explain that data quality and source metadata are global.
3. Open **Customers & cohorts**. Contrast the window repeat rate with the 90-day measure. Show customer identification coverage before interpreting customer behaviour.
4. Open **Product performance**. Search a SKU, compare units and sales, and inspect recorded reversals. Explain why a high cancellation amount is not a matched product return rate.
5. Open **Pricing & promotion evidence**. State what is missing and describe a treatment/control experiment.
6. Open **Definitions & SQL** and explain one aggregation and the cohort CTE. End with one business recommendation, its evidence, and the next test needed.

## Questions you should be able to answer

**Why this dataset for Myntra?** It has linked invoices, products, customers, quantities, prices, countries and two years of dates. Those support transferable retail operations methods. It is giftware with wholesale exposure, so I would not transfer the numeric thresholds or findings to fashion customers without validation.

**Why SQLite and Streamlit?** SQL makes business calculations inspectable and testable. Streamlit provides interactive filters and exports from the same queries without duplicating logic across a separate BI tool. The data is small enough for a local analytical database.

**Why not just delete duplicates?** A repeated line may be a real order entry. I removed proven duplicate invoice copies between sheets, retained ambiguous repeats, and reported a sensitivity instead of quietly changing revenue.

**Why not count every row as an order?** One invoice can contain multiple products. An order metric needs invoice grain. The warehouse aggregates eligible merchandise lines first.

**Why keep anonymous purchases?** They are real sales. Dropping them understates sales and changes the customer mix. They remain in revenue and AOV but cannot enter identified-customer repeat metrics.

**How did you avoid misleading retention?** The window repeat rate is explicitly window-dependent. For cohorts, I give every included customer 90 days of follow-up and determine first observed purchase using earlier history, not the selected start date.

**Can you claim profit or promotion uplift?** No. There are no product costs or reliable promotion exposure fields. Net recorded merchandise value is not profit. Price differences alone do not establish causal effects.

**What did testing catch or protect against?** Double-counted invoices, anonymous-buyer denominator mistakes, missing returns-only SKUs, incomplete follow-up, filter-driven false acquisition, and dashboard regressions. The full-data reconciliation checks pandas totals against SQL.

**What would you do with Myntra data?** Add style/size/category hierarchies, order and return status histories, campaign exposure, stock availability, lead times and costs. Define contribution margin, distinguish lost sales from low demand, and validate decisions with time-based evaluation and controlled experiments.

## Ownership

This was built with coding-assistant support. Review the pipeline and SQL, reproduce the figures, and practise changing a definition before presenting it as work you understand. Explain the decisions you can defend. Do not claim production deployment, stakeholder adoption, or commercial outcomes that did not happen.
