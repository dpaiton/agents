# Unity Space Simulation - Project Epic

**Status:** Planning
**Created:** 2026-02-12
**Owner:** Main Orchestration System

---

## Overview

Build a 3D realistic space simulation game using Unity with a deterministic, LLM-orchestrated asset generation pipeline powered by Blender Python scripting and multi-agent coordination.

---

## Goals

1. **Establish reproducible asset pipeline** - Version-controlled, deterministic asset generation
2. **Create 4 specialized agents** - Visual Mock Generator, Geometry Agent, Validation Agent, World Integration Agent
3. **Set up development environment** - Unity, Blender, GitHub Actions CI/CD
4. **Generate first procedural assets** - Test pipeline with simple assets, scale to complex ships/stations
5. **Maintain quality standards** - Real-world scale, poly budgets, NASA-inspired realism

---

## Success Criteria

- [ ] All project documentation created (5 core docs + README)
- [ ] 4 new agent types defined and operational
- [ ] Blender headless pipeline working in CI/CD
- [ ] Unity project configured and accepting imports
- [ ] First test asset generated end-to-end (test cube)
- [ ] Validation system catching constraint violations
- [ ] Integration with main orchestration repo complete

---

## Project Structure

```
projects/unity-space-sim/
├── .claude/agents/          # 4 project-specific agents
├── assets/                  # Asset pipeline outputs
├── docs/                    # 5 core documentation files
├── scripts/                 # Python automation scripts
├── unity-project/           # Unity 2022.3 LTS project
├── .github/workflows/       # CI/CD automation
├── README.md               # Setup instructions
└── PROJECT_EPIC.md         # This file
```

---

## Phase Breakdown

### Phase 1: Foundation (Tasks 7-12, 23)

**Objective:** Create project structure, core documentation, and integrate with main repo.

**Tasks:**
- #7: Create project structure and documentation
- #8: Write PIPELINE_OVERVIEW.md
- #9: Write STYLE_GUIDE.md
- #10: Write VISUAL_PROMPT_GUIDE.md
- #11: Write GEOMETRY_PROMPT_GUIDE.md
- #12: Write VALIDATION_RULES.md
- #23: Update main repo CLAUDE.md

**Deliverables:**
- Complete directory structure
- 5 comprehensive documentation files
- Project README with installation instructions
- Integration with orchestration system

**Duration Estimate:** Foundation work

**Dependencies:** None (can start immediately)

---

### Phase 2: Blender Pipeline (Tasks 13-15, 17)

**Objective:** Build Blender asset generation and validation scripts.

**Tasks:**
- #13: Create test Blender Python script
- #14: Create asset generation script template
- #15: Create asset validation script
- #17: Create sample asset specification (test cube)

**Deliverables:**
- `scripts/test_blender.py` - Environment verification
- `scripts/generate_asset.py` - Generation template
- `scripts/validate_asset.py` - Validation automation
- `assets/specs/test_cube.json` - Sample specification
- `assets/prompts/geometry/test_cube_geometry_prompt.md`

**Duration Estimate:** Pipeline scripting

**Dependencies:** Phase 1 (requires documentation for reference)

---

### Phase 3: Unity Integration (Tasks 18-21)

**Objective:** Set up Unity project and integration scripts.

**Tasks:**
- #18: Create Unity project and configure settings
- #19: Create Unity AssetPostprocessor
- #20: Create Unity integration helper scripts
- #21: Create Unity AssetMetadata component

**Deliverables:**
- Unity 2022.3 LTS project configured
- `Assets/Editor/ModelImportSettings.cs`
- `Assets/Editor/LODConfigurator.cs`
- `Assets/Editor/ColliderGenerator.cs`
- `Assets/Editor/MaterialAssigner.cs`
- `Assets/Editor/PrefabCreator.cs`
- `Assets/Scripts/AssetMetadata.cs`

**Duration Estimate:** Unity setup and scripting

**Dependencies:** Phase 1 (requires documentation)

---

### Phase 4: CI/CD Automation (Task 16)

**Objective:** Automate asset pipeline with GitHub Actions.

**Tasks:**
- #16: Set up GitHub Actions workflow

**Deliverables:**
- `.github/workflows/asset-pipeline.yml`
- Automated Blender installation
- Automated validation and artifact upload
- Issue labeling based on validation results

**Duration Estimate:** CI/CD configuration

**Dependencies:** Phase 2 (requires scripts to run)

---

### Phase 5: End-to-End Testing (Task 22)

**Objective:** Verify complete pipeline works with test asset.

**Tasks:**
- #22: Test end-to-end pipeline with test cube

**Process:**
1. Generate test cube geometry (Blender)
2. Validate GLB output
3. Import to Unity
4. Configure LOD, collider, materials
5. Create prefab
6. Document results and issues

**Deliverables:**
- Generated `assets/generated/props/test_cube.glb`
- Validation reports (JSON + Markdown)
- Unity prefab: `Prefabs/Props/test_cube.prefab`
- Integration report
- Documentation of pipeline issues

**Duration Estimate:** Testing and iteration

**Dependencies:** Phases 2, 3, 4 (requires all systems operational)

---

## Agent Definitions

### 1. Visual Mock Generator Agent

**File:** `.claude/agents/visual-mock-generator.md`

**Role:** Generate concept renders and deterministic asset specifications

**Key Responsibilities:**
- Create visual mockups (front, side, 3/4 views)
- Write JSON asset specifications
- Generate deterministic geometry prompts
- Iterate based on feedback
- Never generate Blender code

**Status:** ✅ Defined

---

### 2. Geometry Agent

**File:** `.claude/agents/geometry-agent.md`

**Role:** Generate Blender Python scripts from geometry prompts

**Key Responsibilities:**
- Read approved geometry prompts
- Generate deterministic Blender Python
- Execute headless Blender
- Export Unity-compatible GLB/FBX
- Never make artistic choices

**Status:** ✅ Defined

---

### 3. Validation Agent

**File:** `.claude/agents/validation-agent.md`

**Role:** Validate generated assets against technical constraints

**Key Responsibilities:**
- Run 10 validation checks (scale, poly budget, manifold, etc.)
- Generate structured reports (JSON + Markdown)
- Approve or reject with evidence
- Suggest specific fixes
- Never modify assets

**Status:** ✅ Defined

---

### 4. World Integration Agent

**File:** `.claude/agents/world-integration-agent.md`

**Role:** Integrate validated assets into Unity procedural systems

**Key Responsibilities:**
- Import to Unity with correct settings
- Configure LOD groups, colliders, materials
- Create prefabs
- Test runtime performance
- Register for procedural generation
- Never modify geometry

**Status:** ✅ Defined

---

## Technical Stack

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Unity** | 2022.3 LTS+ | Game engine |
| **Blender** | 3.6+ | 3D asset generation |
| **Python** | 3.10+ | Scripting and automation |
| **uv** | Latest | Python package management |
| **Git** | Latest | Version control |

### Key Technologies

**Asset Generation:**
- Blender Python API (bpy)
- GLB/FBX export
- Procedural geometry generation

**Unity:**
- Universal Render Pipeline (URP)
- C# scripting
- Asset Database API
- Prefab system

**CI/CD:**
- GitHub Actions
- Headless Blender execution
- Automated validation

**Orchestration:**
- Main repo agent system
- Comment-driven development
- GitHub issue workflows

---

## Quality Standards

### Art Direction

- **Style:** NASA-inspired realism, simulation-grade
- **Philosophy:** Function-first design, industrial plausibility
- **Scale:** Real-world meters (1 Unity unit = 1 meter)
- **Materials:** Physically accurate (titanium, carbon composite, etc.)

### Technical Constraints

- **Poly Budgets:**
  - Small ships: < 5k tris (LOD0)
  - Medium ships: < 15k tris (LOD0)
  - Large ships: < 40k tris (LOD0)
- **Bevel Standards:** 0.02m (standard), 0.04m (heavy), 0.005m (micro)
- **Texel Density:** 512px/meter (standard), 1024px/meter (hero)
- **LOD Levels:** 3 levels minimum (LOD0, LOD1, LOD2)

### Workflow Principles

1. **Deterministic** - Same input → same output, always
2. **Version Controlled** - All specs, prompts, scripts committed
3. **Reproducible** - Pipeline can regenerate any asset
4. **Validated** - No asset merges without passing validation
5. **Documented** - All decisions and processes written down

---

## Risks and Mitigations

### Risk: Blender API Changes

**Impact:** Scripts break on Blender updates

**Mitigation:**
- Pin Blender version (3.6+)
- Document API dependencies
- Test on version upgrades before adopting

### Risk: Unity Import Issues

**Impact:** GLB imports incorrectly scaled or oriented

**Mitigation:**
- Strict import settings via AssetPostprocessor
- Validation checks scale and axes
- Document Unity version compatibility

### Risk: Poly Budget Overruns

**Impact:** Performance issues in procedural world

**Mitigation:**
- Validation Agent enforces budgets
- Reject assets exceeding limits
- LOD system reduces far-distance polys

### Risk: Agent Hallucination (Geometry Agent)

**Impact:** Agent adds geometry not in prompt

**Mitigation:**
- Deterministic geometry prompts eliminate interpretation
- Validation checks against spec
- Human review of visual mocks before geometry generation

---

## Next Steps

1. **Start Phase 1:** Create project structure and all documentation
2. **Set up development environment:** Install Unity 2022.3 LTS, Blender 3.6+
3. **Begin Phase 2:** Build Blender pipeline scripts
4. **Parallel Phase 3:** Set up Unity project while Blender pipeline develops
5. **Integrate in Phase 4:** Add CI/CD automation
6. **Validate in Phase 5:** Run end-to-end test with test cube

---

## References

- [Main Orchestration Repo](../../README.md)
- [Agent Definitions](./.claude/agents/)
- [Project README](./README.md)
- [MASTER SPECIFICATION](#) - Original specification document

---

## Progress Tracking

Use the main orchestration system's task tools to track progress:

```bash
# View all tasks
eco status

# Update task status
# (via GitHub issue comments or CLI)

# Mark task complete
# (agent updates task when done)
```

**Current Phase:** Phase 1 (Foundation)

**Next Milestone:** Complete all documentation (Tasks 7-12, 23)

---

## Notes

- All agent definitions are project-specific and live in `.claude/agents/`
- Main repo agents (Architect, Infrastructure Engineer, etc.) can support setup
- Use `eco run` from main repo to orchestrate work on this project
- Project maintains its own documentation separate from main repo docs
- GitHub workflows trigger on issue labels: `approved-for-build`, `validation-passed`, etc.
