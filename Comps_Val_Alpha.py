import streamlit as st
import pandas as pd
import numpy as np
import requests
import time

# --- API Key (hardcoded) ---
api_key = "NTAFR2HOV4CJFTJK"

if not api_key:
    st.info("Please enter your Alpha Vantage API key to run the analysis.")
    st.stop()

# --- App ---
st.set_page_config(page_title="Comps Valuation - Alpha Vantage", layout="wide")
st.title("Comparable Company Valuation")
st.caption("Using Alpha Vantage • Free tier")

# Target Company Input
st.subheader("Target Company (Manual Input)")
col1, col2, col3, col4 = st.columns(4)
with col1:
    target_name = st.text_input("Company Name", "Target Inc.")
with col2:
    target_revenue = st.number_input("Revenue $M", value=500.0, step=100.0)
with col3:
    target_ebitda = st.number_input("EBITDA $M", value=120.0, step=50.0)
with col4:
    target_net_profit = st.number_input("Net Profit $M", value=80.0, step=50.0)

# Additional inputs
col5, col6 = st.columns(2)
with col5:
    net_debt = st.number_input("Net Debt $M", value=0.0, step=50.0, help="Positive = net debt, Negative = net cash")
with col6:
    illiquidity_discount = st.slider("Illiquidity Discount %", 0.0, 70.0, 30.0, 5.0) / 100

# Peer Tickers
tickers_input = st.text_input(
    "Comparable companies (comma or space separated)",
    "CF, NTR, YAR.OL, MOS, UAN, LXU"
)

if st.button("Run Comps Analysis (Alpha Vantage)", type="primary"):
    tickers = [t.strip().upper() for t in tickers_input.replace(",", " ").split() if t.strip()]
    results = []
    descriptions = {}
    progress = st.progress(0)

    for idx, ticker in enumerate(tickers):
        progress.progress((idx + 1) / len(tickers))
        try:
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
            data = requests.get(url).json()

            if not data or "Symbol" not in data:
                results.append({
                    "Ticker": ticker, "Company": "No data", "Revenue $M": "-", "EV/Revenue": "-", 
                    "EBITDA $M": "-", "EV/EBITDA": "-", "Net Profit $M": "-", "P/E": "-"
                })
                descriptions[ticker] = "No description available."
                time.sleep(12)
                continue

            name = data.get("Name", ticker)[:40]

            ev_rev    = float(data.get("EVToRevenue") or 0) or None
            ev_ebitda = float(data.get("EVToEBITDA") or 0) or None
            pe        = float(data.get("PERatio") or 0) or None

            revenue    = float(data.get("RevenueTTM") or 0) / 1e6
            ebitda     = float(data.get("EBITDA") or 0) / 1e6
            net_profit = float(data.get("NetIncomeTTM") or 0) / 1e6

            full_desc = data.get("Description", "No description available.")
            short_desc = ". ".join(full_desc.split(". ")[:2])
            if not short_desc.endswith("."): short_desc += "."
            descriptions[ticker] = short_desc

            results.append({
                "Ticker": ticker,
                "Company": name,
                "Revenue $M": f"{revenue:,.0f}" if revenue else "-",
                "EV/Revenue": f"{ev_rev:.2f}x" if ev_rev else "-",
                "EBITDA $M": f"{ebitda:,.0f}" if ebitda else "-",
                "EV/EBITDA": f"{ev_ebitda:.2f}x" if ev_ebitda else "-",
                "Net Profit $M": f"{net_profit:,.0f}" if net_profit else "-",
                "P/E": f"{pe:.1f}x" if pe else "-",
            })
        except:
            results.append({
                "Ticker": ticker, "Company": "Error", "Revenue $M": "-", "EV/Revenue": "-", 
                "EBITDA $M": "-", "EV/EBITDA": "-", "Net Profit $M": "-", "P/E": "-"
            })
            descriptions[ticker] = "No description available."
        time.sleep(12)

    df = pd.DataFrame(results)

    # Medians
    med_rev    = pd.to_numeric(df["EV/Revenue"].str.replace('x',''), errors='coerce').dropna().median()
    med_ebitda = pd.to_numeric(df["EV/EBITDA"].str.replace('x',''), errors='coerce').dropna().median()
    med_pe     = pd.to_numeric(df["P/E"].str.replace('x',''), errors='coerce').dropna().median()

    # Calculations
    ev_rev_val    = target_revenue * med_rev    if pd.notna(med_rev) else None
    ev_ebitda_val = target_ebitda * med_ebitda  if pd.notna(med_ebitda) and target_ebitda > 0 else None
    equity_pe_val = target_net_profit * med_pe  if pd.notna(med_pe) and target_net_profit > 0 else None

    equity_rev     = ev_rev_val - net_debt    if ev_rev_val is not None else None
    equity_ebitda  = ev_ebitda_val - net_debt if ev_ebitda_val is not None else None
    equity_pe      = equity_pe_val

    fair_rev     = equity_rev * (1 - illiquidity_discount)     if equity_rev is not None else None
    fair_ebitda  = equity_ebitda * (1 - illiquidity_discount)  if equity_ebitda is not None else None
    fair_pe      = equity_pe * (1 - illiquidity_discount)      if equity_pe is not None else None

    fair_values = [v for v in [fair_rev, fair_ebitda, fair_pe] if v is not None]
    final_fair_value = sum(fair_values) / len(fair_values) if fair_values else None

    def fmt(val): return f"${val:,.0f}M" if val is not None else "-"

    median_row = {"Ticker": "MEDIAN", "Company": "", "Revenue $M": "", "EV/Revenue": f"{med_rev:.2f}x", "EBITDA $M": "", "EV/EBITDA": f"{med_ebitda:.2f}x", "Net Profit $M": "", "P/E": f"{med_pe:.1f}x"}
    target_row = {"Ticker": "Target EV", "Company": target_name, "Revenue $M": f"{target_revenue:,.0f}", "EV/Revenue": f"{med_rev:.2f}x → {fmt(ev_rev_val)}", "EBITDA $M": f"{target_ebitda:,.0f}", "EV/EBITDA": f"{med_ebitda:.2f}x → {fmt(ev_ebitda_val)}", "Net Profit $M": f"{target_net_profit:,.0f}", "P/E": f"{med_pe:.1f}x → {fmt(equity_pe_val)}"}
    equity_row = {"Ticker": "Equity Value", "Company": "(EV − Net Debt)", "Revenue $M": "", "EV/Revenue": fmt(equity_rev), "EBITDA $M": "", "EV/EBITDA": fmt(equity_ebitda), "Net Profit $M": "", "P/E": fmt(equity_pe)}
    fair_row   = {"Ticker": "Fair Equity Value", "Company": f"(-{illiquidity_discount*100:.0f}% Illiquidity)", "Revenue $M": "", "EV/Revenue": fmt(fair_rev), "EBITDA $M": "", "EV/EBITDA": fmt(fair_ebitda), "Net Profit $M": "", "P/E": fmt(fair_pe)}

    final_df = pd.concat([df, pd.DataFrame([median_row, target_row, equity_row, fair_row])], ignore_index=True)
    st.dataframe(final_df, use_container_width=True, hide_index=True)

    # FINAL FAIR EQUITY VALUE
    st.markdown("---")
    if final_fair_value:
        st.markdown(
            f"""
            <div style="background-color:#37474f; color:#eceff1; padding:14px; border-radius:8px; margin:20px 0;">
                <p style="margin:0; font-size:1.05em; font-weight:600;">
                    Final fair equity value: <strong style="font-size:1.35em;">{fmt(final_fair_value)}</strong>
                </p>
                <p style="margin:4px 0 0; font-size:0.9em; opacity:0.9;">
                    Simple average of {len(fair_values)} method{'s' if len(fair_values)!=1 else ''} after net debt and {illiquidity_discount*100:.0f}% illiquidity discount
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.info("Not enough data to calculate final fair equity value.")

    csv = final_df.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "comps_alpha_vantage.csv", "text/csv")

    st.markdown("---")
    st.subheader("Company Descriptions")
    for ticker in tickers:
        st.markdown(f"**{ticker}** – {descriptions.get(ticker, 'No description available.')}")
