# Blender Python Generation Scripts

This directory contains procedural 3D asset generation scripts for the Unity Space Simulation project using the Blender Python API (bpy). These scripts generate NASA-inspired sci-fi spaceships that follow the design guidelines in `docs/STYLE_GUIDE.md`.

## 🚀 Quick Start

```bash
# Install Blender 3.6+ (if not already installed)
# On macOS: brew install --cask blender
# On Linux: snap install blender --classic

# Generate a single spaceship (headless)
blender --background --python scripts/generate_basic_spaceship.py -- --type cargo --size medium

# Generate all spaceship variants for MVP
blender --background --python scripts/batch_generate_ships.py

# Run validation tests
pytest tests/ -v
```

## 📁 Directory Structure

```
blender/
├── scripts/
│   ├── generate_basic_spaceship.py    # Core spaceship generation
│   └── batch_generate_ships.py        # Batch generation utility
├── tests/
│   └── test_spaceship_generation.py   # Validation test suite
└── README.md                          # This file
```

## 🛠 Scripts Overview

### `generate_basic_spaceship.py`

Core script for generating individual spaceship assets with NASA-inspired design.

**Features:**
- Procedural geometry generation using bpy API
- Three ship types: `cargo`, `science`, `fighter`
- Three size categories: `small`, `medium`, `large`
- Automatic LOD (Level of Detail) generation
- PBR material assignment following STYLE_GUIDE.md color palette
- Unity-compatible FBX export with proper axes and scale
- Built-in validation against poly budgets and scale requirements

**Usage:**
```bash
# Basic usage
blender --background --python generate_basic_spaceship.py

# With parameters
blender --background --python generate_basic_spaceship.py -- \
  --type science \
  --size large \
  --output-dir path/to/output

# Validation only (no export)
blender --background --python generate_basic_spaceship.py -- --validate-only
```

**Ship Types:**

| Type | Description | Key Features |
|------|-------------|--------------|
| `cargo` | Boxy cargo hauler | Large cargo bay doors, utilitarian design |
| `science` | Research vessel | Sensor arrays, solar panels, antenna |
| `fighter` | Combat spacecraft | Compact, maneuverable, minimal profile |

**Size Categories:**

| Size | Dimensions | Poly Budget | Use Case |
|------|------------|-------------|----------|
| `small` | 10×6×4m | <3k triangles | Fighter pods, shuttles |
| `medium` | 15×8×5m | <8k triangles | General purpose, player ships |
| `large` | 25×12×8m | <15k triangles | Capital ships, stations |

### `batch_generate_ships.py`

Utility for generating complete asset catalogs for the MVP phase.

**Features:**
- Generates all ship type/size combinations
- Progress tracking and performance metrics
- Comprehensive validation reporting
- Automated file organization

**Usage:**
```bash
# Generate all variants (default)
blender --background --python batch_generate_ships.py

# Generate specific subset
blender --background --python batch_generate_ships.py -- \
  --types cargo science \
  --sizes small medium \
  --output-dir assets/models

# Custom report location
blender --background --python batch_generate_ships.py -- \
  --report-file assets/generation_report.txt
```

**Output:**
- Individual FBX files for each LOD level
- Generation performance report
- Validation results summary

## 🧪 Testing

The test suite validates generation quality, performance, and export compatibility.

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/ -k "test_validation" -v
pytest tests/ -k "test_export" -v

# Performance tests
pytest tests/ -k "test_performance" -v
```

**Test Coverage:**
- ✅ Geometry generation for all ship types/sizes
- ✅ Material creation and assignment
- ✅ LOD generation and decimate modifiers
- ✅ Asset validation (poly count, scale, materials)
- ✅ FBX export compatibility
- ✅ Performance characteristics
- ✅ Memory usage (no leaks)

## 🎨 Design Principles

All generated assets follow the NASA-inspired aesthetic defined in `docs/STYLE_GUIDE.md`:

**Visual Style:**
- Clean, modular design (like ISS modules)
- White hull with gray/aluminum structural elements
- Matte black for radiators and engines
- Blue accent markings
- Functional surface details (no decorative "greebles")

**Technical Standards:**
- 1 Blender unit = 1 meter (consistent scale)
- PBR materials with realistic metallic/roughness values
- Proper UV mapping for texture support
- Three LOD levels for performance optimization
- Unity-compatible FBX export settings

**Quality Targets:**
- Poly budgets are guidelines, not strict limits
- Adjust for visual quality and gameplay needs
- All assets must pass validation tests
- Clean topology suitable for real-time rendering

## 📦 Export Format

Generated FBX files are Unity-ready with:

```
Axis Configuration:
- Forward: -Z (Unity standard)
- Up: Y (Unity standard)
- Scale: Applied and consistent

Materials:
- PBR workflow (Principled BSDF)
- Separate texture files (not embedded)
- Material naming convention: {ShipType}_{MaterialType}

File Naming:
- Format: {type}_{size}_ship_LOD{level}.fbx
- Example: cargo_medium_ship_LOD0.fbx
```

## ⚡ Performance

**Generation Times:**
- Small ships: ~2-5 seconds
- Medium ships: ~5-10 seconds
- Large ships: ~10-20 seconds
- Full catalog (9 variants): ~60-120 seconds

**Memory Usage:**
- Minimal memory footprint
- Clean scene management prevents leaks
- Suitable for CI/CD batch processing

## 🔧 Development

### Adding New Ship Types

1. Extend `create_basic_spaceship_geometry()` function
2. Add type-specific geometry logic
3. Update material assignments in `assign_materials()`
4. Add test cases in `test_spaceship_generation.py`
5. Update documentation

### Adding New Features

1. Follow existing function patterns
2. Maintain headless Blender compatibility
3. Add validation tests
4. Update batch generation script
5. Document in README

### Debug Mode

For interactive development, you can run scripts inside Blender GUI:

```python
# In Blender Python console
exec(open('scripts/generate_basic_spaceship.py').read())
```

## 🐛 Troubleshooting

**Common Issues:**

1. **"bpy module not found"**
   - Run scripts with `blender --background --python script.py`
   - Or add Blender's Python to your PATH

2. **Export path errors**
   - Ensure output directories exist
   - Use absolute paths when possible
   - Check file permissions

3. **Triangle budget exceeded**
   - Adjust size parameters or complexity
   - Review LOD generation settings
   - Consider design simplification

4. **Scale issues in Unity**
   - Verify 1 Blender unit = 1 meter
   - Check FBX export scale settings
   - Apply transforms before export

**Debug Commands:**
```bash
# Verbose Blender output
blender --background --python script.py --debug-python

# Check generated files
ls -la projects/unity-space-sim/assets/models/

# Validate specific asset
blender --background --python generate_basic_spaceship.py -- --validate-only
```

## 📋 Requirements

**Blender:**
- Blender 3.6+ (LTS recommended)
- bpy API (included with Blender)

**Python Dependencies:**
- pytest (for testing)
- mathutils (included with Blender)

**System:**
- 4GB+ RAM for complex models
- OpenGL 3.3+ for headless rendering
- 1GB+ disk space for generated assets

## 🤝 Contributing

When modifying these scripts:

1. **Follow the NASA aesthetic** - Reference `docs/STYLE_GUIDE.md`
2. **Maintain headless compatibility** - Scripts must run in `--background` mode
3. **Add validation tests** - Every feature needs test coverage
4. **Update documentation** - Keep README and comments current
5. **Test export pipeline** - Verify Unity compatibility

## 📚 References

- [Blender Python API Documentation](https://docs.blender.org/api/current/)
- [Unity FBX Import Guide](https://docs.unity3d.com/Manual/HOWTO-ImportObjectBlender.html)
- [Project Style Guide](../docs/STYLE_GUIDE.md)
- [Issue #97 - Basic Spaceship Concept Art](https://github.com/dpaiton/agents/issues/97)

---

**Status:** Foundation implementation (Phase 1.5)
**Last Updated:** 2026-02-14
**Maintainer:** blender-engineer agent