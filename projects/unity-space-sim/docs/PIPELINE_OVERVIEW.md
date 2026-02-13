# Asset Pipeline Overview

## Overview

The Unity Space Sim asset pipeline is a **deterministic, LLM-orchestrated system** that generates 3D space assets using Blender Python scripting and integrates them into Unity. The pipeline emphasizes automation, quality validation, and a believable sci-fi aesthetic.

**Philosophy:** Like GTA's approach to driving—feels right without needing to be a simulation. Gameplay and visual appeal first, then plausibility.

---

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                     ASSET PIPELINE FLOW                          │
└─────────────────────────────────────────────────────────────────┘

1. DESIGN PHASE
   └─> Visual Mock Generation (AI-assisted)
       └─> NASA-inspired concept art & wireframes

2. GEOMETRY GENERATION
   └─> Blender Python Scripting (bpy API)
       └─> Procedural modeling with deterministic prompts
       └─> Material setup & UV mapping
       └─> LOD generation (2-3 levels)

3. VALIDATION
   └─> Automated Quality Checks
       └─> Poly count validation
       └─> Material verification
       └─> LOD transition testing
       └─> Scale/unit verification

4. EXPORT
   └─> FBX Export (Blender → Unity)
       └─> Standardized export settings
       └─> Embedded textures
       └─> Correct scale (1 Unity unit = 1 meter)

5. UNITY INTEGRATION
   └─> Asset Import Pipeline
       └─> Prefab creation
       └─> Component attachment
       └─> Scene placement testing

6. CI/CD AUTOMATION
   └─> Headless Blender rendering
       └─> Automated validation
       └─> Asset catalog updates
```

---

## Stage 1: Design Phase

**Responsible Agent:** `unity-asset-designer`

### Process:
1. **Requirements Gathering**
   - Asset type (ship, station, debris, etc.)
   - Functional requirements (size, attachment points, etc.)
   - Visual reference goals

2. **Visual Mock Generation**
   - AI-generated concept art using visual prompt guidelines
   - NASA-inspired aesthetic references
   - Wireframe sketches for geometry planning

3. **Design Review**
   - Feasibility check (can it be modeled procedurally?)
   - Performance estimate (poly budget feasibility)
   - Art direction approval

**Deliverables:**
- Concept art (PNG/JPG)
- Wireframe sketches
- Design specification document

---

## Stage 2: Geometry Generation

**Responsible Agent:** `blender-engineer`

### Blender Python Scripting (bpy API)

All geometry is generated via **deterministic Python scripts** using Blender's `bpy` API. No manual modeling.

**Script Structure:**
```python
import bpy
import math

def generate_asset(config):
    """Deterministic asset generation from config dict."""
    # 1. Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # 2. Generate base geometry
    create_hull(config)

    # 3. Add details (procedural)
    add_detail_elements(config)

    # 4. Setup materials
    setup_materials(config)

    # 5. Generate LODs
    generate_lods(config)

    # 6. Export FBX
    export_fbx(config)

# Script is version-controlled and reproducible
```

**Key Principles:**
- **Deterministic:** Same config → Same output every time
- **Parameterized:** Config-driven (JSON/YAML input)
- **Modular:** Reusable components (hull generators, detail attachments)
- **Version Controlled:** All scripts in `projects/unity-space-sim/blender/scripts/`

### LOD Generation

Generate 2-3 LOD levels automatically:

| LOD Level | Poly Reduction | Use Distance |
|-----------|---------------|--------------|
| LOD0 (High) | 100% (target polys) | 0-500m |
| LOD1 (Medium) | ~40% of LOD0 | 500-2000m |
| LOD2 (Low) | ~15% of LOD0 | 2000m+ |

**LOD Script Example:**
```python
def generate_lods(base_mesh, levels=3):
    """Generate LOD levels using decimate modifier."""
    lods = []
    for i in range(levels):
        ratio = 1.0 / (2.5 ** i)  # Exponential reduction
        lod = base_mesh.copy()
        decimate = lod.modifiers.new('Decimate', 'DECIMATE')
        decimate.ratio = ratio
        bpy.context.view_layer.update()
        lods.append(lod)
    return lods
```

---

## Stage 3: Validation

**Responsible Agent:** `gamedev-integration-engineer`

### Automated Quality Checks

**Validation Rules (see VALIDATION_RULES.md):**
- ✅ Poly count within budget
- ✅ Materials assigned and valid
- ✅ LODs present and correct
- ✅ Scale verification (1 Blender unit = 1 meter)
- ✅ No overlapping geometry
- ✅ Clean topology (no ngons for primary surfaces)

**Validation Script:**
```python
def validate_asset(fbx_path):
    """Run validation checks on exported FBX."""
    asset = load_fbx(fbx_path)

    checks = [
        check_poly_count(asset),
        check_materials(asset),
        check_lods(asset),
        check_scale(asset),
        check_topology(asset),
    ]

    return all(checks)  # Pass/Fail
```

**Failure Handling:**
- Validation failures block Unity import
- Report generated with specific issues
- Script automatically re-runs after fixes

---

## Stage 4: Export

**Responsible Agent:** `blender-engineer`

### FBX Export Settings

Standardized export configuration for Unity compatibility:

```python
def export_fbx(output_path, asset_name):
    """Export asset with Unity-compatible settings."""
    bpy.ops.export_scene.fbx(
        filepath=f"{output_path}/{asset_name}.fbx",
        use_selection=False,
        global_scale=1.0,  # 1 Blender unit = 1 Unity unit = 1 meter
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        object_types={'MESH', 'ARMATURE'},
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        use_tspace=True,  # Tangent space for normal maps
        embed_textures=True,
        path_mode='COPY',
        batch_mode='OFF',
    )
```

**Export Checklist:**
- ✅ Correct axis orientation (Unity's coordinate system)
- ✅ Scale = 1.0 (no conversion needed)
- ✅ Textures embedded in FBX
- ✅ LODs exported as separate meshes
- ✅ Clean naming convention: `{category}_{name}_LOD{n}.fbx`

---

## Stage 5: Unity Integration

**Responsible Agent:** `unity-engineer`

### Asset Import Pipeline

Unity automatically processes imported FBX files via import settings:

**Import Settings (C# ScriptedImporter or .meta files):**
```csharp
// AssetPostprocessor for automatic configuration
public class SpaceAssetImporter : AssetPostprocessor
{
    void OnPreprocessModel()
    {
        ModelImporter importer = assetImporter as ModelImporter;

        // Scale & orientation
        importer.globalScale = 1.0f;  // Already correct from Blender
        importer.useFileScale = false;

        // Materials
        importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
        importer.importMaterials = true;

        // LODs (if embedded in FBX)
        importer.importAnimation = false;
        importer.importBlendShapes = false;
    }
}
```

### Prefab Creation

**Automated Prefab Generation:**
1. FBX imported → Unity creates prefab
2. Attach standard components:
   - MeshRenderer + MeshFilter (automatic)
   - Collider (generated from LOD0 mesh)
   - Optional: Rigidbody for physics objects
3. Configure LOD Group component
4. Save prefab to `Assets/Prefabs/Ships/` or relevant category

**Example Prefab Structure:**
```
CargoShip_Small.prefab
├── MeshRenderer (LOD0 material)
├── MeshFilter (LOD0 geometry)
├── LODGroup
│   ├── LOD0: CargoShip_Small_LOD0
│   ├── LOD1: CargoShip_Small_LOD1
│   └── LOD2: CargoShip_Small_LOD2
├── BoxCollider (auto-generated or custom)
└── ShipController (C# component)
```

---

## Stage 6: CI/CD Automation

### Headless Blender Rendering

**Automated Pipeline Execution:**

```bash
#!/bin/bash
# ci/generate_asset.sh

ASSET_CONFIG=$1  # JSON config file path
BLENDER_SCRIPT="scripts/generate_ship.py"

# Run Blender in headless mode
blender --background --python $BLENDER_SCRIPT -- --config $ASSET_CONFIG

# Validate output
python scripts/validate_fbx.py output/*.fbx

# If valid, copy to Unity project
if [ $? -eq 0 ]; then
    cp output/*.fbx ../unity/Assets/Models/Ships/
    echo "Asset imported successfully"
else
    echo "Validation failed"
    exit 1
fi
```

**GitHub Actions Workflow (future):**
```yaml
name: Generate Asset
on:
  push:
    paths:
      - 'blender/configs/**.json'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Blender
        run: sudo snap install blender --classic
      - name: Generate Asset
        run: ./ci/generate_asset.sh ${{ github.event.path }}
      - name: Commit FBX to Unity
        run: |
          git add unity/Assets/Models/
          git commit -m "Auto-generated asset from ${{ github.event.path }}"
```

---

## Tool Versions & Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| **Blender** | 3.6+ | 3D modeling & scripting (bpy API) |
| **Python** | 3.10+ | Blender scripting & automation |
| **Unity** | 2022.3 LTS+ | Game engine & runtime |
| **C#** | .NET Standard 2.1 | Unity scripting |
| **FBX SDK** | 2020.3+ | Export format compatibility |

---

## File Organization

```
projects/unity-space-sim/
├── blender/
│   ├── scripts/           # bpy Python scripts
│   │   ├── generators/    # Asset generation modules
│   │   ├── materials/     # Material setup scripts
│   │   └── export.py      # FBX export utilities
│   ├── configs/           # JSON/YAML asset configs
│   │   └── ships/
│   │       └── cargo_small.json
│   └── output/            # Generated FBX files (gitignored)
│
├── unity/
│   └── Assets/
│       ├── Models/        # Imported FBX files
│       │   └── Ships/
│       ├── Prefabs/       # Unity prefabs
│       ├── Materials/     # Unity materials
│       └── Scripts/       # C# components
│
└── docs/
    ├── PIPELINE_OVERVIEW.md (this file)
    ├── STYLE_GUIDE.md
    ├── VISUAL_PROMPT_GUIDE.md
    └── GEOMETRY_PROMPT_GUIDE.md
```

---

## Quality Assurance

### Performance Targets

- **Target Frame Rate:** 60 FPS on mid-range hardware
- **Poly Budget Per Ship:** See VALIDATION_RULES.md
- **Draw Calls:** Minimize via batching and atlasing
- **Texture Memory:** 2K max for ships, 1K for small objects

### Visual Quality

- **Art Direction:** NASA-inspired, believable sci-fi
- **Consistency:** All assets follow STYLE_GUIDE.md
- **Technical Quality:** Clean topology, proper UVs, optimized LODs

---

## Workflow Example: Creating a Small Cargo Ship

1. **Designer creates concept:**
   ```bash
   # Generate visual mock using AI prompt from VISUAL_PROMPT_GUIDE.md
   # Save to designs/ships/cargo_small_concept.png
   ```

2. **Engineer writes Blender script:**
   ```python
   # blender/scripts/generators/cargo_ship_small.py
   def generate(config):
       create_hull(length=10, width=6, height=4)
       add_cargo_bay()
       add_thrusters(count=4)
       setup_pbr_materials()
       generate_lods(levels=3)
       export_fbx("output/CargoShip_Small.fbx")
   ```

3. **Engineer creates config:**
   ```json
   // blender/configs/ships/cargo_small.json
   {
     "name": "CargoShip_Small",
     "category": "ships",
     "scale": 1.0,
     "poly_budget": 5000,
     "materials": ["hull_metal", "cargo_door"],
     "lod_levels": 3
   }
   ```

4. **Run generation:**
   ```bash
   blender --background --python scripts/generators/cargo_ship_small.py
   ```

5. **Validate:**
   ```bash
   python scripts/validate_fbx.py output/CargoShip_Small.fbx
   ```

6. **Import to Unity:**
   ```bash
   cp output/CargoShip_Small.fbx ../unity/Assets/Models/Ships/
   # Unity auto-imports and creates prefab
   ```

7. **Test in scene:**
   - Drag prefab into scene
   - Verify scale, LODs, materials
   - Test physics/gameplay integration

---

## Next Steps

- See **STYLE_GUIDE.md** for visual reference guidelines
- See **GEOMETRY_PROMPT_GUIDE.md** for deterministic script creation
- See **VALIDATION_RULES.md** for quality thresholds
- See **README.md** for setup instructions

---

**Status:** Foundation documentation (Phase 1)
**Last Updated:** 2026-02-12
**Maintainer:** Architect Agent
