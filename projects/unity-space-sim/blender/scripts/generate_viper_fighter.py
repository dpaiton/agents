#!/usr/bin/env python3
"""
Viper-Class Fighter Generation Script
Unity Space Sim - Combat Fighter Asset

Generates a Star Wars / No Man's Sky inspired single-seat fighter with:
- Angular wedge-shaped hull with swept wings
- Multiple weapon systems (wing cannons, chin guns, turret)
- Quad engine cluster with emission
- NASA-inspired believable sci-fi aesthetic
- Aggressive combat-ready appearance

Based on approved Fighter Ship v4 design specification.

Usage:
    blender --background --python generate_viper_fighter.py
    blender --background --python generate_viper_fighter.py -- --output-dir /custom/path

Outputs:
    - viper_fighter_LOD0.fbx (main geometry ~5k tris)
    - viper_fighter_LOD1.fbx (simplified ~2k tris)
    - viper_fighter_LOD2.fbx (low-poly ~750 tris)
    - viper_fighter_3quarter.png (rendered preview)
    - viper_fighter_side.png (rendered preview)
"""

import bpy
import bmesh
import math
import os
import sys
import argparse
from pathlib import Path
from mathutils import Vector

# ==================== Configuration ====================

class ViperConfig:
    """Configuration for Viper-class fighter based on approved design."""

    # Dimensions (meters)
    HULL_LENGTH = 14.0
    HULL_WIDTH = 2.0
    HULL_HEIGHT = 1.4

    # Wing dimensions
    WING_LENGTH = 4.0
    WING_WIDTH = 3.5
    WING_THICKNESS = 0.14
    WING_OFFSET_X = 2.5
    WING_OFFSET_Y = -0.5
    WING_SWEEP_Y = -0.8
    WING_TIP_SCALE_Y = 0.3

    # Cockpit
    COCKPIT_LENGTH = 2.0
    COCKPIT_WIDTH = 0.6
    COCKPIT_HEIGHT = 0.3
    COCKPIT_POS_Y = 2.5
    COCKPIT_POS_Z = 0.22
    COCKPIT_TAPER = 0.4

    # Weapons
    WING_CANNON_RADIUS = 0.06
    WING_CANNON_LENGTH = 5.0
    WING_CANNON_POS_X = 3.5
    WING_CANNON_POS_Y = 0.5
    WING_CANNON_POS_Z = -0.05

    CHIN_GUN_RADIUS = 0.035
    CHIN_GUN_LENGTH = 3.0
    CHIN_GUN_POS_X = 0.12
    CHIN_GUN_POS_Y = 3.0
    CHIN_GUN_POS_Z = -0.28

    TURRET_DOME_RADIUS = 0.3
    TURRET_DOME_SCALE = (1.0, 1.2, 0.5)
    TURRET_POS = (0, -1.0, -0.28)
    TURRET_BARREL_RADIUS = 0.03
    TURRET_BARREL_LENGTH = 1.4

    # Engines
    ENGINE_RADIUS = 0.22
    ENGINE_LENGTH = 3.0
    ENGINE_POS_Y = -7.5
    ENGINE_SPACING_X = 0.5
    ENGINE_SPACING_Z = 0.12
    ENGINE_GLOW_RADIUS = 0.18

    # Dorsal fin
    FIN_WIDTH = 0.06
    FIN_LENGTH = 2.5
    FIN_HEIGHT = 1.2
    FIN_POS = (0, -3.5, 0.55)
    FIN_SWEEP_Y = -0.7
    FIN_TIP_SCALE_Y = 0.5

    # Materials (RGB values from spec)
    MATERIALS = {
        'hull': {
            'name': 'Fighter_Hull',
            'color': (0.32, 0.34, 0.36, 1.0),  # Worn grey
            'metallic': 0.4,
            'roughness': 0.55
        },
        'dark_panels': {
            'name': 'Dark_Panels',
            'color': (0.05, 0.05, 0.07, 1.0),  # Engine/vent areas
            'metallic': 0.6,
            'roughness': 0.7
        },
        'gun_metal': {
            'name': 'Gun_Metal',
            'color': (0.15, 0.15, 0.18, 1.0),  # Weapons
            'metallic': 0.9,
            'roughness': 0.35
        },
        'canopy': {
            'name': 'Canopy_Glass',
            'color': (0.04, 0.10, 0.16, 1.0),  # Dark tinted
            'metallic': 0.0,
            'roughness': 0.05,
            'alpha': 0.45,
            'transmission': 0.8
        },
        'engine_glow': {
            'name': 'Engine_Glow',
            'color': (0.05, 0.2, 0.6, 1.0),  # Blue emission
            'metallic': 0.0,
            'roughness': 0.0,
            'emission': 5.0
        },
        'weapon_tips': {
            'name': 'Weapon_Tips',
            'color': (0.6, 0.05, 0.02, 1.0),  # Red emission
            'metallic': 0.0,
            'roughness': 0.0,
            'emission': 3.0
        },
        'accent': {
            'name': 'Orange_Accent',
            'color': (0.65, 0.22, 0.04, 1.0),  # Orange stripes
            'metallic': 0.2,
            'roughness': 0.5
        }
    }

    # Target poly counts
    POLY_BUDGETS = {
        'LOD0': 5000,
        'LOD1': 2000,
        'LOD2': 750
    }


# ==================== Utility Functions ====================

def clear_scene():
    """Clear all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    # Clear all materials
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)

    # Clear all meshes
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)

    print("✓ Scene cleared")


def create_material(mat_config):
    """Create a PBR material with Principled BSDF."""
    mat = bpy.data.materials.new(name=mat_config['name'])
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    nodes.clear()

    # Add Principled BSDF
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled.location = (0, 0)

    # Set base color
    principled.inputs['Base Color'].default_value = mat_config['color']
    principled.inputs['Metallic'].default_value = mat_config['metallic']
    principled.inputs['Roughness'].default_value = mat_config['roughness']

    # Handle alpha/transmission for canopy
    if 'alpha' in mat_config:
        principled.inputs['Alpha'].default_value = mat_config['alpha']
        mat.blend_method = 'BLEND'
        mat.use_backface_culling = False

    if 'transmission' in mat_config:
        principled.inputs['Transmission'].default_value = mat_config['transmission']
        principled.inputs['IOR'].default_value = 1.45  # Glass

    # Handle emission
    if 'emission' in mat_config and mat_config['emission'] > 0:
        principled.inputs['Emission'].default_value = mat_config['color'][:3] + (1.0,)
        principled.inputs['Emission Strength'].default_value = mat_config['emission']

    # Add output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)

    # Connect nodes
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    return mat


def create_all_materials():
    """Create all materials for the fighter."""
    materials = {}
    for mat_name, mat_config in ViperConfig.MATERIALS.items():
        materials[mat_name] = create_material(mat_config)
    print(f"✓ Created {len(materials)} materials")
    return materials


# ==================== Geometry Generation ====================

def create_hull():
    """Create the main angular hull with tapered front."""
    # Start with a cube
    bpy.ops.mesh.primitive_cube_add(size=1)
    hull = bpy.context.active_object
    hull.name = "Hull"

    # Scale to base dimensions
    hull.scale = (ViperConfig.HULL_WIDTH/2, ViperConfig.HULL_LENGTH/2, ViperConfig.HULL_HEIGHT/2)
    bpy.ops.object.transform_apply(scale=True)

    # Enter edit mode for tapering
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(hull.data)

    # Select front face vertices for tapering
    front_verts = [v for v in bm.verts if v.co.y > ViperConfig.HULL_LENGTH/2 - 0.1]

    # Taper front to 25% X, 50% Z
    for vert in front_verts:
        vert.co.x *= 0.25
        vert.co.z *= 0.5

    # Select rear face vertices for slight taper
    rear_verts = [v for v in bm.verts if v.co.y < -ViperConfig.HULL_LENGTH/2 + 0.1]

    # Taper rear to 70% X
    for vert in rear_verts:
        vert.co.x *= 0.7

    bmesh.update_edit_mesh(hull.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Add subdivision for smoother shape
    subdiv = hull.modifiers.new(name='Subdivision', type='SUBSURF')
    subdiv.levels = 2
    subdiv.render_levels = 2

    print("✓ Created angular hull")
    return hull


def create_cockpit_canopy():
    """Create the cockpit canopy with tapered front."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    canopy = bpy.context.active_object
    canopy.name = "Cockpit_Canopy"

    # Position and scale
    canopy.location = (0, ViperConfig.COCKPIT_POS_Y, ViperConfig.COCKPIT_POS_Z)
    canopy.scale = (
        ViperConfig.COCKPIT_WIDTH/2,
        ViperConfig.COCKPIT_LENGTH/2,
        ViperConfig.COCKPIT_HEIGHT/2
    )
    bpy.ops.object.transform_apply(scale=True, location=False)

    # Taper front
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(canopy.data)

    front_verts = [v for v in bm.verts if v.co.y > 0.5]
    for vert in front_verts:
        vert.co.x *= ViperConfig.COCKPIT_TAPER

    bmesh.update_edit_mesh(canopy.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Add subdivision
    subdiv = canopy.modifiers.new(name='Subdivision', type='SUBSURF')
    subdiv.levels = 2

    print("✓ Created cockpit canopy")
    return canopy


def create_wings():
    """Create swept-back wings."""
    wings = []

    for side in [-1, 1]:  # Left and right
        bpy.ops.mesh.primitive_cube_add(size=1)
        wing = bpy.context.active_object
        wing.name = f"Wing_{'Right' if side > 0 else 'Left'}"

        # Position and scale
        wing.location = (
            side * ViperConfig.WING_OFFSET_X,
            ViperConfig.WING_OFFSET_Y,
            0
        )
        wing.scale = (
            ViperConfig.WING_LENGTH/2,
            ViperConfig.WING_WIDTH/2,
            ViperConfig.WING_THICKNESS/2
        )
        bpy.ops.object.transform_apply(scale=True, location=False)

        # Apply wing sweep
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(wing.data)

        # Select wing tip vertices (outer edge)
        if side > 0:  # Right wing
            tip_verts = [v for v in bm.verts if v.co.x > 1.5]
        else:  # Left wing
            tip_verts = [v for v in bm.verts if v.co.x < -1.5]

        # Sweep tips back and scale Y
        for vert in tip_verts:
            vert.co.y += ViperConfig.WING_SWEEP_Y
            vert.co.y *= ViperConfig.WING_TIP_SCALE_Y

        bmesh.update_edit_mesh(wing.data)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Add bevel for smoother edges
        bevel = wing.modifiers.new(name='Bevel', type='BEVEL')
        bevel.width = 0.05
        bevel.segments = 2

        wings.append(wing)

    print("✓ Created swept wings")
    return wings


def create_wing_cannons():
    """Create wing-mounted laser cannons."""
    cannons = []

    for side in [-1, 1]:
        # Cannon barrel
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ViperConfig.WING_CANNON_RADIUS,
            depth=ViperConfig.WING_CANNON_LENGTH,
            vertices=16
        )
        barrel = bpy.context.active_object
        barrel.name = f"Wing_Cannon_{'Right' if side > 0 else 'Left'}"
        barrel.location = (
            side * ViperConfig.WING_CANNON_POS_X,
            ViperConfig.WING_CANNON_POS_Y,
            ViperConfig.WING_CANNON_POS_Z
        )
        barrel.rotation_euler = (math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        # Cannon housing
        bpy.ops.mesh.primitive_cube_add(size=1)
        housing = bpy.context.active_object
        housing.name = f"Cannon_Housing_{'Right' if side > 0 else 'Left'}"
        housing.location = barrel.location
        housing.scale = (0.18/2, 0.7/2, 0.14/2)
        bpy.ops.object.transform_apply(scale=True, location=False)

        # Cannon tip (emission sphere)
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.08,
            segments=16,
            ring_count=8
        )
        tip = bpy.context.active_object
        tip.name = f"Cannon_Tip_{'Right' if side > 0 else 'Left'}"
        tip.location = (
            barrel.location[0],
            barrel.location[1] + ViperConfig.WING_CANNON_LENGTH/2 + 0.05,
            barrel.location[2]
        )

        cannons.extend([barrel, housing, tip])

    print("✓ Created wing cannons")
    return cannons


def create_chin_guns():
    """Create chin-mounted twin guns."""
    guns = []

    for side in [-1, 1]:
        # Gun barrel
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ViperConfig.CHIN_GUN_RADIUS,
            depth=ViperConfig.CHIN_GUN_LENGTH,
            vertices=12
        )
        gun = bpy.context.active_object
        gun.name = f"Chin_Gun_{'Right' if side > 0 else 'Left'}"
        gun.location = (
            side * ViperConfig.CHIN_GUN_POS_X,
            ViperConfig.CHIN_GUN_POS_Y,
            ViperConfig.CHIN_GUN_POS_Z
        )
        gun.rotation_euler = (math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        guns.append(gun)

    # Single housing for both guns
    bpy.ops.mesh.primitive_cube_add(size=1)
    housing = bpy.context.active_object
    housing.name = "Chin_Gun_Housing"
    housing.location = (0, ViperConfig.CHIN_GUN_POS_Y - 0.5, ViperConfig.CHIN_GUN_POS_Z)
    housing.scale = (0.3/2, 0.8/2, 0.14/2)
    bpy.ops.object.transform_apply(scale=True, location=False)

    # Add subdivision
    subdiv = housing.modifiers.new(name='Subdivision', type='SUBSURF')
    subdiv.levels = 1

    guns.append(housing)

    print("✓ Created chin guns")
    return guns


def create_underslung_turret():
    """Create underslung turret with twin barrels."""
    turret_parts = []

    # Turret dome
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=ViperConfig.TURRET_DOME_RADIUS,
        segments=24,
        ring_count=12
    )
    dome = bpy.context.active_object
    dome.name = "Turret_Dome"
    dome.location = ViperConfig.TURRET_POS
    dome.scale = ViperConfig.TURRET_DOME_SCALE
    bpy.ops.object.transform_apply(scale=True, location=False)

    # Cut dome in half (only bottom hemisphere)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bm = bmesh.from_edit_mesh(dome.data)

    # Select and delete top half
    top_verts = [v for v in bm.verts if v.co.z > 0.01]
    bmesh.ops.delete(bm, verts=top_verts)

    bmesh.update_edit_mesh(dome.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    turret_parts.append(dome)

    # Twin barrels
    for side in [-1, 1]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ViperConfig.TURRET_BARREL_RADIUS,
            depth=ViperConfig.TURRET_BARREL_LENGTH,
            vertices=12
        )
        barrel = bpy.context.active_object
        barrel.name = f"Turret_Barrel_{'Right' if side > 0 else 'Left'}"
        barrel.location = (
            ViperConfig.TURRET_POS[0] + side * 0.1,
            ViperConfig.TURRET_POS[1] + 0.5,
            ViperConfig.TURRET_POS[2]
        )
        barrel.rotation_euler = (math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        turret_parts.append(barrel)

    print("✓ Created underslung turret")
    return turret_parts


def create_engines():
    """Create quad engine cluster with emission."""
    engines = []

    # Four engine positions
    positions = [
        (ViperConfig.ENGINE_SPACING_X, ViperConfig.ENGINE_SPACING_Z),    # Top right
        (-ViperConfig.ENGINE_SPACING_X, ViperConfig.ENGINE_SPACING_Z),   # Top left
        (ViperConfig.ENGINE_SPACING_X, -ViperConfig.ENGINE_SPACING_Z),   # Bottom right
        (-ViperConfig.ENGINE_SPACING_X, -ViperConfig.ENGINE_SPACING_Z)  # Bottom left
    ]

    for i, (x_offset, z_offset) in enumerate(positions):
        # Engine nacelle
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ViperConfig.ENGINE_RADIUS,
            depth=ViperConfig.ENGINE_LENGTH,
            vertices=24
        )
        nacelle = bpy.context.active_object
        nacelle.name = f"Engine_Nacelle_{i+1}"
        nacelle.location = (x_offset, ViperConfig.ENGINE_POS_Y, z_offset)
        nacelle.rotation_euler = (math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        # Engine nozzle (torus)
        bpy.ops.mesh.primitive_torus_add(
            major_radius=ViperConfig.ENGINE_RADIUS,
            minor_radius=0.04,
            major_segments=24,
            minor_segments=12
        )
        nozzle = bpy.context.active_object
        nozzle.name = f"Engine_Nozzle_{i+1}"
        nozzle.location = (
            x_offset,
            ViperConfig.ENGINE_POS_Y - ViperConfig.ENGINE_LENGTH/2,
            z_offset
        )
        nozzle.rotation_euler = (math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        # Engine glow (circle)
        bpy.ops.mesh.primitive_circle_add(
            vertices=24,
            radius=ViperConfig.ENGINE_GLOW_RADIUS,
            fill_type='NGON'
        )
        glow = bpy.context.active_object
        glow.name = f"Engine_Glow_{i+1}"
        glow.location = (
            x_offset,
            ViperConfig.ENGINE_POS_Y - ViperConfig.ENGINE_LENGTH/2 - 0.05,
            z_offset
        )
        glow.rotation_euler = (math.pi/2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        engines.extend([nacelle, nozzle, glow])

    print("✓ Created quad engines")
    return engines


def create_dorsal_fin():
    """Create swept dorsal fin behind cockpit."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    fin = bpy.context.active_object
    fin.name = "Dorsal_Fin"

    # Position and scale
    fin.location = ViperConfig.FIN_POS
    fin.scale = (
        ViperConfig.FIN_WIDTH/2,
        ViperConfig.FIN_LENGTH/2,
        ViperConfig.FIN_HEIGHT/2
    )
    bpy.ops.object.transform_apply(scale=True, location=False)

    # Sweep the top back
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(fin.data)

    # Select top vertices
    top_verts = [v for v in bm.verts if v.co.z > 0.3]

    # Sweep back and scale Y
    for vert in top_verts:
        vert.co.y += ViperConfig.FIN_SWEEP_Y
        vert.co.y *= ViperConfig.FIN_TIP_SCALE_Y

    bmesh.update_edit_mesh(fin.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Add bevel
    bevel = fin.modifiers.new(name='Bevel', type='BEVEL')
    bevel.width = 0.03
    bevel.segments = 2

    print("✓ Created dorsal fin")
    return fin


def apply_materials(objects_dict, materials):
    """Apply materials to fighter components."""
    # Hull gets worn grey
    objects_dict['hull'].data.materials.append(materials['hull'])

    # Cockpit canopy gets glass
    objects_dict['canopy'].data.materials.append(materials['canopy'])

    # Wings get hull material with dark panel accents
    for wing in objects_dict['wings']:
        wing.data.materials.append(materials['hull'])

    # Weapons get gun metal
    for cannon in objects_dict['wing_cannons']:
        if 'Tip' in cannon.name:
            cannon.data.materials.append(materials['weapon_tips'])
        else:
            cannon.data.materials.append(materials['gun_metal'])

    for gun in objects_dict['chin_guns']:
        gun.data.materials.append(materials['gun_metal'])

    for turret_part in objects_dict['turret']:
        turret_part.data.materials.append(materials['gun_metal'])

    # Engines get dark panels and emission
    for engine in objects_dict['engines']:
        if 'Glow' in engine.name:
            engine.data.materials.append(materials['engine_glow'])
        else:
            engine.data.materials.append(materials['dark_panels'])

    # Dorsal fin gets hull material
    objects_dict['fin'].data.materials.append(materials['hull'])

    print("✓ Materials applied")


def join_fighter_parts(objects_dict, name="Viper_Fighter"):
    """Join all fighter parts into a single object."""
    # Collect all objects
    all_objects = []
    all_objects.append(objects_dict['hull'])
    all_objects.append(objects_dict['canopy'])
    all_objects.extend(objects_dict['wings'])
    all_objects.extend(objects_dict['wing_cannons'])
    all_objects.extend(objects_dict['chin_guns'])
    all_objects.extend(objects_dict['turret'])
    all_objects.extend(objects_dict['engines'])
    all_objects.append(objects_dict['fin'])

    # Select all objects
    bpy.ops.object.select_all(action='DESELECT')
    for obj in all_objects:
        obj.select_set(True)

    # Set active and join
    bpy.context.view_layer.objects.active = objects_dict['hull']
    bpy.ops.object.join()

    # Rename
    joined = bpy.context.active_object
    joined.name = name

    # Apply all modifiers
    for modifier in joined.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    print(f"✓ Joined all parts into {name}")
    return joined


# ==================== LOD Generation ====================

def generate_lods(base_object):
    """Generate LOD versions of the fighter."""
    lods = {"LOD0": base_object}

    # LOD1 - ~40% triangles
    bpy.ops.object.select_all(action='DESELECT')
    base_object.select_set(True)
    bpy.context.view_layer.objects.active = base_object

    bpy.ops.object.duplicate()
    lod1 = bpy.context.active_object
    lod1.name = "Viper_Fighter_LOD1"

    # Add decimate modifier
    decimate = lod1.modifiers.new(name='Decimate_LOD1', type='DECIMATE')
    decimate.ratio = 0.4
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='Decimate_LOD1')

    lods["LOD1"] = lod1

    # LOD2 - ~15% triangles
    bpy.ops.object.select_all(action='DESELECT')
    base_object.select_set(True)
    bpy.context.view_layer.objects.active = base_object

    bpy.ops.object.duplicate()
    lod2 = bpy.context.active_object
    lod2.name = "Viper_Fighter_LOD2"

    decimate = lod2.modifiers.new(name='Decimate_LOD2', type='DECIMATE')
    decimate.ratio = 0.15
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='Decimate_LOD2')

    lods["LOD2"] = lod2

    print("✓ Generated 3 LOD levels")
    return lods


# ==================== Export Functions ====================

def export_fbx(obj, filepath):
    """Export object as FBX with Unity-compatible settings."""
    # Select only the object to export
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Export with Unity settings
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        mesh_smooth_type='FACE',
        use_mesh_modifiers=False,
        use_mesh_edges=False,
        use_tspace=True,
        use_custom_props=False,
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_armature_deform_only=True,
        bake_anim=False,
        embed_textures=False,
        batch_mode='OFF',
        use_batch_own_dir=False
    )

    print(f"✓ Exported: {filepath}")


# ==================== Rendering Functions ====================

def setup_camera_and_lights():
    """Setup camera and lighting for preview renders."""
    # Add camera for 3/4 view
    bpy.ops.object.camera_add(location=(20, -25, 10))
    camera = bpy.context.active_object
    camera.name = "Render_Camera"
    camera.rotation_euler = (math.radians(60), 0, math.radians(45))

    # Add sun light
    bpy.ops.object.light_add(type='SUN', location=(10, -10, 20))
    sun = bpy.context.active_object
    sun.name = "Sun_Light"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(45), 0, math.radians(30))

    # Add fill light
    bpy.ops.object.light_add(type='AREA', location=(-15, 10, 5))
    fill = bpy.context.active_object
    fill.name = "Fill_Light"
    fill.data.energy = 1.0
    fill.data.size = 10

    return camera


def render_preview(fighter_obj, output_dir):
    """Render preview images of the fighter."""
    # Setup camera and lighting
    camera = setup_camera_and_lights()

    # Configure render settings
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.render.device = 'GPU'
    scene.cycles.samples = 128  # Lower samples for faster preview
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = True

    # Set camera
    scene.camera = camera

    # Focus camera on fighter
    bpy.ops.object.select_all(action='DESELECT')
    fighter_obj.select_set(True)
    bpy.context.view_layer.objects.active = fighter_obj
    bpy.ops.view3d.camera_to_view_selected()

    # Render 3/4 view
    output_path = os.path.join(output_dir, "viper_fighter_3quarter.png")
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"✓ Rendered 3/4 view: {output_path}")

    # Adjust camera for side view
    camera.location = (0, -30, 0)
    camera.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.view3d.camera_to_view_selected()

    # Render side profile
    output_path = os.path.join(output_dir, "viper_fighter_side.png")
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"✓ Rendered side profile: {output_path}")


# ==================== Validation ====================

def validate_fighter(obj, lod_name):
    """Validate fighter meets requirements."""
    print(f"\n=== Validating {lod_name} ===")

    # Get mesh data
    mesh = obj.data
    mesh.calc_loop_triangles()

    # Count triangles
    tri_count = len(mesh.loop_triangles)
    budget = ViperConfig.POLY_BUDGETS.get(lod_name, 5000)

    if tri_count <= budget * 1.1:  # Allow 10% over
        print(f"✓ Triangle count: {tri_count} (budget: {budget})")
    else:
        print(f"✗ Triangle count: {tri_count} exceeds budget {budget}")

    # Check scale
    if obj.scale == (1.0, 1.0, 1.0):
        print("✓ Scale applied correctly")
    else:
        print(f"✗ Scale not applied: {obj.scale}")

    # Check materials
    mat_count = len(obj.material_slots)
    print(f"✓ Materials assigned: {mat_count}")

    # Check dimensions
    dims = obj.dimensions
    print(f"✓ Dimensions: {dims.x:.1f}m × {dims.y:.1f}m × {dims.z:.1f}m")

    return tri_count <= budget * 1.1


# ==================== Main Function ====================

def main():
    """Main generation function."""
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default='', help='Output directory for FBX and renders')

    # Handle Blender's -- separator
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    args = parser.parse_args(argv)
    output_dir = args.output_dir or os.getcwd()

    print("=== Viper-Class Fighter Generation ===")
    print(f"Output directory: {output_dir}")

    # Clear scene
    clear_scene()

    # Create materials
    materials = create_all_materials()

    # Generate fighter components
    print("\n--- Building Fighter Components ---")
    hull = create_hull()
    canopy = create_cockpit_canopy()
    wings = create_wings()
    wing_cannons = create_wing_cannons()
    chin_guns = create_chin_guns()
    turret = create_underslung_turret()
    engines = create_engines()
    fin = create_dorsal_fin()

    # Organize components
    objects_dict = {
        'hull': hull,
        'canopy': canopy,
        'wings': wings,
        'wing_cannons': wing_cannons,
        'chin_guns': chin_guns,
        'turret': turret,
        'engines': engines,
        'fin': fin
    }

    # Apply materials
    print("\n--- Applying Materials ---")
    apply_materials(objects_dict, materials)

    # Join all parts
    print("\n--- Assembling Fighter ---")
    fighter = join_fighter_parts(objects_dict, "Viper_Fighter_LOD0")

    # Generate LODs
    print("\n--- Generating LODs ---")
    lods = generate_lods(fighter)

    # Validate each LOD
    print("\n--- Validation ---")
    for lod_name, lod_obj in lods.items():
        validate_fighter(lod_obj, lod_name)

    # Export FBX files
    print("\n--- Exporting FBX ---")
    for lod_name, lod_obj in lods.items():
        filename = f"viper_fighter_{lod_name}.fbx"
        filepath = os.path.join(output_dir, filename)
        export_fbx(lod_obj, filepath)

    # Render preview images
    print("\n--- Rendering Previews ---")
    render_preview(lods["LOD0"], output_dir)

    print("\n=== ✓ Viper Fighter Generation Complete! ===")
    print("\nGenerated files:")
    print("  - viper_fighter_LOD0.fbx (main asset)")
    print("  - viper_fighter_LOD1.fbx (medium distance)")
    print("  - viper_fighter_LOD2.fbx (low detail)")
    print("  - viper_fighter_3quarter.png (preview)")
    print("  - viper_fighter_side.png (preview)")


if __name__ == "__main__":
    main()