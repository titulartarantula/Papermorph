# Authoring a chapter

## Shape

The algebra book used roughly 5–11 minute chapters and 5–40 second beats. Let the content determine length and the number of checks/practice sets.

| Beat | Purpose |
| --- | --- |
| `intro` | Title card (unit and chapter number, title, one line of purpose). |
| lesson beats | One idea each, built up in the picture while the narration explains it. |
| `q1`, `q2`, … | A check of already taught content, separated from the next check by a lesson beat. |
| `wrap` | Three or four numbered takeaways. |
| `final1` … | Consecutive full-screen practice sets labelled "Chapter practice N of M", covering the whole chapter. |
| `finish` | Score card (`finishCard`): first-try results for quick checks and practice. |

Beat ids are shared by the page (`BEATS`) and the narration file; a beat with `ask` waits for the answers before moving on.

## Storyboard

Before writing code, write the chapter's objectives (three to five things the reader can do afterwards: "classify a thought by theme", "predict which explanation keeps a learner trying"); every question tests one of them. Then list the beats. For each lesson beat decide:

- what the eye should watch, and what changes;
- why that change is true (the animation is the argument, not decoration);
- which words trigger which actions (these become `[[marks]]`);
- what text appears on screen: the key formula, rule or label, placed beside the thing it names;
- what is still on screen from the previous beat, and what fades.

Principles that held up over a whole book:

- **Open on the subject.** When a beat clears the picture, the new topic (expression, diagram, question) appears right away; labels and steps then follow the words. The engine moves an opening group forward if nothing appears in the first 0.8 s, but design for it. Normal transitions and short pauses for thought are fine; the picture need not move all the time.
- **One new thing at a time.** Don't introduce several objects, colours and texts at once.
- **Same colour, same meaning** within a chapter (and, where it fits, across the book).
- **Be exact.** Number lines, grids and areas are to scale; a deliberately enlarged drawing says "drawn larger" on screen. Approximations are written as approximations (≈ 4.47…, never = 4.47).
- **Teach the chapter's scope.** If the book jumps ahead or uses something not yet taught, leave it out or say so.
- **Show the common mistake** where one exists (e.g. squaring the coefficient too), visually crossed out, then the right way.

## Narration

`content/<book>/chNN/narration.<lang>.json` (English example):

```json
{ "voice": "en-US-AndrewMultilingualNeural", "rate": "-4%",
  "beats": { "intro": "Chapter five. [[sub]]Subtraction undoes addition.", "...": "..." } }
```

ElevenLabs instead of Edge TTS, when the user names a voice for the book (record it in BOOK.md; every chapter of a book uses the same voice):

```json
{ "provider": "elevenlabs", "voice": "<voice id>", "model": "eleven_v4",
  "settings": { "speed": 0.96 }, "beats": { "...": "..." } }
```

- Model: `eleven_v4` for every ElevenLabs book (user decision, 2026-10-10). Books narrated earlier keep the model named in their narration files; changing it re-synthesises every chapter.
- The API key comes from `ELEVENLABS_API_KEY` or a `.env` file in the project root (git-ignored). Never put the key in a narration file, BOOK.md or the site. It is a secret starting with `sk_`; a 64-character hex string is a key ID and is rejected.
- Same command (`uv run --with edge-tts … tts.py …`); the script needs no extra package for ElevenLabs. Word times come from the API's character alignment, so marks and captions work as with Edge.
- ElevenLabs bills per character. Tell the user the chapter's character count before the first synthesis of a book; afterwards only changed beats are re-synthesised. A voice, model or settings change re-synthesises the whole chapter.
- Pacing differs from Edge: check marks land on the intended words in the delivery pass.
- Respell for the voice with `{{shown|spoken}}` (e.g. `{{honne|honneh}}`): the voice reads `spoken`, captions show `shown`. The spoken text keys the audio cache, so wrapping an already-synthesized respelling costs nothing.

- `[[name]]` goes right before the word an action waits for; `m('name', offset)` in the page returns when that word starts. Names are unique within a beat; a misspelt mark makes the page throw, and a mark that matches no spoken word makes `tts.py` stop.
- Write for the ear: short sentences, one idea each. Say math in words ("negative seven halves", "x squared"); the picture shows the symbols.
- Match the audience: plain, warm, never childish. Explain why, not only how.
- Question beats get one short line ("Quick check. Find the mean."); the card holds the question.
- `tts.py` caches word timings beside the narration JSON; the output folder receives `<beat>.mp3` and `timings.js` (duration, marks, sentence captions). Moving or adding `[[marks]]` reuses the spoken-text cache and recalculates timings. Existing caches made with raw-text keys are reused for an unchanged beat and then upgraded; changing its marks before that upgrade may require one new synthesis.
- Audio is replaced only after synthesis and timing validation succeed, and each completed beat is cached immediately. After a later failure, rerun the same command to reuse completed beats rather than regenerating the chapter.

## Questions

### Choice questions: the mcq-item-writer skill

Every `choice` question is written with the **mcq-item-writer** skill (`MCQ`), never inline. Call it in Write mode as its *Calling this skill from another project* describes, with this brief:

```yaml
objectives: [the storyboard's objectives for this chapter]
source: books/<book>/pages/chNN/text.md
learner_level: <BOOK.md readers>
purpose: learning            # both, if BOOK.md says scores reach a gradebook (SCORM)
assessment_type: formative
options_per_item: 3          # cards fit three; four only on SCREEN practice, with four real distractors
export: [markdown]           # the review sheet; the page needs only the JSON
out_dir: books/<book>/items/  # chNN.items.json, chNN.review.md
```

Papermorph adds these to the skill's rules:

- **Ids** keep the book's prefixes: `c-…` for a quick check, `p-…` for practice (the finish card adds them up by prefix); unique within the chapter.
- **The card is the screen.** Put the scenario and lead-in in `stem`; no `data_table` or `media` (the picture is the figure: draw the data in the beat and ask about it). Options stay short enough for one line on the card.
- **Feedback** follows the skill (every option, misconception named), kept to two or three sentences so the answered card fits. The engine adds "Correct." / "Not quite.", so don't start feedback with a verdict; `items.py` drops one if present.
- **Order.** The engine shows options as authored (no shuffle): set `shuffle: false` and spread key positions across the chapter.
- **Ordered (diagnostic) MC** may be offered as the skill describes; on a card it scores right/wrong only.

Then lint, build and ask:

```sh
python MCQ/scripts/lint_items.py books/<book>/items/chNN.items.json
python MCQ/scripts/export.py books/<book>/items/chNN.items.json --format markdown --out books/<book>/items/chNN.review.md
python SKILL/scripts/items.py books/<book>/items/chNN.items.json site/<book>/chNN/items.js
```

The chapter loads `<script src="items.js"></script>` right after `engine.js` and asks with `mcq('c-attrib')` inside `quiz(...)` (engine.md). To change a question, edit the bank and rebuild; never edit `items.js`. Items stay `draft` until the user approves the chapter.

### Other question types

The interactive types below carry no bank, but the same rules from `MCQ/references/` apply by judgment: the task is clear before acting (`writing-rules.md`), every clickable target or row is a plausible option with its own mistake-specific feedback (`learning-and-feedback.md`), no answer clues or trick wording (`technical-flaws.md`), and people in scenarios follow `people-in-scenarios.md`. A named person's own pronouns are fine.

Pick the type that lets the student act on the picture itself whenever possible (click the point, the cell, the step) rather than choosing text.

| Type | Use for |
| --- | --- |
| `choice` / `mcq` | One best answer from a few options, each wrong option with its own explanation; new questions come from the bank via `mcq(id)` |
| `blanks` | Typed numbers inside an expression; fractions and mixed numbers accepted; `test` judges a whole row (answers in any order) |
| `grid` | Several items, each classified (yes/no, which category, true/false) |
| `tap` / `tapEls` / `pickEls` | Click a point on the number line / a token in an expression / any drawn object |
| `pickPoint` | Choose a grid point on a coordinate plane |
| `sorter` | Drag items into regions (the number-set diagram) |

New types are welcome when the content calls for one; each needs keyboard play (see engine.md).

- Ids: `c-…` for quick checks, `p-…` for practice; the score card adds them up.
- The prompt is HTML text; put math in it with `$m(...)`.
- Vary the right option's position across a chapter's `choice` questions; a fixed position (always the first) becomes guessable.
- Feedback: right → `why` (and an animation via `fx`/`onRight`); wrong → a hint aimed at that mistake; after a wrong try, Show answer.
- Grade meaning: equal values match (6/8 = 3/4) unless the lowest form is asked for; sets and pairs in any order; no denominators of zero; never judge irrationality from finitely many digits.
- The built-in numeric parser uses safe integer numerators and denominators and exact integer products for equality. For answers outside that range, use a subject-specific input and grader rather than allowing rounded values to pass.
- Place cards so they don't cover the object being asked about (`BAND` under a number line, `TOPR` top right, a custom `{x, y, w, cls: 'side'}` beside a figure, `SCREEN` for practice).

## Content rules

- Follow the agreed chapter scope and order. Verify facts, calculations and answers actually used in the finished lesson; correct or replace source errors and note them in `books/<book>/chapters/chNN.md` for the user.
- Use BOOK.md's definitions, notation and rounding conventions. Record new shared decisions there.
- Colours follow [palette.md](palette.md): `COL` names, text ≥ 4.5:1, `COL.board` text on accent fills, never colour alone.

## Citations

Every work named on screen (an author–year, a quoted study, a book title) is a live link to that work. Links come from a verified list, never from memory.

1. **List.** Add each cited work to `books/<book>/refs.json`, taking authors, year and full title from the source book's own reference list (`pages/*/text.md`). The key is `surname-surname-year` (`scheper-hughes-lock-1987`); `cite` is the on-screen label.
2. **Find.** `python SKILL/scripts/refs.py lookup books/<book>/refs.json --write`. This accepts a Crossref DOI only when the year, first author and title all match. For books without a DOI it takes the ISBN of the English edition from the cited year (Open Library), which links to its WorldCat record. Decide each `NO CONFIDENT MATCH` by hand: pick the right candidate or a trusted academic page (`url`, e.g. PubMed, JSTOR, ERIC, a university repository). If none exists, keep the citation as plain text and note it in the chapter file.
3. **Verify.** `python SKILL/scripts/refs.py verify books/<book>/refs.json --write` resolves every DOI or ISBN, checks it against the entry, fills in the missing metadata and stamps `verified`. Fix every `FAIL`.
4. **Build.** `python SKILL/scripts/refs.py build books/<book>/refs.json site/<book>/refs.js`. Chapters and the contents page load it. The book's separate References view (linked from the end of the contents) lists every work, and each chapter's finish card lists the sources that chapter cites.
5. **Draw.** `cite(p, key, { x, y, size, fill, anchor, weight, o: 0 })` draws the label as an underlined link and returns it, ready for `show()`/`tw()` like `T`. `str` overrides the label (e.g. `'(1987)'` after a name drawn separately). Clicking a citation opens the source in a new tab and pauses the lesson. Faded-out links take no clicks or Tab focus. A work discussed but not drawn goes in `CHAPTER.refs` so the finish card still lists it.

Never put a citation inside a long `T` sentence. Draw it with `cite()` next to the text it supports, so the link is a separate target of at least 24 px text height.
