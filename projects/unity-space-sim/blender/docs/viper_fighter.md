# Viper-Class Fighter Generation

## Overview

The Viper-class fighter is a single-seat combat spacecraft inspired by Star Wars and No Man's Sky aesthetics. This document describes the Blender Python generation script that creates this asset procedurally.

## Design Specifications

Based on the approved Fighter Ship v4 concept art from issue #97.

### Physical Characteristics
- **Type:** Single-seat space fighter
- **Style:** Angular, aggressive, combat-ready
- **Dimensions:** 14m × 2m × 1.4m (L×W×H)
- **Poly Budget:**
  - LOD0: ~5,000 triangles
  - LOD1: ~2,000 triangles
  - LOD2: ~750 triangles

### Key Features
- Angular wedge-shaped hull with tapered nose
- Swept-back wings with mounted laser cannons
- Chin-mounted twin guns under cockpit
- Underslung turret with twin barrels
- Quad engine cluster with blue emission
- Dorsal fin behind cockpit
- Battle-worn grey metallic finish

## Generation Script

### Location
`projects/unity-space-sim/blender/scripts/generate_viper_fighter.py`

### Usage

**Basic generation:**
```bash
blender --background --python generate_viper_fighter.py
```

**With custom output directory:**
```bash
blender --background --python generate_viper_fighter.py -- --output-dir /path/to/output
```

### Output Files

The script generates:
- `viper_fighter_LOD0.fbx` - Main high-detail model
- `viper_fighter_LOD1.fbx` - Medium distance version
- `viper_fighter_LOD2.fbx` - Low detail for far distances
- `viper_fighter_3quarter.png` - 3/4 view render
- `viper_fighter_side.png` - Side profile render

## Technical Details

### Geometry Breakdown

**Hull**
- Base: Cube primitive (2.0 × 14.0 × 1.4m)
- Front taper: 25% X, 50% Z
- Rear taper: 70% X
- Subdivision: Level 2 for smoothness

**Wings (×2)**
- Base: Cube primitive (4.0 × 3.5 × 0.14m)
- Position: ±2.5m X offset
- Sweep: Tips translated -0.8m Y, scaled to 30% Y
- Bevel modifier for smooth edges

**Weapons Systems**
1. **Wing Cannons** - Cylinder barrels with emission tips
2. **Chin Guns** - Twin forward-firing barrels
3. **Turret** - Hemisphere dome with twin barrels

**Engines**
- 4× cylinder nacelles in quad configuration
- Torus nozzles for detail
- Emission planes for glow effect

### Materials (PBR)

| Material | Base Color RGB | Metallic | Roughness | Special |
|----------|---------------|----------|-----------|---------|
| Hull | (0.32, 0.34, 0.36) | 0.4 | 0.55 | - |
| Dark Panels | (0.05, 0.05, 0.07) | 0.6 | 0.7 | - |
| Gun Metal | (0.15, 0.15, 0.18) | 0.9 | 0.35 | - |
| Canopy | (0.04, 0.10, 0.16) | 0.0 | 0.05 | Alpha 0.45 |
| Engine Glow | (0.05, 0.2, 0.6) | 0.0 | 0.0 | Emission 5.0 |
| Weapon Tips | (0.6, 0.05, 0.02) | 0.0 | 0.0 | Emission 3.0 |

### LOD Strategy

LODs are generated using Blender's Decimate modifier:
- **LOD0:** Original geometry (~5k triangles)
- **LOD1:** 40% decimation (~2k triangles)
- **LOD2:** 15% decimation (~750 triangles)

## Testing

Run the test suite to verify generation:

```bash
python projects/unity-space-sim/blender/tests/test_viper_fighter.py
```

This will:
1. Run validation tests
2. Generate all assets
3. Verify output files
4. Check poly budgets

## Integration Notes

### Unity Import Settings

When importing to Unity:
1. Set **Scale Factor** to 1 (FBX uses correct scale)
2. Enable **Import Materials**
3. Set **Material Creation Mode** to "Standard"
4. Configure LOD Group with generated LODs

### Performance Considerations

- Triangle count optimized for real-time rendering
- Efficient UV mapping for texture atlasing
- Minimal material slots (7 total)
- LODs ensure good performance at distance

## Design Evolution

This fighter evolved through several iterations:
1. Initial NASA-inspired scout design
2. User feedback requesting more aggressive look
3. Star Wars / No Man's Sky aesthetic adopted
4. Multiple concept art iterations
5. Final approved design (Fighter Ship v4)

The result is a believable sci-fi fighter that feels both functional and visually striking.