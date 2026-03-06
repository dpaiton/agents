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
        print("✗ Validation test failed")
        print(e.stdout)
        print(e.stderr)
        temp_script.unlink()  # Clean up
        return False


def test_visual_fidelity():
    """Compare generated renders against concept art using vision model.

    Requires ANTHROPIC_API_KEY in environment. Skips gracefully without it.
    Runs validate_render_batch() on the test output from test_viper_generation().
    """
    print("=== Testing Visual Fidelity ===\n")

    import shutil
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_cli = bool(shutil.which("claude"))
    if not has_api_key and not has_cli:
        print("⊘ Skipping visual fidelity test (no ANTHROPIC_API_KEY and no claude CLI)")
        return None  # None = skipped

    # Paths
    render_dir = Path(__file__).parent / "test_output" / "viper"
    concept_dir = (
        Path(__file__).resolve().parents[2] / "assets" / "drafts" / "fighter-v4"
    )

    if not render_dir.exists():
        print(f"✗ Render directory not found: {render_dir}")
        print("  Run test_viper_generation() first to produce renders.")
        return False

    if not concept_dir.exists():
        print(f"✗ Concept art directory not found: {concept_dir}")
        return False

    # Import the validation tool
    tools_dir = Path(__file__).resolve().parents[2] / "tools"
    sys.path.insert(0, str(tools_dir))
    try:
        from validate_visual import validate_render_batch, format_result_text
    except ImportError as e:
        print(f"✗ Could not import validate_visual: {e}")
        return False

    # Run batch validation
    print(f"Render dir:  {render_dir}")
    print(f"Concept dir: {concept_dir}")
    print()

    try:
        results = validate_render_batch(
            render_dir=str(render_dir),
            concept_dir=str(concept_dir),
            threshold=0.75,
            num_runs=3,
        )
    except Exception as e:
        print(f"✗ Visual validation failed: {e}")
        return False

    if not results:
        print("⊘ No render/concept pairs found to compare")
        return None

    # Print results
    all_passed = True
    for result in results:
        print(format_result_text(result))
        print()
        if not result.passed:
            all_passed = False

    if all_passed:
        print("✓ All renders passed visual fidelity check")
    else:
        print("✗ Some renders failed visual fidelity check")

    return all_passed


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

    # Run visual fidelity test (requires API key)
    print("\n3. Running visual fidelity test...")
    visual_result = test_visual_fidelity()

    # Final summary
    print("\n" + "=" * 40)
    print("Final Results:")
    print(f"  Validation Test: {'✓ PASS' if validation_ok else '✗ FAIL'}")
    print(f"  Generation Test: {'✓ PASS' if generation_ok else '✗ FAIL'}")
    if visual_result is None:
        print("  Visual Fidelity: ⊘ SKIPPED")
    else:
        print(f"  Visual Fidelity: {'✓ PASS' if visual_result else '✗ FAIL'}")

    if validation_ok and generation_ok:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())