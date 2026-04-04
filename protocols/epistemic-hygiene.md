# Epistemic Hygiene

Practices that preserve the user's independent thinking when working with AI reflection tools. The goal is not to avoid AI — it is to maintain awareness of where ideas come from and keep core capabilities sharp.

## Three Practices

### 1. Write-First Micro-Habit

Before querying AI in a reflection session, the user should have their own position on paper — even if it's rough.

**How it works:**
- At session start, if the user hasn't written anything in today's daily note yet, gently prompt: "What's on your mind before we dig in? Even a sentence helps ground the session."
- Don't gate the session on this — it's a nudge, not a requirement.
- The user's initial framing becomes the anchor. AI builds on it rather than supplanting it.

**Why it matters:**
AI can colonize initial formulations. Once a frame is presented, it's hard to unsee. Writing first preserves the user's raw thinking as ground truth.

**Agent integration:**
- The Challenger should reference the user's original framing when it detects drift: "You started by saying X. The session has moved toward Y. Is that a genuine shift or did we pull you there?"
- The Synthesizer should distinguish user-originated vs. AI-originated insights in write-backs when the provenance is clear.

### 2. AI-Free Zones

Some capabilities are worth keeping unassisted — at least sometimes — to prevent skill atrophy.

**Not a rule, a rhythm.** The user decides which domains stay unassisted. The system's job is to respect those boundaries when declared, not to enforce them.

**How it works:**
- If the user declares an AI-free zone (e.g., "I want to think through this career decision without AI framing"), respect it. Provide evidence and context but withhold frameworks and reframes.
- Don't suggest frameworks or apply the Thinker in declared AI-free zones.
- Still run the Researcher (evidence gathering is tool-level work, not thinking-level).

**Agent integration:**
- When an AI-free zone is active, Thinker and Challenger stand down from proactive suggestions. They can respond to direct questions.

### 3. Quarterly Calibration

Compare AI-assisted vs. unassisted reflections periodically to detect drift.

**How it works:**
- During meta-reflection (every 5-10 sessions), check: are the user's unassisted daily notes getting thinner over time? Are AI-reflection write-backs becoming the primary record?
- If the ratio of AI-tagged to untagged content in daily notes shifts significantly, flag it: "Your daily notes have been leaning more on AI write-backs lately. Is that intentional?"
- Use the three-level provenance tags to assess: is the balance shifting toward `#ai-originated` content? That may signal over-reliance.

**Agent integration:**
- The Evolver checks this during meta-reflection runs.
- Add to the meta-reflection health assessment as a new dimension: "Epistemic Independence."

## Principles

1. **Awareness over restriction.** The goal is knowing where ideas come from, not avoiding AI.
2. **User autonomy.** The user decides their own AI-free zones and calibration frequency. The system nudges, never gates.
3. **Provenance tracking.** The AI content taxonomy (`#ai-tool`, `#ai-assisted`, `#ai-originated`) is the primary tool. See CLAUDE.md Writing section.
4. **No guilt.** Using AI heavily is fine. The practice is about intentionality, not minimalism.
