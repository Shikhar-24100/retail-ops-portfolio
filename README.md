# Retail Operations Portfolio

SQL-driven sales and customer analytics, built by **Shikhar Shrivastav** as a business operations portfolio. A shared transaction warehouse connects the completed sales analysis to a planned demand forecasting and inventory study.

**Project 1:** a working interactive Streamlit dashboard, seven SQL analyses, a reproducible data pipeline, audited metric definitions, and historical business recommendations. **Project 2 is planned, not yet implemented.**

This uses public UK giftware sales. It does not contain Myntra data, fashion categories, live stock levels, or measured commercial impact.

## Run locally

Python 3.12 recommended. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m retail_ops.pipeline
.\.venv\Scripts\python -m streamlit run app.py
```

On macOS/Linux, replace `.\.venv\Scripts\python` with `.venv/bin/python`.

The pipeline downloads the original approximately 44 MB UCI workbook and reads both sheets. The first run can take several minutes; subsequent builds use a checksum-validated Parquet cache. Raw data and the SQLite database stay local. Download is an explicit pipeline action, not a dashboard side effect.

After setup on Windows, `./run.ps1` starts the app and builds the database if it is missing.

## Explore the dashboard

- **Sales overview:** market/date filters, gross sales, orders, AOV, repeat rate, monthly trading and a gross-to-net recorded value reconciliation.
- **Customers & cohorts:** identified-customer coverage, transparent behavioural segments and a fixed 90-day repeat-purchase measure.
- **Product performance:** searchable SKU results, concentration, recorded reversals and CSV exports.
- **Pricing & promotion evidence:** observed price variation and the precise data missing for a promotion-effectiveness claim.
- **Definitions & SQL:** source audit, metric contracts and the actual parameterized SQL used by every result.

The default window is **1 December 2009–30 November 2011**, covering complete months. The last nine observed days of December 2011 are available through the date filter and visibly flagged as a partial month.

![Verified dashboard overview in a compact browser window](docs/screenshots/dashboard.jpg)

## Review the work

| Evidence | Location |
|---|---|
| Business findings and proposed actions | [Business review](docs/business_review.md) |
| Numerators, denominators, exclusions and limitations | [Methodology](docs/methodology.md) |
| Interview explanation and questions | [Interview guide](docs/interview_guide.md) |
| Independent scope for the second project | [Forecasting and inventory plan](docs/project_2_plan.md) |
| Actual SQL | [sql/](sql/) |
| Regenerated historical result tables | [reports/](reports/) |
| Data quality and source checksum | [reports/data_quality.json](reports/data_quality.json) |

## Validate

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m retail_ops.validate
```

Unit checks use small hand-verifiable invoices. The Streamlit integration check exercises rendered metrics, search, and empty date selections. The full-data validator independently recalculates headline metrics with pandas, then reconciles SQL product, market, month and customer totals. GitHub Actions runs the fixture and dashboard checks without downloading the full source.

## Data model

`data/raw/online_retail_II.xlsx` → normalized source cache → disposition and overlap audit → `sales`, `returns`, `orders` in `data/processed/retail.sqlite` → shared SQL → dashboard and historical CSVs.

`sales` and `returns` contain merchandise line items. `orders` aggregates positive merchandise lines to one row per invoice. Raw source row and sheet references survive in both line tables. Daily observed units by SKU and market are also exported locally for project 2. Missing dates have not been filled as zero demand.

## Source and attribution

Chen, D. (2012). **Online Retail II** [Dataset]. UCI Machine Learning Repository. [Dataset page](https://archive.ics.uci.edu/dataset/502/online+retail+ii). [DOI: 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D). Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Transformations include normalized identifiers, proven cross-sheet invoice overlap removal, merchandise classification, integer monetary storage, and aggregated reporting. The accompanying software is MIT licensed. Historical patterns are not claims of future performance or business improvement.
