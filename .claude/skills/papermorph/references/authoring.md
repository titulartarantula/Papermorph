# Authoring a chapter

## Shape

Chapters have run 5–18 minutes with 5–40 second beats; a long chapter can hold several parts (each a short title beat, lessons, a quick check and a wrap). Let the content determine length and the number of checks/practice sets.

| Beat | Purpose |
| --- | --- |
| `intro` | Title card (unit and chapter number, title, one line of purpose). |
| lesson beats | One idea each, built up in the picture while the narration explains it. |
| `q1`, `q2`, … | A check of already taught content, separated from the next check by a lesson beat. |
| `wrap` | Three or four numbered takeaways. |
| `final1` … | Full-screen practice covering the whole chapter. With several sets, label them like `'Chapter practice, set 1 of 2 · question'` (the engine appends "k of n"). |
| `finish` | Score card (`finishCard`): first-try results for quick checks and practice. |

Beat ids are shared by the page (`BEATS`) and the narration file; a beat with `ask` waits for the answers before moving on.

## Beats

Before writing code, write the chapter's objectives (three to five things the reader can do afterwards: "classify a thought by theme", "predict which explanation keeps a learner trying"); every question tests one of them. Then list the beats. For each lesson beat decide what the eye should watch and what changes; why that change is true (the animation is the argument); which words trigger which actions (these become `[[marks]]`); what text appears, beside the thing it names; and what carries over from the previous beat. Then lay out the key moments as pictures (storyboard): [diagrams.md](diagrams.md) and [scenes.md](scenes.md).

- **Open on the subject.** When a beat clears the picture, the new topic appears right away; labels and steps follow the words. Short pauses for thought are fine.
- **One new thing at a time**, and **the same colour means the same thing** across the chapter and, where it fits, the book.
- **Teach the chapter's scope**, choosing sections by idea; note any reordering in `chapters/chNN.md`.

## Narration

`content/<book>/chNN/narration.<lang>.json` (English example):

```json
{ "voice": "en-US-AndrewNeural", "rate": "-4%",
  "beats": { "intro": "Chapter five. [[sub]]Subtraction undoes addition.", "...": "..." } }
```

- `[[name]]` goes right before the word an action waits for; `m('name', offset)` in the page returns when that word starts. Names are unique within a beat; a misspelt mark makes the page throw, and a mark that matches no spoken word makes `tts.py` stop.
- Write for the ear: short sentences, one idea each. Say symbols and units in words ("negative seven halves", "meters per second squared"); the picture shows the symbols.
- Match the audience: plain, warm, never childish. Explain why, not only how.
- Question beats get one short line ("Quick check. Find the mean."); the card holds the question.
- `tts.py` writes `<beat>.mp3` and `timings.js` (duration, marks, captions) and caches each finished beat beside the narration JSON: moving `[[marks]]` reuses the cache, and after a failure the same command resumes rather than starting over. It takes a few seconds a beat, so a long chapter can outlast a tool's foreground time limit: run it in the background and wait for it before `lint.py`.
- Engine: `"engine": "edge"` (default, online), `"kokoro"` (local, Apache 2.0; English word timings; voices such as `am_michael`, `af_heart`, `bm_george`) or `"elevenlabs"` (below), set at the top of the narration file with `voice` and `rate`. Keep one engine and voice per book, recorded in `style.json` `voice`. Edge's `...MultilingualNeural` voices guess the language sentence by sentence and read a short line such as "No zero, no fractions, no negatives." with a Spanish or Portuguese accent; a book in one language uses a one-language voice of that language.
- Respell for the voice with `{{shown|spoken}}` (e.g. `{{honne|honneh}}`): the voice reads `spoken`, captions show `shown`. The spoken text keys the audio cache, so wrapping an already-synthesized respelling costs nothing.

ElevenLabs, when the user names an ElevenLabs voice for the book (`style.json` `voice`; every chapter of a book uses the same voice). `tts.py` calls the ElevenLabs API directly with the user's key; `eleven.py` (documentaries) goes through OpenRouter instead:

```json
{ "engine": "elevenlabs", "voice": "<voice id>", "model": "eleven_v4",
  "settings": { "speed": 0.96 }, "beats": { "...": "..." } }
```

- Model: `eleven_v4` for every ElevenLabs book (user decision, 2026-10-10). Books narrated earlier keep the model named in their narration files; changing it re-synthesises every chapter. Older narration files that say `"provider": "elevenlabs"` still work.
- The API key comes from `ELEVENLABS_API_KEY` or a `.env` file in the project root (git-ignored). Never put the key in a narration file, `style.json` or the site. It is a secret starting with `sk_`; a 64-character hex string is a key ID and is rejected.
- Same command (`uv run --with edge-tts … tts.py …`); the script needs no extra package for ElevenLabs. Word times come from the API's character alignment, so marks and captions work as with Edge.
- ElevenLabs bills per character. Tell the user the chapter's character count before the first synthesis of a book; afterwards only changed beats are re-synthesised. A voice, model or settings change re-synthesises the whole chapter.
- Pacing differs from Edge: check marks land on the intended words in the delivery pass.

## Questions

### Choice questions: the mcq-item-writer skill

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

The chapter loads `<script src="items.js"></script>` right after `engine.js` and asks with `mcq('c-attrib')` inside `quiz(...)` (engine.md). To change a question, edit the bank and rebuild; never edit `items.js`. Items stay `draft` until the user approves the chapter.

### Other question types

The interactive types below carry no bank, but the same rules from `MCQ/references/` apply by judgment: the task is clear before acting (`writing-rules.md`), every clickable target or row is a plausible option with its own mistake-specific feedback (`learning-and-feedback.md`), no answer clues or trick wording (`technical-flaws.md`), and people in scenarios follow `people-in-scenarios.md`. A named person's own pronouns are fine.

Pick the type that lets the student act on the picture itself whenever possible (click the point, the cell, the step) rather than choosing text.

| Type | Use for |
| --- | --- |
| `choice` / `mcq` | One best answer from a few options, each wrong option with its own explanation; new questions come from the reviewed item bank via `mcq(id)` ([courses.md](courses.md)) |
| `blanks` | Typed numbers inside an expression; fractions and mixed numbers accepted; `test` judges a whole row (answers in any order) |
| `grid` | Several items, each classified (yes/no, which category, true/false) |
| `tap` / `tapEls` / `pickEls` | Click a point on the number line / a token in an expression / any drawn object |
| `pickPoint` | Choose a grid point on a coordinate plane (math.js) |
| `sorter` | Drag items into regions (the number-set diagram; math.js) |

New types are welcome when the content calls for one; each needs keyboard play (see engine.md).

- Ids: `c-…` for quick checks, `p-…` for practice; the score card adds them up.
- The prompt is rich text ([engine.md](engine.md#traps)).
- Vary the right option's position across a chapter's `choice` questions; a fixed position (always the first) becomes guessable.
- Feedback: right → `why` (and an animation via `fx`/`onRight`); wrong → a hint aimed at that mistake; after a wrong try, Show answer.
- Grade meaning: equal values match (6/8 = 3/4) unless the lowest form is asked for; sets and pairs in any order; no denominators of zero; never judge irrationality from finitely many digits.
- The built-in numeric parser uses safe integer numerators and denominators and exact integer products for equality. For answers outside that range, use a subject-specific input and grader rather than allowing rounded values to pass.
- Compose the question beat for its card: the picture the question is about stays visible (for example in the top 60 % with a `BAND` card below, or beside a `{x, y, w, cls: 'side'}` card); `SCREEN` for practice.
- Units in typed answers: write the unit as a word after the box (`{ box: '60' }, ' kilograms'`) so it is not set as a math variable.

## Content rules

- Follow the agreed chapter scope and order. Verify facts, calculations and answers actually used in the finished lesson; correct or replace source errors and note them in `books/<book>/chapters/chNN.md` for the user.
- Check worked examples as the subject, not only as arithmetic (a push on someone standing on the ground is not the net force).
- Use the notation and rounding in `style.json` (`look.notation`). Record new shared decisions there. Group thousands with a no-break space (U+00A0) or the book's comma: a thin space all but vanishes in bold system fonts (150 000 000 read as 150000000).
- Colours follow [palette.md](palette.md): `COL` names, text ≥ 4.5:1, `COL.board` text on accent fills, never colour alone.

## Citations

Every work named on screen (an author–year, a quoted study, a book title) is a live link to that work, from a verified list, never from memory: follow [courses.md](courses.md#citations) (list, find, verify, build, draw) for every book of this fork.
