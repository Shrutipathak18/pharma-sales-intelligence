    k3.metric("Target achievement", f"{attainment:.2f}%")

    st.subheader("Monthly revenue trend")
    monthly["date"] = pd.to_datetime(monthly["month"].astype(str) + "-01", errors="coerce")
    monthly["revenue_mn"] = monthly["revenue"] / 1_000_000
    monthly = monthly.sort_values("date")
    # Use discrete month labels to avoid repeated labels on a continuous date axis.
    monthly["month_label"] = monthly["date"].dt.strftime("%b")
    timeline = (
        alt.Chart(monthly)
        .mark_line(point=True, strokeWidth=3, color=TEAL)
        .encode(
            x=alt.X(
                "month_label:N",
                sort=monthly["month_label"].tolist(),
                axis=alt.Axis(labelAngle=0),
                title=None,
            ),
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
