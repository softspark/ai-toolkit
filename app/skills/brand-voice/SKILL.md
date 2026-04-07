---
name: brand-voice
description: "Loaded when writing documentation, content, README, or user-facing text. Prevents generic LLM rhetoric and enforces direct, technical voice."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Brand Voice

Auto-loaded when writing documentation, content, or user-facing text. Enforces consistent, direct voice and eliminates LLM rhetoric.

## Anti-Trope List (Banned Phrases)

### Opening Tropes (Never Start With)

- "In today's fast-paced world..."
- "In the ever-evolving landscape of..."
- "Let's dive into..."
- "Let's explore..."
- "Welcome to this comprehensive guide..."
- "Are you looking for...?"
- "Whether you're a beginner or an expert..."

### Filler Adjectives (Remove or Replace)

| Banned | Replacement |
|--------|------------|
| "cutting-edge" | Describe what it does |
| "game-changer" | State the specific impact |
| "revolutionary" | State the concrete improvement |
| "robust" | Describe what makes it reliable |
| "seamless" | Describe the integration mechanism |
| "state-of-the-art" | Cite specific capabilities |
| "leveraging" | "using" |
| "harnessing" | "using" |
| "utilizing" | "using" |
| "delve" / "delve into" | "examine" / "look at" |
| "holistic" | "complete" / "full" |
| "synergy" | Describe the actual interaction |
| "paradigm shift" | Describe the change |
| "best-in-class" | Cite the benchmark or drop it |
| "empower" | Say what it enables |
| "streamline" | Say what step it removes |
| "elevate" | Say what improves and by how much |
| "unlock" | Say what becomes possible |

### Closing Tropes (Never End With)

- "Happy coding!"
- "And that's it! You're all set!"
- "I hope this helps!"
- "Feel free to reach out if you have any questions"
- "Now go build something amazing!"

### Structural Tropes

- Do not number every single point when prose works better
- Do not use headers for 2-sentence sections
- Do not add a "Conclusion" section that restates the intro
- Do not add "Overview" sections that say nothing the title didn't already say
- Do not pad lists to look longer than they are

## Voice Principles

| Principle | Rule |
|-----------|------|
| **Direct over diplomatic** | Say what you mean. "This function is slow" not "This function could potentially benefit from optimization." |
| **Specific over general** | Numbers, names, versions. "Reduces cold start by 40ms" not "Improves performance significantly." |
| **Evidence over assertion** | Show, don't tell. Include benchmarks, examples, or code. |
| **Short over long** | One sentence beats three. Cut filler words on every pass. |
| **Active over passive** | "The function returns X" not "X is returned by the function." |
| **Technical over casual** | Match the audience's expertise. Never dumb down for developers. |
| **Honest over promotional** | State limitations alongside strengths. |

## Sentence-Level Rules

- **Lead with the action or outcome**, not the context. Bad: "In order to configure X, you need to..." Good: "Configure X by..."
- **Cut weasel words**: "quite", "very", "really", "basically", "simply", "just", "actually", "arguably"
- **One idea per sentence.** If a sentence has "and" linking two distinct ideas, split it.
- **Use concrete subjects.** Bad: "It is important to note that..." Good: (delete the phrase, state the fact)

## Before Publishing Checklist

- [ ] No banned phrases from anti-trope list?
- [ ] Opening sentence provides value (not filler)?
- [ ] Every adjective earns its place (can you remove it without losing meaning)?
- [ ] No "comprehensive guide" or "complete overview" unless it truly is?
- [ ] Consistent terminology throughout?
- [ ] Active voice used by default?
- [ ] No weasel words remaining?
- [ ] Technical claims backed by evidence or examples?
