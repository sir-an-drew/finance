import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time

st.set_page_config(page_title="Auto-Peer Valuation", layout="wide")
st.title("Auto-Peer Valuation from Ticker")
st.caption("Yahoo Finance • Automatically finds peers in same sector")

# Input ticker
ticker_input = st.text_input("Enter Ticker Symbol", "MOS").upper()

# Target inputs
st.subheader("Target Company (Manual Input)")
c1, c2, c3, c4 = st.columns(4)
with c1: target_name = st.text_input("Company Name", "Target Inc.")
with c2: target_revenue = st.number_input("Revenue $M", value=500.0, step=100.0)
with c3: target_ebitda = st.number_input("EBITDA $M", value=120.0, step=50.0)
with c4: target_net_profit = st.number_input("Net Profit $M", value=80.0, step=50.0)

c5, c6 = st.columns(2)
with c5: net_debt = st.number_input("Net Debt $M", value=0.0, step=50.0)
with c6: illiquidity_discount = st.slider("Illiquidity Discount %", 0.0, 70.0, 30.0, 5.0) / 100

if st.button("Fetch Peers & Run Valuation", type="primary"):
    # Step 1: Get company info to find sector
    try:
        ticker_obj = yf.Ticker(ticker_input)
        info = ticker_obj.info
        
        if not info or "sector" not in info:
            st.error(f"Could not find data for ticker '{ticker_input}'")
            st.info("Try a different ticker like: AAPL, MSFT, GOOGL, CF, NTR, MOS")
            st.stop()
        
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        company_name = info.get("longName", ticker_input)
        
        if not sector:
            st.error("Could not find sector for ticker.")
            st.stop()
            
        st.success(f"✅ Found: **{company_name}**")
        st.info(f"Sector: **{sector}** | Industry: **{industry}**")
        
    except Exception as e:
        st.error(f"Error fetching ticker data: {str(e)}")
        st.stop()

    # Step 2: Get peers - use predefined lists by sector
    sector_peers = {
        "Basic Materials": ["CF", "NTR", "MOS", "IPI", "SMG", "FMC", "APD", "LIN", "DD", "DOW"],
        "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "ORCL", "CRM", "ADBE", "INTC", "AMD"],
        "Healthcare": ["JNJ", "UNH", "PFE", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY"],
        "Financial Services": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP", "USB"],
        "Consumer Cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "TJX", "BKNG"],
        "Consumer Defensive": ["WMT", "PG", "KO", "PEP", "COST", "PM", "MDLZ", "CL", "KMB", "GIS"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PXD", "VLO", "PSX", "OXY"],
        "Industrials": ["CAT", "BA", "HON", "UNP", "UPS", "RTX", "LMT", "GE", "MMM", "DE"],
        "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "EA", "TTWO"],
        "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ED"],
        "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "WELL", "DLR", "O", "SPG", "VICI"],
    }
    
    # Find matching sector
    peers = []
    for sector_key, peer_list in sector_peers.items():
        if sector_key.lower() in sector.lower():
            peers = [p for p in peer_list if p != ticker_input][:10]
            break
    
    # Default fallback if no match
    if not peers:
        peers = ["AAPL", "MSFT", "GOOGL", "JNJ", "JPM", "XOM", "HD", "WMT"]
        st.warning(f"Using default peers - sector '{sector}' not in predefined list")

    st.write(f"**Using {len(peers)} peers:** {', '.join(peers)}")

    # Step 3: Fetch financial data for each peer
    results = []
    descriptions = {}
    progress = st.progress(0)

    for idx, ticker in enumerate(peers):
        progress.progress((idx + 1) / len(peers))
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            if not info or "symbol" not in info:
                results.append({
                    "Ticker": ticker, "Company": "No data", 
                    "Revenue $M": "-", "EV/Revenue": "-", 
                    "EBITDA $M": "-", "EV/EBITDA": "-", 
                    "Net Profit $M": "-", "P/E": "-"
                })
                descriptions[ticker] = "No description available."
                continue

            name = info.get("shortName", ticker)[:40]
            
            # Get financial metrics (convert to millions)
            revenue = info.get("totalRevenue", 0) / 1e6 if info.get("totalRevenue") else None
            ebitda = info.get("ebitda", 0) / 1e6 if info.get("ebitda") else None
            net_profit = info.get("netIncomeToCommon", 0) / 1e6 if info.get("netIncomeToCommon") else None
            
            # Get valuation ratios
            ev_rev = info.get("enterpriseToRevenue")
            ev_ebitda = info.get("enterpriseToEbitda")
            pe = info.get("trailingPE")
            
            # Description
            full_desc = info.get("longBusinessSummary", "No description available.")
            short_desc = ". ".join(full_desc.split(". ")[:2]) if full_desc else ""
            if short_desc and not short_desc.endswith("."): 
                short_desc += "."
            descriptions[ticker] = short_desc if short_desc else "No description available."

            results.append({
                "Ticker": ticker, 
                "Company": name,
                "Revenue $M": f"{revenue:,.0f}" if revenue else "-",
                "EV/Revenue": f"{ev_rev:.2f}x" if ev_rev and ev_rev > 0 else "-",
                "EBITDA $M": f"{ebitda:,.0f}" if ebitda else "-",
                "EV/EBITDA": f"{ev_ebitda:.2f}x" if ev_ebitda and ev_ebitda > 0 else "-",
                "Net Profit $M": f"{net_profit:,.0f}" if net_profit else "-",
                "P/E": f"{pe:.1f}x" if pe and pe > 0 else "-",
            })
            
        except Exception as e:
            results.append({
                "Ticker": ticker, "Company": f"Error", 
                "Revenue $M": "-", "EV/Revenue": "-", 
                "EBITDA $M": "-", "EV/EBITDA": "-", 
                "Net Profit $M": "-", "P/E": "-"
            })
        
        time.sleep(0.1)  # Small delay to avoid rate limits

    # Valuation calculations
    df = pd.DataFrame(results)
    med_rev    = pd.to_numeric(df["EV/Revenue"].str.replace('x',''), errors='coerce').dropna().median()
    med_ebitda = pd.to_numeric(df["EV/EBITDA"].str.replace('x',''), errors='coerce').dropna().median()
    med_pe     = pd.to_numeric(df["P/E"].str.replace('x',''), errors='coerce').dropna().median()

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

    median_row = {
        "Ticker": "MEDIAN", "Company": "", 
        "Revenue $M": "", "EV/Revenue": f"{med_rev:.2f}x" if pd.notna(med_rev) else "-", 
        "EBITDA $M": "", "EV/EBITDA": f"{med_ebitda:.2f}x" if pd.notna(med_ebitda) else "-", 
        "Net Profit $M": "", "P/E": f"{med_pe:.1f}x" if pd.notna(med_pe) else "-"
    }
    target_row = {
        "Ticker": "Target EV", "Company": target_name, 
        "Revenue $M": f"{target_revenue:,.0f}", 
        "EV/Revenue": f"{med_rev:.2f}x → {fmt(ev_rev_val)}" if pd.notna(med_rev) else "-", 
        "EBITDA $M": f"{target_ebitda:,.0f}", 
        "EV/EBITDA": f"{med_ebitda:.2f}x → {fmt(ev_ebitda_val)}" if pd.notna(med_ebitda) else "-", 
        "Net Profit $M": f"{target_net_profit:,.0f}", 
        "P/E": f"{med_pe:.1f}x → {fmt(equity_pe_val)}" if pd.notna(med_pe) else "-"
    }
    equity_row = {
        "Ticker": "Equity Value", "Company": "(EV − Net Debt)", 
        "Revenue $M": "", "EV/Revenue": fmt(equity_rev), 
        "EBITDA $M": "", "EV/EBITDA": fmt(equity_ebitda), 
        "Net Profit $M": "", "P/E": fmt(equity_pe)
    }
    fair_row = {
        "Ticker": "Fair Value", "Company": f"(-{illiquidity_discount*100:.0f}% DLOM)", 
        "Revenue $M": "", "EV/Revenue": fmt(fair_rev), 
        "EBITDA $M": "", "EV/EBITDA": fmt(fair_ebitda), 
        "Net Profit $M": "", "P/E": fmt(fair_pe)
    }

    final_df = pd.concat([df, pd.DataFrame([median_row, target_row, equity_row, fair_row])], ignore_index=True)
    st.dataframe(final_df, use_container_width=True, hide_index=True)

    # Final value display
    st.markdown("---")
    if final_fair_value:
        st.markdown(
            f"""
            <div style="background-color:#37474f; color:#eceff1; padding:14px; border-radius:8px; margin:20px 0;">
                <p style="margin:0; font-size:1.05em; font-weight:600;">
                    Final Fair Value: <strong style="font-size:1.35em;">{fmt(final_fair_value)}</strong>
                </p>
                <p style="margin:4px 0 0; font-size:0.9em; opacity:0.9;">
                    Average of {len(fair_values)} method(s) after net debt and {illiquidity_discount*100:.0f}% DLOM
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Football field chart
    if fair_values:
        st.markdown("### Football Field Valuation")
        chart_data = pd.DataFrame({
            "Method": ["EV/Revenue", "EV/EBITDA", "P/E"], 
            "Value": [fair_rev or 0, fair_ebitda or 0, fair_pe or 0]
        }).set_index("Method")
        st.bar_chart(chart_data)

    # Download button
    st.download_button(
        "Download Results", 
        final_df.to_csv(index=False).encode(), 
        "valuation_results.csv",
        "text/csv"
    )

    # Company descriptions
    st.markdown("---")
    st.subheader("Peer Company Descriptions")
    for ticker in peers:
        st.markdown(f"**{ticker}** – {descriptions.get(ticker, 'No description available.')}")