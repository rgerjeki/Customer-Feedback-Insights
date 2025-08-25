# Customer Feedback Insights — Lite (Streamlit + SQLite)

A minimal, interview-friendly app that demonstrates **Customer Obsession** while staying lightweight and transparent.  
Upload a CSV → filter → see **KPIs**, a **trend line**, **segments by product**, and **negative insights** (comment browser, keyword hotspots, and export).  
All aggregations are done with **SQL** against an in-memory **SQLite** table.

---

## Why this matters (Customer Obsession)
- Surfaces customer pain quickly via a **Negative Insights** panel  
  - Browse all negative comments (filter & search)  
  - See **keyword hotspots** and average ratings tied to themes  
  - Export filtered slices for deeper analysis  
- Shows **where** issues occur (segments) and **when** they spike (trend)  
- Queries are transparent and auditable (SQL shown in the UI)

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

---

## What’s Included

- `app.py` — the Streamlit app (~150 lines, easy to read)  
- `requirements.txt` — minimal dependencies  
- **Sample datasets** (see below)

---

## How to Use

1. **Choose your data source** (sidebar)  
   - **Upload CSV**: supply your own file  
   - **Use sample dataset**: pick from multiple realistic examples
2. **Filter**  
   - Select **Products** and a **Date range**
3. **Explore**  
   - **KPIs**: ticket count + average rating  
   - **Trend**: ticket volume over time (bar if 1 month, line+points if multiple months)  
   - **Segments**: performance by product  
   - **Top Negative Comments**: quick scan of pain points  

---

## Input Data (Flexible Schema)

The app expects **four logical fields** (names can vary):

- `created_at` — date/time  
- `product` — category to segment by  
- `rating` — numeric score  
- `review_text` — free-text comment  

### Header Aliases (built-in)
`app.py` auto-maps common alternatives, e.g.:

- `created_at`: `date`, `timestamp`, `submitted_at`  
- `product`: `category`, `service`, `queue`, `team`  
- `rating`: `score`, `stars`, `satisfaction`  
- `review_text`: `comment`, `message`, `body`, `feedback`  

If `product` is missing, it falls back to `"Unknown"` so the app still runs.  
**Date format:** keep it Pandas-parseable (e.g., `YYYY-MM-DD`).

---

## SQL Under the Hood

All metrics are computed with **SQLite** queries (shown in expanders).

- **KPIs**
  ```sql
  SELECT COUNT(*) AS total_tickets, ROUND(AVG(rating), 2) AS avg_rating
  FROM feedback
  -- WHERE added dynamically
  ;
  ```

- **Trend**
  ```sql
  SELECT month, COUNT(*) AS volume, ROUND(AVG(rating), 2) AS avg_rating
  FROM feedback
  -- WHERE on product/date(created_at_date)
  GROUP BY month
  ORDER BY month;
  ```

- **Segments**
  ```sql
  SELECT product, COUNT(*) AS tickets, ROUND(AVG(rating), 2) AS avg_rating
  FROM feedback
  -- WHERE added dynamically
  GROUP BY product
  ORDER BY tickets DESC;
  ```

---

## Included Sample Datasets

Use the sidebar's **Sample dataset** selector to switch between these instantly:

- **Widgets Expanded** — `sample_feedback_expanded_widgets.csv`  
  - Products: *Widget A/B/C*  
  - 150 rows spanning 2025 with mixed review lengths and ratings

- **Mortgage Expanded** — `sample_feedback_expanded_mortgage.csv`  
  - Products: *Loan Portal*, *Doc Uploader*, *Rate Tracker*, *Closing Scheduler*  
  - 150 rows, including empty reviews, long complaints, and alias-style headers

- **E-commerce Expanded** — `sample_feedback_expanded_ecommerce.csv`  
  - Products: *Storefront*, *Inventory API*, *Recommender*  
  - 150 rows with realistic shopping feedback (checkout, inventory, recommendations)

- **Support Expanded** — `sample_feedback_expanded_support.csv`  
  - Queues: *Identity*, *Billing*, *Shipping*, *Returns*  
  - 150 rows capturing tickets with varying severity and comment length

These demonstrate cross‑domain usage and header‑alias handling without code changes.
