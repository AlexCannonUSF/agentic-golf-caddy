# Agentic Golf Caddy — 5-min talk script (Group 28, Alex Cannon)

Total budget: 5 min talk + 2 min Q&A. 11 slides → ~27 sec each.
Don't read this verbatim — practice once, then talk it through.

---

## Slide 1 — Title (15s)
"Hi, I'm Alex Cannon, Group 28. My final project is the Agentic Golf
Caddy — a 7-agent system that combines real golf math with an LLM kept on
a tight leash, so the recommendations it gives you are actually
trustworthy."

## Slide 2 — Motivation (30s)
"Every golf shot is a small puzzle. You're juggling distance, wind,
elevation, the lie, hazards, the pin — plus your own tendencies — and you
have about a minute to decide. Today's tools force a trade-off:
rangefinders give a number with no reasoning, and AI caddies sound smart
but make up yardages and don't know what's in your bag. I wanted both —
accuracy and reasoning."

## Slide 3 — Related work (30s)
"Three buckets of prior work. GPS rangefinders are accurate but offer no
reasoning. AI caddies are conversational but hallucinate. And generic
multi-agent frameworks like AutoGen and ReAct give you templates but no
domain math, no fact-checking, and no safety rules. The gap nobody fills:
real golf math plus an LLM kept on a tight leash and double-checked
afterwards — for the same shot."

## Slide 4 — Challenges (25s)
"Five concrete things had to work: stop hallucination by limiting the LLM
to clubs that are in your bag; ask follow-ups only when they'd change the
answer; safety rules for bunkers and deep rough; personalize to each
golfer; and prove it works without a public benchmark. The principle is
simple: do the math the same way every time, then double-check what the
LLM says."

## Slide 5 — Solution / architecture (40s)
"Seven agents in a pipeline. Yellow boxes are bounded LLM steps; dark
green is math; light green is real-world data; mid green is logic
guardrails. A free-text shot goes through the Input Interpreter, then
Clarification decides if a follow-up is needed. Context pulls live
weather. The Decision agent is pure math — works out how far the shot
plays and gives a 3-to-5-club shortlist. Adaptive Strategy lets the LLM
re-rank that shortlist, but it can never invent a club. Coach explains
the result. Verifier fact-checks every number."

## Slide 6 — Agent roles (25s)
"Every agent has one job and a strict input/output contract. The math
agents set the rules of what's correct; the LLM agents only get to play
inside those rules. Clarification only asks a follow-up if two clubs are
within 20 yards of each other."

## Slide 7 — Contribution + tech stack (30s)
"Solo group, so I owned all of it: the 7-agent pipeline, the math
engine, real-world data integration, profile importers for TrackMan,
Foresight, and Golf Pad, the test harness, and the Streamlit app. Tech
stack: Python 3.10 with Pydantic data contracts; OpenAI gpt-4o-mini
powers the three LLM agents; Streamlit for the UI; live data from
Open-Meteo, USGS, and OSM Overpass; pytest for ~30 unit and scenario
tests. Roughly 3,000 lines of Python."

## Slide 8 — Demo mockup (35s)
"Here's the end-to-end flow. The user types: '145 out, into the wind ~12,
ball sitting down a little, back pin, just middle of the green.' The
Interpreter pulls 5 details — none unclear. Clarification stays quiet.
Context pulls live wind. The math says the shot plays like 162 yards;
shortlist is 8-iron, 9-iron, 7-iron — these numbers are using the
TrackMan PGA Tour Average 2024 profile. Adaptive Strategy keeps the
8-iron and flags that a long miss leaves a tough chip. Coach writes the
explanation. Verifier checks every number."

## Slide 9 — Evaluation (35s)
"Real-run logging captured 1,021 shots through the system. Across all 927
that completed, the verifier never had to rewrite — that's 100% grounded.
The system only asked a follow-up question 9% of the time, and only when
it really mattered. 17% of inputs came in as plain English. The Adaptive
Strategy agent surfaced risk flags 258 times — including 4 cases where it
overrode the math to block a bad-lie carry."

## Slide 10 — Live demo video (35s)
"And here it is for real. Same flow as the mockup — TrackMan PGA Tour
profile, free-text shot, the system parses the conditions, runs the
pipeline, and gives a recommendation with a backup club and a one-line
explanation. The video plays on click."
[Click the video to play it. Optionally narrate over: "watch the parsed
fields populate", "now the recommendation banner", "and there's the
explanation".]

## Slide 11 — Closing (20s)
"Takeaway: when the answer has to be right, small specialized agents
beat one big LLM. Future work includes lie detection from a phone photo
and a hands-free voice interface. Thank you — happy to take questions."

---

## Likely Q&A (have answers ready)

- **"Why not just fine-tune one LLM?"** — Even a fine-tuned model
  hallucinates on numeric tasks under distribution shift. Splitting math
  out gives provable correctness on the part that matters most.
- **"How do you measure 'grounded'?"** — The Verifier checks that every
  numeric claim in the explanation maps to a value in the decision data
  (club, plays-like distance, adjustments, backup). If not, it swaps in
  a deterministic template.
- **"Where's the LLM creativity?"** — In re-ranking the shortlist using
  hazard / lie / history context, and in writing the explanation. Both
  are bounded by structured inputs.
- **"What model are you using?"** — OpenAI gpt-4o-mini, with all prompts
  versioned in `prompts/`. The pipeline falls back to a deterministic
  template if the API is unavailable, so it never blocks the user.
- **"Cold-start for a new player?"** — Use one of the built-in benchmark
  profiles (PGA / LPGA / Shot Scope handicap buckets); tendencies are
  learned from feedback over time.
- **"Latency?"** — Math core is sub-millisecond; full pipeline including
  LLM calls runs in single-digit seconds.
