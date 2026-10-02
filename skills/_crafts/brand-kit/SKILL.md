# craft: brand-kit
version: 1.0.0
offline: true
used_by: brand-kit-lock, leadership-brief, weekly-ops-review

job: Read brand tokens from house.py and refuse script-level design keys.

rules:
  - Palette and type come from house.py only.
  - No logo download and no brand API.
  - A beat that carries style, color, font, css, theme, or background fails QA.

forbidden:
  - any external HTTP API or brand SaaS
  - public internet egress
  - a font or color that house.py does not name
