# Lesson checks

The shared pass (lint, `check.py`, strips, `still.py`, `shot.py`, `perf.py`, review rounds) is in [core/review.md](../core/review.md); a lesson watches its question cards to the end too, and adds the checks below.

## Frames and openings

```sh
uv run --with playwright SKILL/scripts/check_blank.py site/<book> chNN --url http://localhost:8765/<book>/
uv run --with playwright SKILL/scripts/overlap.py chNN --url http://localhost:8765/<book>/
```

`check_blank.py` reports openings empty for more than a second after speech starts. `overlap.py` samples every beat and lists, with times, where an arrow runs through text or two texts collide, so you can look at exactly those frames. Both skip a picture book, whose set is always there and whose words are captions.

On the `shot.py` sheets a lesson also looks for geometry contradicting its values, shapes inside circles and curves crossing the outline.

## Questions

```sh
python MCQ/scripts/lint_items.py books/<book>/items/chNN.items.json
```

Fix every error. Treat warnings as prompts: fix them or record in the item's `audit.warnings` why they stay. Then do the skill's judgment checks (Write mode, step 9): cover the options and answer from the stem, one best answer, plausible distractors, no clue to the key. Rebuild `items.js` after any bank change ([courses.md](courses.md)), then answer one choice question per card position (wrong, then right) to see the answered card fit with Continue visible. Read each interactive (non-bank) question once the same way. Give the user `chNN.review.md` with the chapter.

## Contrast and citations

```sh
python SKILL/scripts/check_contrast.py site/<book>
python SKILL/scripts/refs.py verify books/<book>/refs.json
```

The contrast check must pass. Then look at each listed literal below 4.5:1 that the chapter added: it may colour only large text, lines or shapes (≥ 3:1) or decoration (below 3:1). Change any literal used for normal text to a `COL` colour ([core/palette.md](../core/palette.md)). Every author–year or work title on screen should be a `cite()` link whose key is verified in `refs.json`, and `refs.js` must be rebuilt after `refs.json` changes. Look for citation links that are missing, unreadable or overlapping other targets, and open one citation per chapter in the browser to confirm it lands on the work.

## Interaction tests

Adapt `assets/templates/e2e.py` into `tools/<book>/e2e_chNN.py`: it checks playback, that every beat replays the same frame when seeked, that quiz cards stay readable and on stage at two viewport sizes, and walks the answers, practice and finish card. `ANSWERS` maps each question beat to one step per question: a digit picks a choice, `=a,b` fills the boxes, `#2;1+3` answers a grid (rows split by `;`, each row's columns counted from 1, `+` for several, `#2;;1` a row left empty), `@2` clicks the second target ring on the stage (`tap`, `tapEls`, `pickEls`, counted in the order of their values, `idx` or items). Run it in Chromium and with `BROWSER=firefox`. After changing the book's engine or library, rerun the approved chapters' tests.

After scoring changes, check a wrong first try stays recorded after revisiting and a restart clears it; after progress changes, check book isolation and missing or malformed stored data. Fix engine bugs at the engine source and copy them to the books with `scripts/engine.py`; book-specific settings stay in each book's `lib/book.css`.

Test details: keyboard first (Enter checks, Esc leaves a box, press Esc before S, R replays on the finish card); a page opened with `?beat=` is not started, so start it before pressing keys; `seek(i, false)` stops before the old panel's fade, so seek playing or evaluate past it; compare text in lower case (CSS uppercases kickers); avoid assertions on totals that grow with the book.
