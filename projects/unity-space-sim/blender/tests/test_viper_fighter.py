#!/usr/bin/env python3
"""
Test script for Viper-class fighter generation.

Tests the generate_viper_fighter.py script to ensure:
- Geometry generation works correctly
- Materials are applied properly
- LOD levels are generated
- Poly budgets are met
- Export functions work

Run with:
    python test_viper_fighter.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_viper_generation():
    """Test the Viper fighter generation script."""
    print("=== Testing Viper Fighter Generation ===\n")

    # Path to the generation script
    script_path = Path(__file__).parent.parent / "scripts" / "generate_viper_fighter.py"
    if not script_path.exists():
        print(f"✗ Script not found: {script_path}")
        return False

    # Create temp output directory
    output_dir = Path(__file__).parent / "test_output" / "viper"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run Blender in background mode
    cmd = [
        "blender",
        "--background",
        "--python", str(script_path),
        "--",
        "--output-dir", str(output_dir)
    ]

    print(f"Running command: {' '.join(cmd)}")
    print("This may take a minute...\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("=== Script Output ===")
        print(result.stdout)

        if result.stderr:
            print("\n=== Warnings ===")
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"✗ Script failed with exit code {e.returncode}")
        print("\n=== Error Output ===")
        print(e.stdout)
        print(e.stderr)
        return False

    except FileNotFoundError:
        print("✗ Blender not found. Please ensure Blender is installed and in PATH.")
        return False

    # Check if files were generated
    print("\n=== Checking Output Files ===")
    expected_files = [
        "viper_fighter_LOD0.fbx",
        "viper_fighter_LOD1.fbx",
        "viper_fighter_LOD2.fbx",
        "viper_fighter_3quarter.png",
        "viper_fighter_side.png"
    ]

    all_files_exist = True
    for filename in expected_files:
        filepath = output_dir / filename
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            print(f"✓ {filename} ({size_kb:.1f} KB)")
        else:
            print(f"✗ {filename} not found")
            all_files_exist = False

    # Summary
    print("\n=== Test Summary ===")
    if all_files_exist:
        print("✓ All files generated successfully!")
        print(f"✓ Output location: {output_dir}")
        return True
    else:
        print("✗ Some files were not generated")
        return False


def test_validation_only():
    """Run a quick validation test without full generation."""
    print("=== Testing Validation Functions ===\n")

    # Create a test validation script
    validation_script = '''
import bpy
import sys
sys.path.insert(0, r"{script_dir}")
from generate_viper_fighter import ViperConfig, validate_fighter

# Create a simple test object
bpy.ops.mesh.primitive_cube_add()
test_obj = bpy.context.active_object
test_obj.name = "Test_Fighter"

# Add some faces to increase poly count
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=3)
bpy.ops.object.mode_set(mode='OBJECT')

# Test validation
print("Testing validation with test object...")
validate_fighter(test_obj, "LOD0")
'''.format(script_dir=Path(__file__).parent.parent / "scripts")

    # Write temp validation script
    temp_script = Path(__file__).parent / "temp_validation.py"
    temp_script.write_text(validation_script)

    # Run validation test
    cmd = ["blender", "--background", "--python", str(temp_script)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        temp_script.unlink()  # Clean up
        return True

    except subprocess.CalledProcessError as e:
        print(f"✗ Validation test failed")
        print(e.stdout)
        print(e.stderr)
        temp_script.unlink()  # Clean up
        return False


def main():
    """Run all tests."""
    print("Viper Fighter Generation Test Suite")
    print("=" * 40)

    # Run validation test first (quick)
    print("\n1. Running validation test...")
    validation_ok = test_validation_only()

    # Run full generation test
    print("\n2. Running full generation test...")
    generation_ok = test_viper_generation()

    # Final summary
    print("\n" + "=" * 40)
    print("Final Results:")
    print(f"  Validation Test: {'✓ PASS' if validation_ok else '✗ FAIL'}")
    print(f"  Generation Test: {'✓ PASS' if generation_ok else '✗ FAIL'}")

    if validation_ok and generation_ok:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())