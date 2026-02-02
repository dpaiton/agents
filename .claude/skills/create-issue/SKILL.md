# Create Issue Skill

Create standardized GitHub issues for the agents repository.

## Before You Write

**Clear Thinking First (P3):** Before creating an issue, answer these questions:
1. What is the user's actual goal? (P1: User Centricity)
2. Can this be solved with code or CLI instead of an agent task? (P11: Goal → Code → CLI → Prompts → Agents)
3. What does "done" look like? (P7: Spec / Test / Evals First)
4. What should be measured to verify success? (P15: Science as Meta-Loop)

## Usage

Invoke this skill to create a new GitHub issue with consistent formatting and labeling.

## Title Conventions

Every issue title MUST begin with one of these prefixes:

- `[Feature]` — New functionality
- `[Bug]` — Bug fix
- `[Test]` — Test-only changes
- `[Infrastructure]` — Repo setup, CI, tooling
- `[Docs]` — Documentation
- `[Epic]` — High-level tracking issue containing child issues

Prefixes can be combined: `[Epic] [Placeholder] Web Platform`

## Labels

Apply one or more of these labels to every issue:

| Label | Use when |
|---|---|
| `epic` | Issue is a top-level tracking epic |
| `infrastructure` | Repo structure, CI, tooling |
| `evaluation` | LLM-as-judge evaluation framework |
| `orchestration` | Multi-agent orchestration and routing |
| `agent` | Agent definitions and configuration |
| `tdd` | Test-driven development workflow |
| `placeholder` | Future work, not yet actionable |
| `priority:high` | Must be done first |
| `priority:medium` | Important but not blocking |
| `priority:low` | Nice to have |

## Body Template

Use this template for the issue body (omit sections that don't apply):

```markdown
## Summary
<!-- 1-3 sentences describing the issue. Start with the user goal (P1). -->

## Acceptance Criteria
<!-- Measurable criteria. What does "done" look like? (P7: Spec/Test/Evals First) -->
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Verification
<!-- How will you measure success? (P15: Science as Meta-Loop) -->
<!-- What command(s) prove this works? (P10: CLI as Interface) -->

## Technical Notes
<!-- Implementation details, constraints, references -->
<!-- Apply decision hierarchy: code > CLI > prompts > agents (P11) -->

## Design Principles
<!-- Which of the 16 principles apply and how? List 2-4 most relevant. -->

## Agent Assignment
<!-- Which agent(s) should work on this: orchestrator, engineer, test-writer, reviewer, issue-creator, judge -->
```

## How to Create

Use `gh issue create` via Bash:

```bash
gh issue create \
  --title "[Prefix] Title here" \
  --label "label1,label2" \
  --body "$(cat <<'EOF'
## Summary
...

## Acceptance Criteria
- [ ] ...

## Technical Notes
...

## Agent Assignment
...
EOF
)"
```

## Guidelines

1. **Clear Thinking First** — Clarify the problem before writing the issue (P3)
2. Every issue needs at least one measurable acceptance criterion (P7)
3. Include a Verification section — how do you prove it works? (P15)
4. Each issue should do one thing well (P8: UNIX Philosophy)
5. Prefer deterministic solutions: code > CLI > prompts > agents (P5, P11)
6. Epics list child issues with checkboxes; child issues link back to parent
7. Assign agent roles when the responsible agent is known (P14)
8. Apply priority labels to non-epic issues
9. Agents must be allowed to say "I don't know" or "this needs human input" (P16)
