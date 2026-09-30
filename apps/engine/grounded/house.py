"""Locked house style. Renderers read these tokens. Scripts cannot override them."""

PAPER = "#f3f0e8"
INK = "#1a1814"
MUTED = "#5e584e"
RULE = "#d3cdc2"
ACCENT = "#1d3c34"
NEGATIVE = "#7a2e2e"
THEATER = "#241f1a"
CAPTION = "#1a1814"
CAPTION_INK = "#f3f0e8"

FONT_TITLE = 'Georgia, "Iowan Old Style", "Palatino Linotype", Palatino, serif'
FONT_UI = '"Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'


def css() -> str:
    return f"""
:root {{
  --paper: {PAPER};
  --ink: {INK};
  --muted: {MUTED};
  --rule: {RULE};
  --accent: {ACCENT};
  --negative: {NEGATIVE};
  --theater: {THEATER};
  --caption: {CAPTION};
  --caption-ink: {CAPTION_INK};
  --title: {FONT_TITLE};
  --ui: {FONT_UI};
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0;
  background: var(--theater);
  color: var(--ink);
  font-family: var(--ui);
}}
.deck {{
  height: 100vh;
  overflow-y: auto;
  scroll-snap-type: y mandatory;
}}
.slide {{
  height: 100vh;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 20px;
}}
.frame {{
  width: min(1180px, calc(100vw - 48px));
  aspect-ratio: 16 / 9;
  background: var(--paper);
  color: var(--ink);
  padding: 48px 60px 28px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
.eyebrow {{
  margin: 0 0 16px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
}}
.eyebrow.risk {{ color: var(--negative); }}
h1 {{
  margin: 0;
  max-width: 18em;
  font-family: var(--title);
  font-weight: 400;
  font-size: 36px;
  line-height: 1.2;
  letter-spacing: -0.015em;
}}
.cover h1 {{ font-size: 60px; line-height: 1.05; max-width: 12em; }}
.lead {{
  margin-top: 28px;
  font-family: var(--title);
  font-size: 28px;
  line-height: 1.35;
  max-width: 22em;
}}
.figures {{
  margin-top: 36px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px 48px;
}}
.figures .label {{
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--muted);
}}
.num {{
  font-family: var(--title);
  font-weight: 400;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
  line-height: 0.95;
}}
.num.xl {{ font-size: 84px; }}
.num.lg {{ font-size: 64px; }}
.delta {{
  margin-top: 22px;
  font-size: 20px;
  color: var(--accent);
}}
.delta.down {{ color: var(--negative); }}
table {{
  width: 100%;
  margin-top: 28px;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}}
th {{
  padding: 0 12px 8px;
  border-bottom: 1px solid var(--ink);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  text-align: left;
}}
td {{
  padding: 12px;
  border-bottom: 1px solid var(--rule);
  font-size: 20px;
}}
td.num, th.num {{ text-align: right; font-family: var(--title); }}
td.down {{ color: var(--negative); }}
.footer {{
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 13px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}}
.caption-bar {{
  margin-top: 20px;
  background: var(--caption);
  color: var(--caption-ink);
  padding: 16px 18px;
  font-family: var(--title);
  font-size: 22px;
  line-height: 1.35;
}}
.screen {{
  margin-top: auto;
  font-family: var(--title);
  font-size: 64px;
  line-height: 1;
}}
.zoom {{
  margin-top: 12px;
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
}}
.page {{
  max-width: 760px;
  margin: 0 auto;
  padding: 56px 24px 80px;
  background: var(--paper);
  min-height: 100vh;
  color: var(--ink);
}}
.page h1 {{ font-size: 42px; }}
.page p, .page li {{ font-size: 17px; line-height: 1.45; }}
.page a {{ color: var(--accent); }}
.pass {{ color: var(--accent); }}
.fail {{ color: var(--negative); }}
"""
