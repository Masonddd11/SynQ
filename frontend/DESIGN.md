---
version: alpha
name: JingsStreet-japanese-high-density
description: A Japanese high-density web operating surface for the autonomous trading agent. Jings' Street renders as a packed mosaic of ruled rectangular modules on a bright white field — thousands of data cells tiled edge-to-edge, each marked by a small utility-red tab — with dense black text and cool-gray hairline borders. The trading agent's full state (positions, P&L, cycle decisions, portfolio metrics, candidate scores) packs onto one screen without the whitespace inflation of a default SaaS grid. Every number is a rigid fixed-width cell; every module is a named area in a dense CSS grid template. There is no airy editorial layout and no warm paper; this is the machine that trades, viewed raw and complete.

# Direction Contract

THESIS: The autonomous trading agent produces more simultaneous state than a conventional dashboard can show, so the surface is a **module mosaic** that packs positions, decisions, and metrics edge-to-edge in one dense screen — refusing both the airy editorial layout of the incumbent broadsheet and the card-tower whitespace of a default SaaS grid.
OWN-WORLD: Bright white ground, dense near-black text, one **utility-red** signal for prices, tabs, and live/active states; cool gray (`#E5E5E5`-family) hairline borders and module fills; a compact gothic sans at small sizes with tight leading; every module a ruled rectangle with a small header tab; fixed mono cells for every number.
STORY: The visitor, a desk-screen trader, lands on the full trading ledger at a glance — every position, P&L, session, and cycle decision visible in the packed grid — and reads the mosaic like a control-room board, scanning modules rather than scrolling.
FIRST VIEWPORT: The session/portfolio dashboard: a persistent multi-row nav rail on the left, a dense module mosaic filling the rest — each backtest/paper session as a header-tabbed module showing return %, vs SPY, max drawdown, Sharpe, position count; running sessions pulse.
FORM: High-density web module mosaic (Operate mode); the concept-seed key ca87c8de assigned this register; the mosaic is the committed structure.

colors:
  # Dense white ground, black text, cool gray structure, one utility-red signal.
  ground: "#FFFFFF"            # bright white — the field, not paper
  ink: "#111111"               # dense near-black reading text
  ink-soft: "rgba(17,17,17,0.68)"  # secondary reading ink / meta
  faint: "rgba(17,17,17,0.42)"     # muted/disabled content — ~7:1 on white
  hairline: "rgba(17,17,17,0.15)"  # module borders, cell rules, section dividers
  border: "rgba(17,17,17,0.22)"    # emphasized rules, active module borders

  # The single signal accent — utility red (the Japanese retail/trading register).
  red: "#D8332F"              # signal red — prices, live/active tab, decisive state
  red-deep: "#B22622"         # hover / pressed / emphasis (AA on white)
  red-soft: "rgba(216,51,47,0.14)"  # active-module tint wash

  # Cool grays for module fills and secondary structure (not warm paper).
  gray-50: "#FAFAFA"          # module background base / hover lift
  gray-100: "#F2F2F2"         # module fill, banded rows
  gray-200: "#E5E5E5"         # active module border / checked cell

  # Direction = semantic, in the Japanese register.
  trading-up: "#D8332F"       # live/active/attention — utility red
  trading-down: "rgba(17,17,17,0.45)"  # dormnat/down — drops to faint ink

typography:
  # One compact gothic sans for UI + labels; JetBrains Mono for every number.
  module-title:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', 'Hiragino Sans', 'BIZ UDGothic', system-ui, sans-serif"
    fontSize: 13px
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: 0
  module-kicker:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: 0.02em
  body-sm:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: 0.03em
  number-hero:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: 28px
    fontWeight: 500
    lineHeight: 1
    letterSpacing: -0.02em
  number-md:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.3
    tabularNums: true
  number-sm:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.4
    tabularNums: true
  number-xs:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.4
    tabularNums: true
  button:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 700
    lineHeight: 1
    letterSpacing: 0.01em
  nav-link:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0.01em
  tab-heading:
    fontFamily: "'Helvetica Neue', 'Noto Sans JP', system-ui, sans-serif"
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: 0.05em

rounded:
  none: 0px          # the mosaic is flat and ruled; modules do not round, matching the dense-grid register.
  xs: 2px            # tiny inline tags/badges only.

spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 20px
  xxl: 28px

components:
  module:
    backgroundColor: "{colors.gray-50}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.none}"
    border: 1px "{colors.hairline}"
    hoverBorder: 1px "{colors.ink}"
    activeTint: "{colors.red-soft}"
    activeBorder: 1px "{colors.red}"
  module-tab:
    backgroundColor: "transparent"
    textColor: "{colors.red}"
    typography: "{typography.tab-heading}"
    activeBackground: "{colors.red}"
    activeText: "{colors.ground}"
  button-primary:
    backgroundColor: "{colors.red}"
    textColor: "{colors.ground}"
    typography: "{typography.button}"
    rounded: "{rounded.none}"
    padding: 8px 14px
  button-secondary:
    backgroundColor: "{colors.gray-100}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.none}"
    padding: 7px 13px
    border: 1px "{colors.hairline}"
  input-dense:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.number-md}"
    rounded: "{rounded.none}"
    padding: 6px 8px
    border: 1px "{colors.border}"
    focusRing: 0 0 0 2px "{colors.red}"
  nav-rail:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink}"
    typography: "{typography.nav-link}"
    borderRight: 1px "{colors.hairline}"
    activeText: "{colors.red}"
  section-rule:
    borderTop: 1px "{colors.hairline}"
  signal-live:
    textColor: "{colors.ground}"
    backgroundColor: "{colors.red}"
    inversion: live value snaps to a red tab (white glyph on red field)
  signal-dormant:
    textColor: "{colors.faint}"
    backgroundColor: "transparent"
  brand-mark:
    backgroundColor: "{colors.red}"
    textColor: "{colors.ground}"
    rounded: "{rounded.none}"
---

## Overview

Jings' Street is a **dense Japanese high-density operating surface** for an autonomous trading agent. The app renders as a **packed mosaic of ruled rectangular modules** on a bright white field (`#FFFFFF`) — each module a named area in a dense CSS grid, marked by a small header tab, carrying its data in tight fixed cells. This is the register of a Japanese high-density retail/marketplace site applied to a trading control-room board: dozens of modules tile one screen, dark text at small sizes, cool-gray hairlines rule everything, and a single **utility-red** accent flags prices, live state, and the decisive action.

The visual metaphor is a **control-room data board**: the trading agent's full state — positions, P&L, cycle decisions, portfolio metrics, candidate scores, sessions — packs onto one screen you scan corner to corner. Nothing wastes a pixel. A *live or changed* value snaps to a **red tab** (white glyph on red field). A *dormant* value drops to faint ink. There is no warm paper, no serif narrative, no airy editorial whitespace — this is the machine that trades, dense and legible.

Type is **one compact voice**: a **gothic sans** (Helvetica Neue / Noto Sans JP / Hiragino Sans) for every label and module heading, and **JetBrains Mono** for every number, price, and score. Numbers sit in fixed-width tabular cells so columns align and scanning is instant.

This is an **Operate** surface. The landing page (Persuade) may reuse the mosaic at larger scale, but the dashboard is the primary register: dense, ruled, red-signaled.

## Colors

- **White ground** (`#FFFFFF`): the field. Bright, crisp, dense — not warm paper.
- **Ink** (`#111111`): reading text. Dense near-black.
- **Utility red** (`#D8332F`): the single signal. Prices, live/active tabs, the decisive CTA, the live value's inversion. `red-deep` (`#B22622`) for hover/pressed.
- **Cool grays** (`#F2F2F2`, `#E5E5E5`, `#FAFAFA`): module fills, banded rows, active module borders. Not warm.
- **Faint** (`rgba(17,17,17,0.42)`): dormant/muted content — ~7:1 on white, safe for meta.
- **Hairline** (`rgba(17,17,17,0.15)`): module borders, cell rules, section dividers.

Direction/live semantics:
- **Live / changed / active / up** → snaps to a **red tab** (white glyph on red field). The green/red replacement — in the Japanese retail register.
- **Dormant / neutral / down / fading** → drops to **faint ink**.
- There is no green-as-good / red-as-bad beyond the red-attention marker itself. Red = attention/live; faint = quiet/resting.

## Typography

**One system voice** — compact gothic for the UI, mono for the figures.

| Token | Face | Size | Use |
|---|---|---|---|
| `{typography.module-title}` | gothic sans | 13px 700 | Module headings / section titles |
| `{typography.module-kicker}` | gothic sans | 11px 600 | Module kickers / tabs |
| `{typography.body-sm}` | gothic sans | 12px 400 | Body copy, chat, description |
| `{typography.caption}` | gothic sans | 11px 500 tracked | Meta labels, table headers |
| `{typography.tab-heading}` | gothic sans | 11px 700 | Header-tab labels |
| `{typography.number-hero}` | JetBrains Mono | 28px 500 | Big session return / P&L numbers |
| `{typography.number-md/sm/xs}` | JetBrains Mono | 16/12/11px | Prices, metrics, cells, micro |
| `{typography.button}` | gothic sans | 12px 700 | CTA labels |

All numbers in JetBrains Mono, `tabular-nums`, fixed columns. UI text in the gothic sans at small sizes with tight leading.

## Layout

- **No max-width softness:** the dashboard uses the full viewport — the mosaic is dense. A focus column (~260–300px) holds a **persistent multi-row nav rail** (Dashboard, Sessions, Backtest, Paper, Settings, Playbook).
- **Module mosaic:** the rest is a **dense CSS grid** with `grid-template-areas` naming every module; hundreds of small blocks tile edge-to-edge, separated only by 1px hairlines with `gap-px`-style adjacency. Modules do not float with whitespace between; they pack.
- **Module anatomy:** each module is a ruled rectangle with a **small header tab** (red text → white-on-red when active) at top-left, a mono value cell region, and secondary actions revealed on hover (border raises + action row slides in).
- **Session list:** one module per backtest/paper session — return %, vs SPY, max drawdown, Sharpe, position count, phase; running sessions get a pulsing red mark.
- **Controls/state:** hovering a module raises its border (1px hairline → 1px ink) and reveals actions; tabs switch content in place; badges mark new/active/finished.

## Elevation & Depth

No shadows, no glass, no gradients. Depth is **border weight and tint**: hairline (`0.15`) for structure, ink for the raised/active border, `red-soft` tint for the highlighted module, `red` for the live signal. Modules sit flat on the white field; the grid lines hold them together.

## Shapes

The mosaic is square — `{rounded.none}` (0px) for modules and structural elements. Only tiny inline tags/chips use `{rounded.xs}` (2px). A high-density board does not round its cells.

## Components

- **`module`** — gray-50 fill, ink text, square, 1px hairline border; hover raises to 1px ink; active module gets `red-soft` tint + 1px `red` border.
- **`module-tab`** — red text tab; active tab inverts to red field + white glyph.
- **`button-primary`** — red field, white glyph, square, bold gothic caps. The decisive CTA.
- **`button-secondary`** — gray-100 fill, ink text, 1px hairline border.
- **`input-dense`** — bare white input, ink text, 1px border; focus = 2px red ring.
- **`nav-rail`** — white, ink text, 1px right hairline; active item red.
- **`signal-live`** — white glyph on red field. The live verdict / changing value.
- **`signal-dormant`** — faint ink. Neutral/fading.
- **`brand-mark`** — red tile, white glyph, square.

## Do's and Don'ts

### Do
- Keep the **bright white ground + dense ink + one utility-red signal + cool-gray borders**. Density is the identity; never return to airy warm-paper editorial.
- **Pack the mosaic.** Modules tile edge-to-edge in a dense CSS grid with named areas; no whitespace inflation between cards.
- Set **every number in JetBrains Mono, fixed-width tabular cells**. Figures always state in mono columns.
- Use the **gothic sans** for all UI labels and module text — surfaces stay dense and compact.
- Use **utility-red tab** as the decisive signal: live/changed → white-on-red; dormant → faint ink. No green/red hue-as-direction beyond the red marker itself.
- Use **module borders + tint** for state: hover raises to ink border, active gets red tint + red border.
- Keep **accessibility** the priority: ink-on-white and white-on-red both clear AA; faint is ≥7:1 on white, only for meta; hover/focus/state changes visible.

### Don't
- Don't return to a **warm paper / serif editorial layout** — that is the incumbent Broadsheet look being replaced.
- Don't use color for red-down/green-up direction; use utility-red (attention) vs faint (resting).
- Don't let numbers break out of fixed mono cells; alignment is what makes the board scannable.
- Don't round modules; the mosaic is flat and square.
- Don't add shadows, glass, or gradients — depth is border weight + tint.
- Don't leave a fabricated result; an empty module renders an honest muted cell.

## Responsive Behavior

- **Desktop (> 1024px):** full module mosaic with the left nav rail; thousands of cells tile at once.
- **Tablet (768–1024px):** modules widen; the mosaic drops to fewer columns but keeps the ruled grid and density.
- **Mobile (< 768px):** nav rail collapses to a top hamburger; modules stack into a single dense column; the mosaic becomes a scrollable ruled queue. Density and mono cells persist.
- **Motion:** minimal and functional — one authored hover/action reveal, an instant red-tab snap on live state. Halts fully under `prefers-reduced-motion`.

## Iteration Guide

1. Density is the ground — bright white, packed modules, hairline-ruled, no whitespace inflation.
2. Gothic sans for every label; JetBrains Mono for every number in fixed tabular cells.
3. Signal = utility-red tab (white-on-red) for live, faint ink for dormant. No hue-as-direction.
4. Structure = the module mosaic: named CSS grid areas, edge-to-edge, header tabs, border-tint state.
5. Accessibility is non-negotiable: ink/red on white all clear AA; faint reserved for meta only.

## Known Gaps

- The trading agent requires live Alpaca keys / an LLM key for full paper/live trading; without them, session modules render in honest empty/dormant states — never fabricated.
- The frontend is under active rebuild; DESIGN.md is written first so the build agent consumes this world as authority.
- Fonts: a compact gothic sans (Helvetica Neue / Noto Sans JP / Hiragino Sans) must be available next to JetBrains Mono; add via `next/font/google` (or system fallback) in `layout.tsx`.
- WSAG 2.2 AA: ink-on-white (`#111111` on `#FFFFFF`) ≈ 19:1; white-on-red (`#FFFFFF` on `#D8332F`) ≈ 4.6:1; `faint` (`rgba(17,17,17,0.42)` on white) ≈ 7:1. Hover states use `red-deep` (`#B22622`).
- The incumbent Broadsheet of Record world was **replaced by user decision** via the design selector (English High-Density Web). PRODUCT.md and DESIGN.md both now record this direction.
