"""Pharma Sales Intelligence — Streamlit portfolio dashboard.

The dashboard reads checked-in synthetic summary snapshots in app_data/.
It does not connect to, or expose credentials for, the local PostgreSQL server.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Pharma Sales Intelligence | 2025",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "app_data"
NAVY = "#162C47"
TEAL = "#138A90"
BLUE = "#2989C8"

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 3rem;}
      div[data-testid="stMetric"] {background: #F4F7FA; border: 1px solid #E3EAF1;
        border-radius: 12px; padding: 14px 18px;}
      div[data-testid="stMetricLabel"] {color: #435468;}
      h1, h2, h3 {letter-spacing: -.02em;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_snapshots():
    filenames = {
        "monthly": "monthly_growth.csv",
        "products": "product_performance.csv",
        "sales": "sales_by_territory.csv",
        "targets": "territory_target_attainment.csv",
    }
    missing = [file for file in filenames.values() if not (DATA_DIR / file).is_file()]
    if missing:
        raise FileNotFoundError("Missing app_data files: " + ", ".join(missing))
    tables = {key: pd.read_csv(DATA_DIR / filename) for key, filename in filenames.items()}

    required = {
        "monthly": {"month", "revenue"},
        "products": {"brand", "therapeutic_category", "total_revenue", "units_sold"},
        "sales": {"region", "city", "total_revenue", "transactions"},
        "targets": {"month", "region", "city", "actual_revenue", "target_revenue"},
    }
    for key, cols in required.items():
        missing_cols = cols - set(tables[key].columns)
        if missing_cols:
            raise ValueError(f"{filenames[key]} is missing columns: {', '.join(sorted(missing_cols))}")
    return tables


try:
    data = load_snapshots()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"The Streamlit app can't load its synthetic data: {exc}")
    st.info("Copy the four analytical CSV files into app_data/ and commit them to GitHub.")
    st.stop()

monthly = data["monthly"].copy()
products = data["products"].copy()
sales = data["sales"].copy()
targets = data["targets"].copy()

for df, col in (
    (monthly, "revenue"),
    (products, "total_revenue"),
    (products, "units_sold"),
    (sales, "total_revenue"),
    (sales, "transactions"),
    (targets, "actual_revenue"),
    (targets, "target_revenue"),
):
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# Monthly target data is pre-aggregated by city and month. Do not sum its
# percentage column: recompute annual attainment from annual actual/target totals.
territories = (
    targets.groupby(["region", "city"], as_index=False)[["actual_revenue", "target_revenue"]]
    .sum()
    .merge(
        sales[["region", "city", "transactions"]],
        on=["region", "city"],
        how="left",
        validate="one_to_one",
    )
)
territories["transactions"] = territories["transactions"].fillna(0).astype(int)
territories["attainment_pct"] = (
    100 * territories["actual_revenue"] / territories["target_revenue"].where(territories["target_revenue"].ne(0))
)
territories["variance_inr"] = territories["actual_revenue"] - territories["target_revenue"]
territories["shortfall_inr"] = (-territories["variance_inr"]).clip(lower=0)
territories["performance_status"] = territories["variance_inr"].apply(
    lambda amount: "Target Achieved" if amount >= 0 else "Below Target"
)

revenue = float(sales["total_revenue"].sum())
target = float(territories["target_revenue"].sum())
transactions = int(sales["transactions"].sum())
attainment = 100 * revenue / target if target else 0.0


def crore(value):
    return f"₹{value / 10_000_000:,.2f} Cr"


def million(value):
    return f"₹{value / 1_000_000:,.2f} M"


def title_line(title, description):
    st.title(title)
    st.caption(description)


def bar_chart(frame, label, metric, ytitle, *, height=300, sort="-x", color=BLUE):
    chart = (
        alt.Chart(frame)
        .mark_bar(color=color, cornerRadiusEnd=4)
        .encode(
            x=alt.X(f"{metric}:Q", title=ytitle),
            y=alt.Y(f"{label}:N", sort=sort, title=None),
            tooltip=[alt.Tooltip(f"{label}:N", title=label.replace("_", " ").title()),
                     alt.Tooltip(f"{metric}:Q", format=",.2f", title=ytitle)],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


st.sidebar.title("Pharma Sales Intelligence")
st.sidebar.caption("Portfolio dashboard | 2025")
page = st.sidebar.radio(
    "Report page",
    ["Executive Overview", "Territory Performance", "Product Performance"],
)
st.sidebar.divider()
st.sidebar.info("**Synthetic data only.** This is an independent portfolio project, not actual pharma sales data or client work.")

if abs(revenue - float(products["total_revenue"].sum())) > 1 or abs(revenue - float(monthly["revenue"].sum())) > 1:
    st.warning("Revenue totals disagree across CSV summaries. Regenerate and re-copy the snapshots.")

if page == "Executive Overview":
    title_line("Executive Sales Overview", "2025 | National pharmaceutical commercial performance")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total sales revenue", crore(revenue))
    k2.metric("Sales transactions", f"{transactions:,}")
    k3.metric("Target achievement", f"{attainment:.2f}%")

    st.subheader("Monthly revenue trend")
    monthly["date"] = pd.to_datetime(monthly["month"].astype(str) + "-01", errors="coerce")
    monthly["revenue_mn"] = monthly["revenue"] / 1_000_000
    monthly = monthly.sort_values("date")
    timeline = (
        alt.Chart(monthly)
        .mark_line(point=True, strokeWidth=3, color=TEAL)
        .encode(
            x=alt.X("date:T", axis=alt.Axis(format="%b", labelAngle=0), title=None),
            y=alt.Y("revenue_mn:Q", title="Revenue (₹ million)", scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("month:N", title="Month"),
                     alt.Tooltip("revenue:Q", title="Revenue (₹)", format=",.2f")],
        )
        .properties(height=320)
    )
    st.altair_chart(timeline, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Revenue by region")
        region_rev = sales.groupby("region", as_index=False)["total_revenue"].sum()
        region_rev["revenue_mn"] = region_rev["total_revenue"] / 1_000_000
        chart = (
            alt.Chart(region_rev).mark_bar(color=BLUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("region:N", sort="-y", title=None),
                y=alt.Y("revenue_mn:Q", title="Revenue (₹ million)"),
                tooltip=["region:N", alt.Tooltip("total_revenue:Q", title="Revenue (₹)", format=",.2f")],
            ).properties(height=290)
        )
        st.altair_chart(chart, use_container_width=True)
    with c2:
        st.subheader("Top 5 cities by revenue")
        top_cities = sales.nlargest(5, "total_revenue").copy()
        top_cities["revenue_mn"] = top_cities["total_revenue"] / 1_000_000
        bar_chart(top_cities, "city", "revenue_mn", "Revenue (₹ million)", height=290)

elif page == "Territory Performance":
    title_line("Territory Performance", "2025 | Target achievement and revenue gaps")
    chosen_region = st.sidebar.selectbox("Filter region", ["All regions"] + sorted(territories["region"].unique().tolist()))
    t = territories if chosen_region == "All regions" else territories[territories["region"] == chosen_region]
    achieved = int((t["performance_status"] == "Target Achieved").sum())
    below = int((t["performance_status"] == "Below Target").sum())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Territories", f"{len(t):,}")
    k2.metric("Target achieved", f"{achieved:,}")
    k3.metric("Below target", f"{below:,}")
    k4.metric("Target attainment", f"{100 * t['actual_revenue'].sum() / t['target_revenue'].sum():.2f}%" if t["target_revenue"].sum() else "N/A")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Bottom 5 by target attainment")
        bottom = t.nsmallest(5, "attainment_pct").copy()
        bar_chart(bottom, "city", "attainment_pct", "Target achievement (%)", height=300, sort="x", color=TEAL)
    with c2:
        st.subheader("Top 5 revenue shortfalls")
        top_gap = t.nlargest(5, "shortfall_inr").copy()
        top_gap["shortfall_lakh"] = top_gap["shortfall_inr"] / 100_000
        bar_chart(top_gap, "city", "shortfall_lakh", "Shortfall (₹ lakh)", height=300)

    st.subheader("Target attainment by region")
    region_perf = t.groupby("region", as_index=False)[["actual_revenue", "target_revenue"]].sum()
    region_perf["attainment_pct"] = 100 * region_perf["actual_revenue"] / region_perf["target_revenue"]
    regional_chart = (
        alt.Chart(region_perf).mark_bar(color=BLUE, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("region:N", title=None, sort="-y"),
            y=alt.Y("attainment_pct:Q", title="Target achievement (%)"),
            tooltip=[alt.Tooltip("region:N", title="Region"),
                     alt.Tooltip("attainment_pct:Q", title="Achievement (%)", format=".2f")],
        ).properties(height=280)
    )
    st.altair_chart(regional_chart, use_container_width=True)

    st.subheader("Territory details")
    shown = t.sort_values("attainment_pct")[["region", "city", "transactions", "actual_revenue", "target_revenue", "attainment_pct", "shortfall_inr", "performance_status"]]
    st.dataframe(shown, hide_index=True, use_container_width=True)
    st.download_button("Download territory report (CSV)", shown.to_csv(index=False).encode("utf-8"), "territory_report_2025.csv", "text/csv")

else:
    title_line("Product Performance", "2025 | Brand and therapeutic-category sales analytics")
    chosen_category = st.sidebar.selectbox("Filter therapeutic category", ["All categories"] + sorted(products["therapeutic_category"].unique().tolist()))
    p = products if chosen_category == "All categories" else products[products["therapeutic_category"] == chosen_category]
    k1, k2, k3 = st.columns(3)
    k1.metric("Pharmaceutical brands", f"{p['brand'].nunique():,}")
    k2.metric("Product revenue", crore(p["total_revenue"].sum()))
    k3.metric("Units sold", f"{int(p['units_sold'].sum()):,}")

    st.subheader("Revenue by pharmaceutical brand")
    by_brand = p.sort_values("total_revenue", ascending=False).copy()
    by_brand["revenue_mn"] = by_brand["total_revenue"] / 1_000_000
    bar_chart(by_brand, "brand", "revenue_mn", "Revenue (₹ million)", height=340)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Revenue by therapeutic category")
        categories = p.groupby("therapeutic_category", as_index=False)["total_revenue"].sum()
        categories["revenue_mn"] = categories["total_revenue"] / 1_000_000
        bar_chart(categories, "therapeutic_category", "revenue_mn", "Revenue (₹ million)", height=290)
    with c2:
        st.subheader("Units sold by brand")
        bar_chart(p, "brand", "units_sold", "Units sold", height=290)

    st.subheader("Product details")
    st.dataframe(p.sort_values("total_revenue", ascending=False), hide_index=True, use_container_width=True)
    st.download_button("Download product report (CSV)", p.to_csv(index=False).encode("utf-8"), "product_report_2025.csv", "text/csv")

st.divider()
st.caption("© Pharma Sales Intelligence — synthetic educational data. Figures are not real pharmaceutical market results. Website uses committed CSV snapshots; it does not connect to your local PostgreSQL database.")
