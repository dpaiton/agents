# Validation Rules

## Overview

This document defines **technical validation criteria and quality thresholds** for Unity Space Sim assets. All assets must pass validation before being imported into Unity.

**Philosophy:** These are **guidelines and targets**, not strict limits. Adjust based on gameplay needs and performance profiling. The goal is to maintain consistent quality while staying within performance budgets.

---

## Poly Count Budgets

### Target Triangle Counts (LOD0)

| Asset Category | Size Class | Target Tris | Max Tris | Notes |
|----------------|------------|-------------|----------|-------|
| **Small Ships** | 5-10m | 3,000 | 5,000 | Fighters, pods, small craft |
| | 10-20m | 5,000 | 10,000 | Cargo shuttles, interceptors |
| **Medium Ships** | 20-40m | 10,000 | 15,000 | Corvettes, mining barges |
| | 40-60m | 12,000 | 20,000 | Frigates, transports |
| **Large Ships** | 60-100m | 15,000 | 40,000 | Cruisers, freighters |
| | 100-200m | 25,000 | 60,000 | Battleships, carriers |
| **Capital Ships** | 200-500m | 40,000 | 80,000 | Dreadnoughts, colony ships |
| **Stations** | 50-100m modules | 15,000 | 40,000 | Modular station components |
| | 100-200m hubs | 25,000 | 60,000 | Central station hubs |
| **Props/Debris** | <5m | 500 | 2,000 | Small debris, cargo crates |
| | 5-10m | 1,000 | 3,000 | Satellites, probes |

**Philosophy:**
- **Targets** are for typical assets in that category
- **Max** is the hard ceiling before requiring approval/optimization
- Adjust based on screen time and importance (hero ships can exceed targets)

---

### LOD Requirements

**All assets >5m must have at least 2 LOD levels. Assets >50m should have 3 LOD levels.**

| LOD Level | Poly Ratio | Transition Distance | Purpose |
|-----------|-----------|---------------------|---------|
| **LOD0** | 100% (target) | 0 - 500m | Close-up, cockpit view |
| **LOD1** | ~40% of LOD0 | 500 - 2000m | Mid-range gameplay |
| **LOD2** | ~15% of LOD0 | 2000m+ | Distant objects, backgrounds |
| **LOD3** (optional) | ~5% of LOD0 | 5000m+ | Very distant (capital ships only) |

**LOD Transition Formula:**
```
Distance = BaseDistance * (ObjectSize / ReferenceSize)

Where:
- BaseDistance = 500m for LOD0→LOD1 transition
- ObjectSize = Largest dimension of asset in meters
- ReferenceSize = 20m (reference ship size)

Example:
- 10m ship: LOD0→LOD1 at 250m (500 * 10/20)
- 100m ship: LOD0→LOD1 at 2500m (500 * 100/20)
```

**Validation:**
```python
def validate_lods(asset, lod_count):
    """Check LOD requirements based on asset size."""
    size = max(asset.dimensions)

    if size > 50 and lod_count < 3:
        return False, f"Asset >50m requires 3 LODs, has {lod_count}"
    elif size > 5 and lod_count < 2:
        return False, f"Asset >5m requires 2 LODs, has {lod_count}"

    return True, "LOD count valid"
```

---

## Material Requirements

### Material Slot Limits

| Asset Size | Max Material Slots | Reason |
|------------|-------------------|--------|
| **Small (<20m)** | 2-3 | Reduce draw calls |
| **Medium (20-60m)** | 3-5 | Balance detail vs performance |
| **Large (60m+)** | 5-8 | Necessary for detail, use atlasing |

**Best Practice:** Combine materials where possible using texture atlases.

---

### Required PBR Channels

All materials must use Physically Based Rendering (PBR) workflow:

| Channel | Required | Format | Notes |
|---------|----------|--------|-------|
| **Base Color (Albedo)** | ✅ Yes | RGB | No lighting info baked in |
| **Metallic** | ✅ Yes | Grayscale | 0 = dielectric, 1 = metal |
| **Roughness** | ✅ Yes | Grayscale | 0 = smooth, 1 = rough |
| **Normal Map** | ⚠️ Recommended | RGB (tangent space) | For surface detail |
| **Ambient Occlusion** | ⚠️ Optional | Grayscale | Can bake into albedo |
| **Emissive** | ⚠️ Optional | RGB | For lights, screens, thrusters |

**Validation:**
```python
def validate_material(material):
    """Check material has required PBR channels."""
    required = ['Base Color', 'Metallic', 'Roughness']
    inputs = material.node_tree.nodes.get('Principled BSDF').inputs

    missing = [ch for ch in required if not inputs[ch].is_linked]
    if missing:
        return False, f"Missing channels: {', '.join(missing)}"

    return True, "Material valid"
```

---

### Texture Resolution Limits

| Asset Size | Albedo/Base Color | Normal Map | Other Maps |
|------------|-------------------|------------|------------|
| **Small (<10m)** | 512 - 1024 | 512 - 1024 | 512 |
| **Medium (10-50m)** | 1024 - 2048 | 1024 - 2048 | 512 - 1024 |
| **Large (50m+)** | 2048 (atlased) | 2048 (atlased) | 1024 |

**Atlas Strategy:** For large ships, use texture atlases instead of increasing resolution.

---

## Geometry Requirements

### Topology Rules

| Rule | Requirement | Why |
|------|-------------|-----|
| **No N-gons** | All faces must be tris or quads | Unity converts to tris, control the result |
| **Clean Geometry** | No duplicate vertices | Performance, correct normals |
| **Manifold Mesh** | No holes, no inverted normals | Correct rendering, physics |
| **Applied Transforms** | Scale = (1,1,1), Rotation = (0,0,0) | Correct size in Unity |
| **Sensible Pivot** | Origin at logical center/base | Easier placement, rotation |

**Validation:**
```python
def validate_topology(mesh):
    """Check mesh topology is clean."""
    checks = []

    # Check for n-gons
    ngons = [f for f in mesh.polygons if len(f.vertices) > 4]
    if ngons:
        checks.append((False, f"{len(ngons)} n-gons found"))
    else:
        checks.append((True, "No n-gons"))

    # Check for duplicate vertices (simplified check)
    # (In real code, use bmesh for accurate duplicate detection)

    # Check normals (no inverted faces)
    inverted = [f for f in mesh.polygons if f.area < 0]
    if inverted:
        checks.append((False, f"{len(inverted)} inverted faces"))
    else:
        checks.append((True, "No inverted normals"))

    return all(check[0] for check in checks), checks
```

---

### Scale & Units

**Standard: 1 Blender Unit = 1 Meter = 1 Unity Unit**

| Validation | Check | Pass Criteria |
|------------|-------|---------------|
| **Object Scale** | `obj.scale` | Must be (1.0, 1.0, 1.0) |
| **Applied Scale** | Transforms applied | Scale baked into geometry |
| **Size Accuracy** | Dimensions match config | ±5% tolerance |

**Example:**
```python
def validate_scale(obj, expected_length):
    """Validate object scale and size."""
    # Check scale is applied
    if obj.scale != (1.0, 1.0, 1.0):
        return False, f"Scale not applied: {obj.scale}"

    # Check size matches expected (within 5% tolerance)
    actual_length = obj.dimensions.x
    tolerance = expected_length * 0.05
    if abs(actual_length - expected_length) > tolerance:
        return False, f"Size mismatch: {actual_length}m vs {expected_length}m"

    return True, "Scale and size valid"
```

---

## Performance Metrics

### Draw Call Budget

**Goal: Minimize draw calls through batching and atlasing.**

| Scene Type | Max Draw Calls | Strategy |
|------------|----------------|----------|
| **Combat** | 100-200 | Many small ships, aggressive LODs |
| **Exploration** | 50-100 | Fewer large objects, static batching |
| **Station Interior** | 50-80 | Static batching, baked lighting |

**Techniques:**
- Static batching for stationary objects
- GPU instancing for repeated objects (asteroids, debris)
- Texture atlasing to reduce material count
- LOD culling for distant objects

---

### Texture Memory Budget

**Target: 2GB total VRAM for all assets (conservative estimate)**

| Category | VRAM Budget | Notes |
|----------|-------------|-------|
| **Ships** | 1.2 GB | Largest category, optimize aggressively |
| **Stations** | 400 MB | Reuse modules, atlasing |
| **Environment** | 200 MB | Skybox, nebulae, asteroids |
| **UI/HUD** | 100 MB | 2D textures |
| **Other** | 100 MB | Effects, particles |

**Per-Asset Estimate:**
```
VRAM = (Albedo_MB + Normal_MB + Other_MB) * LOD_count

Example (Medium Ship):
= (2K albedo: 16MB + 2K normal: 16MB + other: 4MB) * 2 LODs
= 36MB * 2 = 72MB per ship
```

---

## Export Requirements

### FBX Export Settings

**Required Settings (Unity Compatibility):**

| Setting | Value | Reason |
|---------|-------|--------|
| **Scale** | 1.0 | No conversion needed |
| **Axis Forward** | -Z | Unity forward axis |
| **Axis Up** | Y | Unity up axis |
| **Apply Unit** | ✅ Yes | Correct size |
| **Apply Transform** | ✅ Yes | Clean transforms |
| **Triangulate** | ✅ Yes | Consistent triangulation |
| **Tangent Space** | ✅ Yes | For normal maps |
| **Embed Textures** | ✅ Yes | Self-contained FBX |
| **Bake Animation** | ❌ No | No animation needed (yet) |

**Validation Script:**
```python
def export_fbx(objects, output_path):
    """Export with Unity-compatible settings."""
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        global_scale=1.0,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        object_types={'MESH'},
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        use_tspace=True,
        embed_textures=True,
        path_mode='COPY',
        batch_mode='OFF',
    )
    print(f"✓ Exported: {output_path}")
```

---

### File Naming Convention

**Pattern:** `{category}_{name}_LOD{n}.fbx`

**Examples:**
- `ship_cargo_small_LOD0.fbx`
- `ship_science_medium_LOD1.fbx`
- `station_hab_module_LOD0.fbx`
- `prop_cargo_crate_LOD0.fbx`

**Rules:**
- Lowercase with underscores
- No spaces or special characters
- LOD suffix for all levels (including LOD0)
- Descriptive but concise (max 50 chars)

---

## Automated Validation Pipeline

### Pre-Export Checks

Run before exporting to Unity:

```python
def validate_asset(obj, config):
    """Master validation function - runs all checks.

    Returns:
        (bool, list[str]): (passed, [messages])
    """
    messages = []

    # 1. Poly count
    poly_count = len(obj.data.polygons) * 2  # Tris (rough estimate)
    budget = config.get('poly_budget', 10000)
    if poly_count > budget:
        messages.append(f"✗ FAIL: Poly count {poly_count} > {budget}")
        passed = False
    else:
        messages.append(f"✓ PASS: Poly count {poly_count}/{budget}")
        passed = True

    # 2. Scale
    if obj.scale != (1.0, 1.0, 1.0):
        messages.append(f"✗ FAIL: Scale not applied: {obj.scale}")
        passed = False
    else:
        messages.append("✓ PASS: Scale applied")

    # 3. Materials
    mat_count = len(obj.material_slots)
    max_mats = 5
    if mat_count == 0:
        messages.append("✗ FAIL: No materials assigned")
        passed = False
    elif mat_count > max_mats:
        messages.append(f"⚠ WARN: {mat_count} materials (recommended <{max_mats})")
    else:
        messages.append(f"✓ PASS: {mat_count} materials")

    # 4. Topology
    ngons = [f for f in obj.data.polygons if len(f.vertices) > 4]
    if ngons:
        messages.append(f"✗ FAIL: {len(ngons)} n-gons found")
        passed = False
    else:
        messages.append("✓ PASS: No n-gons")

    # 5. LODs (check if LOD objects exist)
    lod_count = len([o for o in bpy.data.objects if o.name.startswith(obj.name)])
    size = max(obj.dimensions)
    required_lods = 3 if size > 50 else 2 if size > 5 else 1
    if lod_count < required_lods:
        messages.append(f"✗ FAIL: Need {required_lods} LODs, have {lod_count}")
        passed = False
    else:
        messages.append(f"✓ PASS: {lod_count} LODs")

    return passed, messages
```

### Post-Export Unity Checks

Run after importing to Unity (optional):

```csharp
// Unity C# validation script (AssetPostprocessor)
public class AssetValidator : AssetPostprocessor
{
    void OnPostprocessModel(GameObject go)
    {
        // Check poly count
        var meshes = go.GetComponentsInChildren<MeshFilter>();
        int totalTris = meshes.Sum(mf => mf.sharedMesh.triangles.Length / 3);
        Debug.Log($"Total tris: {totalTris}");

        // Check materials
        var renderers = go.GetComponentsInChildren<Renderer>();
        int materialCount = renderers.Sum(r => r.sharedMaterials.Length);
        if (materialCount > 5)
            Debug.LogWarning($"High material count: {materialCount}");

        // Check scale
        if (go.transform.localScale != Vector3.one)
            Debug.LogWarning($"Non-uniform scale: {go.transform.localScale}");

        // Check LOD group
        var lodGroup = go.GetComponent<LODGroup>();
        if (lodGroup == null && totalTris > 5000)
            Debug.LogWarning("No LOD group on high-poly asset");
    }
}
```

---

## Quality Checklist

### Before Export (Blender)

- ✅ Poly count within budget (see table above)
- ✅ Topology clean (no n-gons, manifold mesh)
- ✅ Scale applied (1.0, 1.0, 1.0)
- ✅ Size matches config (±5% tolerance)
- ✅ Materials assigned (PBR channels present)
- ✅ Material count reasonable (<5 for small/medium ships)
- ✅ LODs generated (2-3 levels based on size)
- ✅ Textures embedded in FBX
- ✅ Pivot at logical center
- ✅ Named correctly (category_name_LOD#)

### After Import (Unity)

- ✅ FBX imports without errors
- ✅ Scale is correct (1 unit = 1 meter)
- ✅ Materials look correct (PBR values)
- ✅ LOD transitions are smooth
- ✅ No missing textures
- ✅ Prefab created successfully
- ✅ Colliders generated/attached
- ✅ Performance acceptable (FPS check)

---

## Common Issues & Fixes

### Issue: Poly Count Too High

**Diagnosis:** Asset exceeds poly budget at LOD0

**Fixes:**
1. Simplify geometry (remove unnecessary detail)
2. Use normal maps for detail instead of geometry
3. Adjust decimate ratio for LODs
4. Consider splitting into multiple lower-poly pieces

---

### Issue: N-gons Present

**Diagnosis:** Faces with >4 vertices

**Fixes:**
1. Triangulate manually in Blender (select faces → Ctrl+T)
2. Enable "Triangulate" in FBX export settings
3. Fix topology at source (proper edge flow)

---

### Issue: Scale Not Applied

**Diagnosis:** `obj.scale != (1.0, 1.0, 1.0)`

**Fix:**
```python
# In Blender
bpy.ops.object.transform_apply(scale=True, rotation=True, location=False)
```

---

### Issue: Too Many Materials

**Diagnosis:** Material count > 5-8

**Fixes:**
1. Combine similar materials (e.g., merge "white_hull_1" and "white_hull_2")
2. Use texture atlasing (multiple textures → one texture)
3. Use vertex colors for variation instead of separate materials

---

### Issue: LOD Transitions Visible ("Popping")

**Diagnosis:** Abrupt change when LOD switches

**Fixes:**
1. Adjust LOD transition distances (make transitions further apart)
2. Smooth LOD transitions in Unity (use fade mode)
3. Reduce poly difference between LOD levels (smaller jumps)

---

## Performance Profiling

### Unity Profiler Metrics

**Target Frame Budget (60 FPS = 16.6ms):**

| Category | Budget | Notes |
|----------|--------|-------|
| **Rendering** | 8ms | GPU time for drawing |
| **Scripts** | 3ms | C# gameplay code |
| **Physics** | 2ms | Collision detection |
| **Other** | 3.6ms | Audio, UI, etc. |

**Rendering Breakdown:**
- Draw calls: <200
- Tris rendered: <500k on screen
- SetPass calls: <100 (material changes)

**Tools:**
- Unity Profiler (Window → Analysis → Profiler)
- Frame Debugger (Window → Analysis → Frame Debugger)
- Stats window (Game view stats overlay)

---

## Exceptions & Overrides

### When to Exceed Budgets

**Approved Exceptions:**
1. **Hero Ships** - Player ship, main story ships (can use 2x poly budget)
2. **Cinematic Assets** - Non-gameplay cutscene ships (no budget)
3. **Distant Objects** - Never seen close-up (can skip high LODs)
4. **Unique Set Pieces** - One-time story moments (relaxed limits)

**Approval Process:**
1. Document why standard budget is insufficient
2. Show performance impact (profiler data)
3. Propose optimization trade-offs
4. Get architect/lead engineer sign-off

---

## Continuous Improvement

**These rules will evolve based on:**
- Performance profiling data
- Playtesting feedback
- Hardware target updates (if min spec changes)
- Workflow optimization discoveries

**Review Schedule:** After each major asset batch, review:
- Are budgets too strict/loose?
- Are LOD transitions working?
- Is visual quality consistent?
- Are poly budgets realistic?

---

**Status:** Foundation documentation (Phase 1)
**Last Updated:** 2026-02-12
**Maintainer:** Architect Agent
