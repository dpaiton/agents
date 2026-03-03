#!/usr/bin/env python3
"""Test suite for Blender spaceship generation scripts.

Tests the spaceship generation functions for quality, performance, and export compatibility.
Run with: pytest projects/unity-space-sim/blender/tests/

Requirements:
    - Blender 3.6+ with bpy available in Python path
    - pytest for test framework
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add blender scripts to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    import bpy
    import bmesh
    from generate_basic_spaceship import (
        clear_scene,
        create_basic_spaceship_geometry,
        assign_materials,
        generate_lods,
        validate_asset,
        export_fbx,
        create_material
    )
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    pytest.skip("Blender not available", allow_module_level=True)


class TestSpaceshipGeneration:
    """Test spaceship geometry generation functions."""

    def setup_method(self):
        """Set up clean Blender scene for each test."""
        if BLENDER_AVAILABLE:
            clear_scene()

    def test_clear_scene(self):
        """Test that scene clearing removes all objects."""
        # Add some test objects
        bpy.ops.mesh.primitive_cube_add()
        bpy.ops.mesh.primitive_sphere_add()

        assert len(bpy.context.scene.objects) >= 2

        clear_scene()
        assert len(bpy.context.scene.objects) == 0

    @pytest.mark.parametrize("ship_type", ["cargo", "science", "fighter"])
    def test_create_basic_spaceship_geometry(self, ship_type):
        """Test spaceship geometry creation for different types."""
        ship = create_basic_spaceship_geometry(
            ship_type=ship_type,
            length=15.0,
            width=8.0,
            height=5.0
        )

        assert ship is not None
        assert ship.type == 'MESH'
        assert ship_type in ship.name.lower()

        # Check dimensions are approximately correct
        dims = ship.dimensions
        assert 10.0 < dims.x < 20.0  # Length should be reasonable
        assert 5.0 < dims.y < 12.0   # Width should be reasonable
        assert 3.0 < dims.z < 8.0    # Height should be reasonable

    @pytest.mark.parametrize("size", ["small", "medium", "large"])
    def test_size_variations(self, size):
        """Test that different sizes produce appropriately scaled ships."""
        size_params = {
            'small': {'length': 10.0, 'width': 6.0, 'height': 4.0},
            'medium': {'length': 15.0, 'width': 8.0, 'height': 5.0},
            'large': {'length': 25.0, 'width': 12.0, 'height': 8.0}
        }

        params = size_params[size]
        ship = create_basic_spaceship_geometry(
            ship_type="cargo",
            length=params['length'],
            width=params['width'],
            height=params['height']
        )

        dims = ship.dimensions
        # Allow 20% tolerance for complexity additions
        assert abs(dims.x - params['length']) < params['length'] * 0.3
        assert abs(dims.y - params['width']) < params['width'] * 0.3
        assert abs(dims.z - params['height']) < params['height'] * 0.3


class TestMaterialSystem:
    """Test material creation and assignment."""

    def setup_method(self):
        """Set up clean scene for each test."""
        if BLENDER_AVAILABLE:
            clear_scene()

    def test_create_material(self):
        """Test PBR material creation."""
        mat = create_material(
            name="Test_Material",
            base_color=(1.0, 0.5, 0.2, 1.0),
            metallic=0.8,
            roughness=0.3
        )

        assert mat is not None
        assert mat.name == "Test_Material"
        assert mat.use_nodes is True

        # Check if Principled BSDF exists and has correct values
        principled = mat.node_tree.nodes.get("Principled BSDF")
        assert principled is not None

        base_color = principled.inputs["Base Color"].default_value
        assert abs(base_color[0] - 1.0) < 0.01
        assert abs(base_color[1] - 0.5) < 0.01
        assert abs(base_color[2] - 0.2) < 0.01

    def test_assign_materials(self):
        """Test material assignment to spaceship geometry."""
        ship = create_basic_spaceship_geometry("cargo", 15.0, 8.0, 5.0)
        assign_materials(ship, "cargo")

        assert len(ship.data.materials) > 0

        # Check that materials follow NASA color palette
        material_names = [mat.name for mat in ship.data.materials]
        assert any("Hull_White" in name for name in material_names)
        assert any("Aluminum" in name for name in material_names)


class TestLODGeneration:
    """Test Level of Detail generation."""

    def setup_method(self):
        """Set up clean scene for each test."""
        if BLENDER_AVAILABLE:
            clear_scene()

    def test_generate_lods(self):
        """Test LOD generation produces multiple detail levels."""
        ship = create_basic_spaceship_geometry("cargo", 15.0, 8.0, 5.0)
        original_tri_count = len(ship.data.polygons)

        lods = generate_lods(ship, lod1_ratio=0.5, lod2_ratio=0.25)

        assert len(lods) == 3
        assert all(lod.type == 'MESH' for lod in lods)

        # Check naming convention
        assert "LOD0" in lods[0].name
        assert "LOD1" in lods[1].name
        assert "LOD2" in lods[2].name

        # LODs should have decimate modifiers applied
        assert any(mod.type == 'DECIMATE' for mod in lods[1].modifiers)
        assert any(mod.type == 'DECIMATE' for mod in lods[2].modifiers)


class TestValidation:
    """Test asset validation functions."""

    def setup_method(self):
        """Set up clean scene for each test."""
        if BLENDER_AVAILABLE:
            clear_scene()

    def test_validate_asset(self):
        """Test asset validation against technical standards."""
        ship = create_basic_spaceship_geometry("cargo", 15.0, 8.0, 5.0)
        assign_materials(ship, "cargo")

        validation = validate_asset(
            ship,
            max_triangles=10000,
            expected_dimensions=(15.0, 8.0, 5.0)
        )

        # Check validation structure
        required_keys = [
            'triangle_count', 'max_triangles', 'triangle_budget_ok',
            'actual_dimensions', 'expected_dimensions', 'scale_accuracy',
            'material_count', 'has_materials', 'has_uv_map'
        ]

        for key in required_keys:
            assert key in validation

        # Basic validation checks
        assert validation['triangle_count'] > 0
        assert validation['has_materials'] is True
        assert validation['material_count'] > 0

    @pytest.mark.parametrize("max_tris", [1000, 5000, 15000])
    def test_triangle_budget_validation(self, max_tris):
        """Test triangle budget validation with different limits."""
        ship = create_basic_spaceship_geometry("cargo", 12.0, 6.0, 4.0)

        validation = validate_asset(
            ship,
            max_triangles=max_tris,
            expected_dimensions=(12.0, 6.0, 4.0)
        )

        # Budget validation should work correctly
        actual_count = validation['triangle_count']
        expected_ok = actual_count <= max_tris
        assert validation['triangle_budget_ok'] == expected_ok


class TestExport:
    """Test FBX export functionality."""

    def setup_method(self):
        """Set up clean scene for each test."""
        if BLENDER_AVAILABLE:
            clear_scene()

    def test_export_fbx(self):
        """Test FBX export creates valid files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            ship = create_basic_spaceship_geometry("cargo", 10.0, 5.0, 3.0)
            assign_materials(ship, "cargo")

            output_path = os.path.join(temp_dir, "test_ship.fbx")
            export_fbx([ship], output_path)

            # Check file was created
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

    def test_lod_export_workflow(self):
        """Test complete workflow: generate → LODs → validate → export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate ship
            ship = create_basic_spaceship_geometry("science", 12.0, 6.0, 4.0)
            assign_materials(ship, "science")

            # Generate LODs
            lods = generate_lods(ship)

            # Validate primary LOD
            validation = validate_asset(
                lods[0],
                max_triangles=8000,
                expected_dimensions=(12.0, 6.0, 4.0)
            )

            assert validation['triangle_budget_ok']
            assert validation['has_materials']

            # Export all LODs
            for i, lod in enumerate(lods):
                output_path = os.path.join(temp_dir, f"science_ship_LOD{i}.fbx")
                export_fbx([lod], output_path)
                assert os.path.exists(output_path)


class TestPerformance:
    """Test performance characteristics of generation scripts."""

    def setup_method(self):
        """Set up clean scene for each test."""
        if BLENDER_AVAILABLE:
            clear_scene()

    def test_generation_performance(self):
        """Test that ship generation completes in reasonable time."""
        import time

        start_time = time.time()
        ship = create_basic_spaceship_geometry("cargo", 20.0, 10.0, 6.0)
        assign_materials(ship, "cargo")
        lods = generate_lods(ship)
        generation_time = time.time() - start_time

        # Should complete in less than 30 seconds (very generous)
        assert generation_time < 30.0

        # Sanity check that something was actually created
        assert len(lods) == 3
        assert all(lod.type == 'MESH' for lod in lods)

    def test_memory_usage(self):
        """Test that repeated generation doesn't cause memory leaks."""
        initial_objects = len(bpy.data.objects)
        initial_meshes = len(bpy.data.meshes)

        # Generate multiple ships
        for i in range(3):
            clear_scene()
            ship = create_basic_spaceship_geometry("fighter", 8.0, 4.0, 3.0)
            assign_materials(ship, "fighter")

        # Clean up
        clear_scene()

        # Check that we're not accumulating objects/meshes
        final_objects = len(bpy.data.objects)
        final_meshes = len(bpy.data.meshes)

        # Should be back to baseline (allowing some tolerance for Blender's internal behavior)
        assert abs(final_objects - initial_objects) <= 1
        assert abs(final_meshes - initial_meshes) <= 5  # Blender may keep some mesh data


if __name__ == '__main__':
    # Run tests if executed directly
    pytest.main([__file__, '-v'])