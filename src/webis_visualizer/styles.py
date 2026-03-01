"""
Webis Visualizer – Commercial Light Theme
Clean, professional SaaS dashboard inspired by Linear, Vercel, and Stripe.
Focus: layout structure, element proportions, white-space, hierarchy.
"""


def get_global_css() -> str:
    """Return the complete CSS for the Webis visualizer UI."""
    return '''
    <style>
        /* ============================================================
           0. FONTS – Inter + JetBrains Mono
           ============================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* ============================================================
           1. DESIGN TOKENS – LIGHT COMMERCIAL
           ============================================================ */
        :root {
            /* Surfaces */
            --bg-page:       #f8fafb;
            --bg-card:       #ffffff;
            --bg-card-hover: #fafcfd;
            --bg-sidebar:    #ffffff;
            --bg-inset:      #f1f5f4;
            --bg-hover:      #f0f4f3;
            --bg-active:     #e8f5e9;
            --bg-muted:      #f5f7f6;
            --bg-overlay:    rgba(0,0,0,0.45);

            /* Green palette */
            --green-50:  #f0fdf4;
            --green-100: #dcfce7;
            --green-200: #bbf7d0;
            --green-300: #86efac;
            --green-400: #4ade80;
            --green-500: #22c55e;
            --green-600: #16a34a;
            --green-700: #15803d;
            --green-800: #166534;
            --green-900: #14532d;

            /* Accent */
            --accent:            #16a34a;
            --accent-hover:      #15803d;
            --accent-light:      #dcfce7;
            --accent-muted:      rgba(22,163,74,0.08);
            --accent-muted-hover:rgba(22,163,74,0.14);
            --accent-gradient:   linear-gradient(135deg, #16a34a 0%, #15803d 100%);

            /* Typography */
            --ink:        #111827;
            --ink-2:      #374151;
            --ink-3:      #6b7280;
            --muted:      #9ca3af;
            --muted-dim:  #d1d5db;

            /* Borders */
            --border:        #e5e7eb;
            --border-hover:  #d1d5db;
            --border-accent: rgba(22,163,74,0.3);
            --border-strong: #c4c8cc;

            /* Radii */
            --radius-xs:   4px;
            --radius-sm:   6px;
            --radius-md:   10px;
            --radius-lg:   14px;
            --radius-xl:   18px;
            --radius-2xl:  24px;
            --radius-full: 9999px;

            /* Shadows – subtle, layered */
            --shadow-xs:   0 1px 2px rgba(0,0,0,0.04);
            --shadow-sm:   0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
            --shadow-md:   0 4px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
            --shadow-lg:   0 8px 24px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);
            --shadow-xl:   0 16px 48px rgba(0,0,0,0.10), 0 4px 12px rgba(0,0,0,0.05);
            --shadow-focus: 0 0 0 3px rgba(22,163,74,0.15);

            /* Motion */
            --transition-fast:   0.12s ease;
            --transition-base:   0.2s ease;
            --transition-smooth: 0.35s cubic-bezier(0.22,1,0.36,1);
        }

        /* ============================================================
           2. BASE
           ============================================================ */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            color: var(--ink-2);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
        }
        *, *::before, *::after { box-sizing: border-box; }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', sans-serif;
            color: var(--ink);
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.25;
        }
        h1 { font-size: 1.5rem; font-weight: 800; margin-top: 0 !important; }
        h2 { font-size: 1.15rem; font-weight: 700; }
        h3 { font-size: 0.95rem; font-weight: 600; }

        ::selection { background: var(--green-200); color: var(--green-900); }

        /* ============================================================
           3. SCROLLBARS
           ============================================================ */
        ::-webkit-scrollbar { width: 7px; height: 7px; }
        ::-webkit-scrollbar-thumb {
            background: var(--muted-dim);
            border-radius: var(--radius-full);
            border: 2px solid transparent;
            background-clip: padding-box;
        }
        ::-webkit-scrollbar-thumb:hover { background: var(--muted); background-clip: padding-box; }
        ::-webkit-scrollbar-track { background: transparent; }

        /* ============================================================
           4. APP BACKGROUND
           ============================================================ */
        .stApp,
        div[data-testid="stAppViewContainer"] {
            background: var(--bg-page) !important;
        }

        /* ============================================================
           5. HIDE STREAMLIT CHROME
           ============================================================ */
        [data-testid="stDeployButton"],
        [data-testid="stMainMenu"],
        [data-testid="stSidebarCollapseButton"],
        a[aria-label="Deploy"],
        button[aria-label="Deploy"],
        button[aria-label="Close sidebar"],
        button[aria-label="Open sidebar"],
        button[title="Deploy"],
        button[title="Settings"],
        #MainMenu,
        header[data-testid="stHeader"] [data-testid="stToolbar"],
        header[data-testid="stHeader"] [data-testid="stToolbarActions"],
        header[data-testid="stHeader"] .stAppToolbar,
        header[data-testid="stHeader"] .stAppToolbarContainer,
        div[data-testid="stToolbar"] {
            display: none !important;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
            height: 0 !important;
            min-height: 0 !important;
        }
        header[data-testid="stHeader"]::after { background: transparent !important; }

        /* ============================================================
           6. MAIN CONTAINER – wider, breathable
           ============================================================ */
        div[data-testid="stAppViewContainer"] .block-container {
            padding: 2rem 2.5rem 1.5rem;
            max-width: 1280px;
        }

        /* ============================================================
           7. SIDEBAR – clean white, wider
           ============================================================ */
        section[data-testid="stSidebar"] {
            background: var(--bg-sidebar) !important;
            border-right: 1px solid var(--border) !important;
            width: 20rem !important;
            min-width: 20rem !important;
            box-shadow: var(--shadow-sm);
        }
        section[data-testid="stSidebar"][aria-expanded="false"] {
            margin-left: 0 !important;
            transform: none !important;
            width: 20rem !important;
            min-width: 20rem !important;
        }
        button[kind="header"][data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 0.15rem;
            padding-bottom: 0.25rem;
        }
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--ink) !important;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            margin-top: 0.3rem;
            margin-bottom: 0.5rem;
            color: var(--ink-3) !important;
        }
        section[data-testid="stSidebar"] hr {
            margin: 0.75rem 0 !important;
            border-color: var(--border) !important;
        }
        section[data-testid="stSidebar"] label {
            font-weight: 500;
            font-size: 0.78rem;
            color: var(--ink-3) !important;
            letter-spacing: 0.02em;
        }
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
            color: var(--ink-3) !important;
            font-size: 0.85rem;
        }

        /* Sidebar inputs */
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] > div {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md);
            transition: all var(--transition-fast);
        }
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
            color: var(--ink) !important;
            font-weight: 500;
            font-size: 0.88rem;
        }
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder {
            color: var(--muted) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stTextInput"] > div:focus-within {
            border-color: var(--accent) !important;
            box-shadow: var(--shadow-focus) !important;
        }
        div[data-testid="stTextInput"] small { display: none !important; }

        /* Sidebar slider */
        section[data-testid="stSidebar"] div[data-testid="stSlider"] [role="slider"] {
            background: var(--accent) !important;
        }

        /* Sidebar selectbox */
        section[data-testid="stSidebar"] div[data-testid="stSelectbox"] > div {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md);
        }
        section[data-testid="stSidebar"] div[data-testid="stSelectbox"] span {
            color: var(--ink-2) !important;
        }

        /* Sidebar buttons – pale green background, mid-green text */
        section[data-testid="stSidebar"] .stButton > button {
            background: var(--green-100) !important;
            color: var(--green-700) !important;
            border: 1px solid var(--green-300) !important;
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 0.85rem;
            padding: 0.55rem 1rem;
            box-shadow: var(--shadow-xs);
            transition: all var(--transition-fast);
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: var(--green-200) !important;
            border-color: var(--green-400) !important;
            box-shadow: var(--shadow-sm) !important;
            color: var(--green-800) !important;
            transform: translateY(-1px);
        }
        section[data-testid="stSidebar"] .stButton > button:active {
            transform: translateY(0);
        }

        /* Sidebar mini title – tinted card */
        .sidebar-mini-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.84rem;
            font-weight: 700;
            color: var(--ink) !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin: 0.4rem 0 0.65rem 0;
            padding: 12px 16px;
            background: linear-gradient(130deg, var(--green-50) 0%, #ffffff 100%);
            border: 1px solid var(--green-200);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-xs);
            width: 100%;
        }
        .sidebar-mini-title .smt-icon {
            width: 32px; height: 32px;
            border-radius: var(--radius-sm);
            background: var(--green-100);
            display: grid;
            place-items: center;
            flex-shrink: 0;
        }
        .sidebar-mini-title .smt-icon svg {
            width: 18px; height: 18px;
            stroke: var(--green-700);
            fill: none;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .sidebar-mini-title span { color: var(--ink) !important; font-weight: 700; }

        /* ============================================================
           8. BRAND BAR – taller, hero-style header
           ============================================================ */
        .brand-bar {
            display: flex;
            align-items: center;
            gap: 18px;
            padding: 20px 28px;
            border-radius: var(--radius-xl);
            background: var(--bg-card);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
            margin-bottom: 24px;
            position: relative;
        }
        .brand-bar::after {
            content: "";
            position: absolute;
            bottom: 0; left: 28px; right: 28px;
            height: 3px;
            border-radius: 3px 3px 0 0;
            background: var(--accent-gradient);
            opacity: 0.6;
        }
        .brand-mark img {
            width: 44px;
            height: 44px;
            object-fit: contain;
            border-radius: var(--radius-md);
        }
        .brand-info { flex: 1; min-width: 0; }
        .brand-title {
            font-family: 'Inter', sans-serif;
            font-size: 1.5rem;
            font-weight: 900;
            margin: 0;
            letter-spacing: -0.04em;
            color: var(--ink);
        }
        .brand-subtitle {
            font-size: 0.82rem;
            color: var(--muted);
            margin-top: 2px;
            font-weight: 400;
            letter-spacing: 0.01em;
        }
        .brand-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: var(--radius-full);
            background: var(--accent-light);
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--accent);
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-left: auto;
            flex-shrink: 0;
        }
        .brand-stats {
            display: flex;
            gap: 24px;
            margin-left: auto;
            flex-shrink: 0;
        }
        .brand-stat {
            text-align: center;
        }
        .brand-stat-value {
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.03em;
            line-height: 1;
        }
        .brand-stat-label {
            font-size: 0.65rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
            margin-top: 4px;
        }

        /* ============================================================
           9. OUTPUT FOLDER SELECTOR
           ============================================================ */
        div[class*="st-key-output_folder_select"] {
            width: 520px;
            max-width: 100%;
            margin: 0 0 4px !important;
        }
        div[data-testid="stElementContainer"]:has(> div[class*="st-key-output_folder_select"]) {
            margin-bottom: -4px !important;
        }
        div[class*="st-key-output_folder_select"] div[data-testid="stSelectbox"] {
            margin-bottom: 0 !important;
        }
        div[class*="st-key-output_folder_select"] div[data-testid="stSelectbox"] > label {
            margin: 0 !important; padding: 0 !important; min-height: 0 !important;
        }
        div[class*="st-key-output_folder_select"] div[data-testid="stSelectbox"] > div {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md);
            padding: 6px 14px;
            box-shadow: var(--shadow-xs);
            transition: all var(--transition-fast);
        }
        div[class*="st-key-output_folder_select"] div[data-testid="stSelectbox"] > div:hover {
            border-color: var(--border-hover) !important;
        }
        div[class*="st-key-output_folder_select"] div[data-testid="stSelectbox"] > div:focus-within {
            border-color: var(--accent) !important;
            box-shadow: var(--shadow-focus) !important;
        }
        div[class*="st-key-output_folder_select"] div[data-testid="stSelectbox"] span {
            font-weight: 500;
            color: var(--ink-2) !important;
            font-size: 0.88rem;
        }

        /* ============================================================
           10. TABS – segmented control
           ============================================================ */
        div[data-testid="stTabs"] { margin-top: 0; }
        div[data-testid="stTabs"] [role="tablist"] {
            margin-bottom: 20px;
            background: var(--bg-inset);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 4px;
            width: fit-content;
        }
        div[data-testid="stTabs"] [role="tab"] {
            border-radius: var(--radius-sm);
            padding: 8px 20px;
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--ink-3) !important;
            transition: all var(--transition-fast);
            border: 1px solid transparent;
        }
        div[data-testid="stTabs"] [role="tab"]:hover {
            color: var(--ink-2) !important;
            background: var(--bg-card);
        }
        div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--accent) !important;
            box-shadow: var(--shadow-sm);
            font-weight: 700;
        }
        div[data-testid="stTabs"] [role="tabpanel"] { padding-top: 0; }

        /* ============================================================
           11. TRANSFORM NAV (Radio pills)
           ============================================================ */
        div[class*="st-key-transform_nav_tab2"] {
            width: 100%;
            max-width: none;
        }
        div[class*="st-key-transform_nav_tab2"] > div,
        div[class*="st-key-transform_nav_tab2"] div[data-testid="stRadio"] {
            width: 100%;
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] {
            gap: 0 !important;
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            overflow: hidden;
            width: 100% !important;
            max-width: none !important;
            display: flex !important;
            background: var(--bg-card);
            box-shadow: var(--shadow-sm);
            margin-bottom: 1rem;
            padding: 0 !important;
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label {
            margin: 0 !important;
            border-right: 1px solid var(--border);
            min-height: 3.2rem;
            flex: 1 1 0;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all var(--transition-fast);
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label:last-child {
            border-right: none;
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label > div {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            font-weight: 600;
            font-size: 0.88rem;
            color: var(--ink-3) !important;
            padding: 0 0.5rem;
            transition: all var(--transition-fast);
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label:hover {
            background: var(--bg-hover);
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label:hover > div {
            color: var(--ink-2) !important;
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label:has(input:checked) {
            background: var(--accent-muted);
        }
        div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label:has(input:checked) > div {
            color: var(--accent) !important;
            font-weight: 700;
        }

        /* ============================================================
           12. DIALOG / KEY CONFIG
           ============================================================ */
        div[data-testid="stDialog"] [role="dialog"] {
            border: 1px solid var(--border);
            border-radius: var(--radius-xl);
            background: var(--bg-card) !important;
            width: min(780px, 92vw) !important;
            max-width: 780px !important;
            max-height: 82vh;
            overflow-y: auto;
            box-shadow: var(--shadow-xl);
        }
        div[data-testid="stDialog"] [role="dialog"] > div {
            padding-bottom: 12px !important;
        }
        div[data-testid="stDialog"] [role="dialog"] form {
            margin-bottom: 0 !important;
        }
        div[data-testid="stDialog"] [role="dialog"] [data-testid="stFormSubmitButton"] {
            margin-bottom: 0 !important;
            position: sticky;
            bottom: 0;
            z-index: 2;
            background: linear-gradient(180deg, transparent, var(--bg-card));
            padding-top: 10px;
            padding-bottom: 8px;
        }
        .key-config-scroll {
            max-height: 58vh;
            overflow-y: auto;
            overflow-x: hidden;
            padding-right: 6px;
        }
        .key-config-scroll::-webkit-scrollbar { width: 5px; }
        .key-config-scroll::-webkit-scrollbar-thumb {
            background: var(--muted-dim);
            border-radius: var(--radius-full);
        }
        .key-config-note {
            border: 1px solid var(--green-200);
            background: var(--green-50);
            border-radius: var(--radius-md);
            padding: 12px 16px;
            color: var(--green-800);
            font-size: 0.85rem;
            margin-bottom: 12px;
            line-height: 1.55;
        }

        /* ============================================================
           13. STAT CARDS – clean dashboard cards
           ============================================================ */
        .stat-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
            margin: 20px 0 28px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 22px 24px 20px;
            box-shadow: var(--shadow-sm);
            position: relative;
            transition: all var(--transition-base);
        }
        .stat-card:hover {
            border-color: var(--border-hover);
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }
        .stat-label {
            color: var(--ink-3);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }
        .stat-value {
            font-family: 'Inter', sans-serif;
            font-size: 2.2rem;
            font-weight: 900;
            margin-top: 6px;
            color: var(--ink);
            letter-spacing: -0.04em;
            line-height: 1;
        }
        .stat-icon {
            position: absolute;
            top: 20px; right: 22px;
            width: 42px; height: 42px;
            border-radius: var(--radius-md);
            background: var(--accent-muted);
            display: grid;
            place-items: center;
        }
        .stat-icon svg {
            width: 20px; height: 20px;
            color: var(--accent);
            fill: none;
            stroke: currentColor;
            stroke-width: 2;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .stat-trend {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-top: 10px;
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--accent);
            background: var(--accent-muted);
            padding: 2px 8px;
            border-radius: var(--radius-full);
        }

        /* ============================================================
           14. PIPELINE BOARD – structured flow panel
           ============================================================ */
        .pipeline-board {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-xl);
            padding: 28px 32px;
            box-shadow: var(--shadow-sm);
            position: relative;
        }
        .pipeline-title {
            font-weight: 800;
            font-size: 1rem;
            color: var(--ink);
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }
        .pipeline-title-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--accent);
            flex-shrink: 0;
        }
        .pipeline-subtitle {
            font-size: 0.82rem;
            color: var(--muted);
            margin-bottom: 16px;
        }

        /* -- Progress bar -- */
        .progress-shell {
            height: 8px;
            border-radius: var(--radius-full);
            background: var(--bg-inset);
            overflow: hidden;
            margin-bottom: 28px;
            border: 1px solid var(--border);
        }
        .progress-fill {
            height: 100%;
            background: var(--accent-gradient);
            border-radius: var(--radius-full);
            transition: width 0.5s ease;
        }
        .progress-shell.loading .progress-fill {
            background: linear-gradient(90deg, var(--green-500), var(--green-300), var(--green-500));
            background-size: 200% 100%;
            animation: progressPulse 1.8s ease-in-out infinite;
        }
        @keyframes progressPulse {
            0%   { background-position: 200% 50%; }
            100% { background-position: -200% 50%; }
        }

        /* -- Step cards in horizontal flow -- */
        .pipeline-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0;
            position: relative;
        }
        /* Connecting line behind cards */
        .pipeline-grid::before {
            content: "";
            position: absolute;
            top: 28px;
            left: 16.67%;
            right: 16.67%;
            height: 2px;
            background: var(--border);
            z-index: 0;
        }
        .pipeline-step {
            border-radius: var(--radius-lg);
            padding: 20px;
            border: 1px solid var(--border);
            background: var(--bg-card);
            transition: all var(--transition-base);
            position: relative;
            z-index: 1;
            margin: 0 8px;
            text-align: center;
        }
        .pipeline-step:hover {
            border-color: var(--border-hover);
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }

        /* Step number circle */
        .step-number {
            width: 36px; height: 36px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.82rem;
            font-weight: 800;
            margin: 0 auto 12px;
            border: 2px solid var(--border);
            background: var(--bg-card);
            color: var(--ink-3);
            transition: all var(--transition-base);
        }
        .pipeline-step.completed .step-number {
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
        }
        .pipeline-step.in-progress .step-number {
            border-color: var(--accent);
            color: var(--accent);
            animation: pulseRing 2s ease infinite;
        }
        .pipeline-step.failed .step-number {
            border-color: #ef4444;
            color: #ef4444;
        }
        @keyframes pulseRing {
            0%, 100% { box-shadow: 0 0 0 0 rgba(22,163,74,0.2); }
            50% { box-shadow: 0 0 0 6px rgba(22,163,74,0); }
        }

        .step-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        }
        .step-title {
            font-weight: 700;
            color: var(--ink);
            font-size: 0.88rem;
            letter-spacing: -0.01em;
        }
        .step-status {
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 700;
            padding: 2px 10px;
            border-radius: var(--radius-full);
            background: var(--bg-inset);
            color: var(--muted);
            display: inline-block;
            margin-top: 4px;
        }
        .pipeline-step.completed .step-status {
            color: var(--accent);
            background: var(--accent-muted);
        }
        .pipeline-step.in-progress .step-status {
            color: var(--green-700);
            background: var(--green-100);
        }
        .pipeline-step.failed .step-status {
            color: #dc2626;
            background: #fef2f2;
        }
        .step-desc {
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 10px;
            line-height: 1.5;
        }

        /* ============================================================
           15. STATUS DOTS
           ============================================================ */
        .status-dot {
            height: 8px; width: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            flex-shrink: 0;
        }
        .status-idle       { background-color: var(--muted-dim); }
        .status-in-progress { background-color: var(--green-500); animation: dotPulse 2s ease infinite; }
        .status-completed  { background-color: var(--accent); }
        .status-failed     { background-color: #ef4444; }
        @keyframes dotPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* ============================================================
           16. LAYOUT UTILS
           ============================================================ */
        .section-title {
            font-weight: 700;
            font-size: 1rem;
            margin-bottom: 0.6rem;
            color: var(--ink);
        }
        .section-gap { height: 24px; }

        /* ============================================================
           17. CHAT INPUT
           ============================================================ */
        div[data-testid="stChatInput"] {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-lg);
            padding: 4px 8px;
            box-shadow: var(--shadow-sm);
        }
        div[data-testid="stChatInput"]:focus-within {
            border-color: var(--accent) !important;
            box-shadow: var(--shadow-focus) !important;
        }
        div[data-testid="stChatInput"] textarea {
            background: transparent !important;
            border: none !important;
            color: var(--ink) !important;
        }
        div[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; }
        div[data-testid="stChatInput"] button {
            background: var(--accent-gradient) !important;
            color: #fff !important;
            border: none !important;
            border-radius: var(--radius-full) !important;
        }

        /* ============================================================
           18. PREVIEW BOX
           ============================================================ */
        .preview-box {
            width: 100%;
            min-height: 440px;
            max-height: 660px;
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            background: var(--bg-card);
            box-shadow: var(--shadow-sm);
            overflow: auto;
            margin-bottom: 1rem;
            transition: border-color var(--transition-fast);
        }
        .preview-box:hover { border-color: var(--border-hover); }
        .preview-box-empty {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 440px;
            color: var(--muted);
            font-size: 0.9rem;
            gap: 12px;
        }
        .preview-box-empty svg { opacity: 0.25; stroke: var(--muted); }
        .preview-box-content {
            padding: 1.75rem;
            color: var(--ink-2);
        }
        .preview-box-content pre { color: var(--ink-2) !important; }
        .preview-box-content img { max-width: 100%; border-radius: var(--radius-sm); }
        .preview-box iframe {
            width: 100%;
            min-height: 420px;
            border: none;
            border-radius: var(--radius-md);
        }

        /* Loading spinner */
        @keyframes spinRing {
            to { transform: rotate(360deg); }
        }
        .preview-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 440px;
            gap: 1rem;
        }
        .preview-loading .spinner {
            width: 36px; height: 36px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spinRing 0.8s linear infinite;
        }
        .preview-loading .spinner-text {
            color: var(--muted);
            font-size: 0.85rem;
        }

        /* ============================================================
           19. RIGHT RAIL items
           ============================================================ */
        .right-rail { display: none !important; }
        .right-rail-title {
            font-weight: 700; font-size: 0.72rem;
            letter-spacing: 0.08em; text-transform: uppercase;
            color: var(--ink-3); padding: 0 2px 8px;
            border-bottom: 1px solid var(--border);
        }
        .right-rail-list { display: grid; gap: 10px; }
        .right-rail-item {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: var(--radius-md); padding: 10px 14px;
            display: flex; align-items: center; gap: 10px;
            box-shadow: var(--shadow-xs); color: var(--ink-2);
            font-weight: 600; font-size: 0.85rem; text-decoration: none;
            transition: all var(--transition-fast);
        }
        .right-rail-item, .right-rail-item *, .right-rail-item:visited,
        .right-rail-item:hover, .right-rail-item:active, .right-rail-item:focus {
            text-decoration: none !important; color: var(--ink-2) !important;
        }
        .right-rail-item:hover {
            transform: translateY(-1px); border-color: var(--border-hover);
            box-shadow: var(--shadow-md);
        }
        .right-rail-item:focus-visible, .right-rail-download:focus-visible,
        .right-rail-button:focus-visible {
            outline: 2px solid var(--accent); outline-offset: 2px;
        }
        .right-rail-item.disabled { pointer-events: none; opacity: 0.4; }
        .right-rail-button {
            width: 100%; text-align: left; cursor: pointer;
            appearance: none; border: 1px solid var(--border);
            background: var(--bg-card);
        }
        .right-rail-button:disabled { cursor: not-allowed; }
        .right-rail-link {
            display: inline-flex; align-items: center; gap: 8px;
            margin-top: 14px; padding: 10px 14px;
            border-radius: var(--radius-md); border: 1px dashed var(--border);
            color: var(--ink-2); text-decoration: none;
            font-weight: 600; font-size: 0.85rem;
        }
        .right-rail-link.muted { color: var(--muted); border-style: solid; }
        .right-rail-preview {
            border: 1px solid var(--border); border-radius: var(--radius-md);
            padding: 9px 12px; color: var(--ink-2);
            background: var(--bg-inset); font-weight: 600; font-size: 0.82rem;
        }
        .right-rail-preview-row { display: flex; align-items: center; gap: 10px; }
        .right-rail-preview-row .right-rail-preview { flex: 1; }
        .right-rail-preview-row .right-rail-download { margin-left: auto; }
        .right-rail-preview.muted { color: var(--muted); }
        .right-rail-preview iframe { display: none; }
        .right-rail-footer { margin-top: auto; display: grid; gap: 10px; padding-top: 4px; }
        .right-rail-download {
            display: inline-flex; align-items: center; justify-content: center;
            gap: 6px; padding: 6px 12px; border-radius: var(--radius-sm);
            border: none; background: var(--accent-gradient);
            color: #fff; font-weight: 700; font-size: 0.74rem;
            text-decoration: none; box-shadow: var(--shadow-sm);
            transition: all var(--transition-fast);
        }
        .right-rail-download, .right-rail-download:visited,
        .right-rail-download:hover, .right-rail-download:active,
        .right-rail-download:focus { text-decoration: none !important; color: #fff !important; }
        .right-rail-download:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
        .right-rail-download svg { width: 14px; height: 14px; fill: currentColor; }
        .right-rail-item.download-btn { cursor: pointer; }
        .right-rail-icon {
            width: 28px; height: 28px; border-radius: var(--radius-sm);
            display: grid; place-items: center; flex: 0 0 auto;
        }
        .right-rail-icon.icon-json { background: #eff6ff; color: #3b82f6; }
        .right-rail-icon.icon-html { background: #fff7ed; color: #f97316; }
        .right-rail-icon.icon-md  { background: var(--green-50); color: var(--accent); }
        .right-rail-icon.icon-key { background: #fefce8; color: #eab308; }
        .right-rail-icon svg { width: 16px; height: 16px; fill: currentColor; }

        /* ============================================================
           20. DOWNLOAD BUTTONS
           ============================================================ */
        .stDownloadButton > button {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            color: var(--ink-2) !important;
            font-weight: 600 !important;
            transition: all var(--transition-fast) !important;
        }
        .stDownloadButton > button:hover {
            border-color: var(--border-hover) !important;
            box-shadow: var(--shadow-md) !important;
        }

        /* ============================================================
           21. GENERATE BUTTON – solid green CTA
           ============================================================ */
        div[class*="st-key-unified_generate"] .stButton > button {
            background: var(--accent-gradient) !important;
            color: #fff !important;
            border: none !important;
            border-radius: var(--radius-md) !important;
            font-weight: 700 !important;
            font-size: 0.9rem !important;
            padding: 0.65rem 1.5rem !important;
            box-shadow: var(--shadow-md) !important;
            transition: all var(--transition-fast) !important;
        }
        div[class*="st-key-unified_generate"] .stButton > button:hover {
            box-shadow: var(--shadow-lg) !important;
            transform: translateY(-1px) !important;
            filter: brightness(1.04);
        }
        div[class*="st-key-unified_generate"] .stButton > button:disabled {
            background: var(--bg-inset) !important;
            color: var(--muted) !important;
            box-shadow: none !important;
            transform: none !important;
            filter: none;
            border: 1px solid var(--border) !important;
        }

        /* ============================================================
           22. ALERTS
           ============================================================ */
        div[data-testid="stAlert"] {
            border-radius: var(--radius-md) !important;
        }

        /* ============================================================
           23. ANIMATIONS
           ============================================================ */
        @keyframes fadeSlideUp {
            from { transform: translateY(10px); opacity: 0; }
            to   { transform: translateY(0);   opacity: 1; }
        }

        /* ============================================================
           24. FOOTER – compact commercial footer
           ============================================================ */
        .webis-footer {
            text-align: center;
            font-size: 0.76rem;
            color: var(--muted);
            padding: 2rem 0 0.5rem;
            border-top: 1px solid var(--border);
            margin-top: 2.5rem;
        }
        .webis-footer a {
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
        }
        .webis-footer a:hover { text-decoration: underline; }

        /* ============================================================
           25. DATA SOURCES – styled card list
           ============================================================ */
        .source-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
        }
        .source-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            font-size: 0.84rem;
            color: var(--ink-3);
            transition: all var(--transition-fast);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .source-item:hover {
            border-color: var(--border-hover);
            box-shadow: var(--shadow-sm);
            color: var(--ink-2);
        }
        .source-item::before {
            content: "";
            width: 8px; height: 8px;
            border-radius: 50%;
            background: var(--accent);
            flex-shrink: 0;
        }

        /* ============================================================
           26. RESPONSIVE
           ============================================================ */
        @media screen and (max-width: 1200px) {
            div[class*="st-key-output_folder_select"] { width: 100%; }
            .stat-row { grid-template-columns: repeat(2, 1fr); }
            .pipeline-grid { grid-template-columns: repeat(2, 1fr); gap: 14px; }
            .pipeline-grid::before { display: none; }
            .pipeline-step { margin: 0; text-align: left; }
            .step-header { align-items: flex-start; flex-direction: row; }
            .step-number { margin: 0 0 0 0; }
        }
        @media screen and (max-width: 992px) {
            section[data-testid="stSidebar"] {
                width: 17rem !important;
                min-width: 17rem !important;
            }
            div[data-testid="stAppViewContainer"] .block-container {
                padding: 1.5rem 1.5rem 1rem;
            }
            .brand-bar { padding: 16px 20px; }
            .brand-mark img { width: 38px; height: 38px; }
            .brand-title { font-size: 1.3rem; }
            .brand-stats { gap: 16px; }
            .brand-stat-value { font-size: 1.1rem; }
        }
        @media screen and (max-width: 768px) {
            section[data-testid="stSidebar"] {
                width: 100% !important;
                min-width: 100% !important;
                position: relative !important;
                height: auto !important;
                border-right: none !important;
                border-bottom: 1px solid var(--border) !important;
            }
            div[data-testid="stAppViewContainer"] .block-container {
                padding: 1rem 1rem 0.75rem;
            }
            .brand-bar {
                padding: 14px 16px; gap: 12px;
                border-radius: var(--radius-lg);
                margin-bottom: 16px;
            }
            .brand-mark img { width: 34px; height: 34px; }
            .brand-title { font-size: 1.2rem; }
            .brand-badge { display: none; }
            .brand-stats { display: none; }
            .stat-row { grid-template-columns: 1fr; gap: 12px; }
            .stat-card { padding: 16px 18px; }
            .stat-value { font-size: 1.8rem; }
            .pipeline-grid { grid-template-columns: 1fr; gap: 12px; }
            .pipeline-grid::before { display: none; }
            .pipeline-step { margin: 0; text-align: left; }
            .step-header { flex-direction: row; align-items: center; }
            .step-number { margin: 0; }
            .pipeline-board { padding: 20px; border-radius: var(--radius-lg); }
            div[class*="st-key-output_folder_select"] { width: 100%; }
            div[data-testid="stTabs"] [role="tablist"] { width: 100%; }
            div[data-testid="stTabs"] [role="tab"] { font-size: 0.8rem; padding: 6px 12px; }
            div[class*="st-key-transform_nav_tab2"] [role="radiogroup"] > label { min-height: 2.8rem; }
            .preview-box { min-height: 320px; max-height: 480px; }
            .preview-box-empty { min-height: 320px; }
        }
        @media screen and (max-width: 480px) {
            div[data-testid="stAppViewContainer"] .block-container {
                padding: 0.75rem 0.75rem;
            }
            .brand-bar { padding: 10px 12px; gap: 10px; }
            .brand-mark img { width: 28px; height: 28px; }
            .brand-title { font-size: 1rem; }
            .stat-card { padding: 14px 16px; }
            .stat-value { font-size: 1.5rem; }
            .pipeline-board { padding: 16px; }
            .pipeline-step { padding: 14px; }
        }

        /* ============================================================
           27. REDUCED MOTION & PRINT
           ============================================================ */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        @media print {
            section[data-testid="stSidebar"] { display: none !important; }
            header[data-testid="stHeader"] { display: none !important; }
            .brand-bar { box-shadow: none; border: none; }
        }

        /* ============================================================
           28. FILE UPLOADER
           ============================================================ */
        div[data-testid="stFileUploader"] {
            border: 2px dashed var(--border);
            border-radius: var(--radius-lg);
            background: var(--bg-inset);
            padding: 28px 12px;
            min-height: 120px;
            transition: border-color var(--transition-fast);
        }
        div[data-testid="stFileUploader"]:hover { border-color: var(--accent); }

        /* ============================================================
           29. SIDEBAR TOGGLE BUTTON – floating pill
           ============================================================ */
        #sidebar-toggle-btn {
            position: fixed;
            top: 50%;
            left: 0;
            transform: translateY(-50%);
            z-index: 99999;
            width: 28px;
            height: 56px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-left: none;
            border-radius: 0 var(--radius-md) var(--radius-md) 0;
            box-shadow: var(--shadow-md);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            padding: 0;
            transition: all var(--transition-fast);
            color: var(--ink-3);
        }
        #sidebar-toggle-btn:hover {
            background: var(--green-50);
            border-color: var(--green-200);
            color: var(--green-700);
            box-shadow: var(--shadow-lg);
            width: 32px;
        }
        #sidebar-toggle-btn svg {
            width: 15px;
            height: 15px;
            flex-shrink: 0;
        }

        /* ============================================================
           30. STREAMLIT OVERRIDES
           ============================================================ */
        .stSelectbox > div > div,
        .stMultiSelect > div > div {
            background: var(--bg-card) !important;
            border-color: var(--border) !important;
        }
        .stTextInput > div > div {
            background: var(--bg-card) !important;
            border-color: var(--border) !important;
        }
        div[data-testid="stForm"] {
            background: transparent !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-lg) !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
        }

        /* General buttons */
        .stButton > button {
            background: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--ink-2) !important;
            border-radius: var(--radius-md) !important;
            font-weight: 600 !important;
            transition: all var(--transition-fast) !important;
        }
        .stButton > button:hover {
            background: var(--bg-hover) !important;
            border-color: var(--border-hover) !important;
            box-shadow: var(--shadow-sm) !important;
        }
        /* Sidebar buttons override – keep green style */
        section[data-testid="stSidebar"] .stButton > button {
            background: var(--green-100) !important;
            color: var(--green-700) !important;
            border: 1px solid var(--green-300) !important;
        }
    </style>
    '''
