# Palette: University of Toronto, WCAG AA

Books use the University of Toronto brand palette (brand.utoronto.ca, Guidelines → Colours and Websites → Web styling → Colour, read 2026-10-08) on a U of T Blue board. The engine, cover/contents template and `COL` already carry it. Check it with `scripts/check_contrast.py site/<book>`.

## Brand colours

| Role (brand) | Name | HEX |
| --- | --- | --- |
| Primary | U of T Blue (PMS 655) | `#1E3765` |
| Secondary | Secondary Blue (PMS 633) | `#007894` |
| Accent | Purple · Warm Red · Cool Blue · Teal · Fuchsia · Dark Green · Yellow · Light Green | `#6D247A` · `#DC4633` · `#6FC7EA` · `#00A189` · `#AB1368` · `#0D534D` · `#F1C500` · `#8DBF2E` |
| Neutral | White · Cool Gray · Black | `#FFFFFF` · `#D0D1C9` · `#000000` |

The brand asks for U of T Blue as the dominant colour and accents for small details (callouts, charts, icons, buttons), never large areas. Its web guidance requires WCAG AA for any text on colour.

## The board

The board is U of T Blue, so the brand colour dominates every frame. On it, Purple, Fuchsia, Dark Green, Secondary Blue, Warm Red and Teal are too dark for text (1.2–3.6:1). The palette therefore uses white tints of those hues, mixed only until they reach 5:1. Yellow, Cool Blue, Light Green and Cool Gray pass as they are.

| Token / `COL` | HEX | Source | On board |
| --- | --- | --- | --- |
| `board` | `#1E3765` | U of T Blue | — |
| `page` (outside the frame, control bar) | `#14254A` | darker U of T Blue | — |
| `panel` (cards, help) | `#172B50` | darker U of T Blue | — |
| `edge` (card borders, dividers) | `#536583` | U of T Blue + Cool Gray | decoration |
| `chalk` | `#FFFFFF` | White | 11.7 |
| `dim` | `#D0D1C9` | Cool Gray | 7.6 |
| `faint` | `#7B8799` | U of T Blue + Cool Gray | 3.2, lines/shapes only |
| `task` | `#F1C500` | Yellow | 7.1 |
| `quiz`, `whole` | `#6FC7EA` | Cool Blue | 6.2 |
| `good`, `irr` | `#8DBF2E` | Light Green | 5.4 |
| `bad`, `nat` | `#EA9287` | Warm Red tint | 5.0 |
| `int` | `#47BBAA` | Teal tint | 5.0 |
| `rat` | `#D995BB` | Fuchsia tint | 5.0 |
| `real` | `#BF9FC4` | Purple tint | 5.0 |

Unit colours on the contents page (`HUES`) cycle through Cool Blue, Yellow, Light Green, Warm Red tint, Teal tint, Fuchsia tint and Purple tint.

## Rules

- **Text** (SVG `T`/`M`, card text, labels) uses `chalk`, `dim` or an accent: all ≥ 5:1 on board, panel and page. Never `faint`, `edge` or a hand-picked hex below 4.5:1.
- **Text on a filled accent shape** (a numbered disc, a chip, a pressed option) uses `COL.board`; every accent gives ≥ 5:1 with it. White on an accent fails.
- **Lines, axes, arrows and shape outlines that carry meaning** need ≥ 3:1: any palette colour or `faint`. Translucent washes (`rgba(255,255,255,.08)` and the like) are decoration and must not be the only cue.
- **Colour is never the only signal.** Right/wrong also shows ✓/✗ or a crossing-out; categories also carry a label or position.
- **Close pairs.** The purple and fuchsia tints (`real`/`rat`) are close for everyone, and yellow and light green (`task`/`good`, `irr`) merge under protanopia. Don't let either pair be the only way to tell two things apart; give each a label, shape or position. Blue, teal and green separate well.
- **New colours** come from the table: an accent, or a tint mixed toward white until ≥ 4.5:1 on the board. A darker shade of U of T Blue is fine for surfaces. Avoid literals; add a named constant (`COL`, or the book's `book.js`) and record its meaning in BOOK.md.
- Tweened colours need hex values (`c_fill`, `c_stroke`).
- **Texture only darkens.** The board's grain is dark navy, so the board renders at U of T Blue or darker. A light grain, glow or wash behind text raises the board's luminance and erodes the margins above: a white 7% grain once cut the tints from 5.0:1 to 4.2:1 on the rendered board. Check contrast on the rendered page, not only against the hex values.

A book that has to follow another brand replaces these tokens in `lib/engine.css`, `COL` in `lib/engine.js`, and `:root`/`HUES`/the guide colour in `index.html` together, then reruns `check_contrast.py`.
