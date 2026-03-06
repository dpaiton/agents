#!/usr/bin/env python3
"""Generate basic spaceship concept using Blender Python API.

Creates NASA-inspired sci-fi spacecraft following the design guidelines from STYLE_GUIDE.md.
This script generates simple, believable spaceship geometry suitable for Unity primitives-based
MVP implementation (Issue #97).

Usage:
    # Command line (headless Blender)
    blender --background --python generate_basic_spaceship.py -- --type cargo --size medium

    # From within Blender
    exec(open('generate_basic_spaceship.py').read())

Requirements:
    - Blender 3.6+ with bpy API
    - No external dependencies beyond standard Blender modules
"""

import bpy
import sys
import argparse
import os
from typing import List, Tuple, Dict, Any


def clear_scene():
    """Remove all default objects (cube, light, camera) from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def create_material(name: str, base_color: Tuple[float, float, float, float],
                   metallic: float = 0.1, roughness: float = 0.4) -> bpy.types.Material:
    """Create PBR material following NASA-inspired aesthetic.

    Args:
        name: Material name
        base_color: RGBA color tuple
        metallic: Metallic value (0.0-1.0)
        roughness: Roughness value (0.0-1.0)

    Returns:
        Created material object
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True

    # Get the principled BSDF node
    principled = mat.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = base_color
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = roughness

    return mat


def create_basic_spaceship_geometry(ship_type: str = "cargo", length: float = 15.0,
                                  width: float = 8.0, height: float = 5.0) -> bpy.types.Object:
    """Generate basic spaceship geometry using modular NASA-inspired design.

    Creates a simple but believable spaceship following the design principles:
    - Modular, boxy design (like ISS modules)
    - Functional aesthetic (cargo bay, cockpit, engines visible)
    - Simple enough for Unity primitive implementation

    Args:
        ship_type: Type of ship ('cargo', 'science', 'fighter')
        length: Length in meters (Blender units)
        width: Width in meters
        height: Height in meters

    Returns:
        Main ship object with all components parented
    """

    # Create main hull (central body)
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
    hull = bpy.context.active_object
    hull.name = f"{ship_type}_hull"

    # Scale hull to desired dimensions
    hull.scale = (length/2, width/2, height/2)
    bpy.ops.object.transform_apply(scale=True)

    # Add bevel for realistic edges (NASA hardware has rounded edges)
    bevel_mod = hull.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = 0.02  # 2cm bevel for realistic edge
    bevel_mod.segments = 2

    # Create cockpit/command module (front section)
    cockpit_size = min(width, height) * 0.7
    bpy.ops.mesh.primitive_cube_add(size=cockpit_size, location=(length/2.5, 0, height/4))
    cockpit = bpy.context.active_object
    cockpit.name = f"{ship_type}_cockpit"

    # Bevel cockpit
    cockpit_bevel = cockpit.modifiers.new(name="Bevel", type='BEVEL')
    cockpit_bevel.width = 0.015
    cockpit_bevel.segments = 2

    # Create engine nacelles (rear)
    engine_spacing = width * 0.6
    engines = []

    for i, side in enumerate([-1, 1]):
        engine_length = length * 0.3
        engine_radius = min(width, height) * 0.15

        bpy.ops.mesh.primitive_cylinder_add(
            radius=engine_radius,
            depth=engine_length,
            location=(-length/3, side * engine_spacing/2, 0),
            rotation=(0, 1.5708, 0)  # Rotate 90 degrees around Y-axis
        )

        engine = bpy.context.active_object
        engine.name = f"{ship_type}_engine_{i+1}"
        engines.append(engine)

        # Add slight taper to engines (truncated cone shape)
        bevel_eng = engine.modifiers.new(name="Bevel", type='BEVEL')
        bevel_eng.width = 0.01
        bevel_eng.segments = 1

    # Add functional details based on ship type
    details = []

    if ship_type == "cargo":
        # Large cargo bay doors (middle section)
        door_width = width * 0.8
        door_height = height * 0.6
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(0, 0, -height/4)
        )
        cargo_bay = bpy.context.active_object
        cargo_bay.name = f"{ship_type}_cargo_bay"
        cargo_bay.scale = (length/3, door_width, door_height/2)
        bpy.ops.object.transform_apply(scale=True)
        details.append(cargo_bay)

    elif ship_type == "science":
        # Sensor array/antenna (top)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.5,
            depth=2.0,
            location=(0, 0, height/2 + 1.0)
        )
        sensor = bpy.context.active_object
        sensor.name = f"{ship_type}_sensor_array"
        details.append(sensor)

        # Solar panels (sides)
        for side in [-1, 1]:
            bpy.ops.mesh.primitive_cube_add(
                size=1.0,
                location=(0, side * (width/2 + 1.5), 0)
            )
            panel = bpy.context.active_object
            panel.name = f"{ship_type}_solar_panel_{abs(side)}"
            panel.scale = (length/4, 0.1, height/3)
            bpy.ops.object.transform_apply(scale=True)
            details.append(panel)

    # Parent all components to hull
    all_objects = [hull] + engines + details + [cockpit]

    # Select all objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in all_objects:
        obj.select_set(True)

    # Make hull active object
    bpy.context.view_layer.objects.active = hull

    # Join all objects into single mesh
    bpy.ops.object.join()

    return hull


def assign_materials(obj: bpy.types.Object, ship_type: str):
    """Assign NASA-inspired PBR materials to different parts of the ship.

    Creates and applies materials following the color palette from STYLE_GUIDE.md:
    - White hull (primary)
    - Aluminum structural elements
    - Matte black radiators/engines
    - Blue accent markings
    """

    # Create materials following STYLE_GUIDE.md palette
    materials = {
        'hull_white': create_material(
            "Hull_White",
            (0.94, 0.94, 0.94, 1.0),  # #F0F0F0
            metallic=0.1,
            roughness=0.4
        ),
        'aluminum': create_material(
            "Aluminum_Structural",
            (0.66, 0.66, 0.66, 1.0),  # #A8A8A8
            metallic=0.9,
            roughness=0.6
        ),
        'engine_black': create_material(
            "Engine_Black",
            (0.1, 0.1, 0.1, 1.0),  # #1A1A1A
            metallic=0.2,
            roughness=0.2
        ),
        'nasa_blue': create_material(
            "NASA_Blue_Accent",
            (0.0, 0.32, 0.65, 1.0),  # #0052A5
            metallic=0.0,
            roughness=0.7
        )
    }

    # Assign hull white as default material
    obj.data.materials.clear()
    for mat_name, material in materials.items():
        obj.data.materials.append(material)

    # Set active material to hull white
    if obj.data.materials:
        obj.active_material = materials['hull_white']


def generate_lods(base_obj: bpy.types.Object, lod1_ratio: float = 0.5,
                  lod2_ratio: float = 0.25) -> List[bpy.types.Object]:
    """Generate Level of Detail (LOD) meshes using Decimate modifier.

    Args:
        base_obj: Original high-detail mesh (LOD0)
        lod1_ratio: Triangle reduction ratio for LOD1 (0.5 = 50% reduction)
        lod2_ratio: Triangle reduction ratio for LOD2 (0.25 = 75% reduction)

    Returns:
        List of [LOD0, LOD1, LOD2] objects
    """

    # LOD0 is the original object
    lod0 = base_obj
    lod0.name = lod0.name.replace("_hull", "_LOD0")

    # Create LOD1
    lod1 = lod0.copy()
    lod1.data = lod0.data.copy()
    lod1.name = lod0.name.replace("_LOD0", "_LOD1")
    bpy.context.collection.objects.link(lod1)

    # Apply Decimate modifier to LOD1
    decimate_1 = lod1.modifiers.new(name="Decimate_LOD1", type='DECIMATE')
    decimate_1.ratio = lod1_ratio
    decimate_1.use_collapse_triangulate = True

    # Create LOD2
    lod2 = lod0.copy()
    lod2.data = lod0.data.copy()
    lod2.name = lod0.name.replace("_LOD0", "_LOD2")
    bpy.context.collection.objects.link(lod2)

    # Apply Decimate modifier to LOD2
    decimate_2 = lod2.modifiers.new(name="Decimate_LOD2", type='DECIMATE')
    decimate_2.ratio = lod2_ratio
    decimate_2.use_collapse_triangulate = True

    return [lod0, lod1, lod2]


def validate_asset(obj: bpy.types.Object, max_triangles: int,
                   expected_dimensions: Tuple[float, float, float]) -> Dict[str, Any]:
    """Validate generated asset against technical standards.

    Args:
        obj: Object to validate
        max_triangles: Maximum allowed triangle count
        expected_dimensions: Expected (length, width, height) in meters

    Returns:
        Dict with validation results
    """

    # Get mesh data
    mesh = obj.data

    # Count triangles (each quad face = 2 triangles)
    triangle_count = 0
    for poly in mesh.polygons:
        triangle_count += len(poly.vertices) - 2

    # Get object dimensions
    dims = obj.dimensions
    actual_dimensions = (dims.x, dims.y, dims.z)

    validation_results = {
        'triangle_count': triangle_count,
        'max_triangles': max_triangles,
        'triangle_budget_ok': triangle_count <= max_triangles,
        'actual_dimensions': actual_dimensions,
        'expected_dimensions': expected_dimensions,
        'scale_accuracy': all(abs(actual - expected) < 1.0 for actual, expected in
                            zip(actual_dimensions, expected_dimensions)),
        'material_count': len(obj.data.materials),
        'has_materials': len(obj.data.materials) > 0,
        'has_uv_map': len(obj.data.uv_layers) > 0
    }

    return validation_results


def export_fbx(objects: List[bpy.types.Object], output_path: str):
    """Export objects to FBX with Unity-compatible settings.

    Args:
        objects: List of objects to export
        output_path: Full path for output file
    """

    # Select objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Export with Unity-compatible settings
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
        axis_forward='-Z',  # Unity uses -Z forward
        axis_up='Y',        # Unity uses Y up
        apply_scale_options='FBX_SCALE_ALL',
        object_types={'MESH'},
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        use_tspace=True,  # Tangent space for normal maps
        embed_textures=False,  # Keep textures separate for Unity
        path_mode='STRIP'  # Strip paths for portability
    )

    print(f"Exported FBX: {output_path}")


def main():
    """Main function with command line argument parsing."""

    # Parse command line arguments (for headless Blender execution)
    parser = argparse.ArgumentParser(description="Generate basic spaceship concept")
    parser.add_argument('--type', default='cargo', choices=['cargo', 'science', 'fighter'],
                       help='Type of spaceship to generate')
    parser.add_argument('--size', default='medium', choices=['small', 'medium', 'large'],
                       help='Size category of the ship')
    parser.add_argument('--output-dir', default='projects/unity-space-sim/assets/models',
                       help='Output directory for FBX files')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only run validation, do not export')

    # Handle Blender's argument parsing (arguments after -- are for the script)
    try:
        # Find the -- separator in sys.argv
        if '--' in sys.argv:
            script_args = sys.argv[sys.argv.index('--') + 1:]
        else:
            script_args = []

        args = parser.parse_args(script_args)
    except SystemExit:
        # If no arguments provided, use defaults
        args = parser.parse_args([])

    # Size-based parameters
    size_params = {
        'small': {'length': 10.0, 'width': 6.0, 'height': 4.0, 'max_tris': 3000},
        'medium': {'length': 15.0, 'width': 8.0, 'height': 5.0, 'max_tris': 8000},
        'large': {'length': 25.0, 'width': 12.0, 'height': 8.0, 'max_tris': 15000}
    }

    params = size_params[args.size]

    print(f"Generating {args.size} {args.type} spaceship...")

    # Clear scene
    clear_scene()

    # Generate spaceship
    ship = create_basic_spaceship_geometry(
        ship_type=args.type,
        length=params['length'],
        width=params['width'],
        height=params['height']
    )

    # Assign materials
    assign_materials(ship, args.type)

    # Generate LODs
    lods = generate_lods(ship)

    # Validate
    validation = validate_asset(
        ship,
        max_triangles=params['max_tris'],
        expected_dimensions=(params['length'], params['width'], params['height'])
    )

    print("Validation Results:")
    print(f"  Triangle count: {validation['triangle_count']}/{validation['max_triangles']}")
    print(f"  Budget OK: {validation['triangle_budget_ok']}")
    print(f"  Dimensions: {validation['actual_dimensions']}")
    print(f"  Scale accurate: {validation['scale_accuracy']}")
    print(f"  Materials: {validation['material_count']}")

    if not validation['triangle_budget_ok']:
        print("WARNING: Triangle budget exceeded!")

    if not args.validate_only:
        # Export each LOD separately
        for i, lod_obj in enumerate(lods):
            output_filename = f"{args.type}_{args.size}_ship_LOD{i}.fbx"
            output_path = os.path.join(args.output_dir, output_filename)
            export_fbx([lod_obj], output_path)

    print("Spaceship generation complete!")


if __name__ == '__main__':
    main()