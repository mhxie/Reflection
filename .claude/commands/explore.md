# Open Exploration

Free-form exploration session for when the user doesn't have a specific question — they just want to think. This is the "what's interesting?" command.

## Prerequisites

1. Read `profile/identity.md` for context.
2. Read the most recent reflection file from `zk/reflections/`.

## The Exploration Process

### Step 1: Cast a Wide Net

Run 3-4 diverse MCP searches to find surprising connections:

1. **Vector search on a recent theme:** `search_notes(query: "<topic from today's note>", searchType: "vector", limit: 10)` — semantic neighbors
2. **Random tag exploration:** `list_tags()` → pick a tag the user hasn't engaged with recently → `search_notes(query: "<tag>", limit: 5)`
3. **Time-shifted search:** `search_notes(query: "<current interest>", editedAfter: "<12 months ago>", editedBefore: "<6 months ago>", limit: 5)` — what were they thinking about this topic 6-12 months ago?
4. **Cross-domain search:** Search for a term from one life area in another. E.g., if career-focused recently, search for "health" or "learning" topics.

### Step 2: Surface the Surprising

From search results, identify:
- **Forgotten threads:** Notes the user wrote but probably forgot about
- **Unexpected connections:** Two notes from different domains that relate
- **Evolution:** How their thinking on a topic has changed over time
- **Gaps:** Areas of life with no recent notes (signal of avoidance or completion)

### Step 3: Present as Provocations

Don't summarize — provoke. Present 3-4 "sparks":

> **Spark 1: The Forgotten Thread**
> "Six months ago you wrote about [topic] in [[Note Title]]: '[quote]'. That connects to what you're doing now with [current focus]. Have you revisited this?"

> **Spark 2: The Cross-Domain Link**
> "Your [[Career Note]] mentions [concept]. Interestingly, your [[Personal Note]] from last month uses almost the same language about [different topic]. Is there a pattern here?"

> **Spark 3: The Evolution**
> "In [[Old Note]], you believed [X]. In [[Recent Note]], you're leaning toward [Y]. What shifted?"

> **Spark 4: The Silence**
> "I notice you haven't written about [topic] since [date]. Is that intentional, or has it slipped?"

### Step 4: Follow the Thread

Let the user pick which spark interests them. Then:
- Pull more related notes via vector search
- Apply a relevant framework if appropriate
- Ask deepening questions (use Challenger's question taxonomy)

## Output

**File:** `zk/reflections/YYYY-MM-DD-exploration.md`

```markdown
# Exploration — YYYY-MM-DD

## Sparks Surfaced
1. [Spark description] — [[Source Notes]]
2. [Spark description] — [[Source Notes]]
3. [Spark description] — [[Source Notes]]

## Thread Followed
[Which spark the user engaged with and what emerged]

## Connections Discovered
[New links between notes/ideas]

## Open Questions
[Questions that emerged but weren't resolved]

## Notes Referenced
[All [[Note Title]] links]

## Session Meta
- User engagement: high / medium / low
- Surprise factor: yes / no
```

## Write-Back

Optional: only if a genuine insight emerged. Before presenting the write-back, dispatch **Reviewer** + **Challenger** in parallel to verify citation accuracy and framing. **Write-backs are always in English.** Use a descriptive heading and the `#exploration` topic tag. **No provenance tag** (`#ai-reflection` is retired). Write-backs are alloy by default (see `protocols/epistemic-hygiene.md`); the descriptive heading is the duplicate-detection signal.
