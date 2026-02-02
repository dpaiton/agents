# Create Issue Skill

Create standardized GitHub issues for the agents repository.

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
<!-- 1-3 sentences describing the issue -->

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
<!-- Implementation details, constraints, references -->

## Agent Assignment
<!-- Which agent(s) should work on this: orchestrator, engineer, test-writer, reviewer, issue-creator, judge -->

## Labels
<!-- List applied labels -->
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

1. Titles should be concise and descriptive
2. Every issue needs at least one acceptance criterion
3. Epics should list child issues with checkboxes
4. Assign agent roles when the responsible agent is known
5. Apply priority labels to non-epic issues
6. Link related issues using `#N` references
