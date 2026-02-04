# Bias Awareness Guide for Code Review

## Biases to Check

### 1. Position Bias
Tendency to favor the first (or last) item reviewed.

**Mitigation:** Review all files before scoring any. Do not assign scores while reading.

### 2. Verbosity Bias
Tendency to rate longer, more detailed code higher regardless of quality.

**Mitigation:** A shorter correct response scores equal to or higher than a longer correct response. Penalize padding and unnecessary repetition.

### 3. Self-Enhancement Bias
Tendency to prefer code that matches your own style or model family.

**Mitigation:** Score based on rubric criteria only. Ignore stylistic preferences not in the rubric.

### 4. Authority Bias
Tendency to rate code higher because it uses confident language or cites documentation.

**Mitigation:** Ignore citations and confident tone. Score based on whether the code works and reasoning is sound.

### 5. Format Bias
Tendency to score well-formatted code higher regardless of substance.

**Mitigation:** Formatting is not a scoring criterion. A correct answer in plain text scores the same as one with markdown formatting.

## Pre-Submission Checklist

Before submitting a review, verify:

- [ ] I scored based on rubric criteria, not gut feeling
- [ ] I did not equate length with quality
- [ ] I did not favor well-formatted code over correct code
- [ ] I was not swayed by confident comments or documentation references
- [ ] My first impression did not anchor all subsequent scores
- [ ] Each score has specific evidence from the code
