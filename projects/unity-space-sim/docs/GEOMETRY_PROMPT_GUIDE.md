# Geometry Prompt Guide

## Overview

This guide provides templates and best practices for creating **deterministic Blender Python scripts** that generate 3D geometry for Unity Space Sim assets. Unlike visual prompts (which use AI image generation), geometry prompts are **code-based** and use Blender's `bpy` API.

**Goal:** Create reproducible, parameterized Python scripts that generate consistent 3D models from configuration files.

---

## Core Principles

### 1. Deterministic Generation

**Rule:** Same config → Same output, always.

```python
# ✅ GOOD: Deterministic
def generate_hull(length, width, height):
    bpy.ops.mesh.primitive_cube_add(size=1)
    hull = bpy.context.active_object
    hull.scale = (length, width, height)
    return hull

# ❌ BAD: Non-deterministic
import random
def generate_hull(length):
    # Random variations make output unpredictable
    width = length * random.uniform(0.4, 0.6)
    height = length * random.uniform(0.3, 0.5)
    # ... rest of code
```

**Why:** Version control, reproducibility, debugging, collaboration.

---

### 2. Configuration-Driven

**All parameters come from config files (JSON/YAML), not hardcoded.**

**Config File Example (`configs/ships/cargo_small.json`):**
```json
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
    "radiator_panels": 2,
    "cargo_doors": 1
  },
  "lod_levels": 3,
  "poly_budget": 5000
}
```

**Script Structure:**
```python
import bpy
import json
import sys

def load_config(config_path):
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def generate_asset(config):
    """Generate asset from configuration."""
    clear_scene()

    # Use config values
    hull = create_hull(
        length=config['dimensions']['length'],
        width=config['dimensions']['width'],
        height=config['dimensions']['height']
    )

    # Add details based on config
    add_thrusters(hull, count=config['details']['thrusters'])
    add_radiators(hull, count=config['details']['radiator_panels'])

    # Materials from config
    assign_materials(hull, config['materials'])

    # Generate LODs
    generate_lods(hull, levels=config['lod_levels'])

    # Export with name from config
    export_fbx(hull, config['asset_name'])

if __name__ == "__main__":
    config_path = sys.argv[-1]  # Last argument after '--'
    config = load_config(config_path)
    generate_asset(config)
```

**Usage:**
```bash
blender --background --python generate_ship.py -- configs/ships/cargo_small.json
```

---

### 3. Modular & Reusable

**Break scripts into reusable functions and modules.**

**File Structure:**
```
blender/
├── scripts/
│   ├── generators/           # Main generation scripts
│   │   ├── cargo_ship.py
│   │   ├── science_ship.py
│   │   └── station_module.py
│   ├── components/           # Reusable component modules
│   │   ├── hulls.py          # Hull generation functions
│   │   ├── thrusters.py      # Thruster creation
│   │   ├── radiators.py      # Radiator panels
│   │   └── materials.py      # Material setup
│   ├── utils/                # Utility functions
│   │   ├── cleanup.py        # Scene cleanup
│   │   ├── lods.py           # LOD generation
│   │   └── export.py         # FBX export
│   └── validate/             # Validation scripts
│       └── check_fbx.py
└── configs/                  # Asset configurations
    └── ships/
        └── cargo_small.json
```

**Example: Reusable Hull Generator (`components/hulls.py`):**
```python
"""Reusable hull generation functions."""
import bpy
import bmesh

def create_box_hull(length, width, height, bevel=0.1):
    """Create a beveled box hull (common for cargo ships).

    Args:
        length (float): Hull length in meters.
        width (float): Hull width in meters.
        height (float): Hull height in meters.
        bevel (float): Bevel radius for edge softening.

    Returns:
        bpy.types.Object: The generated hull object.
    """
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    hull = bpy.context.active_object
    hull.name = "Hull"
    hull.scale = (length / 2, width / 2, height / 2)
    bpy.ops.object.transform_apply(scale=True)

    # Add bevel modifier for edge softening
    bevel_mod = hull.modifiers.new(name='Bevel', type='BEVEL')
    bevel_mod.width = bevel
    bevel_mod.segments = 3

    return hull


def create_cylindrical_hull(length, radius, segments=32):
    """Create a cylindrical hull (common for station modules).

    Args:
        length (float): Cylinder length in meters.
        radius (float): Cylinder radius in meters.
        segments (int): Number of radial segments (detail level).

    Returns:
        bpy.types.Object: The generated hull object.
    """
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=segments,
        radius=radius,
        depth=length,
        location=(0, 0, 0)
    )
    hull = bpy.context.active_object
    hull.name = "Hull"
    hull.rotation_euler = (0, 1.5708, 0)  # Rotate to align with length axis
    bpy.ops.object.transform_apply(rotation=True)

    return hull
```

**Using Reusable Components:**
```python
from components.hulls import create_box_hull
from components.thrusters import add_thruster_array
from components.materials import assign_hull_material

def generate_cargo_ship(config):
    hull = create_box_hull(
        length=config['dimensions']['length'],
        width=config['dimensions']['width'],
        height=config['dimensions']['height']
    )

    add_thruster_array(hull, positions=[(7, 0, 0), (-7, 0, 0)])
    assign_hull_material(hull, "white_painted_metal")

    return hull
```

---

## Script Template

### Minimal Generation Script

```python
#!/usr/bin/env python3
"""
Generate [ASSET_TYPE] for Unity Space Sim.

Usage:
    blender --background --python generate_[asset].py -- config.json
"""

import bpy
import json
import sys
from pathlib import Path

# Add components directory to path
SCRIPT_DIR = Path(__file__).parent
COMPONENTS_DIR = SCRIPT_DIR / 'components'
sys.path.insert(0, str(COMPONENTS_DIR))

from hulls import create_box_hull
from thrusters import add_thruster_quad
from materials import setup_pbr_materials
from utils.cleanup import clear_scene
from utils.lods import generate_lods
from utils.export import export_fbx


def load_config(config_path):
    """Load asset configuration from JSON."""
    with open(config_path, 'r') as f:
        return json.load(f)


def generate_asset(config):
    """Main generation function."""
    # 1. Clear scene
    clear_scene()

    # 2. Generate base geometry
    hull = create_box_hull(
        length=config['dimensions']['length'],
        width=config['dimensions']['width'],
        height=config['dimensions']['height']
    )

    # 3. Add functional details
    add_thruster_quad(
        hull,
        count=config['details']['thrusters'],
        scale=0.2
    )

    # 4. Setup materials
    setup_pbr_materials(hull, config['materials'])

    # 5. Generate LODs
    lods = generate_lods(hull, levels=config['lod_levels'])

    # 6. Export FBX
    export_fbx(
        lods,
        output_path=f"output/{config['asset_name']}.fbx",
        scale=1.0
    )

    print(f"✓ Generated {config['asset_name']}")


def main():
    """Entry point when run from command line."""
    # Parse config path from arguments (after '--')
    argv = sys.argv
    argv = argv[argv.index("--") + 1:]  # Get args after '--'
    config_path = argv[0]

    # Load and generate
    config = load_config(config_path)
    generate_asset(config)


if __name__ == "__main__":
    main()
```

---

## Common Generation Patterns

### Pattern 1: Box Hull with Details

**Use Case:** Cargo ships, industrial vessels, station modules

```python
def generate_cargo_hull(length, width, height):
    """Generate box hull with cargo bay cutout."""
    # Base hull
    hull = create_box_hull(length, width, height, bevel=0.2)

    # Boolean subtract for cargo bay
    cargo_bay = create_cargo_bay_cutter(
        width=width * 0.8,
        height=height * 0.6,
        depth=length * 0.5
    )

    bool_mod = hull.modifiers.new(name='CargoBay', type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = cargo_bay

    bpy.context.view_layer.update()
    cargo_bay.hide_render = True

    return hull


def create_cargo_bay_cutter(width, height, depth):
    """Create boolean cutter for cargo bay."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    cutter = bpy.context.active_object
    cutter.name = "CargoBayCutter"
    cutter.scale = (depth / 2, width / 2, height / 2)
    bpy.ops.object.transform_apply(scale=True)
    return cutter
```

---

### Pattern 2: Cylindrical Hull with Endcaps

**Use Case:** Station modules, science vessels, fuel tanks

```python
def generate_module_hull(length, radius, segments=32):
    """Generate cylindrical module with spherical endcaps."""
    # Main cylinder
    cylinder = create_cylindrical_hull(length, radius, segments)

    # Front endcap (half sphere)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        segments=segments,
        ring_count=segments // 2,
        location=(length / 2, 0, 0)
    )
    front_cap = bpy.context.active_object

    # Rear endcap
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        segments=segments,
        ring_count=segments // 2,
        location=(-length / 2, 0, 0)
    )
    rear_cap = bpy.context.active_object

    # Join all parts
    bpy.ops.object.select_all(action='DESELECT')
    cylinder.select_set(True)
    front_cap.select_set(True)
    rear_cap.select_set(True)
    bpy.context.view_layer.objects.active = cylinder
    bpy.ops.object.join()

    return cylinder
```

---

### Pattern 3: Panel Details (Surface Greebles)

**Use Case:** Adding visual complexity to large flat surfaces

```python
def add_panel_lines(obj, divisions_x=4, divisions_y=3, inset=0.02):
    """Add panel lines to object using inset and extrude.

    Args:
        obj: Target mesh object.
        divisions_x: Horizontal panel divisions.
        divisions_y: Vertical panel divisions.
        inset: Depth of panel lines (meters).
    """
    # Enter edit mode
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Subdivide for panel divisions
    bpy.ops.mesh.subdivide(number_cuts=divisions_x)

    # Inset faces for panel lines
    bpy.ops.mesh.inset(thickness=inset, depth=inset)

    # Return to object mode
    bpy.ops.object.mode_set(mode='OBJECT')
```

---

### Pattern 4: Thruster Arrays

**Use Case:** RCS thrusters, main engines

```python
def add_thruster_quad(parent, scale=0.2, offset_z=0.0):
    """Add 4 RCS thrusters in quad configuration.

    Args:
        parent: Parent hull object.
        scale: Thruster nozzle size.
        offset_z: Z-axis offset from hull rear.
    """
    rear_x = -parent.dimensions.x / 2  # Rear of hull
    half_width = parent.dimensions.y / 2
    half_height = parent.dimensions.z / 2

    # Thruster positions (rear corners)
    positions = [
        (rear_x, half_width * 0.8, half_height * 0.8),    # Top-right
        (rear_x, -half_width * 0.8, half_height * 0.8),   # Top-left
        (rear_x, half_width * 0.8, -half_height * 0.8),   # Bottom-right
        (rear_x, -half_width * 0.8, -half_height * 0.8),  # Bottom-left
    ]

    thrusters = []
    for i, pos in enumerate(positions):
        thruster = create_thruster_nozzle(scale)
        thruster.location = (pos[0] + offset_z, pos[1], pos[2])
        thruster.parent = parent
        thrusters.append(thruster)

    return thrusters


def create_thruster_nozzle(scale):
    """Create a simple conical thruster nozzle."""
    bpy.ops.mesh.primitive_cone_add(
        vertices=16,
        radius1=scale,
        radius2=scale * 0.6,
        depth=scale * 1.5,
        location=(0, 0, 0)
    )
    thruster = bpy.context.active_object
    thruster.name = "Thruster"
    thruster.rotation_euler = (0, 1.5708, 0)  # Point backward
    bpy.ops.object.transform_apply(rotation=True)
    return thruster
```

---

## Material Setup

### PBR Material Template

```python
def setup_pbr_material(name, base_color, metallic, roughness):
    """Create a PBR material with Principled BSDF.

    Args:
        name: Material name.
        base_color: RGB tuple (0-1 range) or hex string.
        metallic: Metallic value (0-1).
        roughness: Roughness value (0-1).

    Returns:
        bpy.types.Material: The created material.
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    # Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)

    # Set parameters
    if isinstance(base_color, str):  # Hex color
        base_color = hex_to_rgb(base_color)
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness

    # Material Output
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (200, 0)

    # Connect nodes
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


# Create common materials
white_hull = setup_pbr_material(
    name="white_painted_metal",
    base_color="#F0F0F0",
    metallic=0.1,
    roughness=0.4
)

aluminum = setup_pbr_material(
    name="brushed_aluminum",
    base_color="#A8A8A8",
    metallic=0.9,
    roughness=0.6
)
```

---

## LOD Generation

### Automatic LOD with Decimate Modifier

```python
def generate_lods(base_mesh, levels=3):
    """Generate LOD levels using decimate modifier.

    Args:
        base_mesh: LOD0 (highest detail) mesh.
        levels: Number of LOD levels to generate.

    Returns:
        list[bpy.types.Object]: LOD meshes (LOD0, LOD1, LOD2, ...).
    """
    lods = [base_mesh]  # LOD0 is the original

    for i in range(1, levels):
        # Duplicate base mesh
        lod = base_mesh.copy()
        lod.data = base_mesh.data.copy()
        lod.name = f"{base_mesh.name}_LOD{i}"
        bpy.context.collection.objects.link(lod)

        # Add decimate modifier (exponential reduction)
        ratio = 1.0 / (2.5 ** i)  # LOD1: ~40%, LOD2: ~16%
        decimate = lod.modifiers.new(name='Decimate', type='DECIMATE')
        decimate.ratio = ratio
        decimate.use_collapse_triangulate = True

        # Apply modifier
        bpy.context.view_layer.objects.active = lod
        bpy.ops.object.modifier_apply(modifier='Decimate')

        lods.append(lod)

    print(f"✓ Generated {levels} LOD levels")
    return lods
```

---

## Validation Helpers

### Pre-Export Validation

```python
def validate_geometry(obj, poly_budget):
    """Validate geometry meets requirements.

    Returns:
        bool: True if valid, False otherwise.
    """
    checks = []

    # Check poly count
    poly_count = len(obj.data.polygons)
    if poly_count > poly_budget:
        print(f"✗ Poly count {poly_count} exceeds budget {poly_budget}")
        checks.append(False)
    else:
        print(f"✓ Poly count: {poly_count}/{poly_budget}")
        checks.append(True)

    # Check scale (1 Blender unit = 1 meter)
    if obj.scale != (1.0, 1.0, 1.0):
        print(f"✗ Scale not applied: {obj.scale}")
        checks.append(False)
    else:
        print("✓ Scale applied correctly")
        checks.append(True)

    # Check materials assigned
    if len(obj.material_slots) == 0:
        print("✗ No materials assigned")
        checks.append(False)
    else:
        print(f"✓ Materials assigned: {len(obj.material_slots)}")
        checks.append(True)

    return all(checks)
```

---

## Testing & Iteration

### Quick Test Workflow

```bash
# 1. Generate asset
blender --background --python generate_cargo_ship.py -- configs/cargo_small.json

# 2. Open in Blender GUI for visual check
blender output/CargoShip_Small.fbx

# 3. Validate (automated)
python scripts/validate/check_fbx.py output/CargoShip_Small.fbx

# 4. If valid, copy to Unity
cp output/CargoShip_Small.fbx ../unity/Assets/Models/Ships/
```

---

## Best Practices

### ✅ DO:

- **Use config files** for all parameters
- **Version control scripts** in `blender/scripts/`
- **Modularize code** (reusable components)
- **Add docstrings** to all functions
- **Validate before export** (poly count, scale, materials)
- **Test in Blender GUI** before automating
- **Follow naming conventions** (clear, descriptive names)

### ❌ DON'T:

- **Hardcode values** in scripts
- **Use random/non-deterministic** functions
- **Skip validation checks**
- **Create massive monolithic scripts**
- **Forget to apply transforms** (scale, rotation)
- **Export without LODs**
- **Ignore poly budgets** (see VALIDATION_RULES.md)

---

## Example: Complete Cargo Ship Generator

See `blender/scripts/generators/cargo_ship_small.py` for a full working example implementing all patterns from this guide.

**Key Features:**
- Config-driven parameters
- Modular component reuse
- PBR material setup
- Automatic LOD generation
- Pre-export validation
- Unity-compatible FBX export

---

## Next Steps

1. Review example scripts in `blender/scripts/generators/`
2. Create asset config in `blender/configs/`
3. Run generation script with config
4. Validate output against VALIDATION_RULES.md
5. Import to Unity following PIPELINE_OVERVIEW.md

---

**Status:** Foundation documentation (Phase 1)
**Last Updated:** 2026-02-12
**Maintainer:** Architect Agent
