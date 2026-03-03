# Viper-Class Fighter Generation

## Overview

The Viper-class fighter is a single-seat combat spacecraft with an X-wing-inspired cruciform wing configuration. This document specifies the exact geometry required for the Blender Python generation script to faithfully reproduce the approved concept art.

**Style:** Star Wars / No Man's Sky inspired aggressive fighter
**Based on:** Fighter Ship v4 concept art (approved)

## Concept Art Reference

All geometry must match these reference images:

| View | File | Key Features Visible |
|------|------|---------------------|
| Hero (3/4) | `projects/unity-space-sim/assets/drafts/fighter-v4/hero.png` | 4 wings in X, 2 large nacelles, weapon barrels at wing tips, angular fuselage |
| Side profile | `projects/unity-space-sim/assets/drafts/fighter-v4/side.png` | Thick fuselage, single dorsal fin, 2 nacelles at rear, angular cockpit canopy |
| Top-down | `projects/unity-space-sim/assets/drafts/fighter-v4/top.png` | 4 wings clearly in X arrangement, 2 nacelles side-by-side, 4 weapon barrels |
| Rear | `projects/unity-space-sim/assets/drafts/fighter-v4/rear.png` | 2 large engine nozzles with orange/red glow, 4 wings in X, weapon barrels at tips |

## Feature Checklist

Every feature below must be present in the generated model. Counts are exact.

| Feature | Count | Concept Art Evidence | Geometry Requirement |
|---------|-------|---------------------|---------------------|
| Fuselage | 1 | All views: thick rectangular body | Rectangular cross-section, beveled edges, tapered nose |
| Wings | 4 | hero.png, top.png, rear.png | Cruciform X-configuration (2 upper, 2 lower) |
| Engine nacelles | 2 | side.png, rear.png | Large cylinders, side-by-side, attached to rear fuselage |
| Weapon barrels | 4 | hero.png, top.png | 1 barrel per wing tip, extending forward |
| Cockpit canopy | 1 | side.png, hero.png | Angular canopy on top of fuselage, forward 1/3 |
| Dorsal fin | 1 | side.png | Single fin/antenna behind cockpit |
| Chin guns | 0 | Not visible in any view | DO NOT INCLUDE |
| Underslung turret | 0 | Not visible in any view | DO NOT INCLUDE |

## Physical Characteristics

- **Type:** Single-seat space fighter
- **Style:** X-wing-inspired cruciform configuration
- **Overall dimensions:** ~12m length x ~10m wingspan (tip-to-tip) x ~4m height (tip-to-tip)
- **Fuselage:** ~12m L x ~2.5m W x ~1.8m H (thick rectangular, NOT thin wedge)
- **Fuselage cross-section:** Roughly rectangular with beveled edges
- **Poly budget:**
  - LOD0: ~5,000 triangles
  - LOD1: ~2,000 triangles
  - LOD2: ~750 triangles

## Proportions Reference

Key ratios normalized to fuselage length = 1.0. Maintain these regardless of absolute scale.

| Measurement | Ratio | Absolute (~12m fuselage) |
|------------|-------|--------------------------|
| Fuselage length | 1.00 | 12.0m |
| Fuselage width | 0.21 | 2.5m |
| Fuselage height | 0.15 | 1.8m |
| Wingspan (tip-to-tip) | 0.83 | 10.0m |
| Wing chord (root) | 0.13 | 1.5m |
| Wing chord (tip) | 0.07 | 0.8m |
| Wing span (single wing, root to tip) | 0.33 | 4.0m |
| Nacelle length | 0.33 | 4.0m |
| Nacelle diameter | 0.10 | 1.2m |
| Weapon barrel length | 0.21 | 2.5m |
| Dorsal fin height | 0.07 | 0.8m |

## Geometry Breakdown

### Fuselage

- **Base primitive:** Cube
- **Dimensions:** 2.5m W x 12.0m L x 1.8m H
- **Front taper:** Forward face scaled to ~40% width, ~60% height (pointed nose)
- **Rear taper:** Rear face scaled to ~80% width (slight narrowing for nacelle attachment)
- **Modifier:** Subdivision level 1 (keeps angular silhouette)
- **Cross-section:** Rectangular with beveled edges (bevel width 0.02m)

### Wings (x4, cruciform X-configuration)

Viewed from front or rear, the 4 wings form an X shape:

```
        Upper-Left  /  \ Upper-Right
                   /    \
    =============[FUSE]=============
                   \    /
        Lower-Left  \  / Lower-Right
```

- **Base primitive:** Cube per wing
- **Dimensions per wing:** 4.0m span x 1.5m chord (root) x 0.15m thickness
- **Attachment point:** Mid-fuselage, approximately 60% back from nose
- **Angular offsets from horizontal (viewed from rear):**
  - Upper-right: +30 degrees
  - Upper-left: +150 degrees
  - Lower-right: -30 degrees
  - Lower-left: -150 degrees
- **Sweep:** Wing tips translated ~0.8m rearward (swept back)
- **Taper:** Tip chord ~50% of root chord
- **Modifier:** Bevel (0.01m width) for smooth edges

### Engine Nacelles (x2)

- **Base primitive:** Cylinder per nacelle
- **Dimensions:** 1.2m diameter x 4.0m length
- **Position:** Side-by-side, horizontally centered on fuselage rear
- **Horizontal spacing:** Nacelle centers ~1.5m apart (0.3m gap between surfaces)
- **Vertical position:** Centered on fuselage midplane
- **Longitudinal position:** Rear half extends ~1.0m beyond fuselage rear
- **Each nacelle includes:**
  - Main cylinder body (dark panels material)
  - Rear nozzle ring: Torus, major radius = nacelle radius, minor radius 0.06m
  - Exhaust glow: Circle fill (ngon), radius 0.9x nacelle radius, emission material
  - Forward intake ring: Torus, slightly smaller than main body
- **Segmented detail rings:** 2-3 torus rings along nacelle length (minor radius 0.03m)

### Weapon Barrels (x4, one per wing tip)

- **Base primitive:** Cylinder per barrel
- **Dimensions:** 0.06m radius x 2.5m length
- **Position:** Extends forward from each wing tip, parallel to fuselage longitudinal axis
- **Tip accent:** Small sphere (radius 0.08m) at forward end with red emission material
- **Material:** Gun metal

### Cockpit Canopy

- **Base primitive:** Cube
- **Dimensions:** 0.6m W x 2.0m L x 0.35m H
- **Position:** Top of fuselage, centered laterally, forward 1/3 of fuselage length
- **Front taper:** Forward face scaled to ~40% width (tapered nose)
- **Modifier:** Subdivision level 1
- **Material:** Dark tinted glass (alpha 0.45, transmission 0.8)

### Dorsal Fin

- **Base primitive:** Cube
- **Dimensions:** 0.06m W x 2.0m L x 0.8m H
- **Position:** Top of fuselage, directly behind cockpit
- **Sweep:** Top edge shifted ~0.5m rearward
- **Tip taper:** Top scaled to ~50% length
- **Material:** Hull material

## Materials (PBR)

| Material | Base Color RGB | Metallic | Roughness | Special |
|----------|---------------|----------|-----------|---------|
| Hull (worn grey) | (0.32, 0.34, 0.36) | 0.4 | 0.55 | - |
| Dark Panels | (0.05, 0.05, 0.07) | 0.6 | 0.7 | Engine nacelles, vents |
| Gun Metal | (0.15, 0.15, 0.18) | 0.9 | 0.35 | Weapon barrels |
| Canopy Glass | (0.04, 0.10, 0.16) | 0.0 | 0.05 | Alpha 0.45, Transmission 0.8 |
| Engine Glow | (0.05, 0.2, 0.6) | 0.0 | 0.0 | Emission 5.0 (blue) |
| Weapon Tips | (0.6, 0.05, 0.02) | 0.0 | 0.0 | Emission 3.0 (red) |
| Orange Accent | (0.65, 0.22, 0.04) | 0.2 | 0.5 | Stripe accents |

### Material Assignment

| Component | Primary Material | Secondary Material |
|-----------|-----------------|-------------------|
| Fuselage | Hull | - |
| Wings | Hull | - |
| Engine nacelle bodies | Dark Panels | - |
| Engine nozzle rings | Dark Panels | - |
| Engine exhaust glow | Engine Glow | - |
| Weapon barrels | Gun Metal | - |
| Weapon tip spheres | Weapon Tips | - |
| Cockpit canopy | Canopy Glass | - |
| Dorsal fin | Hull | - |

## LOD Strategy

LODs generated using Blender's Decimate modifier:

- **LOD0:** Original geometry (~5,000 triangles)
- **LOD1:** 40% decimation ratio (~2,000 triangles)
- **LOD2:** 15% decimation ratio (~750 triangles)

## Generation Script

### Location

`projects/unity-space-sim/blender/scripts/generate_viper_fighter.py`

### Usage

```bash
blender --background --python generate_viper_fighter.py
blender --background --python generate_viper_fighter.py -- --output-dir /path/to/output
```

### Output Files

- `viper_fighter_LOD0.fbx` - Main high-detail model
- `viper_fighter_LOD1.fbx` - Medium distance version
- `viper_fighter_LOD2.fbx` - Low detail for far distances
- `viper_fighter_3quarter.png` - 3/4 view render (compare against hero.png)
- `viper_fighter_side.png` - Side profile render (compare against side.png)

### Visual Validation

After generation, validate renders against concept art:

```bash
python projects/unity-space-sim/tools/validate_visual.py \
    --render-dir assets/generated/viper-fighter/ \
    --concept-dir assets/drafts/fighter-v4/ \
    --threshold 0.75
```

## Required Script Changes (from current implementation)

The current `generate_viper_fighter.py` must be updated to match this spec:

1. **Wings:** Replace `create_wings()` (2 flat swept-back planes) with 4 wings in cruciform X-configuration at ±30 degree angular offsets
2. **Engines:** Replace `create_engines()` (4 small quad cylinders) with 2 large cylindrical nacelles side-by-side
3. **Remove:** Delete `create_chin_guns()` — not in concept art
4. **Remove:** Delete `create_underslung_turret()` — not in concept art
5. **Fuselage:** Update `ViperConfig` dimensions from 14m x 2m x 1.4m to 12m x 2.5m x 1.8m
6. **Fuselage subdivision:** Keep at level 1 for angular silhouette
7. **Update:** `apply_materials()` for new component set (no turret/chin gun materials)
8. **Update:** `join_fighter_parts()` for new component dictionary

## Testing

```bash
# Syntax validation
python -m py_compile projects/unity-space-sim/blender/scripts/generate_viper_fighter.py

# Full generation + validation
python projects/unity-space-sim/blender/tests/test_viper_fighter.py

# Visual fidelity check (requires ANTHROPIC_API_KEY)
python projects/unity-space-sim/tools/validate_visual.py \
    --render assets/generated/viper-fighter/viper_fighter_3quarter.png \
    --concept assets/drafts/fighter-v4/hero.png
```

## Unity Import Settings

- Scale Factor: 1 (FBX uses correct scale)
- Import Materials: Enabled
- Material Creation Mode: Standard
- Configure LOD Group with LOD0/LOD1/LOD2

## Design Evolution

1. Initial NASA-inspired scout design
2. User feedback requesting more aggressive look
3. Star Wars / No Man's Sky aesthetic adopted
4. Multiple concept art iterations
5. Final approved design: Fighter Ship v4 (4 views in `assets/drafts/fighter-v4/`)
6. Geometry spec corrected to match concept art (this document)
