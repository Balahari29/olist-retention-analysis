# User Stories
**Project:** Olist Customer Retention & Delivery Experience Analysis
**Version:** 0.1 (draft, Phase 1) | **Date:** 2026-11-02

> Format: *As a [stakeholder], I want [capability], so that [business value].* Each acceptance criterion (AC) is
> written to be tested pass/fail in the Phase 7 UAT checklist. KPI names follow `02_KPI_dictionary.md`.

---

### US-01: Repeat customers and cohort retention
**Business question:** Q1 | **Stakeholder:** Marketing Manager | **Priority:** Must have

*As a* Marketing Manager, *I want* to see the Repeat Customer % and a monthly cohort retention table, *so that* I
know how many new customers come back and how fast each cohort drops off.

- **AC-1:** Repeat Customer % is counted on `customer_unique_id`, and the dashboard value matches the SQL query result saved in `outputs/`.
- **AC-2:** The cohort table shows one row per first-purchase month (inside the agreed analysis window) and Cohort Retention % for months 1 to [TBD] after first purchase.
- **AC-3:** Each cohort row shows its cohort size (number of new customers), so small cohorts can be identified.

### US-02: Late delivery vs review score
**Business question:** Q2 | **Stakeholder:** Head of Customer Experience | **Priority:** Must have

*As the* Head of Customer Experience, *I want* to compare review scores of late and on-time orders, with a
statistical test, *so that* I can prove whether late delivery lowers satisfaction before funding logistics fixes.

- **AC-1:** A chart shows Avg Review Score and order count for each delay bucket (Early, On time, 1–3, 4–7, 7+ days late).
- **AC-2:** A Mann-Whitney U test of late vs on-time review scores reports the p-value, an effect size and a one-sentence plain-English conclusion, saved to `outputs/`.
- **AC-3:** Only delivered orders with a review are included, and the number of orders excluded is reported.

### US-03: Seller delivery performance ranking
**Business question:** Q3 | **Stakeholder:** Logistics Manager | **Priority:** Must have

*As a* Logistics Manager, *I want* a ranked list of sellers by Late Order %, *so that* I can put the worst
performers on an improvement plan.

- **AC-1:** Only sellers with at least [TBD] delivered orders are ranked, so sellers with very few orders do not top the list by chance.
- **AC-2:** Sellers are split into performance groups with `NTILE`, and the worst group can be filtered on its own.
- **AC-3:** Selecting a seller (drill-through) shows that seller's order count, Late Order %, Avg Delivery Delay and Avg Review Score.

### US-04: Delays by category and customer state
**Business question:** Q3 | **Stakeholder:** Logistics Manager | **Priority:** Should have

*As a* Logistics Manager, *I want* to see Late Order % and Avg Delivery Delay by product category and customer
state, *so that* I can find the routes and product types where estimated dates are unrealistic.

- **AC-1:** Categories are shown in English, using the translation table; any category with no translation is shown as "Unknown" and counted.
- **AC-2:** Late Order % and Avg Delivery Delay per category and per state match the SQL query results in `outputs/`.
- **AC-3:** A map or bar chart ranks customer states by Late Order %, with the order count shown for each state.

### US-05: RFM customer segments
**Business question:** Q4 | **Stakeholder:** Marketing Manager | **Priority:** Must have

*As a* Marketing Manager, *I want* customers grouped into named RFM segments (e.g. Champions, At Risk,
Hibernating), *so that* I can choose which segments to target with re-engagement campaigns.

- **AC-1:** Every customer (`customer_unique_id`) with a valid order has exactly one segment; the segment counts add up to the total customer count.
- **AC-2:** For each segment the dashboard shows customer count, % of customers, total revenue and average recency.
- **AC-3:** The RFM scoring rules (quantile bins and segment mapping) are documented in the notebook and README.

### US-06: Revenue concentration (Pareto)
**Business question:** Q5 | **Stakeholder:** Marketing Manager | **Priority:** Should have

*As a* Marketing Manager, *I want* a Pareto view of revenue by product category and by customer state, *so that*
I know how dependent Olist is on a few categories and states and where to focus budget.

- **AC-1:** Categories and states are sorted by Total Revenue, highest first, with a cumulative revenue % line.
- **AC-2:** The number of categories (and states) that make up 80% of revenue is shown, and matches the SQL result in `outputs/`.
- **AC-3:** The sum of revenue across all categories equals Total Revenue (no rows lost when products are joined to categories).

---

## Traceability: questions → stories → stakeholders
| Business question | User story | Stakeholder |
|---|---|---|
| Q1 Repeat purchase & cohort retention | US-01 | Marketing Manager |
| Q2 Late delivery vs review score | US-02 | Head of Customer Experience |
| Q3 Sources of delivery delay | US-03, US-04 | Logistics Manager |
| Q4 RFM segments to target | US-05 | Marketing Manager |
| Q5 Revenue concentration | US-06 | Marketing Manager |
