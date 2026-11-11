# Questions

## Choice questions: the mcq-item-writer skill

Every `choice` question is written with the **mcq-item-writer** skill (`MCQ`), never inline. Call it in Write mode as its *Calling this skill from another project* describes, with this brief:

```yaml
objectives: [the storyboard's objectives for this chapter]
source: books/<book>/pages/chNN/text.md
learner_level: <style.json book.readers>
purpose: learning            # both, if style.json questions.purpose says scores reach a gradebook (SCORM)
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

The chapter loads `<script src="items.js"></script>` right after `engine.js` and asks with `mcq('c-attrib')` inside `quiz(...)` ([API](#api)). To change a question, edit the bank and rebuild; never edit `items.js`. Items stay `draft` until the user approves the chapter.

## Other question types

The interactive types below carry no bank, but the same rules from `MCQ/references/` apply by judgment: the task is clear before acting (`writing-rules.md`), every clickable target or row is a plausible option with its own mistake-specific feedback (`learning-and-feedback.md`), no answer clues or trick wording (`technical-flaws.md`), and people in scenarios follow `people-in-scenarios.md`. A named person's own pronouns are fine.

Prefer a type that lets the student act on the picture itself (click the point, the cell, the step) over choosing text.

| Type | Use for |
| --- | --- |
| `choice` / `mcq` | One best answer from a few options, each wrong option with its own explanation; new questions come from the reviewed item bank via `mcq(id)` ([courses.md](courses.md)) |
| `blanks` | Typed numbers inside an expression; fractions and mixed numbers accepted; `test` judges a whole row (answers in any order) |
| `grid` | Several items, each classified (yes/no, which category, true/false) |
| `tap` / `tapEls` / `pickEls` | Click a point on the number line / a token in an expression / any drawn object |
| `pickPoint` | Choose a grid point on a coordinate plane (math.js) |
| `sorter` | Drag items into regions (the number-set diagram; math.js) |

New types are welcome when the content calls for one; each needs keyboard play.

## Writing them

- Ids: `c-…` for quick checks, `p-…` for practice; the score card adds them up.
- Vary the right option's position across a chapter's `choice` questions; a fixed position (always the first) becomes guessable.
- Prompts, feedback, `grid` text rows and `choice` options are rich text in HTML cards: a string is shown as written (`<` is a character, never markup, so `3 < 5` is safe), math goes in `$m(...)` ([maths.md](maths.md#math-parts)), and anything richer (a table) is an element made with `h()` and passed as a part.
- Feedback: right → `why` (and an animation via `fx`/`onRight`); wrong → a hint aimed at that mistake; after a wrong try, Show answer.
- Grade meaning: equal values match (6/8 = 3/4) unless the lowest form is asked for; sets and pairs in any order; no denominators of zero; never judge irrationality from finitely many digits.
- The built-in numeric parser compares exact integer products of safe-integer numerators and denominators; for answers outside that range, use a subject-specific input and grader rather than letting rounded values pass.
- Compose the question beat around its card so the picture it asks about stays visible (in the top 60 % above a `BAND` card, or beside a `{x, y, w, cls: 'side'}` card); `SCREEN` for practice.
- A card whose content is too long for `BAND` becomes several `blanks` rows in a wider side card.
- Units in typed answers: write the unit as a word after the box (`{ box: '60' }, ' kilograms'`) so it is not set as a math variable.

## API

```js
quiz(position, [{ id: 'c-mean', prompt: ['Find the mean of ', $m('7, 3, 9'), '.'], build: blanks([...]) }, …], done, 'Quick check')
```

- Positions: `BAND` (bottom band, y 686–886; long content can push it past the stage, so check it), `TOPR` (top right, ≤ 470 high), `RIGHT`, `SCREEN` (full-screen practice; the label names the set in the book's language, such as `'Chapter practice · set 1 of 2'`, and the engine appends "· question k of n" when a quiz has several questions), `SORT_SCREEN`, or any `{x, y, w, cls: 'side'}`.
- `choice(options, right, why, wrongWhys[], onRight?)` — number keys.
- `mcq(id, onRight?)` — ([courses.md](courses.md)) a whole quiz entry (`{id, prompt, build: choice(...)}`) from the chapter's item bank: `quiz(TOPR, [mcq('c-attrib'), mcq('c-cause')], done)`. Needs `items.js` (built by `scripts/items.py`) loaded after `engine.js`; an unknown id throws.
- `blanks(rows)` — rows `{parts: [..., {box: '21'}, ...], why, hint?, fx?, test?}`; accepts −5, 3/4, 2 1/4, 0.75 as exact values, also with a currency sign ($60, 5 €) and thousands grouped by spaces of any kind (1 250, as [authoring.md](authoring.md#content-rules) shows numbers) or, where the decimal sign is a point, by commas (1,250); `{box, lowest: true}` demands lowest terms; `test(values)` judges the whole row (e.g. two factors in either order). `hint` is one message for any wrong value in its row; when different mistakes need their own answers, split the step into rows or ask it as a `choice` with `wrongWhys`. Tab moves between boxes, Enter checks, Esc leaves a box.
- `grid(rows, cols, {multi, text})` — rows `{parts, ans: [keys], why, fx?}`, cols `[[key, label, colour?, hotkey?]]`. `multi` is true by default: a row may take several columns; give `{ multi: false }` when each row has one answer (one category per item). Without `text: true` a row's parts are set as maths; with it they are rich text (math via `$m`). ↑/↓ change rows.
- `tap(values, right, why, v => wrongWhy, onRight?)` points on the number line; `tapEls(row, idx, right, …)` tokens of a `tokens` row; `pickEls([{el, box: [x,y,w,h], label}], right, …)` any drawn objects; `pickPoint(P, [x,y], why, (x,y) => wrongWhy, onRight?, test?)` grid points (arrows + Enter or click); `sorter(items, trayXY)` drag into the set diagram (keys 1–6). `pickPoint` and `sorter` are in math.js.
- Answer animations run on their own clock: `fx`, `fxp`, `pulseFx`, `shakeFx`, `floatText`, `qlayer()` (a layer cleared with the question). They finish automatically when the beat is left; when a question beat is continued early, the engine finishes the beat's pending tweens first, so don't rely on half-finished fades.
- A new type: `build(body, api)` returns `{ reveal, check?, lock?, key?(e), hint? }` and calls `api.grade(ok, message, {right, total})`. `key` handles its shortcuts (return true when used); `hint` lists the keys under the prompt. Every action needs a key; the help overlay (`?`) lists the global ones.
- Scores: `SCORE[id]` keeps the first try across revisits and step jumps; restarting the chapter clears it. A multi-row question scores one per row. A correct retry changes the feedback, not the first-attempt score.
