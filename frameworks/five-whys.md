# Five Whys

Origin: Taiichi Ohno (Toyota Production System). A root cause analysis technique that drills past symptoms to find the real problem.

## When to Use

- A problem keeps recurring despite fixes
- You're about to solve something but aren't sure it's the real issue
- Surface explanation feels too simple
- Post-mortem on a failure or mistake

## The Process

### Step 1: State the problem clearly
Be specific. Not "things aren't going well" but "I haven't made progress on my learning goal in 6 weeks."

### Step 2: Ask "Why?" five times
Each answer becomes the subject of the next "Why?"

```
Problem: I haven't made progress on my learning goal in 6 weeks.
Why? → I haven't set aside time for it.
Why? → Work has been consuming all my energy.
Why? → I've been saying yes to every request.
Why? → I'm afraid of looking uncommitted during my first months.
Why? → I believe my value is measured by visible output, not by growth.
```

### Step 3: Identify the root cause
The fifth "why" usually reveals a belief, system, or constraint — not a surface behavior.

### Step 4: Address the root cause
Fix at the deepest level you can influence. In the example above:
- Surface fix: "Block time for learning" (will fail again)
- Root fix: "Redefine what 'commitment' means to include growth" (changes the pattern)

## Rules

1. **Each "why" must be factual**, not speculative. If you don't know, investigate.
2. **Don't blame people** — blame systems and incentives.
3. **You don't always need exactly 5.** Stop when you hit a root you can act on.
4. **Multiple branches are okay.** Some "whys" have multiple valid answers — follow each branch.

## Branch Example

```
Problem: I feel stuck in my career.
Why? → I'm not learning new things.
  Why? → I don't have time.
    Why? → I'm doing too much operational work.
Why? → I'm not getting interesting projects.
  Why? → I haven't built relationships with decision-makers.
    Why? → I avoid networking because it feels inauthentic.
```

Two different root causes from the same problem — both worth addressing.

## Pitfalls

- **Stopping too early**: The first or second "why" is almost never the root cause.
- **Circular reasoning**: "Why am I unproductive?" → "Because I procrastinate" → "Why?" → "Because I'm unproductive." Break the loop with specifics.
- **Blame path**: "Why did the deploy fail?" → "Because John didn't test it." Wrong. Ask why the system allowed that.

## Cross-validates with

- **Theory of Constraints** — Five Whys finds root cause; TOC finds the bottleneck in the system
- **Immunity to Change** — Five Whys may reveal hidden competing commitments at the root
