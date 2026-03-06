#!/usr/bin/env python3
"""Batch generate multiple spaceship variants for the Unity Space Sim project.

This script generates a complete set of spaceship assets for the MVP, creating
multiple types, sizes, and LOD levels following the NASA-inspired aesthetic.

Usage:
    # Generate all ship variants
    blender --background --python batch_generate_ships.py

    # Generate specific subset
    blender --background --python batch_generate_ships.py -- --types cargo science --sizes small medium

Requirements:
    - Blender 3.6+ with bpy API
    - generate_basic_spaceship.py in same directory
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Import our spaceship generation functions
sys.path.insert(0, str(Path(__file__).parent))
from generate_basic_spaceship import (
    clear_scene,
    create_basic_spaceship_geometry,
    assign_materials,
    generate_lods,
    validate_asset,
    export_fbx
)


def generate_ship_variant(ship_type: str, size: str, output_dir: str) -> dict:
    """Generate a single ship variant with all LODs.

    Args:
        ship_type: Type of ship ('cargo', 'science', 'fighter')
        size: Size category ('small', 'medium', 'large')
        output_dir: Directory for FBX output files

    Returns:
        Dict with generation results and validation data
    """

    # Size parameters (matching generate_basic_spaceship.py)
    size_params = {
        'small': {'length': 10.0, 'width': 6.0, 'height': 4.0, 'max_tris': 3000},
        'medium': {'length': 15.0, 'width': 8.0, 'height': 5.0, 'max_tris': 8000},
        'large': {'length': 25.0, 'width': 12.0, 'height': 8.0, 'max_tris': 15000}
    }

    params = size_params[size]
    variant_name = f"{ship_type}_{size}"

    print(f"Generating {variant_name} ship...")

    # Clear scene
    clear_scene()

    start_time = time.time()

    # Generate spaceship geometry
    ship = create_basic_spaceship_geometry(
        ship_type=ship_type,
        length=params['length'],
        width=params['width'],
        height=params['height']
    )

    # Apply materials
    assign_materials(ship, ship_type)

    # Generate LODs
    lods = generate_lods(ship)

    # Validate primary LOD
    validation = validate_asset(
        lods[0],
        max_triangles=params['max_tris'],
        expected_dimensions=(params['length'], params['width'], params['height'])
    )

    generation_time = time.time() - start_time

    # Export each LOD
    exported_files = []
    for i, lod_obj in enumerate(lods):
        output_filename = f"{variant_name}_LOD{i}.fbx"
        output_path = os.path.join(output_dir, output_filename)
        export_fbx([lod_obj], output_path)
        exported_files.append(output_path)

    # Return results
    result = {
        'variant_name': variant_name,
        'ship_type': ship_type,
        'size': size,
        'generation_time': generation_time,
        'exported_files': exported_files,
        'validation': validation,
        'triangle_count': validation['triangle_count'],
        'triangle_budget_ok': validation['triangle_budget_ok'],
        'dimensions': validation['actual_dimensions']
    }

    return result


def generate_ship_catalog(ship_types: list, sizes: list, output_dir: str) -> dict:
    """Generate a complete catalog of ship variants.

    Args:
        ship_types: List of ship types to generate
        sizes: List of sizes to generate
        output_dir: Output directory for all assets

    Returns:
        Dict with summary of all generated variants
    """

    results = {
        'variants': [],
        'total_generation_time': 0,
        'total_files_exported': 0,
        'validation_summary': {
            'passed': 0,
            'failed': 0,
            'warnings': []
        }
    }

    # Generate all combinations
    for ship_type in ship_types:
        for size in sizes:
            try:
                variant_result = generate_ship_variant(ship_type, size, output_dir)
                results['variants'].append(variant_result)
                results['total_generation_time'] += variant_result['generation_time']
                results['total_files_exported'] += len(variant_result['exported_files'])

                # Track validation results
                if variant_result['triangle_budget_ok']:
                    results['validation_summary']['passed'] += 1
                else:
                    results['validation_summary']['failed'] += 1
                    warning = f"{variant_result['variant_name']}: {variant_result['triangle_count']} triangles (over budget)"
                    results['validation_summary']['warnings'].append(warning)

                print(f"✓ {variant_result['variant_name']}: {variant_result['triangle_count']} triangles, {variant_result['generation_time']:.1f}s")

            except Exception as e:
                print(f"✗ Failed to generate {ship_type}_{size}: {str(e)}")
                results['validation_summary']['failed'] += 1
                results['validation_summary']['warnings'].append(f"{ship_type}_{size}: Generation failed - {str(e)}")

    return results


def print_generation_summary(results: dict):
    """Print a detailed summary of batch generation results."""

    print("\n" + "="*60)
    print("BATCH GENERATION SUMMARY")
    print("="*60)

    print(f"Variants generated: {len(results['variants'])}")
    print(f"Total files exported: {results['total_files_exported']}")
    print(f"Total generation time: {results['total_generation_time']:.1f} seconds")
    print(f"Average time per variant: {results['total_generation_time']/max(len(results['variants']), 1):.1f} seconds")

    validation = results['validation_summary']
    print("\nValidation Results:")
    print(f"  ✓ Passed: {validation['passed']}")
    print(f"  ✗ Failed: {validation['failed']}")

    if validation['warnings']:
        print("\nWarnings:")
        for warning in validation['warnings']:
            print(f"  ⚠ {warning}")

    print("\nGenerated Variants:")
    for variant in results['variants']:
        status = "✓" if variant['triangle_budget_ok'] else "⚠"
        print(f"  {status} {variant['variant_name']:15} {variant['triangle_count']:5} tri  {variant['generation_time']:4.1f}s")

    print("\n" + "="*60)


def main():
    """Main function for batch generation."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Batch generate spaceship variants")
    parser.add_argument('--types', nargs='+',
                       default=['cargo', 'science', 'fighter'],
                       choices=['cargo', 'science', 'fighter'],
                       help='Ship types to generate')
    parser.add_argument('--sizes', nargs='+',
                       default=['small', 'medium', 'large'],
                       choices=['small', 'medium', 'large'],
                       help='Size categories to generate')
    parser.add_argument('--output-dir',
                       default='projects/unity-space-sim/assets/models',
                       help='Output directory for FBX files')
    parser.add_argument('--report-file',
                       default='projects/unity-space-sim/assets/models/generation_report.txt',
                       help='File to save generation report')

    # Handle Blender's argument parsing
    try:
        if '--' in sys.argv:
            script_args = sys.argv[sys.argv.index('--') + 1:]
        else:
            script_args = []
        args = parser.parse_args(script_args)
    except SystemExit:
        # Use defaults if no arguments
        args = parser.parse_args([])

    print("Unity Space Sim - Batch Ship Generation")
    print(f"Ship types: {args.types}")
    print(f"Sizes: {args.sizes}")
    print(f"Output directory: {args.output_dir}")
    print("")

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate all variants
    start_time = time.time()
    results = generate_ship_catalog(args.types, args.sizes, args.output_dir)
    total_time = time.time() - start_time

    # Print summary
    print_generation_summary(results)

    # Save report to file
    if args.report_file:
        report_dir = os.path.dirname(args.report_file)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)

        with open(args.report_file, 'w') as f:
            f.write("Unity Space Sim - Ship Generation Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total time: {total_time:.1f} seconds\n\n")

            f.write("Variants:\n")
            for variant in results['variants']:
                f.write(f"  {variant['variant_name']:15} {variant['triangle_count']:5} triangles\n")
                for file_path in variant['exported_files']:
                    f.write(f"    -> {os.path.basename(file_path)}\n")

            f.write("\nValidation Issues:\n")
            for warning in results['validation_summary']['warnings']:
                f.write(f"  ⚠ {warning}\n")

        print(f"Report saved to: {args.report_file}")

    print(f"\nBatch generation completed in {total_time:.1f} seconds!")


if __name__ == '__main__':
    main()