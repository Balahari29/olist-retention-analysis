# Business Requirements Document (BRD)
**Project:** Olist Customer Retention & Delivery Experience Analysis
**Author:** Bala Hariharan B (Business / Data Analyst)
**Version:** 0.1 (draft, Phase 1) | **Date:** 2026-11-02 | **Status:** For stakeholder review

> No figures in this document come from the data yet. Values marked **[TBD]** will be filled from files saved
> under `outputs/` in later phases.

---

## 1. Background
Olist is a Brazilian marketplace that connects small sellers to large online stores. The public dataset covers
about 100K orders from 2016 to 2018, with customers, sellers, products, payments, delivery timestamps and
customer reviews.

## 2. Problem statement
Olist relies on customers coming back, but the business does not know:
- how many customers buy a second time, and how quickly each monthly group of new customers stops buying;
- whether late deliveries are hurting customer satisfaction (review scores), and how much;
- which sellers, product categories and customer states cause most of the delivery delays;
- which customers marketing should target to win repeat purchases;
- how dependent revenue is on a small number of categories and states.

Without these answers, money spent on marketing and logistics improvements cannot be prioritised.

## 3. Business objectives
| # | Objective | Business question |
|---|---|---|
| BO-1 | Measure repeat-purchase rate and monthly cohort retention | Q1 |
| BO-2 | Measure the effect of late delivery on review score, with a statistical test | Q2 |
| BO-3 | Identify the sellers, categories and states that cause the most delivery delays | Q3 |
| BO-4 | Segment customers (RFM) and recommend which segments marketing should target | Q4 |
| BO-5 | Measure how concentrated revenue is across categories and states (Pareto) | Q5 |

## 4. Stakeholders and what each one needs
| Stakeholder | Role in project | What they need from it | Decisions it supports |
|---|---|---|---|
| **Head of Customer Experience** | Project sponsor; owns satisfaction KPIs | Proof of whether, and how much, late delivery lowers review scores; a top-level dashboard of satisfaction and delivery KPIs | Whether to fund delivery-promise / logistics improvements; which customer-experience issues to fix first |
| **Logistics Manager** | Owns delivery KPIs | On-time and late rates by seller, category and customer state; a ranked list of the worst-performing sellers | Which sellers to put on improvement plans; which routes/states need better carriers or more realistic estimated dates |
| **Marketing Manager** | Owns revenue and retention KPIs | Repeat-customer %, cohort retention curve, RFM segments with size and value, revenue concentration | Which segments to target with re-engagement campaigns; where to focus category/state marketing budget |

## 5. Scope
### In scope
- The 9 CSV files of the Kaggle dataset `olistbr/brazilian-ecommerce`, loaded into MySQL 8 (database `olist`).
- Data-quality checks and documented cleaning rules (Phase 2).
- SQL analysis: cohort retention, delivery-delay buckets vs review score, seller late-rate ranking, Pareto, month-over-month trend.
- Python: RFM segmentation, Mann-Whitney U hypothesis test (late vs on-time review scores), seller-to-customer distance vs delay.
- Excel seller scorecard and a Power BI dashboard (4 pages) built on SQL views.
- BA deliverables: this BRD, KPI dictionary, user stories, process map, UAT checklist, insight memo.

### Out of scope
- Real-time or automated data pipelines (the dataset is a static historical snapshot).
- Predictive / machine-learning models (e.g. churn prediction, delivery-time forecasting).
- Text/sentiment analysis of review comments (comments are in Portuguese; only `review_score` is used).
- Profit or margin analysis (no cost data in the dataset).
- Marketing-funnel analysis (the separate Olist marketing-funnel dataset is not used).
- Carrier-level analysis (the dataset has no carrier identifier).
- Running campaigns or changing seller contracts. The project only recommends.

## 6. Assumptions and constraints
| # | Assumption / constraint | To confirm in |
|---|---|---|
| A-1 | `customer_unique_id` identifies a real person; `customer_id` is unique **per order** and must not be used for repeat-customer counts. | Phase 2 DQ |
| A-2 | Revenue = product price (`order_items.price`), **excluding freight**. Reason: price is stored per item, so it can be split by seller and category; `payment_value` is per order and includes freight and instalment interest. | Phase 2 |
| A-3 | Revenue and retention KPIs use orders that were not canceled or unavailable; delivery KPIs use only `order_status = 'delivered'` orders that have a delivered date. Exact status list **[TBD]**. | Phase 2 DQ |
| A-4 | The first and last months of data are sparse/partial and will be excluded from cohort and trend analysis. Cut-off months **[TBD]**. | Phase 2 DQ |
| A-5 | An order is "on time" if delivered on or before the estimated delivery **date** (date-level comparison, time of day ignored). | Phase 2 |
| A-6 | Where an order has more than one review, one review per order will be used (proposed: the most recently answered). Rule **[TBD]**. | Phase 2 DQ |
| A-7 | Results describe Olist in 2016–2018 and are not assumed to hold today. | — |
| C-1 | Tools are limited to free/desktop tools: MySQL 8, Python, Excel, Power BI Desktop, draw.io. | — |

## 7. Data sources
| File (Kaggle `olistbr/brazilian-ecommerce`) | Grain (one row per…) | Used for |
|---|---|---|
| `olist_orders_dataset.csv` | order | Status, purchase date, delivered and estimated delivery dates |
| `olist_order_items_dataset.csv` | item within an order | Price, freight, seller, product |
| `olist_order_payments_dataset.csv` | payment within an order | Payment type and value (reconciliation check) |
| `olist_order_reviews_dataset.csv` | review | Review score |
| `olist_customers_dataset.csv` | customer per order (`customer_id`) | `customer_unique_id`, state, zip prefix |
| `olist_sellers_dataset.csv` | seller | Seller state, zip prefix |
| `olist_products_dataset.csv` | product | Category (Portuguese) |
| `product_category_name_translation.csv` | category | English category name |
| `olist_geolocation_dataset.csv` | zip prefix (many rows each) | Lat/lng for seller-to-customer distance (aggregate first) |

Known file issues spotted while reading headers (to handle in Phase 2): the products file spells two columns
`product_name_lenght` / `product_description_lenght` (sic, typo in source), and the translation CSV begins with a
byte-order mark (BOM) before its first column name.

## 8. Success criteria
The project is successful when:
1. Every KPI in `02_KPI_dictionary.md` is calculated by a SQL query or notebook cell, and its result is saved to `outputs/`.
2. Each business question Q1–Q5 has an answer backed by an output file.
3. The late-vs-on-time review difference has a hypothesis test result (p-value, effect size) and a plain-English conclusion.
4. Every Power BI KPI matches its SQL query result exactly in the UAT checklist (target: **100% pass**).
5. Each user story US-01 to US-06 passes all of its acceptance criteria.
6. The insight memo gives 3 recommendations, each with an estimated impact taken from `outputs/`.
7. Stakeholder targets for the KPIs (e.g. On-Time Delivery % target **[TBD]**) are agreed and recorded.

## 9. Related documents
- `02_KPI_dictionary.md`: KPI definitions and formulas
- `03_user_stories.md`: user stories and acceptance criteria
- `04_process_map_steps.md` / `04_process_map.drawio`: order-to-review process map
- `05_UAT_checklist.md`, `06_insight_memo.md` (Phase 7)
