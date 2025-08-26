import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os

st.markdown("""
<meta property="og:title" content="Customer Feedback Insights — Streamlit App" />
<meta property="og:description" content="A Streamlit app to explore customer feedback with KPIs, trends, segments, and negative insights." />
<meta property="og:url" content="https://rgerjeki-customer-feedback-insights.streamlit.app" />
<meta property="og:image" content="" />
""", unsafe_allow_html=True)

st.set_page_config(page_title="Customer Feedback (Lite)", layout="wide")
st.title("💬 Customer Feedback Insights — Lite")
st.caption("A minimal Streamlit + SQLite app: upload CSV → filter → see KPIs, a trend chart, segments, and pattern-driven negative insights.")

# ---- Sidebar: Data source & filters ----
with st.sidebar:
    st.header("1) Data source")
    src = st.radio("Choose data source", ["Upload CSV", "Use sample dataset"], index=1)
    uploaded = None
    sample_choice = None
    if src == "Upload CSV":
        uploaded = st.file_uploader(
            "CSV with 4 logical fields: date/time, category, numeric rating, free-text comment",
            type=["csv"]
        )
    else:
        sample_choice = st.selectbox(
            "Sample dataset",
            [
                "Widgets Expanded — sample_feedback_expanded_widgets.csv",
            "Mortgage Expanded — sample_feedback_expanded_mortgage.csv",
            "E-commerce Expanded — sample_feedback_expanded_ecommerce.csv",
            "Support Expanded — sample_feedback_expanded_support.csv",
            ],
            index=0,
        )
    st.markdown("---")
    st.header("2) Filters")
    # (actual filter widgets rendered after data load)

# ---- Load data ----
def load_data() -> pd.DataFrame:
    # Load from upload or selected sample file
    if src == "Upload CSV" and uploaded is not None:
        df = pd.read_csv(uploaded)
    else:
        base_path = os.path.join(os.path.dirname(__file__), "data")
        file_map = {
            "Widgets Expanded — sample_feedback_expanded_widgets.csv": os.path.join(base_path, "sample_feedback_expanded_widgets.csv"),
            "Mortgage Expanded — sample_feedback_expanded_mortgage.csv": os.path.join(base_path, "sample_feedback_expanded_mortgage.csv"),
            "E-commerce Expanded — sample_feedback_expanded_ecommerce.csv": os.path.join(base_path, "sample_feedback_expanded_ecommerce.csv"),
            "Support Expanded — sample_feedback_expanded_support.csv": os.path.join(base_path, "sample_feedback_expanded_support.csv"),
        }
        df = pd.read_csv(file_map.get(sample_choice, "sample_feedback_expanded_widgets.csv"))

    # Normalize expected columns (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # ---- Header alias mapping (built-in) ----
    aliases = {
        "created_at": {"created_at", "date", "timestamp", "created", "submitted_at"},
        "product": {"product", "category", "service", "queue", "team"},
        "rating": {"rating", "score", "stars", "satisfaction"},
        "review_text": {"review_text", "comment", "message", "text", "body", "feedback"},
    }
    lower = {c.lower(): c for c in df.columns}
    rename = {}
    for target, candidates in aliases.items():
        if target not in df.columns:
            for cand in candidates:
                if cand in lower:
                    rename[lower[cand]] = target
                    break
    if rename:
        df = df.rename(columns=rename)
    if "product" not in df.columns:
        df["product"] = "Unknown"

    # Parse types
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    # Precompute SQLite-safe date fields
    df["created_at_date"] = df["created_at"].dt.strftime("%Y-%m-%d")                     # YYYY-MM-DD
    df["month"] = df["created_at"].dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-01")  # YYYY-MM-01

    # Drop unusable rows
    df = df.dropna(subset=["created_at", "rating"]).copy()
    return df

df = load_data()
st.success(f"Loaded {len(df)} rows.")

# Prepare filter options
products = sorted(df["product"].astype(str).unique())
date_min_ts = pd.to_datetime(df["created_at"].min())
date_max_ts = pd.to_datetime(df["created_at"].max())
date_min = date_min_ts.date()
date_max = date_max_ts.date()

with st.sidebar:
    sel_products = st.multiselect("Product", products, default=products)
    sel_dates = st.date_input(
        "Date range",
        (date_min, date_max),
        min_value=date_min,
        max_value=date_max
    )

with st.sidebar:
    st.markdown("---")
    st.markdown("### 👨‍💻 About the Author")
    st.markdown(
        "Created by **Reese Gerjekian**  \n"
        "[LinkedIn](https://www.linkedin.com/in/rgerjeki/) · "
        "[GitHub](https://github.com/rgerjeki) · "
        "[Portfolio](https://rgerjeki.github.io)"
    )

# ---- Push data into in-memory SQLite and build WHERE ----
conn = sqlite3.connect(":memory:")
df.to_sql("feedback", conn, index=False, if_exists="replace")

clauses = []
params = []

if sel_products:
    placeholders = ",".join(["?"] * len(sel_products))
    clauses.append(f"product IN ({placeholders})")
    params.extend(sel_products)

if sel_dates:
    start_date, end_date = sel_dates
    # Use the precomputed date-only column for safe SQLite comparisons
    clauses.append("date(created_at_date) BETWEEN date(?) AND date(?)")
    params.extend([str(start_date), str(end_date)])

WHERE = ("WHERE " + " AND ".join(clauses)) if clauses else ""

# ---- KPIs (SQL) ----
kpi_sql = f"""
SELECT
  COUNT(*) AS total_tickets,
  ROUND(AVG(rating), 2) AS avg_rating
FROM feedback
{WHERE};
"""
kpi = pd.read_sql_query(kpi_sql, conn, params=params)
c1, c2 = st.columns(2)
c1.metric("Total Tickets", int(kpi.iloc[0]["total_tickets"]) if not kpi.empty else 0)
c2.metric("Average Rating", float(kpi.iloc[0]["avg_rating"]) if not kpi.empty else 0.0)

with st.expander("Show KPI SQL"):
    st.code(kpi_sql.strip(), language="sql")

# ---- Trend (SQL → Altair) ----
trend_sql = f"""
SELECT month,
       COUNT(*) AS volume,
       ROUND(AVG(rating), 2) AS avg_rating
FROM feedback
{WHERE}
GROUP BY month
ORDER BY month;
"""
trend = pd.read_sql_query(trend_sql, conn, params=params)
st.subheader("Trend")
if trend.empty:
    st.info("No data for the selected filters.")
else:
    trend["month"] = pd.to_datetime(trend["month"], errors="coerce")
    if len(trend) == 1:
        chart = alt.Chart(trend).mark_bar().encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("volume:Q", title="Ticket Volume"),
            tooltip=["month", "volume", "avg_rating"]
        ).properties(height=260)
    else:
        line = alt.Chart(trend).mark_line().encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("volume:Q", title="Ticket Volume"),
            tooltip=["month", "volume", "avg_rating"]
        )
        pts = alt.Chart(trend).mark_point().encode(x="month:T", y="volume:Q")
        chart = (line + pts).properties(height=260)
    st.altair_chart(chart, use_container_width=True)

with st.expander("Show Trend SQL"):
    st.code(trend_sql.strip(), language="sql")

# ---- Segments (SQL table) ----
seg_sql = f"""
SELECT product,
       COUNT(*) AS tickets,
       ROUND(AVG(rating), 2) AS avg_rating
FROM feedback
{WHERE}
GROUP BY product
ORDER BY tickets DESC;
"""
segments = pd.read_sql_query(seg_sql, conn, params=params)
st.subheader("Segments by Product")
st.dataframe(segments, use_container_width=True)
with st.expander("Show Segments SQL"):
    st.code(seg_sql.strip(), language="sql")

# ============================================================
# NEGATIVE INSIGHTS (replaces "Top 5 Lowest-Rated Comments")
# ============================================================
st.markdown("---")
st.header("⚠️ Negative Insights")

# Controls for negative insights
ni_col1, ni_col2, ni_col3 = st.columns([1, 1, 2])
with ni_col1:
    neg_threshold = st.slider("Show ratings ≤", 1, 5, 3, help="Comments with rating at or below this are considered 'negative'.")
with ni_col2:
    sort_mode = st.selectbox("Sort comments by", ["Most recent", "Lowest rating", "Longest comment", "Highest rating"], index=0)
with ni_col3:
    keyword_filter = st.text_input("Keyword filter (optional)", "", help="Filter comments containing this text (case-insensitive).")

# Build a dataframe-level mask aligned with sidebar filters
mask = pd.Series(True, index=df.index)
if sel_products:
    mask &= df["product"].isin(sel_products)
if sel_dates:
    start_ts = pd.to_datetime(sel_dates[0])
    end_ts = pd.to_datetime(sel_dates[1])
    mask &= df["created_at"].between(start_ts, end_ts)

# Apply negative rating and keyword filters
mask &= df["rating"] <= neg_threshold
if keyword_filter.strip():
    mask &= df["review_text"].astype(str).str.contains(keyword_filter.strip(), case=False, na=False)

neg_df = df.loc[mask, ["created_at", "product", "rating", "review_text"]].copy()

# Sorting modes
if sort_mode == "Most recent":
    neg_df = neg_df.sort_values("created_at", ascending=False)
elif sort_mode == "Lowest rating":
    neg_df = neg_df.sort_values(["rating", "created_at"], ascending=[True, True])
elif sort_mode == "Longest comment":
    neg_df["__len"] = neg_df["review_text"].astype(str).str.len()
    neg_df = neg_df.sort_values(["__len", "created_at"], ascending=[False, False]).drop(columns="__len")
elif sort_mode == "Highest rating":
    neg_df = neg_df.sort_values(["rating", "created_at"], ascending=[False, False])

# 1) Comment Browser (full, filterable)
st.subheader("All Negative Comments (filtered)")
if neg_df.empty:
    st.info("No negative comments for the selected filters.")
else:
    # Friendlier date display
    neg_df_display = neg_df.copy()
    neg_df_display["created_at"] = pd.to_datetime(neg_df_display["created_at"]).dt.date
    st.dataframe(neg_df_display, use_container_width=True, height=320)

# 2) Keyword Frequency from negative comments
st.subheader("Keyword Frequency (from negative comments)")
if neg_df.empty:
    st.info("No data to extract keywords from.")
else:
    import re
    from collections import Counter

    STOP = set("""
    a an the and or but if then this that to of in on for from with by as is are was were be been being
    i you he she it we they my your our their me us them not no yes very more most less least so too
    it's i'm i've you're we'll can't won't didn't don't does do did could would should
    """.split())

    def tokenize(s: str):
        tokens = re.findall(r"[A-Za-z']+", str(s).lower())
        return [w for w in tokens if len(w) > 2 and w not in STOP]

    all_words = []
    token_lists = []
    for txt in neg_df["review_text"].astype(str):
        toks = tokenize(txt)
        token_lists.append(toks)
        all_words.extend(toks)

    if all_words:
        from collections import defaultdict
        top = Counter(all_words).most_common(15)
        kw_freq = pd.DataFrame(top, columns=["keyword", "mentions"])

        # Average rating by keyword (compute over tokenized rows)
        rows = []
        for toks, rating in zip(token_lists, neg_df["rating"].tolist()):
            for t in set(toks):  # set() so repeated words in the same comment count once for avg calc
                rows.append((t, rating))
        if rows:
            kw_df = pd.DataFrame(rows, columns=["keyword", "rating"])
            kw_stats = (
                kw_df.groupby("keyword")["rating"]
                .agg(avg_rating="mean", count="size")
                .reset_index()
            )
            # Merge with frequency to align ordering
            kw_summary = pd.merge(kw_freq, kw_stats, on="keyword", how="left")
            kw_summary = kw_summary.sort_values(["mentions", "avg_rating"], ascending=[False, True])
        else:
            kw_summary = kw_freq.copy()
            kw_summary["avg_rating"] = float("nan")

        # Show bar chart for frequency
        chart = alt.Chart(kw_freq).mark_bar().encode(
            x=alt.X("keyword:N", sort="-y", title="Keyword"),
            y=alt.Y("mentions:Q", title="Mentions"),
            tooltip=["keyword", "mentions"]
        ).properties(height=240)
        st.altair_chart(chart, use_container_width=True)

        # Show combined table with avg rating
        st.caption("Keywords ranked by frequency; lower avg rating indicates topics most associated with pain.")
        st.dataframe(kw_summary, use_container_width=True)
    else:
        st.info("No meaningful keywords extracted.")

# 3) Export the currently filtered negative slice (safety: enforce threshold again)
st.subheader("Export Negative Slice")

neg_export = neg_df.copy()
neg_export["rating"] = pd.to_numeric(neg_export["rating"], errors="coerce")

# Re-enforce the negative threshold to be extra safe
neg_export = neg_export[neg_export["rating"] <= neg_threshold]

if neg_export.empty:
    st.info("No negative comments to export for the selected filters.")
else:
    neg_csv = neg_export.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download negative comments (CSV)",
        data=neg_csv,
        file_name=f"negative_comments_le_{neg_threshold}.csv",
        mime="text/csv",
    )

# Optional: export the full filtered slice (cleaned)
st.caption("Need everything for offline analysis?")

full_slice = df.copy()

# Apply sidebar filters
if sel_products:
    full_slice = full_slice[full_slice["product"].isin(sel_products)]
if sel_dates:
    start_ts = pd.to_datetime(sel_dates[0]); end_ts = pd.to_datetime(sel_dates[1])
    full_slice = full_slice[full_slice["created_at"].between(start_ts, end_ts)]

# Clean columns:
# - Keep created_at as date (not duplicate created_at_date)
# - Convert 'month' to month name (e.g., "Jan 2025")
export_df = full_slice.copy()
export_df["created_at"] = pd.to_datetime(export_df["created_at"]).dt.date
export_df["month"] = pd.to_datetime(export_df["month"], errors="coerce").dt.strftime("%b %Y")

# Drop helper columns that aren't useful outside the app
export_df = export_df.drop(columns=["created_at_date"], errors="ignore")

full_csv = export_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download FULL filtered dataset (CSV)",
    data=full_csv,
    file_name="full_filtered_feedback.csv",
    mime="text/csv",
)