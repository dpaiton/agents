# Unity Space Simulation

> A 3D space game built with Unity, featuring a deterministic LLM-orchestrated asset pipeline powered by Blender Python scripting and multi-agent coordination.

**Epic:** [Issue #65](https://github.com/dpaiton/agents/issues/65)
**Project Board:** [Unity Space Simulation](https://github.com/users/dpaiton/projects/2)

---

## Overview

Unity Space Sim is a **NASA-inspired believable sci-fi** space game that uses cutting-edge AI orchestration to generate 3D assets procedurally. The project emphasizes:

- **Deterministic asset generation** via Blender Python (`bpy` API)
- **Multi-agent orchestration** for design, modeling, validation, and integration
- **Realistic aesthetic** inspired by real space hardware (SpaceX, NASA, ESA)
- **Performance-first** approach (optimized for gameplay at 60 FPS)

**Philosophy:**
> "Like GTA's approach to driving—feels right without needing to be a simulation. Gameplay and visual appeal first, then plausibility."

---

## Quick Start

### Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| **Unity** | 2022.3 LTS+ | [Unity Hub](https://unity.com/download) |
| **Blender** | 3.6+ | [Blender.org](https://www.blender.org/download/) |
| **Python** | 3.10+ | [Python.org](https://www.python.org/downloads/) |
| **Git** | Latest | [Git-SCM](https://git-scm.com/downloads) |
| **uv** | Latest | [astral.sh/uv](https://docs.astral.sh/uv/) |

**Optional:**
- **Visual Studio Code** (for Python scripting)
- **Rider** or **Visual Studio** (for Unity C# development)

---

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/dpaiton/agents.git
cd agents/projects/unity-space-sim

# 2. Install Python dependencies (if needed for automation)
uv sync

# 3. Verify Blender is accessible via command line
blender --version
# Should output: Blender 3.6.x or higher

# 4. Open Unity project
# Open Unity Hub → Add → Select: projects/unity-space-sim/unity/
# Unity will import the project (may take a few minutes)
```

---

### Project Structure

```
projects/unity-space-sim/
├── README.md                  # This file
├── docs/                      # Documentation
│   ├── PIPELINE_OVERVIEW.md   # Asset pipeline workflow
│   ├── STYLE_GUIDE.md         # Visual aesthetic guidelines
│   ├── VISUAL_PROMPT_GUIDE.md # AI image generation prompts
│   ├── GEOMETRY_PROMPT_GUIDE.md # Blender Python scripting guide
│   └── VALIDATION_RULES.md    # Quality thresholds & validation
├── .claude/                   # Agent definitions & skills
│   ├── agents/
│   │   ├── unity-asset-designer.md
│   │   ├── blender-engineer.md
│   │   ├── unity-engineer.md
│   │   └── gamedev-integration-engineer.md
│   └── skills/
├── blender/                   # Blender asset generation
│   ├── scripts/               # Python generation scripts
│   │   ├── generators/        # Main asset generators
│   │   ├── components/        # Reusable components
│   │   └── utils/             # Export, LODs, validation
│   ├── configs/               # Asset configuration files (JSON)
│   └── output/                # Generated FBX files (gitignored)
├── unity/                     # Unity project
│   └── Assets/
│       ├── Models/            # Imported FBX files
│       ├── Prefabs/           # Unity prefabs
│       ├── Materials/         # Unity materials
│       ├── Scenes/            # Game scenes
│       └── Scripts/           # C# gameplay scripts
├── assets/                    # Source assets (concepts, references)
│   ├── concepts/              # AI-generated concept art
│   └── references/            # Real space hardware references
├── src/                       # Future: Python automation tools
└── tests/                     # Future: Automated tests
```

---

## Workflow

### Creating a New Asset (Step-by-Step)

#### Phase 1: Design

**Agent:** `unity-asset-designer`

1. **Define Requirements**
   ```bash
   # Create issue or document requirements
   # Example: "Small cargo ship, 15m long, modular boxy design"
   ```

2. **Generate Visual Concepts**
   - Follow **VISUAL_PROMPT_GUIDE.md** to create AI prompts
   - Generate concept art using Midjourney/DALL-E/Stable Diffusion
   - Save to `assets/concepts/ships/{category}/{name}/`

3. **Create Orthographic References**
   - Generate blueprint-style images (front, side, top views)
   - Use for geometry planning

**Deliverables:**
- Concept art (PNG/JPG)
- Orthographic blueprints
- Design specification (notes on size, materials, details)

---

#### Phase 2: Geometry Generation

**Agent:** `blender-engineer`

1. **Create Asset Configuration**
   ```bash
   # File: blender/configs/ships/cargo_small.json
   {
     "asset_name": "CargoShip_Small",
     "category": "ships",
     "dimensions": {
       "length": 15.0,
       "width": 8.0,
       "height": 6.0
     },
     "materials": {
       "hull": "white_painted_metal",
       "cargo_door": "dark_gray_metal"
     },
     "details": {
       "thrusters": 4,
       "radiator_panels": 2
     },
     "lod_levels": 3,
     "poly_budget": 5000
   }
   ```

2. **Write or Use Generation Script**
   - Follow **GEOMETRY_PROMPT_GUIDE.md**
   - Use existing script: `blender/scripts/generators/cargo_ship.py`
   - Or create new script for custom asset types

3. **Generate Asset**
   ```bash
   cd blender
   blender --background --python scripts/generators/cargo_ship.py -- configs/ships/cargo_small.json
   ```

**Output:** `blender/output/CargoShip_Small.fbx` (with LODs)

---

#### Phase 3: Validation

**Agent:** `gamedev-integration-engineer`

1. **Automated Validation**
   ```bash
   python scripts/validate/check_fbx.py output/CargoShip_Small.fbx
   ```

2. **Manual Visual Check**
   ```bash
   # Open in Blender GUI to verify
   blender output/CargoShip_Small.fbx
   ```

3. **Verify Against VALIDATION_RULES.md**
   - ✅ Poly count within budget
   - ✅ Scale correct (1 unit = 1 meter)
   - ✅ LODs present and smooth
   - ✅ Materials assigned

**If validation fails:** Fix script, regenerate, re-validate.

---

#### Phase 4: Unity Integration

**Agent:** `unity-engineer`

1. **Import FBX to Unity**
   ```bash
   cp blender/output/CargoShip_Small.fbx unity/Assets/Models/Ships/
   # Unity will auto-import on next focus
   ```

2. **Configure Import Settings**
   - Unity applies settings via `AssetPostprocessor` (automated)
   - Verify: Scale = 1.0, materials imported, LODs detected

3. **Create Prefab**
   - Drag model into scene
   - Add components (Rigidbody, Collider, Scripts)
   - Save as prefab: `Assets/Prefabs/Ships/CargoShip_Small.prefab`

4. **Test in Scene**
   - Place in test scene
   - Verify lighting, materials, LOD transitions
   - Test gameplay functionality

**Deliverable:** Prefab ready for gameplay integration

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| **[PIPELINE_OVERVIEW.md](docs/PIPELINE_OVERVIEW.md)** | End-to-end asset generation workflow |
| **[STYLE_GUIDE.md](docs/STYLE_GUIDE.md)** | Visual aesthetic (NASA-inspired sci-fi) |
| **[VISUAL_PROMPT_GUIDE.md](docs/VISUAL_PROMPT_GUIDE.md)** | AI concept art generation prompts |
| **[GEOMETRY_PROMPT_GUIDE.md](docs/GEOMETRY_PROMPT_GUIDE.md)** | Blender Python scripting guide |
| **[VALIDATION_RULES.md](docs/VALIDATION_RULES.md)** | Poly budgets, quality thresholds |

---

## Agent System

This project uses specialized AI agents for different tasks:

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **unity-asset-designer** | 3D Asset Design | Concept art, wireframes, design specs |
| **blender-engineer** | Blender Scripting | bpy Python scripts, procedural modeling, LOD generation |
| **unity-engineer** | Unity C# Scripting | Asset import, prefabs, gameplay components |
| **gamedev-integration-engineer** | E2E Pipeline Testing | Blender→Unity validation, quality checks |

**See:** `.claude/agents/` for full agent definitions.

---

## Development Guidelines

### Code Style

**Python (Blender Scripts):**
- PEP 8 style guide
- Type hints for function signatures
- Docstrings for all public functions
- Config-driven (no hardcoded values)

**C# (Unity Scripts):**
- Unity C# conventions
- XMLDoc comments for public APIs
- Component-based architecture
- Prefer ScriptableObjects for data

---

### Git Workflow

**Branch Strategy:**
```
main                   # Stable, production-ready
├── feature/cargo-ship # Feature branches
├── fix/lod-bug        # Bug fixes
└── docs/style-guide   # Documentation updates
```

**Commit Messages:**
```bash
# Format: [category] brief description
git commit -m "[blender] Add cargo ship generator script"
git commit -m "[unity] Implement ship flight controller"
git commit -m "[docs] Update validation rules poly budgets"
```

**Pull Requests:**
- Small, focused PRs (one feature/fix per PR)
- Reference issue number in PR description
- Include screenshots for visual changes
- Request review from relevant agent (comment `@blender-engineer`)

---

### Testing

**Blender Scripts:**
```bash
# Dry run (validate config without generating)
python scripts/validate_config.py configs/ships/cargo_small.json

# Generate and validate
blender --background --python scripts/generators/cargo_ship.py -- configs/ships/cargo_small.json
python scripts/validate/check_fbx.py output/CargoShip_Small.fbx
```

**Unity:**
- Manual playtesting (primary method for now)
- Performance profiling via Unity Profiler
- Visual QA checklist (see VALIDATION_RULES.md)

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Frame Rate** | 60 FPS | On mid-range hardware (GTX 1060 / RX 580) |
| **Draw Calls** | <200 | Per frame, typical gameplay scene |
| **Poly Budget** | <500k tris | On-screen at any time |
| **VRAM Usage** | <2GB | Total texture memory |
| **Load Times** | <5s | Scene transitions |

**See:** VALIDATION_RULES.md for detailed budgets and optimization strategies.

---

## Roadmap

### Phase 1: Foundation (CURRENT)
- ✅ Project structure
- ✅ Core documentation (pipeline, style, validation)
- ✅ Agent definitions
- 🔄 Initial Blender generator scripts
- 🔄 Unity project setup

### Phase 2: First Playable Asset
- ⏳ Generate first complete ship (small cargo)
- ⏳ Blender→Unity pipeline validated
- ⏳ Basic Unity scene with ship
- ⏳ Flight controls (basic)

### Phase 3: Asset Library
- ⏳ 3-5 ship variants (cargo, science, mining)
- ⏳ Station modules (habitation, docking)
- ⏳ Props (cargo crates, debris)

### Phase 4: Gameplay Systems
- ⏳ Flight physics
- ⏳ Docking mechanics
- ⏳ Camera system
- ⏳ Basic UI/HUD

### Phase 5: Polish & Iteration
- ⏳ Visual effects (thrusters, lights)
- ⏳ Audio integration
- ⏳ Performance optimization
- ⏳ Playtesting & feedback

---

## Contributing

**This project uses an AI agent orchestration system.** To contribute:

1. **Create or comment on a GitHub issue** describing the task
2. **Mention the relevant agent** (e.g., `@blender-engineer` for Blender work)
3. **Agents will process comments** and execute tasks
4. **Review agent output** and provide feedback

**Manual contributions** are also welcome:
- Fork the repository
- Create a feature branch
- Make changes following style guides
- Submit PR with clear description

---

## Troubleshooting

### Blender: "Module not found" error

**Issue:** Python script can't find component modules

**Fix:**
```python
# Add to top of script
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / 'components'))
```

---

### Unity: FBX imports at wrong scale

**Issue:** Model appears 100x too large or small

**Fix:**
- In Blender: Apply scale (`Ctrl+A` → Scale)
- Ensure export scale = 1.0
- In Unity: Set import scale = 1.0 in Inspector

---

### Unity: Materials are pink/missing

**Issue:** Textures not found after FBX import

**Fix:**
- Ensure "Embed Textures" enabled in Blender FBX export
- Or manually assign materials in Unity
- Check texture paths (use relative paths)

---

### Validation: Poly count exceeds budget

**Issue:** Asset has too many polygons for LOD0

**Fix:**
1. Simplify geometry (remove unnecessary detail)
2. Use normal maps instead of actual geometry
3. Adjust LOD decimate ratios
4. Request budget exception (see VALIDATION_RULES.md)

---

## Resources

**Documentation:**
- [Unity Manual](https://docs.unity3d.com/)
- [Blender Python API](https://docs.blender.org/api/current/)
- [FBX Format Specification](https://www.autodesk.com/products/fbx/overview)

**References:**
- [NASA Image Gallery](https://www.nasa.gov/multimedia/imagegallery/)
- [SpaceX Flickr](https://www.flickr.com/photos/spacex/)
- *The Expanse* (TV show - realistic sci-fi aesthetic)

**Community:**
- [Project Issue Tracker](https://github.com/dpaiton/agents/issues?q=label%3Aunity-space-sim)
- [Project Board](https://github.com/users/dpaiton/projects/2)

---

## License

See [LICENSE](../../LICENSE) in repository root.

---

## Acknowledgments

- **NASA** - Visual reference inspiration
- **Blender Foundation** - Excellent open-source 3D software
- **Unity Technologies** - Game engine
- **Anthropic** - AI orchestration via Claude

---

**Status:** Phase 1 - Foundation & Documentation
**Last Updated:** 2026-02-12
**Maintainer:** Architect Agent
**Epic:** [#65](https://github.com/dpaiton/agents/issues/65)
