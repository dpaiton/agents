# Bias Awareness Guide for Evaluation

## Biases to Check During Evaluation

### 1. Position Bias
Tendency to favor the response that appears first in a pairwise comparison.

**Mitigation:** Always run pairwise evaluations twice with swapped positions. If the winner changes, flag as unstable and default to tie.

**Detection:** Track positional agreement rate. If below 85%, revise the judge prompt.

### 2. Verbosity Bias
Tendency to prefer longer responses over shorter ones, regardless of quality.

**Mitigation:** The judge prompt must state: "A shorter correct response scores higher than a longer response with unnecessary detail." Track length-score correlation; if Pearson r > 0.5, flag verbosity bias.

### 3. Self-Enhancement Bias
Tendency of an LLM judge to prefer outputs from its own model family.

**Mitigation:** Blind the judge to model identity. Use neutral labels (Response A, Response B). Strip model-identifying artifacts. When feasible, use a different model family for judging than for generation.

### 4. Authority Bias
Tendency to rate responses higher because they use confident language or cite sources.

**Mitigation:** The judge prompt must state: "Ignore citations and confident tone. Score based on correctness and reasoning." Test with planted authority examples (confident-but-wrong vs. hedging-but-correct).

### 5. Format Bias
Tendency to score well-formatted responses higher regardless of substance.

**Mitigation:** The judge prompt must state: "Formatting is not a scoring criterion." Include calibration examples with minimal formatting that score high and heavy formatting that scores low.

## Pre-Evaluation Checklist

Before finalizing any evaluation:

- [ ] Pairwise evaluations used A/B order swapping
- [ ] Judge prompt instructs "evaluate substance, not length"
- [ ] Model identity stripped from all inputs
- [ ] Judge prompt instructs to ignore authoritative language
- [ ] Judge prompt instructs to ignore formatting quality
- [ ] Calibration examples include short/high-score and long/low-score pairs
