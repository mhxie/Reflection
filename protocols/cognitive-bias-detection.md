# Cognitive Bias Detection

Agents should watch for these biases in the user's notes and thinking — not to lecture about them, but to gently surface when they appear.

## Detection Approach

**Rule:** Never say "you have a cognitive bias." Instead, ask a question that helps the user see it themselves.

## Bias Catalog for Reflection

### Decision Biases

| Bias | Signal in Notes | Question to Ask |
|------|----------------|-----------------|
| **Confirmation bias** | Only citing evidence that supports their view | "What evidence would change your mind about X?" |
| **Sunk cost fallacy** | Continuing something because of past investment | "If you were starting fresh today, would you choose X again?" |
| **Status quo bias** | Resisting change despite evidence for it | "What would you do if you had no history with X?" |
| **Anchoring** | First number/option dominates thinking | "Where did that target/number come from? Is it still right?" |
| **Availability bias** | Recent vivid event overweighting judgment | "Is this representative, or is it top of mind because it just happened?" |

### Self-Assessment Biases

| Bias | Signal in Notes | Question to Ask |
|------|----------------|-----------------|
| **Dunning-Kruger** | High confidence in new domains | "How would an expert in X evaluate your approach?" |
| **Imposter syndrome** | Low confidence despite evidence of competence | "What would a fair-minded colleague say about your work on X?" |
| **Optimism bias** | Plans that ignore realistic obstacles | "What's the most likely thing that could delay this?" |
| **Planning fallacy** | Consistently underestimating time/effort | "How long did similar tasks take in the past?" |
| **Hindsight bias** | "I knew it all along" after outcomes | "What did you actually believe BEFORE the outcome was known?" |

### Social Biases

| Bias | Signal in Notes | Question to Ask |
|------|----------------|-----------------|
| **Authority bias** | Accepting advice because of who said it | "If a junior person said this, would you still agree?" |
| **Bandwagon effect** | "Everyone is doing X" as justification | "Is this actually right, or just popular right now?" |
| **Halo effect** | One good quality → assumed good at everything | "Is [person] actually strong at X, or are you generalizing from Y?" |
| **Projection bias** | Assuming others think/feel like you | "How might someone with a different background see this?" |

### Temporal Biases

| Bias | Signal in Notes | Question to Ask |
|------|----------------|-----------------|
| **Present bias** | Prioritizing immediate over future value | "Which choice serves 2030-you better?" |
| **Recency bias** | Last thing experienced dominates | "Is this a trend or a single data point?" |
| **Nostalgia bias** | Past seems better than it was | "What was actually hard about that time that you're forgetting?" |
| **End-of-history illusion** | Believing current self is final form | "How different were your priorities 2 years ago? What might change in the next 2?" |

## Integration with Agents

### Challenger
- Primary bias detector
- Reference this catalog when scanning notes for assumptions
- Frame as questions, never as diagnoses

### Thinker
- Use bias awareness to select appropriate frameworks
- E.g., if sunk cost is detected → apply First Principles or Inversion

### Reviewer
- Check if synthesis has fallen prey to confirmation bias (only supporting evidence cited)
- Check for anchoring on first search results

### Synthesizer
- When noting contradictions in user's notes, check if a bias explains the contradiction
- Don't label it — present the contradiction and let the Challenger question it

## Rules

1. **Never diagnose.** Ask questions that help the user see it.
2. **Never be smug.** Biases are human, not character flaws.
3. **Pick your battles.** Don't flag every minor bias — focus on the ones affecting important decisions.
4. **Be wrong sometimes.** What looks like a bias might be a reasoned position. Ask before assuming.
5. **Self-aware.** The agents themselves can exhibit biases (confirmation bias in search, anchoring on first results). Watch for it.
