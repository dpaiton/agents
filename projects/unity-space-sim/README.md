# Unity Space Simulation - LLM-Orchestrated Asset Pipeline

A 3D realistic space simulation game using Unity with deterministic asset generation via LLM-orchestrated Blender Python scripting.

---

## Quick Start

```bash
# 1. Install dependencies (see Prerequisites below)
# 2. Set up Unity project
# 3. Configure Blender Python environment
# 4. Run first asset generation test
cd projects/unity-space-sim
python scripts/generate_asset.py --spec assets/specs/cargo_ship_medium.json
```

---

## Project Overview

This project uses a **multi-agent LLM orchestration system** to generate production-ready 3D assets for a procedural space simulation game.

**Core Concept:** Asset creation follows a deterministic pipeline where:
1. **Visual Mock Generator** creates concept renders and specifications
2. **Geometry Agent** generates Blender Python scripts from specs
3. **Validation Agent** ensures quality and Unity compatibility
4. **World Integration Agent** places assets into procedural systems

**Art Direction:**
- Realistic simulation aesthetic (NASA-inspired)
- Industrial plausibility
- Function-first design
- Real-world scale (meters)
- Physically accurate wear and materials

---

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Unity** | 2022.3 LTS+ | Game engine |
| **Blender** | 3.6+ | 3D geometry generation |
| **Python** | 3.10+ | Blender scripting, automation |
| **Git** | Latest | Version control |
| **uv** | Latest | Python package management |

### Installation Instructions

#### 1. Install Unity

**macOS:**
```bash
# Download Unity Hub
# https://unity.com/download

# Install Unity 2022.3 LTS via Unity Hub
# Required modules:
#   - Linux Build Support (if deploying to Linux)
#   - Mac Build Support (Mono)
#   - WebGL Build Support (optional)
```

**Linux:**
```bash
# Download Unity Hub
wget https://public-cdn.cloud.unity3d.com/hub/prod/UnityHubSetup.AppImage
chmod +x UnityHubSetup.AppImage
./UnityHubSetup.AppImage

# Install Unity 2022.3 LTS via Unity Hub
```

**Windows:**
```bash
# Download Unity Hub installer
# https://unity.com/download
# Run installer and install Unity 2022.3 LTS
```

#### 2. Install Blender

**macOS:**
```bash
brew install --cask blender
# Or download from https://www.blender.org/download/
```

**Linux:**
```bash
# Ubuntu/Debian
sudo snap install blender --classic

# Or download from https://www.blender.org/download/
```

**Windows:**
```bash
# Download installer from https://www.blender.org/download/
# Run installer
```

**Verify Installation:**
```bash
blender --version
# Should output: Blender 3.6.x or later
```

#### 3. Configure Blender Python Environment

Blender ships with its own Python interpreter. We need to install dependencies in Blender's Python:

```bash
# Find Blender's Python path
blender --background --python-expr "import sys; print(sys.executable)"

# Example output (macOS):
# /Applications/Blender.app/Contents/Resources/3.6/python/bin/python3.10

# Install dependencies to Blender's Python
/path/to/blender/python -m pip install numpy pillow
```

**Alternative (using addon):**
```bash
# Install dependencies via Blender addon manager
# Preferences > Add-ons > Install > pip_install_addon.py
```

#### 4. Install Project Dependencies

```bash
cd projects/unity-space-sim
uv sync
```

#### 5. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env and configure:
#   BLENDER_PATH=/path/to/blender
#   UNITY_PROJECT_PATH=/path/to/unity/project
#   ANTHROPIC_API_KEY=your_key_here
```

---

## Development Environment Setup

### Unity Project Configuration

1. **Create New Unity Project:**
   ```bash
   # Open Unity Hub
   # New Project > 3D Core
   # Name: SpaceSimulation
   # Location: projects/unity-space-sim/unity-project/
   ```

2. **Configure Project Settings:**
   - **Player Settings:**
     - Color Space: Linear
     - Graphics API: Metal (macOS), Vulkan (Linux), DirectX 12 (Windows)
   - **Quality Settings:**
     - Enable anti-aliasing
     - Shadow quality: High
   - **Physics Settings:**
     - Gravity: (0, 0, 0) for space simulation

3. **Install Required Packages:**
   ```
   Window > Package Manager > Install:
     - Universal Render Pipeline (URP)
     - ProBuilder (optional, for level design)
     - Cinemachine (camera control)
   ```

### Blender Headless Testing

Verify Blender can run headless (required for CI/CD):

```bash
blender -b -P scripts/test_blender.py
```

Expected output:
```
Blender 3.6.x
Python 3.10.x
Test script executed successfully
```

---

## Project Structure

```
projects/unity-space-sim/
├── .claude/
│   └── agents/              # Project-specific agent definitions
│       ├── visual-mock-generator.md
│       ├── geometry-agent.md
│       ├── validation-agent.md
│       └── world-integration-agent.md
│
├── assets/
│   ├── specs/               # JSON asset specifications
│   ├── mocks/               # Concept renders
│   ├── prompts/
│   │   ├── visual/          # Visual generation prompts
│   │   └── geometry/        # Geometry generation prompts
│   ├── generated/           # Generated 3D assets
│   │   ├── ships/
│   │   ├── stations/
│   │   └── props/
│   └── style_guide/         # Reference images
│
├── docs/
│   ├── PIPELINE_OVERVIEW.md
│   ├── STYLE_GUIDE.md
│   ├── VISUAL_PROMPT_GUIDE.md
│   ├── GEOMETRY_PROMPT_GUIDE.md
│   └── VALIDATION_RULES.md
│
├── scripts/
│   ├── generate_asset.py    # Main asset generation script
│   ├── validate_asset.py    # Validation script
│   └── test_blender.py      # Blender environment test
│
├── unity-project/           # Unity game project
│   ├── Assets/
│   ├── Packages/
│   └── ProjectSettings/
│
├── .github/
│   └── workflows/
│       └── asset-pipeline.yml
│
├── README.md                # This file
├── .env.example
└── pyproject.toml
```

---

## Asset Generation Pipeline

### Phase 1: Visual Concept

```bash
# Generate concept render and specification
eco run "Generate visual mock for medium cargo ship" --issue <issue_number>
```

**Visual Mock Generator Agent** creates:
- `/assets/mocks/cargo_ship_medium/render_v001.png`
- `/assets/specs/cargo_ship_medium.json`
- `/assets/prompts/geometry/cargo_ship_medium_geometry_prompt.md`

### Phase 2: Geometry Generation

```bash
# Generate Blender Python script and export asset
blender -b -P scripts/generate_asset.py -- --spec assets/specs/cargo_ship_medium.json
```

**Geometry Agent** creates:
- `/assets/generated/ships/cargo_ship_medium.glb`
- `/assets/generated/ships/cargo_ship_medium/textures/*.png`

### Phase 3: Validation

```bash
# Validate asset against constraints
python scripts/validate_asset.py assets/generated/ships/cargo_ship_medium.glb
```

**Validation Agent** checks:
- Scale (meters)
- Poly count budget
- Pivot placement
- Normal consistency
- Naming conventions
- Unity compatibility

### Phase 4: Unity Integration

```bash
# Import to Unity and configure
eco run "Integrate cargo_ship_medium into Unity" --issue <issue_number>
```

**World Integration Agent**:
- Imports asset to Unity
- Configures LOD groups
- Assigns materials
- Sets up colliders
- Validates runtime performance

---

## Workflow

### Creating a New Asset

1. **Create GitHub Issue** with label `asset-concept`
   ```markdown
   # Cargo Ship - Medium Class

   **Type:** Ship
   **Scale:** 38 meters length
   **Purpose:** Interplanetary cargo hauling
   **Complexity:** Medium
   ```

2. **Visual Mock Generation**
   - Visual Mock Generator Agent creates concept renders
   - Review renders in issue comments
   - Iterate until approved

3. **Approval**
   - Add label: `approved-for-build`
   - Visual Mock Generator creates geometry prompt

4. **Geometry Generation**
   - Geometry Agent reads spec and prompt
   - Generates Blender Python script
   - Exports GLB/FBX asset

5. **Validation**
   - Validation Agent runs checks
   - Reports pass/fail in issue comments
   - On fail: geometry agent iterates

6. **Unity Integration**
   - World Integration Agent imports asset
   - Configures for runtime use
   - Tests in procedural generation

7. **Merge & Close**
   - Asset committed to `/assets/generated/`
   - Issue closed with label: `asset-complete`

---

## Agent Definitions

This project uses **4 specialized agents** (defined in `.claude/agents/`):

| Agent | Role | Cannot Do |
|-------|------|-----------|
| **Visual Mock Generator** | Creates concept renders, writes asset specs | Cannot generate Blender code, cannot freestyle |
| **Geometry Agent** | Generates deterministic Blender Python scripts | Cannot make artistic decisions, must follow spec exactly |
| **Validation Agent** | Validates assets against technical constraints | Cannot modify assets, only approve/reject |
| **World Integration Agent** | Integrates assets into Unity systems | Cannot modify core asset geometry |

See [`.claude/agents/`](.claude/agents/) for detailed definitions.

---

## Style Guide

**Art Direction:**
- NASA-inspired realism
- Industrial plausibility
- Visible mechanical logic
- Physically accurate materials

**Scale Standards:**
- Small ship: 12–20m
- Medium ship: 30–60m
- Large ship: 80–200m
- Station module: 50–300m

**Technical Standards:**
- Units: Meters (1 Unity unit = 1 meter)
- Poly budget: Small < 5k, Medium < 15k, Large < 40k
- Bevel: 0.02m (standard), 0.04m (heavy industrial)
- Texel density: 512px/meter (standard), 1024px/meter (hero assets)

See [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) for complete guidelines.

---

## Testing

```bash
# Test Blender environment
blender -b -P scripts/test_blender.py

# Generate test asset
python scripts/generate_asset.py --spec assets/specs/test_cube.json

# Validate test asset
python scripts/validate_asset.py assets/generated/props/test_cube.glb

# Run full pipeline test
eco test --integration
```

---

## CI/CD

Asset generation runs in GitHub Actions:

```yaml
# .github/workflows/asset-pipeline.yml
on:
  issue_comment:
    types: [created]

jobs:
  generate:
    if: contains(github.event.issue.labels.*.name, 'approved-for-build')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Blender
        run: sudo snap install blender --classic
      - name: Generate Asset
        run: blender -b -P scripts/generate_asset.py -- --issue ${{ github.event.issue.number }}
      - name: Validate
        run: python scripts/validate_asset.py
      - name: Upload Artifact
        uses: actions/upload-artifact@v3
```

---

## Troubleshooting

### Blender Not Found

```bash
# macOS
export PATH="/Applications/Blender.app/Contents/MacOS:$PATH"

# Linux
which blender  # Should output /snap/bin/blender or similar

# Windows
# Add Blender installation directory to PATH
```

### Unity Import Issues

- **Ensure GLB format:** Unity 2022.3+ has best GLB support
- **Check scale:** 1 Blender unit = 1 meter = 1 Unity unit
- **Verify normals:** Use DirectX normal map format
- **Apply transforms:** All transforms must be applied in Blender before export

### Blender Python Errors

```bash
# Test Blender's Python environment
blender --background --python-expr "import sys; print(sys.version)"

# Install missing packages
/path/to/blender/python -m pip install <package>
```

---

## Contributing

See the main orchestration repository's [CLAUDE.md](../../CLAUDE.md) for development principles.

**Asset Pipeline Specific:**
1. All assets must pass validation before merge
2. All prompts must be deterministic and version controlled
3. No artistic improvisation - follow specs exactly
4. Scale must be real-world accurate (meters)
5. All exports must be Unity-compatible

---

## Links

- **Main Orchestration Repo:** [../../README.md](../../README.md)
- **Pipeline Overview:** [docs/PIPELINE_OVERVIEW.md](docs/PIPELINE_OVERVIEW.md)
- **Style Guide:** [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md)
- **Agent Definitions:** [.claude/agents/](.claude/agents/)

---

## License

See main repository for license information.
