# Quality Gates

Use these gates before any final recommendation or publish-ready copy.

## Gate 1: Evidence Integrity (Mandatory)

Pass criteria:

- Every strategic claim maps to evidence in `research/` files.
- Time-sensitive claims include date context.
- No fabricated metrics, testimonials, or case studies.

Fail examples:

- "Best in class" without benchmark.
- Revenue or conversion claims without source.
- Generic customer pain assumptions without VOC proof.

## Gate 2: Positioning Contrast (Mandatory)

Pass criteria:

- Chosen angle clearly differs from direct competitors.
- Buyer can explain "why this vs alternative" in one sentence.
- Angle is usable across landing, email, and distribution.

## Gate 3: Voice Consistency (Mandatory)

Pass criteria:

- Copy follows `strategy/voice-profile.md`.
- Avoid list is respected.
- Tone is stable across sections/channels.

## Gate 4: Funnel Clarity (Mandatory)

Pass criteria:

- Traffic source, offer, CTA, and next step are explicit.
- Each asset has one primary job and one primary action.
- Hand-off from content -> capture -> conversion is clear.

## Gate 5: Actionability (Mandatory)

Pass criteria:

- Recommendations are prioritized and sequenced.
- Owner, timeline, and expected impact are provided.
- Iteration backlog is concrete (not generic advice).

## Weighted Score Model

Score each initiative from 1-5:

- Impact (40%)
- Confidence (30%)
- Effort inverse (20%)
- Strategic Fit (10%)

Formula:

`priority_score = (impact*0.4) + (confidence*0.3) + ((6-effort)*0.2) + (fit*0.1)`

Interpretation:

- `>= 4.0`: execute now.
- `3.0-3.9`: queue for near-term sprint.
- `< 3.0`: deprioritize or redesign.

## Rejection Checklist

Reject and rewrite if any is true:

- Sounds interchangeable with generic AI copy.
- Uses hype language to replace proof.
- Lacks specific audience context.
- Doesn't identify tradeoffs or constraints.
- Cannot be implemented by a real team in the stated timeframe.

## Suggested Automation

Run quality checks with:

```bash
python3 scripts/quality_gate_check.py --workspace <project-path>
```

The checker validates:

- Required file presence.
- Hype/AI-tell phrase flags.
- Minimum source-link density in research files.
