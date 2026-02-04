# Write Tests

## Purpose
Author test cases following TDD methodology — tests are written before implementation exists, defining expected behavior as executable specifications.

## When to Use
- Before implementing a new feature (TDD red phase)
- Before fixing a bug (write a regression test that reproduces it)
- When a spec or acceptance criteria needs to be encoded as tests

## Inputs
- Issue specification with acceptance criteria
- Existing codebase interfaces (function signatures, class APIs)
- Test framework conventions from the project

## Steps

### 1. Read the spec (P7: Spec First)
Understand what "done" means before writing a single test. Each acceptance criterion becomes at least one test.

### 2. Identify test categories
For each feature or behavior, plan tests in three categories:
- **Happy path**: the standard, expected use case
- **Edge cases**: boundary values, empty inputs, large inputs, special characters
- **Error cases**: invalid inputs, missing resources, permission errors, malformed data

### 3. Write test names first
Write descriptive test names before test bodies. Names should describe the expected behavior:
- `test_parse_config_returns_dict_for_valid_toml`
- `test_parse_config_raises_error_for_missing_file`
- `test_parse_config_handles_empty_file`

### 4. Write test bodies
Each test follows the Arrange-Act-Assert pattern:
1. **Arrange**: set up inputs and expected outputs
2. **Act**: call the function/method under test
3. **Assert**: verify the result matches expectations

### 5. Verify tests fail (red phase)
Run the tests. They MUST fail because implementation does not yet exist. If tests pass without implementation, they are testing nothing.

### 6. Commit failing tests
Commit the tests on a branch. The failing tests ARE the spec for the engineer.

## Outputs
- Test files following project conventions (`test_*.py`)
- All tests failing (red phase confirmed)
- Each acceptance criterion covered by at least one test

## Principles
- **P7 Spec / Test / Evals First** — Tests define "done." They exist before code.
- **P8 UNIX Philosophy** — This skill only writes tests. It does not implement.
- **P16 Permission to Fail** — If the expected behavior is unclear, ask rather than encode a wrong assumption.
