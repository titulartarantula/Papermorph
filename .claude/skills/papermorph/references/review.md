# Delivery pass

Serve `site/` over HTTP. Use this pass once per chapter; inspect relevant frames, fix clear defects locally and recheck those parts. Deliver for the user's assessment of overall aesthetics, pacing and teaching effectiveness.

## Frames and opening blanks

```sh
uv run --with playwright --with pillow SKILL/scripts/shot.py chNN --url http://localhost:8765/<book>/ --out /tmp/animebook-<book>
uv run --with playwright SKILL/scripts/check_blank.py site/<book> chNN --url http://localhost:8765/<book>/
```

`shot.py` captures open/end frames as 4-up sheets and reports console errors. Read the sheets once; use `shot.py chNN 5:7.5` for a specific transition or correction. Add `--moments mid` when intermediate geometry needs a frame. Run one screenshot browser at a time.

Make a brief judgment of:

- the picture empty or unrelated at `open`;
- text over drawings, labels colliding, anything clipped or off the stage;
- a question card covering the object it asks about;
- leftovers from the previous beat, half faded;
- geometry contradicting the intended values, spacing or area;
- text too small to read at half size, or too much text at once;
- inconsistent colours for the same idea;
- citation links missing, unreadable or overlapping other targets.

The blank check reports openings empty for more than 1 second after speech starts (`LIMIT=0.6` for a stricter pass). Resolve reported openings in the beat. Preserve ordinary transitions and thinking pauses.

Report the delivery result and any unresolved defects in a few lines. A new visual redesign starts with user feedback.

## Questions

```sh
python MCQ/scripts/lint_items.py books/<book>/items/chNN.items.json
```

Fix every error. Treat warnings as prompts: fix them or record in the item's `audit.warnings` why they stay. Then do the skill's judgment checks (Write mode, step 9): cover the options and answer from the stem, one best answer, plausible distractors, no clue to the key. Rebuild `items.js` after any bank change, then answer one choice question per card position (wrong, then right) to see the answered card fit with Continue visible. Read each interactive (non-bank) question once the same way. Give the user `chNN.review.md` with the chapter.

## Contrast and citations

```sh
python SKILL/scripts/check_contrast.py site/<book>
python SKILL/scripts/refs.py verify books/<book>/refs.json
```

The contrast check must pass. Then look at each listed literal below 4.5:1 that the chapter added: it may colour only large text, lines or shapes (≥ 3:1) or decoration (below 3:1). Change any literal used for normal text to a `COL` colour ([palette.md](palette.md)). Every author–year or work title on screen should be a `cite()` link whose key is verified in `refs.json`, and `refs.js` must be rebuilt after `refs.json` changes. Open one citation per chapter in the browser to confirm it lands on the work.

## Targeted interaction tests

For changes to playback, question types or grading, run existing tests that exercise the changed behavior. If needed, adapt `assets/templates/e2e.py` into `tools/<book>/e2e_chNN.py`; set `URL` to the actual chapter URL. Check the relevant wrong/right feedback, Show answer and continuation, or pause/replay/seek behavior. Shared timing/replay changes warrant the whole book's blank check and existing affected tests; ordinary new chapters use the delivery pass above.

For scoring changes, verify a wrong first attempt stays recorded after leaving and revisiting the question, and that restarting clears it. For progress changes, check book isolation and loading with missing or malformed stored data. Apply common fixes to the affected book engines and the Skill engine/template, preserving book-specific helpers and legacy keys.

Test details: keyboard first, plus mouse for changed drag handling; Enter checks and Esc leaves answer boxes; press Esc before S. Multi-row questions score per row. Use R on the finish card (Enter opens the next chapter). Python's server lacks Range requests, so let audio play naturally instead of setting `audio.currentTime`.
