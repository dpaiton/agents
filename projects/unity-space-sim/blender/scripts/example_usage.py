#!/usr/bin/env python3
"""Example usage of Blender spaceship generation scripts.

This script demonstrates how to use the generation functions programmatically
and provides examples for common use cases.

Run with:
    blender --background --python example_usage.py
"""

import bpy
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_basic_spaceship import (
    clear_scene,
    create_basic_spaceship_geometry,
    assign_materials,
    generate_lods,
    validate_asset,
    export_fbx
)


def example_single_ship():
    """Example: Generate a single ship with custom parameters."""
    print("Example 1: Single Ship Generation")
    print("-" * 40)

    # Clear scene
    clear_scene()

    # Generate a medium cargo ship
    ship = create_basic_spaceship_geometry(
        ship_type="cargo",
        length=18.0,
        width=10.0,
        height=6.0
    )

    # Apply materials
    assign_materials(ship, "cargo")

    # Validate
    validation = validate_asset(
        ship,
        max_triangles=10000,
        expected_dimensions=(18.0, 10.0, 6.0)
    )

    print(f"Triangle count: {validation['triangle_count']}")
    print(f"Budget OK: {validation['triangle_budget_ok']}")
    print(f"Dimensions: {validation['actual_dimensions']}")
    print()


def example_lod_generation():
    """Example: Generate LODs with custom reduction ratios."""
    print("Example 2: Custom LOD Generation")
    print("-" * 40)

    clear_scene()

    # Generate science vessel
    ship = create_basic_spaceship_geometry("science", 20.0, 8.0, 5.0)
    assign_materials(ship, "science")

    # Generate LODs with custom ratios
    lods = generate_lods(ship, lod1_ratio=0.7, lod2_ratio=0.4)

    # Validate each LOD
    for i, lod in enumerate(lods):
        # Get triangle count by applying modifiers temporarily
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = lod.evaluated_get(depsgraph)
        tri_count = sum(len(poly.vertices) - 2 for poly in eval_obj.data.polygons)

        print(f"LOD{i}: {tri_count} triangles")

    print()


def example_material_customization():
    """Example: Custom material creation and assignment."""
    print("Example 3: Custom Materials")
    print("-" * 40)

    clear_scene()

    # Generate ship
    ship = create_basic_spaceship_geometry("fighter", 12.0, 5.0, 3.0)

    # Create custom materials
    from generate_basic_spaceship import create_material

    # Custom red material for fighter
    red_material = create_material(
        "Fighter_Red_Accent",
        (0.8, 0.1, 0.1, 1.0),  # Red color
        metallic=0.3,
        roughness=0.5
    )

    # Custom blue glow material
    blue_glow = create_material(
        "Engine_Glow_Blue",
        (0.0, 0.2, 1.0, 1.0),  # Bright blue
        metallic=0.0,
        roughness=0.1
    )

    # Assign materials
    ship.data.materials.clear()
    ship.data.materials.append(red_material)
    ship.data.materials.append(blue_glow)

    print(f"Applied {len(ship.data.materials)} custom materials")
    print()


def example_batch_validation():
    """Example: Validate multiple ships against different criteria."""
    print("Example 4: Batch Validation")
    print("-" * 40)

    ship_configs = [
        {"type": "cargo", "size": (15, 8, 5), "max_tris": 8000},
        {"type": "science", "size": (12, 6, 4), "max_tris": 6000},
        {"type": "fighter", "size": (8, 4, 3), "max_tris": 4000}
    ]

    validation_results = []

    for config in ship_configs:
        clear_scene()

        # Generate ship
        ship = create_basic_spaceship_geometry(
            config["type"],
            config["size"][0],
            config["size"][1],
            config["size"][2]
        )

        assign_materials(ship, config["type"])

        # Validate
        validation = validate_asset(
            ship,
            max_triangles=config["max_tris"],
            expected_dimensions=config["size"]
        )

        validation_results.append({
            "type": config["type"],
            "validation": validation
        })

        status = "✓" if validation['triangle_budget_ok'] else "✗"
        print(f"{status} {config['type']:8} {validation['triangle_count']:5} tri")

    print()

    # Summary
    passed = sum(1 for r in validation_results if r['validation']['triangle_budget_ok'])
    print(f"Validation summary: {passed}/{len(validation_results)} passed")
    print()


def example_export_workflow():
    """Example: Complete generation and export workflow."""
    print("Example 5: Complete Export Workflow")
    print("-" * 40)

    # Create temporary output directory
    output_dir = "/tmp/blender_ship_examples"
    os.makedirs(output_dir, exist_ok=True)

    clear_scene()

    # Generate ship
    ship = create_basic_spaceship_geometry("cargo", 16.0, 9.0, 5.5)
    assign_materials(ship, "cargo")

    # Generate LODs
    lods = generate_lods(ship)

    # Export each LOD
    for i, lod in enumerate(lods):
        output_path = os.path.join(output_dir, f"example_cargo_LOD{i}.fbx")
        export_fbx([lod], output_path)
        print(f"Exported: {os.path.basename(output_path)}")

    print(f"Files saved to: {output_dir}")
    print()


def main():
    """Run all examples."""
    print("Blender Spaceship Generation - Usage Examples")
    print("=" * 50)
    print()

    try:
        example_single_ship()
        example_lod_generation()
        example_material_customization()
        example_batch_validation()
        example_export_workflow()

        print("All examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()