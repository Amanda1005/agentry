import streamlit as st


def nav_bar(active: str = "home"):
    st.markdown("""
    <style>
    /* Hide Streamlit's own header and sidebar */
    [data-testid="stSidebar"]        { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    header[data-testid="stHeader"]   { display: none !important; }
    #stDecoration                    { display: none !important; }
    .block-container                 { padding-top: 0 !important; }

    .top-nav {
        background: #f5ede9;
        border-bottom: 1px solid #e2d5cf;
        margin: 0 -2rem 2rem -2rem;
        padding: 0 2rem;
        display: flex;
        align-items: center;
        gap: 36px;
        height: 56px;
    }
    .top-nav .brand {
        font-size: 16px; font-weight: 900;
        color: #0f172a; text-decoration: none;
        margin-right: 12px;
    }
    .top-nav a {
        font-size: 14px; font-weight: 700;
        color: #0f172a; text-decoration: none;
    }
    .top-nav a:hover  { color: #2563eb; }
    .top-nav a.active { color: #2563eb; }
    </style>
    """, unsafe_allow_html=True)

    active_home = 'class="active"' if active == "home"        else ""
    active_lb   = 'class="active"' if active == "leaderboard" else ""
    active_an   = 'class="active"' if active == "analytics"   else ""

    st.markdown(f"""
    <div class="top-nav">
        <a class="brand" href="/" target="_self">⬡ Agentry</a>
        <a {active_home} href="/"            target="_self">Home</a>
        <a {active_lb}   href="/Leaderboard" target="_self">Leaderboard</a>
        <a {active_an}   href="/Analytics"   target="_self">Analytics</a>
    </div>
    """, unsafe_allow_html=True)
