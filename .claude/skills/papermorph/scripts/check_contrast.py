#!/usr/bin/env python3
"""Check a book's colours against WCAG 2.2 AA on its board.

    python check_contrast.py site/<book>                 # engine palette + every colour literal in the book
    python check_contrast.py site/<book> --strict        # also fail on literals below 3:1 (lines and shapes)

Reads the --tokens in lib/engine.css and COL in lib/engine.js, then checks:
  - text colours (chalk, dim, task, quiz, good, bad and the six category colours) ≥ 4.5:1 on board, panel and page;
  - faint ≥ 3:1 on board (lines, axes and shapes that carry meaning);
  - board-coloured text on each accent fill ≥ 4.5:1.
Then lists every other hex or rgba() colour in the book's HTML/JS/CSS with its contrast on the board
(rgba blended over the board): AA text ≥ 4.5, large text and graphics ≥ 3, below that decoration only.
A literal used for text must reach 4.5 (3 for text ≥ 24 px, or ≥ 18.5 px bold); one used for a meaningful
line or shape must reach 3. Prefer COL names to literals. Exit status 1 when a palette rule fails.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

TEXT = ["chalk", "dim", "task", "quiz", "good", "bad", "nat", "whole", "int", "rat", "irr", "real"]


def rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    c = [x / 255 for x in c]
    c = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def blend(c, a, under):
    return tuple(round(x * a + y * (1 - a)) for x, y in zip(c, under))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("book", type=Path, help="site/<book>")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    css = (a.book / "lib/engine.css").read_text(encoding="utf-8")
    js = (a.book / "lib/engine.js").read_text(encoding="utf-8")
    tok = {k: rgb(v) for k, v in re.findall(r"--([a-z]+):\s*(#[0-9a-fA-F]{3,6})\b", css.split("}")[0])}
    m = re.search(r"const COL = \{(.*?)\};", js, re.S)
    col = {k: rgb(v) for k, v in re.findall(r"(\w+):\s*'(#[0-9a-fA-F]{6})'", m.group(1))}
    board, fails = col["board"], []
    surfaces = {"board": board, "panel": tok.get("panel", board), "page": tok.get("page", board)}

    print("Palette (text needs 4.5)")
    for k in TEXT:
        c = col.get(k) or tok.get(k)
        rs = {s: ratio(c, v) for s, v in surfaces.items()}
        worst = min(rs.values())
        flag = "ok " if worst >= 4.5 else "FAIL"
        if worst < 4.5:
            fails.append(k)
        on_fill = ratio(board, c)
        print(f"  {flag} {k:6} #{'%02X%02X%02X' % c}  " + "  ".join(f"{s} {r:5.2f}" for s, r in rs.items())
              + f"   board text on it {on_fill:5.2f}")
    f = col["faint"]
    r = ratio(f, board)
    print(f"  {'ok ' if r >= 3 else 'FAIL'} faint  #{'%02X%02X%02X' % f}  board {r:5.2f} (lines and shapes; never text)")
    if r < 3:
        fails.append("faint")

    known = {v for v in col.values()} | set(tok.values())
    seen = defaultdict(set)
    for p in sorted(a.book.rglob("*")):
        if p.suffix not in (".html", ".js", ".css") or "audio" in p.parts or p.name in ("engine.js", "engine.css"):
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for hx in re.findall(r"(?<![\w&])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", line):
                seen[(rgb(hx), 1.0)].add(f"{p.relative_to(a.book)}:{i}")
            for r_, g_, b_, al in re.findall(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", line):
                seen[((int(r_), int(g_), int(b_)), float(al))].add(f"{p.relative_to(a.book)}:{i}")
    lows = 0
    print("\nOther colour literals on the board (rgba blended over it)")
    for (c, al), where in sorted(seen.items(), key=lambda kv: ratio(blend(*kv[0], board), board)):
        if al == 1 and c in known:
            continue
        r = ratio(blend(c, al, board), board)
        if r < 1.15 and al < 1:
            continue    # faint washes and shadows: decoration
        cls = "text" if r >= 4.5 else "large/graphics" if r >= 3 else "decoration only"
        lows += r < 3
        name = f"#{'%02X%02X%02X' % c}" + (f" @{al:g}" if al < 1 else "")
        print(f"  {r:5.2f} {cls:15} {name:14} {', '.join(sorted(where)[:4])}{' …' if len(where) > 4 else ''}")
    if fails:
        print(f"\nFAIL: palette colours below AA: {', '.join(fails)}")
    if fails or (a.strict and lows):
        sys.exit(1)


if __name__ == "__main__":
    main()
