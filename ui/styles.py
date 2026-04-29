# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""CSS theme constants and custom styling for the Golf Caddy app."""

# Golf-themed color palette
PRIMARY_GREEN = "#2E7D32"
DARK_GREEN = "#163921"
LIGHT_GREEN = "#E8F5E9"
ACCENT_GOLD = "#D9A441"
CARD_BG = "#FFFFFF"
TEXT_DARK = "#17321F"
TEXT_MUTED = "#5E6D5F"

CONFIDENCE_COLORS = {
    "high": "#2E7D32",
    "medium": "#B7791F",
    "low": "#C6452D",
}

CONFIDENCE_LABELS = {
    "high": "High Confidence",
    "medium": "Medium Confidence",
    "low": "Low Confidence",
}

APP_CSS = """
<style>
    :root {
        --app-sand: #F6F1E6;
        --app-sand-dark: #EDE3D1;
        --app-card: rgba(255, 255, 255, 0.94);
        --app-card-solid: #FFFFFF;
        --app-card-muted: #FBF8F2;
        --app-ink: #17321F;
        --app-muted: #5E6D5F;
        --app-line: rgba(23, 50, 31, 0.12);
        --app-line-strong: rgba(23, 50, 31, 0.18);
        --app-green: #2D6A39;
        --app-green-dark: #163921;
        --app-green-soft: #E6F2E7;
        --app-gold: #D9A441;
        --app-gold-soft: #F6E6BF;
        --app-red: #C6452D;
        --app-shadow: 0 16px 34px rgba(23, 50, 31, 0.08);
        --app-shadow-soft: 0 10px 24px rgba(23, 50, 31, 0.06);
        --app-radius-lg: 22px;
        --app-radius-md: 16px;
        --app-radius-sm: 12px;
    }

    .stApp {
        color: var(--app-ink);
        background:
            radial-gradient(circle at top left, rgba(217, 164, 65, 0.14), transparent 24rem),
            radial-gradient(circle at top right, rgba(45, 106, 57, 0.10), transparent 26rem),
            linear-gradient(180deg, #FCFBF7 0%, var(--app-sand) 100%);
    }

    .stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div {
        color: var(--app-ink);
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--app-green-dark) !important;
        letter-spacing: -0.02em;
    }

    p, label, [data-testid="stCaptionContainer"], .stMarkdown, .stText {
        color: var(--app-ink) !important;
    }

    small, .stCaption, .st-emotion-cache-1rsyhoq, .st-emotion-cache-16txtl3 {
        color: var(--app-muted) !important;
    }

    /* Header */
    .main-header {
        display: none;
    }

    .hero-shell {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(20rem, 1fr);
        gap: 1.1rem;
        align-items: stretch;
        background:
            linear-gradient(140deg, rgba(255, 255, 255, 0.90), rgba(247, 242, 231, 0.96)),
            linear-gradient(135deg, rgba(45, 106, 57, 0.03), rgba(217, 164, 65, 0.04));
        border: 1px solid var(--app-line);
        border-radius: 28px;
        padding: 1.35rem;
        margin-bottom: 1.1rem;
        box-shadow: var(--app-shadow);
    }

    .hero-copy {
        padding: 0.35rem 0.2rem;
    }

    .hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        color: var(--app-green);
        background: var(--app-green-soft);
        border: 1px solid rgba(45, 106, 57, 0.14);
        border-radius: 999px;
        padding: 0.35rem 0.75rem;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .hero-copy h1 {
        margin: 0.8rem 0 0.4rem 0;
        font-size: clamp(2rem, 4vw, 3.35rem);
        line-height: 1.05;
        max-width: 12ch;
    }

    .hero-copy p {
        margin: 0;
        font-size: 1.02rem;
        color: var(--app-muted) !important;
        max-width: 58ch;
        line-height: 1.55;
    }

    .hero-steps {
        display: grid;
        gap: 0.75rem;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid var(--app-line);
        border-radius: 22px;
        padding: 1rem;
        min-width: 0;
    }

    .hero-step {
        display: grid;
        grid-template-columns: 2rem minmax(0, 1fr);
        gap: 0.75rem;
        align-items: start;
        padding: 0.25rem 0;
        min-width: 0;
    }

    .hero-step span {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        border-radius: 999px;
        background: linear-gradient(135deg, var(--app-green), #428C4B);
        color: #FFFFFF !important;
        font-weight: 700;
        box-shadow: 0 6px 14px rgba(45, 106, 57, 0.18);
        grid-row: 1 / span 2;
    }

    .hero-step-copy {
        min-width: 0;
    }

    .hero-step strong {
        display: block;
        font-size: 0.96rem;
        color: var(--app-green-dark) !important;
        margin-bottom: 0.12rem;
        line-height: 1.3;
        white-space: normal;
        word-break: normal;
    }

    .hero-step small {
        display: block;
        font-size: 0.88rem;
        line-height: 1.45;
        color: var(--app-muted) !important;
        white-space: normal;
        word-break: normal;
        overflow-wrap: break-word;
    }

    /* Setup cards */
    .section-eyebrow {
        color: var(--app-green);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }

    .setup-shell,
    .context-shell {
        margin-bottom: 0.9rem;
    }

    .setup-grid,
    .stat-grid,
    .fit-grid {
        display: grid;
        gap: 0.8rem;
    }

    .setup-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .stat-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        margin-bottom: 0.8rem;
    }

    .fit-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        margin-bottom: 0.85rem;
    }

    .setup-card,
    .stat-card,
    .fit-card {
        background: var(--app-card);
        border: 1px solid var(--app-line);
        border-radius: 18px;
        padding: 0.95rem 1rem;
        box-shadow: var(--app-shadow-soft);
    }

    .setup-label,
    .stat-label,
    .fit-label {
        font-size: 0.78rem;
        color: var(--app-muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        margin-bottom: 0.45rem;
    }

    .setup-value,
    .stat-value,
    .fit-value {
        color: var(--app-green-dark) !important;
        font-size: 1.3rem;
        font-weight: 700;
        line-height: 1.15;
    }

    .stat-value span {
        font-size: 0.92rem;
        color: var(--app-muted) !important;
        margin-left: 0.2rem;
    }

    .setup-meta,
    .stat-meta,
    .fit-meta {
        margin-top: 0.35rem;
        color: var(--app-muted) !important;
        font-size: 0.86rem;
        line-height: 1.4;
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
    }

    .context-pill {
        display: inline-flex;
        align-items: center;
        background: var(--app-card);
        border: 1px solid var(--app-line);
        border-radius: 999px;
        padding: 0.45rem 0.8rem;
        box-shadow: var(--app-shadow-soft);
        color: var(--app-green-dark) !important;
        font-size: 0.92rem;
        font-weight: 600;
    }

    /* Forms and inputs */
    div[data-testid="stForm"] {
        background: var(--app-card);
        border: 1px solid var(--app-line);
        border-radius: 22px;
        padding: 1.2rem 1.25rem;
        box-shadow: var(--app-shadow-soft);
    }

    div[data-testid="stExpander"] details {
        background: rgba(255, 255, 255, 0.86);
        border: 1px solid var(--app-line);
        border-radius: 18px;
        padding: 0.3rem 0.8rem;
        box-shadow: var(--app-shadow-soft);
        overflow: hidden;
    }

    div[data-testid="stExpander"] summary {
        background: linear-gradient(180deg, rgba(248, 245, 238, 0.98), rgba(241, 235, 223, 0.98));
        border: 1px solid rgba(23, 50, 31, 0.08);
        border-radius: 14px;
        color: var(--app-green-dark) !important;
        font-weight: 700;
        padding: 0.75rem 0.9rem;
        margin: 0.1rem 0 0.45rem 0;
    }

    div[data-testid="stExpander"] details[open] {
        padding-bottom: 0.9rem;
    }

    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div,
    [data-baseweb="textarea"] > div,
    textarea,
    input {
        background: var(--app-card-solid) !important;
        color: var(--app-ink) !important;
        border: 1px solid var(--app-line-strong) !important;
        border-radius: 14px !important;
        box-shadow: none !important;
        min-height: 2.9rem;
    }

    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] input {
        color: var(--app-ink) !important;
        -webkit-text-fill-color: var(--app-ink) !important;
        font-size: 1rem !important;
    }

    [data-baseweb="input"] > div:focus-within,
    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="textarea"] > div:focus-within {
        border-color: rgba(45, 106, 57, 0.35) !important;
        box-shadow: 0 0 0 3px rgba(45, 106, 57, 0.10) !important;
    }

    [data-baseweb="select"] span,
    [data-baseweb="select"] div,
    [data-baseweb="select"] svg,
    [data-baseweb="input"] svg {
        color: var(--app-ink) !important;
        fill: var(--app-ink) !important;
    }

    label, .stRadio label, .stCheckbox label, .stSelectbox label, .stTextInput label,
    .stTextArea label, .stNumberInput label, .stSlider label {
        color: var(--app-green-dark) !important;
        font-weight: 600 !important;
    }

    .stRadio [role="radiogroup"] label p,
    .stCheckbox p,
    .stSelectbox p,
    .stTextInput p,
    .stNumberInput p,
    .stTextArea p {
        color: var(--app-ink) !important;
        line-height: 1.35 !important;
        word-break: normal !important;
    }

    .stRadio [role="radiogroup"] {
        gap: 0.35rem;
    }

    .stRadio [role="radiogroup"] label {
        padding: 0.1rem 0;
    }

    ::placeholder {
        color: #8A958B !important;
        opacity: 1 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.55rem;
        margin-bottom: 0.95rem;
    }

    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        background: transparent !important;
        box-shadow: none !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 0.7rem 1rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid var(--app-line);
        color: var(--app-green-dark) !important;
        font-weight: 700;
        white-space: nowrap;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--app-green), #428C4B) !important;
        border-color: transparent !important;
        color: #FFFFFF !important;
        box-shadow: 0 10px 20px rgba(45, 106, 57, 0.18);
    }

    .stTabs [aria-selected="true"] * {
        color: #FFFFFF !important;
    }

    .step-caption {
        color: var(--app-muted) !important;
        font-size: 0.92rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button,
    .stFormSubmitButton > button {
        border-radius: 14px !important;
        border: 1px solid rgba(45, 106, 57, 0.18) !important;
        color: var(--app-green-dark) !important;
        background: rgba(255, 255, 255, 0.88) !important;
        font-weight: 700 !important;
        transition: all 0.18s ease;
        box-shadow: var(--app-shadow-soft);
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        border-color: rgba(45, 106, 57, 0.28) !important;
        color: var(--app-green-dark) !important;
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2D6A39, #428C4B) !important;
        color: #FFFFFF !important;
        border-color: transparent !important;
        box-shadow: 0 14px 28px rgba(45, 106, 57, 0.24);
    }

    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover {
        color: #FFFFFF !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(250, 249, 244, 0.98), rgba(242, 235, 220, 0.98));
        border-right: 1px solid rgba(23, 50, 31, 0.08);
    }

    [data-testid="stSidebar"] * {
        color: var(--app-ink) !important;
    }

    /* Recommendation cards */
    .club-banner {
        background:
            radial-gradient(circle at top right, rgba(255, 255, 255, 0.12), transparent 12rem),
            linear-gradient(135deg, #2B5E31, #153A22);
        color: #FFFFFF !important;
        padding: 1.75rem;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 0.9rem;
        box-shadow: 0 20px 40px rgba(21, 58, 34, 0.24);
    }

    .club-banner .club-name {
        font-size: clamp(2.2rem, 4vw, 3.4rem);
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.08em;
        color: #FFFFFF !important;
    }

    .club-banner .plays-like {
        font-size: 1.05rem;
        opacity: 0.94;
        margin-top: 0.45rem;
        color: rgba(255, 255, 255, 0.95) !important;
    }

    .confidence-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.84rem;
        letter-spacing: 0.04em;
        box-shadow: var(--app-shadow-soft);
    }
    .confidence-high {
        background: #E8F5E9;
        color: #226B2C !important;
        border: 1px solid rgba(34, 107, 44, 0.16);
    }
    .confidence-medium {
        background: #FFF5D9;
        color: #9A6718 !important;
        border: 1px solid rgba(154, 103, 24, 0.18);
    }
    .confidence-low {
        background: #FDE7E2;
        color: #B23C26 !important;
        border: 1px solid rgba(178, 60, 38, 0.18);
    }

    .adj-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.55rem 0;
        border-bottom: 1px solid rgba(23, 50, 31, 0.08);
        font-size: 0.96rem;
    }
    .adj-row:last-child {
        border-bottom: none;
    }
    .adj-label {
        color: var(--app-ink) !important;
    }
    .adj-value-pos {
        color: var(--app-red) !important;
        font-weight: 700;
    }
    .adj-value-neg {
        color: var(--app-green) !important;
        font-weight: 700;
    }
    .adj-value-zero {
        color: var(--app-muted) !important;
    }

    .explanation-card,
    .intent-card,
    .adaptive-card,
    .backup-card {
        background: var(--app-card);
        border: 1px solid var(--app-line);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.95rem;
        box-shadow: var(--app-shadow-soft);
    }

    .backup-card {
        border-left: 5px solid var(--app-gold);
        background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(251,246,236,0.95));
    }

    .backup-card .backup-title,
    .intent-title,
    .adaptive-title {
        font-weight: 800;
        color: var(--app-green-dark) !important;
        margin-bottom: 0.35rem;
    }

    .backup-card .backup-detail,
    .intent-detail,
    .adaptive-detail,
    .explanation-card {
        color: var(--app-ink) !important;
        font-size: 0.96rem;
        line-height: 1.55;
    }

    /* Alerts */
    div[data-baseweb="notification"] {
        border-radius: 16px !important;
    }

    div[data-baseweb="notification"] * {
        color: var(--app-ink) !important;
    }

    /* Tables */
    .profile-table {
        display: grid;
        gap: 0.35rem;
    }

    .profile-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.55rem 0.7rem;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(23, 50, 31, 0.08);
        border-radius: 12px;
    }

    .profile-club {
        color: var(--app-green-dark) !important;
        font-weight: 700;
    }

    .profile-distance {
        color: var(--app-muted) !important;
        font-weight: 600;
    }

    /* Generic metric fallback */
    [data-testid="stMetric"] {
        background: var(--app-card);
        border: 1px solid var(--app-line);
        border-radius: 16px;
        padding: 0.8rem 0.9rem;
        box-shadow: var(--app-shadow-soft);
        min-height: 110px;
    }

    [data-testid="stMetric"] * {
        color: var(--app-ink) !important;
    }

    /* Footer */
    .app-footer {
        text-align: center;
        color: #889489 !important;
        font-size: 0.78rem;
        padding-top: 1.6rem;
        border-top: 1px solid rgba(23, 50, 31, 0.10);
        margin-top: 2rem;
    }

    @media (max-width: 1080px) {
        .hero-shell {
            grid-template-columns: 1fr;
        }
        .setup-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .fit-grid {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 768px) {
        .hero-shell {
            padding: 1rem;
            border-radius: 22px;
        }
        .hero-copy h1 {
            font-size: 2rem;
        }
        .hero-step {
            grid-template-columns: 1.8rem 1fr;
        }
        .hero-step span {
            width: 1.8rem;
            height: 1.8rem;
            font-size: 0.9rem;
        }
        .setup-grid,
        .stat-grid {
            grid-template-columns: 1fr;
        }
        .club-banner {
            padding: 1.35rem;
            border-radius: 20px;
        }
        .club-banner .club-name {
            font-size: 2rem;
        }
        div[data-testid="stForm"] {
            padding: 0.95rem;
        }
        .explanation-card,
        .intent-card,
        .adaptive-card,
        .backup-card,
        .setup-card,
        .fit-card,
        .stat-card {
            padding: 0.9rem;
        }
    }
</style>
"""
