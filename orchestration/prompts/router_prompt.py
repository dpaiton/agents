"""Prompt templates for the router agent.

These prompts support task classification and decomposition. The classify
prompt is a fallback for when pattern matching fails (P6) - most classification
should happen in code. All prompts require reasoning first (P3) and allow
uncertainty (P16).
"""


def classify_task_prompt(task_description: str) -> str:
    """Generate a prompt to classify an ambiguous task.

    This is a fallback for when deterministic pattern matching fails.
    Most task classification should happen in code (P6); this prompt
    only fires when pattern matching returns 'unknown'.

    Args:
        task_description: The description of the task to classify.

    Returns:
        A formatted prompt string for task classification.
    """
    return f"""You are a task classification agent. Your job is to categorize an ambiguous task into one of the predefined categories.

## Task Description
{task_description}

## Available Categories

- **code_change**: Tasks requiring modifications to source code (features, bug fixes, refactoring)
- **code_review**: Tasks requiring review of existing code or pull requests
- **documentation**: Tasks requiring creation or modification of documentation
- **testing**: Tasks focused on writing, modifying, or running tests
- **infrastructure**: Tasks related to CI/CD, deployment, or tooling configuration
- **research**: Tasks requiring investigation, analysis, or information gathering
- **unknown**: Use ONLY if the task genuinely does not fit any category above

## Instructions

1. **Analyze the task**: Read the task description carefully and identify key indicators.
2. **Reason before classifying**: Explain your reasoning process:
   - What keywords or phrases suggest certain categories?
   - What is the primary goal of the task?
   - Are there secondary aspects that suggest other categories?
3. **Classify**: Only after reasoning, provide your classification.

## Uncertainty Guidance

If the task could reasonably fit multiple categories:
- Identify the PRIMARY category based on the main goal
- Note secondary categories if applicable
- If genuinely ambiguous, explain why and suggest requesting clarification

If you cannot confidently classify the task, use 'unknown' and explain what additional information would help.

## Output Format

### Reasoning
[Your analysis of the task and reasoning for classification]

### Uncertainty (if any)
[Any ambiguity or alternative interpretations]

### Classification
Primary: [category]
Secondary (if applicable): [category]
Confidence: [high/medium/low]
"""


def decompose_task_prompt(task_description: str) -> str:
    """Generate a prompt to break a complex task into subtasks.

    Args:
        task_description: The description of the complex task to decompose.

    Returns:
        A formatted prompt string for task decomposition.
    """
    return f"""You are a task decomposition agent. Your job is to break a complex task into manageable subtasks that can be executed independently or in sequence.

## Task Description
{task_description}

## Instructions

1. **Understand the task**: Identify the overall goal and scope of the task.
2. **Identify components**: Break down the task into logical components.
3. **Reason about dependencies**: Think through:
   - Which subtasks can be done in parallel?
   - Which subtasks depend on others?
   - What is the optimal ordering?
4. **Define subtasks**: Only after reasoning, list the subtasks with clear descriptions.

## Subtask Guidelines

Each subtask should:
- Be independently executable or have clear dependencies noted
- Have a clear, measurable completion criterion
- Be appropriately sized (not too large, not too granular)
- Include any context needed for execution

## Uncertainty Guidance

If you are uncertain about the decomposition:
- Note which aspects of the task are unclear
- Suggest what clarification would help
- Provide your best decomposition while flagging uncertain parts

It is better to acknowledge "This subtask may need further breakdown once X is clarified" than to guess incorrectly.

## Output Format

### Task Analysis
[Your understanding of the overall task and its scope]

### Reasoning
[Your thought process for breaking down the task]

### Uncertainty (if any)
[Any aspects that are unclear or assumptions you made]

### Subtasks

1. **[Subtask Title]**
   - Description: [What needs to be done]
   - Dependencies: [None / Subtask numbers this depends on]
   - Completion Criterion: [How to verify this is done]

2. **[Subtask Title]**
   - Description: [What needs to be done]
   - Dependencies: [None / Subtask numbers this depends on]
   - Completion Criterion: [How to verify this is done]

[Continue as needed...]

### Execution Order
[Suggested order or parallel execution groups]
"""
