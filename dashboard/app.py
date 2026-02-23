"""
Jhaveri FIE — Dashboard (Streamlit)
Fund Manager's daily interface for inputting views and reviewing recommendations.

Run: streamlit run dashboard/app.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import json
import pandas as pd
from datetime import datetime, date
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Jhaveri FIE — Financial Intelligence Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0f1419; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3 { color: #e2e8f0 !important; }
    .metric-card {
        background: #1a2332;
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #3b82f6; }
    .metric-label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
    .rec-card {
        background: #1a2332;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .rec-high { border-left: 4px solid #10b981; }
    .rec-medium { border-left: 4px solid #f59e0b; }
    .rec-low { border-left: 4px solid #64748b; }
    .signal-buy { color: #10b981; font-weight: 700; }
    .signal-sell { color: #ef4444; font-weight: 700; }
    .signal-hold { color: #f59e0b; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════

with st.sidebar:
    st.image("https://img.icons8.com/color/96/brain--v1.png", width=60)
    st.title("Jhaveri FIE")
    st.caption("Financial Intelligence Engine")
    st.divider()
    
    # Date display
    st.markdown(f"**📅 {datetime.now().strftime('%d %B %Y')}**")
    st.markdown(f"*{datetime.now().strftime('%A, %I:%M %p IST')}*")
    
    st.divider()
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["🧠 FM Input & Directives", "📊 Technical Signals", "👥 Client Recommendations", "📋 Pipeline History"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption("v1.0 MVP — Jhaveri Securities Ltd")


# ═══════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════

@st.cache_data
def load_client_data():
    """Load client and holdings data."""
    data_dir = Path(__file__).parent.parent / "data"
    
    clients_df = pd.read_csv(data_dir / "clients.csv")
    holdings_df = pd.read_csv(data_dir / "holdings.csv")
    
    return clients_df, holdings_df


def load_latest_pipeline_result():
    """Load the most recent pipeline run result."""
    output_dir = Path(__file__).parent.parent / "outputs"
    
    json_files = sorted(output_dir.glob("pipeline_run_*.json"), reverse=True)
    if json_files:
        with open(json_files[0], 'r') as f:
            return json.load(f)
    return None


def run_full_pipeline(fm_input, fm_name):
    """Execute the full Maestro pipeline."""
    from agents.maestro import Maestro
    maestro = Maestro()
    return maestro.run_pipeline(fm_input=fm_input, fm_name=fm_name)


def run_nlp_only(fm_input, fm_name):
    """Run only NLP parsing (preview before full pipeline)."""
    from agents.nlp_parser import NLPParserAgent
    parser = NLPParserAgent()
    return parser.parse(fm_input, fm_name)


# ═══════════════════════════════════════════════
# PAGE 1: FM INPUT & DIRECTIVES
# ═══════════════════════════════════════════════

if "FM Input" in page:
    st.title("🧠 Fund Manager Input")
    st.markdown("Type your market views below. The AI will convert them into structured trading directives.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fm_name = st.text_input("Fund Manager Name", value="Amit Jhaveri")
        
        fm_input = st.text_area(
            "Market Views & Directives",
            height=200,
            placeholder="""Example inputs:
• Energy sector is in a structural uptrend - increase exposure across all portfolios
• If IT exposure > 10%, move to energy sector
• Gold is entering an upward long-term trend - overindex on gold, reallocate 20% to gold-heavy indices
• Banking looks range-bound - hold existing, don't add
• For momentum portfolios, tighten stop-losses to 5%""",
        )
        
        col_parse, col_run = st.columns(2)
        
        with col_parse:
            parse_clicked = st.button("🔍 Preview Directives", type="secondary", use_container_width=True)
        
        with col_run:
            run_clicked = st.button("🚀 Run Full Pipeline", type="primary", use_container_width=True)
    
    with col2:
        st.markdown("### 📋 Quick Reference")
        st.markdown("""
        **Actions:** BUY, SELL, REDUCE, INCREASE, SWITCH, HOLD, BOOK_PROFITS, STOP_SIP
        
        **Sectors:** IT, BANKING, PHARMA, AUTO, FMCG, METAL, ENERGY, INFRA, GOLD
        
        **Profiles:** Conservative, Moderate, Aggressive, Momentum/PMS
        
        **Examples:**
        - *"Reduce IT by 50%"*
        - *"Gold is trending up — move 20% to gold"*  
        - *"Hold banking, don't add"*
        - *"Switch ICICI Tech to SBI Energy"*
        """)
    
    # Preview directives
    if parse_clicked and fm_input:
        with st.spinner("🤖 Claude is parsing your market views..."):
            try:
                parsed = run_nlp_only(fm_input, fm_name)
                st.session_state["parsed_directives"] = parsed
                
                st.success(f"✅ Parsed {parsed.get('directive_count', 0)} directives")
                
                # Display parsed directives
                st.markdown("### 📋 Parsed Directives")
                
                for d in parsed.get("directives", []):
                    conviction_color = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(d.get("conviction"), "⚪")
                    
                    with st.expander(f"{conviction_color} {d.get('id')}: {d.get('action')} → {d.get('target')} ({d.get('conviction')})", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Action", d.get("action"))
                        col2.metric("Target", f"{d.get('target_type')}: {d.get('target')}")
                        col3.metric("Conviction", d.get("conviction"))
                        
                        st.markdown(f"**Magnitude:** {d.get('magnitude', 'N/A')} | **Timeframe:** {d.get('timeframe', 'N/A')} | **Applies to:** {d.get('applies_to', 'ALL')}")
                        st.markdown(f"**Rationale:** {d.get('rationale', '')}")
                
                # Market context
                if parsed.get("market_context"):
                    st.info(f"📊 **Market Context:** {parsed['market_context']}")
                
                if parsed.get("risk_stance"):
                    st.markdown(f"**Risk Stance:** {parsed['risk_stance']}")
                    
            except Exception as e:
                st.error(f"❌ Parsing failed: {str(e)}")
    
    # Run full pipeline
    if run_clicked and fm_input:
        with st.spinner("🚀 Running full pipeline (this may take 2-5 minutes for all clients)..."):
            try:
                result = run_full_pipeline(fm_input, fm_name)
                st.session_state["pipeline_result"] = result
                
                # Summary metrics
                st.markdown("---")
                st.markdown("### ✅ Pipeline Complete")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Clients Processed", result.get("client_count", 0))
                m2.metric("Total Recommendations", result.get("total_recommendations", 0))
                m3.metric("FM Directives", len(result.get("fm_directives", [])))
                m4.metric("Instruments Analyzed", result.get("technical_signals_count", 0))
                
                st.success("Navigate to **👥 Client Recommendations** to review and approve.")
                
            except Exception as e:
                st.error(f"❌ Pipeline failed: {str(e)}")
                st.exception(e)


# ═══════════════════════════════════════════════
# PAGE 2: TECHNICAL SIGNALS
# ═══════════════════════════════════════════════

elif "Technical" in page:
    st.title("📊 Technical Signals Dashboard")
    
    result = st.session_state.get("pipeline_result") or load_latest_pipeline_result()
    
    if not result:
        st.info("No pipeline data yet. Run the pipeline from the FM Input page first.")
    else:
        # Sector signals
        sector_signals = result.get("sector_signals", [])
        if sector_signals:
            st.markdown("### 🏭 Sector Relative Strength vs Nifty 50")
            
            sector_df = pd.DataFrame(sector_signals)
            if not sector_df.empty:
                # Color the signals
                st.dataframe(
                    sector_df[["sector", "rs_1m", "rsi", "composite_score", "signal"]].rename(columns={
                        "sector": "Sector",
                        "rs_1m": "RS vs Nifty (1M%)",
                        "rsi": "RSI",
                        "composite_score": "Composite Score",
                        "signal": "Signal"
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
        
        st.markdown("---")
        st.markdown(f"*Pipeline run: {result.get('run_timestamp', 'N/A')}*")


# ═══════════════════════════════════════════════
# PAGE 3: CLIENT RECOMMENDATIONS
# ═══════════════════════════════════════════════

elif "Client" in page:
    st.title("👥 Client Recommendations")
    
    result = st.session_state.get("pipeline_result") or load_latest_pipeline_result()
    
    if not result:
        st.info("No recommendations yet. Run the pipeline from the FM Input page first.")
    else:
        all_recs = result.get("recommendations", [])
        
        if not all_recs:
            st.warning("No recommendations generated.")
        else:
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                client_names = [r.get("client_summary", {}).get("name", "Unknown") for r in all_recs]
                selected_client = st.selectbox("Filter by Client", ["All Clients"] + client_names)
            
            with col2:
                priority_filter = st.selectbox("Filter by Priority", ["All", "HIGH", "MEDIUM", "LOW"])
            
            # Display recommendations
            for client_result in all_recs:
                client_summary = client_result.get("client_summary", {})
                recommendations = client_result.get("recommendations", [])
                alerts = client_result.get("alerts", [])
                
                client_name = client_summary.get("name", "Unknown")
                
                if selected_client != "All Clients" and client_name != selected_client:
                    continue
                
                # Client header
                st.markdown(f"### {client_name}")
                st.markdown(f"**{client_summary.get('client_id', '')}** | "
                           f"Risk: {client_summary.get('risk_profile', 'N/A')} | "
                           f"AUM: ₹{client_summary.get('total_aum', 0):,.0f} | "
                           f"Health: {client_summary.get('portfolio_health', 'N/A')}")
                
                if alerts:
                    for alert in alerts:
                        st.warning(f"⚠️ {alert}")
                
                if not recommendations:
                    st.info("No recommendations for this client.")
                    st.divider()
                    continue
                
                for rec in recommendations:
                    priority = rec.get("priority", "MEDIUM")
                    
                    if priority_filter != "All" and priority != priority_filter:
                        continue
                    
                    confidence = rec.get("confidence", 0)
                    
                    # Color coding
                    if priority == "HIGH":
                        icon = "🟢"
                    elif priority == "MEDIUM":
                        icon = "🟡"
                    else:
                        icon = "⚪"
                    
                    signal = rec.get("technical_signal", "N/A")
                    
                    with st.expander(
                        f"{icon} {rec.get('action', '')} — {rec.get('instrument', '')} | "
                        f"Confidence: {confidence}/100 | {signal}",
                        expanded=(priority == "HIGH")
                    ):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Action", rec.get("action", ""))
                        c2.metric("Amount", f"₹{rec.get('amount', 0):,.0f}")
                        c3.metric("Confidence", f"{confidence}/100")
                        c4.metric("Tech Signal", signal)
                        
                        st.markdown(f"**Instrument:** {rec.get('instrument', '')} ({rec.get('sector', '')})")
                        
                        if rec.get("target_instrument"):
                            st.markdown(f"**Switch To:** {rec.get('target_instrument')}")
                        
                        st.markdown(f"**Reasoning:** {rec.get('reasoning', '')}")
                        
                        alloc_before = rec.get("allocation_before_pct", 0)
                        alloc_after = rec.get("allocation_after_pct", 0)
                        st.markdown(f"**Allocation:** {alloc_before}% → {alloc_after}%")
                        
                        if rec.get("expected_impact"):
                            st.markdown(f"**Impact:** {rec.get('expected_impact')}")
                        
                        # Approval buttons
                        bc1, bc2, bc3 = st.columns(3)
                        rec_key = f"{client_summary.get('client_id')}_{rec.get('rec_id', '')}"
                        bc1.button("✅ Approve", key=f"approve_{rec_key}", type="primary")
                        bc2.button("❌ Reject", key=f"reject_{rec_key}")
                        bc3.button("✏️ Modify", key=f"modify_{rec_key}")
                
                # Portfolio impact
                impact = client_result.get("portfolio_impact", {})
                if impact:
                    with st.expander("📊 Portfolio Impact Summary"):
                        if impact.get("sector_allocation_after"):
                            st.markdown("**Sector Allocation (After):**")
                            for sector, pct in impact["sector_allocation_after"].items():
                                st.markdown(f"  {sector}: {pct}%")
                        if impact.get("risk_assessment"):
                            st.markdown(f"**Risk Assessment:** {impact['risk_assessment']}")
                
                st.divider()
        
        st.markdown(f"*Generated: {result.get('run_timestamp', 'N/A')}*")


# ═══════════════════════════════════════════════
# PAGE 4: HISTORY
# ═══════════════════════════════════════════════

elif "History" in page:
    st.title("📋 Pipeline History")
    
    output_dir = Path(__file__).parent.parent / "outputs"
    json_files = sorted(output_dir.glob("pipeline_run_*.json"), reverse=True)
    
    if not json_files:
        st.info("No pipeline runs yet.")
    else:
        for f in json_files[:10]:
            with open(f, 'r') as jf:
                data = json.load(jf)
            
            with st.expander(f"📅 {data.get('run_date', 'Unknown')} — {data.get('total_recommendations', 0)} recommendations"):
                st.json({
                    "timestamp": data.get("run_timestamp"),
                    "clients": data.get("client_count"),
                    "recommendations": data.get("total_recommendations"),
                    "fm_input": data.get("fm_input", "")[:200] + "..."
                })
