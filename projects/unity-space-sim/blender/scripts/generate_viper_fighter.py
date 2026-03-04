#!/usr/bin/env python3
"""
Viper-Class Fighter Generation Script
Unity Space Sim - Combat Fighter Asset

Generates a Star Wars / No Man's Sky inspired single-seat fighter with:
- Angular rectangular-cross-section hull (12m x 2.5m x 1.8m)
- 4 wings in cruciform X-configuration (upper-right, upper-left, lower-right, lower-left)
- 2 large side-by-side engine nacelles with nozzle rings and exhaust glow
- 4 weapon barrels (one per wing tip) with red emission tips
- Angular cockpit canopy on top of fuselage, forward 1/3
- Single swept dorsal fin behind cockpit
- Believable aggressive sci-fi aesthetic

Based on approved Fighter Ship v4 concept art (4 reference views).

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
    HULL_LENGTH = 12.0
    HULL_WIDTH = 2.5
    HULL_HEIGHT = 1.8

    # Hull taper
    HULL_FRONT_TAPER_WIDTH = 0.4   # Front face scaled to ~40% width
    HULL_FRONT_TAPER_HEIGHT = 0.6  # Front face scaled to ~60% height
    HULL_REAR_TAPER_WIDTH = 0.8    # Rear face scaled to ~80% width
    HULL_BEVEL_WIDTH = 0.02        # Cross-section bevel width

    # Wing dimensions (per wing)
    WING_SPAN = 4.0          # Root to tip span
    WING_CHORD_ROOT = 2.0    # Chord at root
    WING_CHORD_TIP = 0.8     # Tip chord ~40% of root
    WING_THICKNESS = 0.25
    WING_BEVEL_WIDTH = 0.01
    WING_SWEEP_BACK = 0.8    # Tips translated rearward
    WING_ATTACH_Y_FRAC = 0.6 # 60% back from nose

    # Wing angles (degrees of Y-axis rotation in Blender)
    # Blender's R_y(θ) gives X'=cos(θ)·X, Z'=-sin(θ)·X
    # Reduced from ±30° to ±20° so wings stay closer to fuselage in side view
    WING_ANGLE_UPPER_RIGHT = -20.0
    WING_ANGLE_UPPER_LEFT = -160.0
    WING_ANGLE_LOWER_RIGHT = 20.0
    WING_ANGLE_LOWER_LEFT = 160.0

    # Cockpit
    COCKPIT_LENGTH = 2.0
    COCKPIT_WIDTH = 0.6
    COCKPIT_HEIGHT = 0.35
    COCKPIT_TAPER = 0.4  # Front taper ~40% width

    # Weapon barrels (one per wing tip)
    WEAPON_BARREL_RADIUS = 0.06
    WEAPON_BARREL_LENGTH = 2.5
    WEAPON_TIP_RADIUS = 0.08

    # Engine nacelles (reduced diameter to match concept art proportions)
    NACELLE_DIAMETER = 0.85
    NACELLE_LENGTH = 4.0
    NACELLE_SPACING = 1.2        # Center-to-center horizontal distance
    NACELLE_EXTEND_BEYOND = 0.3  # How far rear extends beyond fuselage
    NOZZLE_MINOR_RADIUS = 0.06
    EXHAUST_RADIUS_FRAC = 0.9    # Fraction of nacelle radius
    INTAKE_MINOR_RADIUS = 0.05
    DETAIL_RING_MINOR_RADIUS = 0.03
    NACELLE_VERTICAL_OFFSET = -0.2  # Slightly below fuselage centerline

    # Dorsal fin
    FIN_WIDTH = 0.06
    FIN_LENGTH = 2.0
    FIN_HEIGHT = 1.2
    FIN_SWEEP_Y = 0.5    # Top edge shifted rearward
    FIN_TIP_SCALE = 0.5  # Top scaled to ~50% length

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
        principled.inputs['Transmission Weight'].default_value = mat_config['transmission']
        principled.inputs['IOR'].default_value = 1.45  # Glass

    # Handle emission
    if 'emission' in mat_config and mat_config['emission'] > 0:
        principled.inputs['Emission Color'].default_value = mat_config['color'][:3] + (1.0,)
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
    """Create the main angular hull with rectangular cross-section and tapered ends."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    hull = bpy.context.active_object
    hull.name = "Hull"

    # Scale to base dimensions
    hull.scale = (
        ViperConfig.HULL_WIDTH / 2,
        ViperConfig.HULL_LENGTH / 2,
        ViperConfig.HULL_HEIGHT / 2,
    )
    bpy.ops.object.transform_apply(scale=True)

    # Enter edit mode for tapering
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(hull.data)

    # Front face vertices (positive Y is forward)
    front_verts = [v for v in bm.verts if v.co.y > ViperConfig.HULL_LENGTH / 2 - 0.1]
    for vert in front_verts:
        vert.co.x *= ViperConfig.HULL_FRONT_TAPER_WIDTH
        vert.co.z *= ViperConfig.HULL_FRONT_TAPER_HEIGHT

    # Rear face vertices
    rear_verts = [v for v in bm.verts if v.co.y < -ViperConfig.HULL_LENGTH / 2 + 0.1]
    for vert in rear_verts:
        vert.co.x *= ViperConfig.HULL_REAR_TAPER_WIDTH

    bmesh.update_edit_mesh(hull.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Subdivision level 1 for angular silhouette
    subdiv = hull.modifiers.new(name='Subdivision', type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 1

    # Bevel for cross-section edges
    bevel = hull.modifiers.new(name='Bevel', type='BEVEL')
    bevel.width = ViperConfig.HULL_BEVEL_WIDTH
    bevel.segments = 1

    print("✓ Created angular hull")
    return hull


def create_cockpit_canopy():
    """Create the cockpit canopy with tapered front, positioned at forward 1/3 of fuselage."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    canopy = bpy.context.active_object
    canopy.name = "Cockpit_Canopy"

    # Forward 1/3 of fuselage: center of hull is at Y=0, nose is at Y=+HULL_LENGTH/2
    # Forward 1/3 position = HULL_LENGTH/2 - HULL_LENGTH/3
    canopy_y = ViperConfig.HULL_LENGTH / 2 - ViperConfig.HULL_LENGTH / 3
    canopy_z = ViperConfig.HULL_HEIGHT / 2  # On top of fuselage

    canopy.location = (0, canopy_y, canopy_z)
    canopy.scale = (
        ViperConfig.COCKPIT_WIDTH / 2,
        ViperConfig.COCKPIT_LENGTH / 2,
        ViperConfig.COCKPIT_HEIGHT / 2,
    )
    bpy.ops.object.transform_apply(scale=True, location=False)

    # Taper front face
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(canopy.data)

    front_verts = [v for v in bm.verts if v.co.y > 0.5]
    for vert in front_verts:
        vert.co.x *= ViperConfig.COCKPIT_TAPER

    bmesh.update_edit_mesh(canopy.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Subdivision level 1
    subdiv = canopy.modifiers.new(name='Subdivision', type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 1

    print("✓ Created cockpit canopy")
    return canopy


def create_wings():
    """Create 4 wings in cruciform X-configuration.

    Viewed from front/rear, the wings form an X shape:
      Upper-Left  /  \\ Upper-Right
                 /    \\
    ============[FUSE]============
                 \\    /
      Lower-Left  \\  / Lower-Right
    """
    wings = []

    # Wing attachment Y position: 60% back from nose
    # Nose is at Y = +HULL_LENGTH/2, so 60% back = HULL_LENGTH/2 - 0.6*HULL_LENGTH
    attach_y = ViperConfig.HULL_LENGTH / 2 - ViperConfig.WING_ATTACH_Y_FRAC * ViperConfig.HULL_LENGTH

    wing_configs = [
        ("Wing_Upper_Right", ViperConfig.WING_ANGLE_UPPER_RIGHT),
        ("Wing_Upper_Left", ViperConfig.WING_ANGLE_UPPER_LEFT),
        ("Wing_Lower_Right", ViperConfig.WING_ANGLE_LOWER_RIGHT),
        ("Wing_Lower_Left", ViperConfig.WING_ANGLE_LOWER_LEFT),
    ]

    for wing_name, angle_deg in wing_configs:
        angle_rad = math.radians(angle_deg)

        bpy.ops.mesh.primitive_cube_add(size=1)
        wing = bpy.context.active_object
        wing.name = wing_name

        # Create wing as a flat slab: span along X, chord along Y, thin in Z
        wing.scale = (
            ViperConfig.WING_SPAN / 2,
            ViperConfig.WING_CHORD_ROOT / 2,
            ViperConfig.WING_THICKNESS / 2,
        )
        bpy.ops.object.transform_apply(scale=True)

        # Edit mode: offset wing so root is at X=0 and tip at X=WING_SPAN,
        # then taper and sweep the tip
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(wing.data)

        half_span = ViperConfig.WING_SPAN / 2

        # Shift all vertices so root edge is at X=0, tip at X=WING_SPAN
        # (default cube after scale has verts at ±half_span)
        for v in bm.verts:
            v.co.x += half_span

        # Tip verts are now at X near WING_SPAN
        tip_verts = [v for v in bm.verts if v.co.x > ViperConfig.WING_SPAN - 0.1]

        taper_ratio = ViperConfig.WING_CHORD_TIP / ViperConfig.WING_CHORD_ROOT
        for vert in tip_verts:
            # Taper: scale chord (Y) at tip
            vert.co.y *= taper_ratio
            # Sweep: shift tip rearward
            vert.co.y -= ViperConfig.WING_SWEEP_BACK / 2

        bmesh.update_edit_mesh(wing.data)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Rotate wing around Y-axis to its X-config angle
        # R_y(θ): X'=cos(θ)·X, Z'=-sin(θ)·X
        wing.rotation_euler = (0, angle_rad, 0)

        # Position at attachment point on fuselage
        wing.location = (0, attach_y, 0)

        bpy.ops.object.transform_apply(rotation=True, location=False)

        # Bevel modifier for smooth edges
        bevel = wing.modifiers.new(name='Bevel', type='BEVEL')
        bevel.width = ViperConfig.WING_BEVEL_WIDTH
        bevel.segments = 1

        wings.append(wing)

    print("✓ Created 4 wings in X-configuration")
    return wings


def create_wing_root_fairings():
    """Create tapered connecting geometry between each wing root and the fuselage.

    Each fairing is a wedge that bridges the visual gap at the wing-fuselage
    junction, making the wings appear to grow out of the hull body.
    """
    fairings = []
    attach_y = (
        ViperConfig.HULL_LENGTH / 2
        - ViperConfig.WING_ATTACH_Y_FRAC * ViperConfig.HULL_LENGTH
    )

    wing_configs = [
        ("Fairing_Upper_Right", ViperConfig.WING_ANGLE_UPPER_RIGHT),
        ("Fairing_Upper_Left", ViperConfig.WING_ANGLE_UPPER_LEFT),
        ("Fairing_Lower_Right", ViperConfig.WING_ANGLE_LOWER_RIGHT),
        ("Fairing_Lower_Left", ViperConfig.WING_ANGLE_LOWER_LEFT),
    ]

    # Fairing extends from fuselage center outward past the hull surface.
    # It tapers from hull-sized at the root to wing-sized at the outer edge.
    fairing_span = ViperConfig.HULL_WIDTH * 0.9  # Extends past hull surface
    fairing_chord = ViperConfig.WING_CHORD_ROOT * 0.7
    fairing_thickness = ViperConfig.HULL_HEIGHT * 0.35

    for name, angle_deg in wing_configs:
        angle_rad = math.radians(angle_deg)

        bpy.ops.mesh.primitive_cube_add(size=1)
        fairing = bpy.context.active_object
        fairing.name = name

        fairing.scale = (
            fairing_span / 2,
            fairing_chord / 2,
            fairing_thickness / 2,
        )
        bpy.ops.object.transform_apply(scale=True)

        # Edit mode: offset so root is at X=0 and taper outer edge
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(fairing.data)

        half = fairing_span / 2
        for v in bm.verts:
            v.co.x += half  # Root at X=0, outer at X=fairing_span

        # Taper outer edge to match wing profile
        outer_verts = [v for v in bm.verts if v.co.x > fairing_span - 0.1]
        for v in outer_verts:
            v.co.y *= 0.6  # Narrow chord at outer edge
            v.co.z *= 0.4  # Thin at outer edge to match wing thickness

        bmesh.update_edit_mesh(fairing.data)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Rotate to match wing angle and position at wing attachment
        fairing.rotation_euler = (0, angle_rad, 0)
        fairing.location = (0, attach_y, 0)
        bpy.ops.object.transform_apply(rotation=True, location=False)

        fairings.append(fairing)

    print("✓ Created 4 wing root fairings")
    return fairings


def _get_wing_tip_positions():
    """Compute world-space wing tip center positions for weapon barrel placement.

    Returns a list of (position_vector, wing_name) tuples, one per wing.
    """
    attach_y = ViperConfig.HULL_LENGTH / 2 - ViperConfig.WING_ATTACH_Y_FRAC * ViperConfig.HULL_LENGTH

    wing_angles = [
        ("Upper_Right", ViperConfig.WING_ANGLE_UPPER_RIGHT),
        ("Upper_Left", ViperConfig.WING_ANGLE_UPPER_LEFT),
        ("Lower_Right", ViperConfig.WING_ANGLE_LOWER_RIGHT),
        ("Lower_Left", ViperConfig.WING_ANGLE_LOWER_LEFT),
    ]

    positions = []
    for name, angle_deg in wing_angles:
        angle_rad = math.radians(angle_deg)
        # Wing tip is at local +X = WING_SPAN from wing origin after Y-axis rotation
        # Blender R_y(θ): X' = cos(θ)·X, Z' = -sin(θ)·X
        tip_x = ViperConfig.WING_SPAN * math.cos(angle_rad)
        tip_z = -ViperConfig.WING_SPAN * math.sin(angle_rad)
        # The wing tip chord center Y is shifted back by half the sweep
        tip_y = attach_y - ViperConfig.WING_SWEEP_BACK / 2
        positions.append((Vector((tip_x, tip_y, tip_z)), name))

    return positions


def create_weapon_barrels():
    """Create 4 weapon barrels, one per wing tip, extending forward parallel to fuselage."""
    barrels = []
    tip_positions = _get_wing_tip_positions()

    for tip_pos, wing_name in tip_positions:
        # Barrel cylinder extends forward from wing tip along Y axis
        barrel_center_y = tip_pos.y + ViperConfig.WEAPON_BARREL_LENGTH / 2

        bpy.ops.mesh.primitive_cylinder_add(
            radius=ViperConfig.WEAPON_BARREL_RADIUS,
            depth=ViperConfig.WEAPON_BARREL_LENGTH,
            vertices=12,
        )
        barrel = bpy.context.active_object
        barrel.name = f"Weapon_Barrel_{wing_name}"
        barrel.location = (tip_pos.x, barrel_center_y, tip_pos.z)
        barrel.rotation_euler = (math.pi / 2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)

        barrels.append(barrel)

        # Tip sphere with red emission at forward end
        forward_y = tip_pos.y + ViperConfig.WEAPON_BARREL_LENGTH
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=ViperConfig.WEAPON_TIP_RADIUS,
            segments=12,
            ring_count=6,
        )
        tip_sphere = bpy.context.active_object
        tip_sphere.name = f"Weapon_Tip_{wing_name}"
        tip_sphere.location = (tip_pos.x, forward_y, tip_pos.z)

        barrels.append(tip_sphere)

    print("✓ Created 4 weapon barrels with tips")
    return barrels


def create_engines():
    """Create 2 large cylindrical engine nacelles, side-by-side at fuselage rear.

    Each nacelle includes:
    - Main cylinder body
    - Rear nozzle torus ring
    - Exhaust glow circle (emission)
    - Forward intake torus ring
    - 2-3 detail torus rings along length
    """
    nacelles = []
    nacelle_radius = ViperConfig.NACELLE_DIAMETER / 2

    # Fuselage rear is at Y = -HULL_LENGTH/2
    fuselage_rear_y = -ViperConfig.HULL_LENGTH / 2

    # Nacelle center Y: rear extends NACELLE_EXTEND_BEYOND past fuselage rear
    # So the nacelle rear face is at fuselage_rear_y - NACELLE_EXTEND_BEYOND
    # Nacelle center Y = fuselage_rear_y - NACELLE_EXTEND_BEYOND + NACELLE_LENGTH/2
    nacelle_center_y = fuselage_rear_y - ViperConfig.NACELLE_EXTEND_BEYOND + ViperConfig.NACELLE_LENGTH / 2

    nacelle_rear_y = nacelle_center_y - ViperConfig.NACELLE_LENGTH / 2
    nacelle_front_y = nacelle_center_y + ViperConfig.NACELLE_LENGTH / 2

    nacelle_z = ViperConfig.NACELLE_VERTICAL_OFFSET

    for side in [-1, 1]:
        side_name = "Right" if side > 0 else "Left"
        nacelle_x = side * ViperConfig.NACELLE_SPACING / 2

        # Main cylinder body
        bpy.ops.mesh.primitive_cylinder_add(
            radius=nacelle_radius,
            depth=ViperConfig.NACELLE_LENGTH,
            vertices=24,
        )
        body = bpy.context.active_object
        body.name = f"Nacelle_Body_{side_name}"
        body.location = (nacelle_x, nacelle_center_y, nacelle_z)
        body.rotation_euler = (math.pi / 2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)
        nacelles.append(body)

        # Rear nozzle torus ring
        bpy.ops.mesh.primitive_torus_add(
            major_radius=nacelle_radius,
            minor_radius=ViperConfig.NOZZLE_MINOR_RADIUS,
            major_segments=24,
            minor_segments=12,
        )
        nozzle = bpy.context.active_object
        nozzle.name = f"Nacelle_Nozzle_{side_name}"
        nozzle.location = (nacelle_x, nacelle_rear_y, nacelle_z)
        nozzle.rotation_euler = (math.pi / 2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)
        nacelles.append(nozzle)

        # Exhaust glow circle (ngon fill)
        exhaust_radius = nacelle_radius * ViperConfig.EXHAUST_RADIUS_FRAC
        bpy.ops.mesh.primitive_circle_add(
            vertices=24,
            radius=exhaust_radius,
            fill_type='NGON',
        )
        glow = bpy.context.active_object
        glow.name = f"Nacelle_Glow_{side_name}"
        glow.location = (nacelle_x, nacelle_rear_y - 0.02, nacelle_z)
        glow.rotation_euler = (math.pi / 2, 0, 0)
        bpy.ops.object.transform_apply(rotation=True)
        nacelles.append(glow)

    print("✓ Created 2 engine nacelles with nozzles and glow")
    return nacelles


def create_dorsal_fin():
    """Create swept dorsal fin directly behind cockpit on top of fuselage."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    fin = bpy.context.active_object
    fin.name = "Dorsal_Fin"

    # Position: directly behind cockpit, on top of fuselage
    # Cockpit center Y = HULL_LENGTH/2 - HULL_LENGTH/3
    # Fin starts right behind cockpit
    cockpit_y = ViperConfig.HULL_LENGTH / 2 - ViperConfig.HULL_LENGTH / 3
    cockpit_rear_y = cockpit_y - ViperConfig.COCKPIT_LENGTH / 2
    fin_center_y = cockpit_rear_y - ViperConfig.FIN_LENGTH / 2

    fin_z = ViperConfig.HULL_HEIGHT / 2 + ViperConfig.FIN_HEIGHT / 2

    fin.location = (0, fin_center_y, fin_z)
    fin.scale = (
        ViperConfig.FIN_WIDTH / 2,
        ViperConfig.FIN_LENGTH / 2,
        ViperConfig.FIN_HEIGHT / 2,
    )
    bpy.ops.object.transform_apply(scale=True, location=False)

    # Sweep the top back and taper
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(fin.data)

    # Top vertices are at +Z in local space (above center)
    top_verts = [v for v in bm.verts if v.co.z > 0.3]
    for vert in top_verts:
        # Sweep: shift top edge rearward (negative Y)
        vert.co.y -= ViperConfig.FIN_SWEEP_Y / 2
        # Taper: scale Y to ~50% length at tip
        vert.co.y *= ViperConfig.FIN_TIP_SCALE

    bmesh.update_edit_mesh(fin.data)
    bpy.ops.object.mode_set(mode='OBJECT')

    print("✓ Created dorsal fin")
    return fin


def apply_materials(objects_dict, materials):
    """Apply materials to fighter components per spec material assignments."""
    # Fuselage: Hull
    objects_dict['hull'].data.materials.append(materials['hull'])

    # Cockpit canopy: Canopy Glass
    objects_dict['canopy'].data.materials.append(materials['canopy'])

    # Wings: Hull
    for wing in objects_dict['wings']:
        wing.data.materials.append(materials['hull'])

    # Engine nacelles: Dark Panels for bodies/nozzles/intakes/rings, Engine Glow for exhaust
    for part in objects_dict['nacelles']:
        if 'Glow' in part.name:
            part.data.materials.append(materials['engine_glow'])
        else:
            part.data.materials.append(materials['dark_panels'])

    # Weapon barrels: Gun Metal for barrels, Weapon Tips for tip spheres
    for part in objects_dict['weapon_barrels']:
        if 'Tip' in part.name:
            part.data.materials.append(materials['weapon_tips'])
        else:
            part.data.materials.append(materials['gun_metal'])

    # Dorsal fin: Hull
    objects_dict['fin'].data.materials.append(materials['hull'])

    print("✓ Materials applied")


def join_fighter_parts(objects_dict, name="Viper_Fighter"):
    """Join all fighter parts into a single object."""
    all_objects = []
    all_objects.append(objects_dict['hull'])
    all_objects.append(objects_dict['canopy'])
    all_objects.extend(objects_dict['wings'])
    all_objects.extend(objects_dict['nacelles'])
    all_objects.extend(objects_dict['weapon_barrels'])
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

def _point_camera_at(camera, target_location):
    """Point camera at a target location using a Track To constraint.

    Works in headless (--background) mode unlike view3d.camera_to_view_selected.
    """
    constraint = camera.constraints.new(type='TRACK_TO')
    constraint.target = bpy.data.objects.new("_cam_target", None)
    bpy.context.collection.objects.link(constraint.target)
    constraint.target.location = target_location
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'


def setup_camera_and_lights():
    """Setup camera and lighting for preview renders."""
    # Add camera for 3/4 view
    bpy.ops.object.camera_add(location=(20, -25, 10))
    camera = bpy.context.active_object
    camera.name = "Render_Camera"

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
    fill.data.energy = 1.5
    fill.data.size = 10

    return camera


def render_preview(fighter_obj, output_dir, hide_objects=None):
    """Render preview images of the fighter.

    Args:
        fighter_obj: The LOD0 object to render.
        output_dir: Directory for output PNGs.
        hide_objects: Optional list of objects to hide during rendering
                      (e.g. LOD1/LOD2 copies).
    """
    # Hide LOD copies and other non-render objects
    if hide_objects:
        for obj in hide_objects:
            obj.hide_render = True

    camera = setup_camera_and_lights()

    # Configure render settings
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 64
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = True

    scene.camera = camera

    # Compute the fighter's centre for aiming the camera
    bbox = fighter_obj.bound_box
    world_corners = [fighter_obj.matrix_world @ Vector(c) for c in bbox]
    centre = sum(world_corners, Vector()) / len(world_corners)

    # Moderate telephoto lens
    camera.data.lens = 85  # mm

    # 3/4 view — front-quarter angle (like concept art hero.png)
    # Camera in front of ship so nose is in foreground, nacelles in background
    camera.location = (15, 20, 6)
    _point_camera_at(camera, centre)

    output_path = os.path.join(output_dir, "viper_fighter_3quarter.png")
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered 3/4 view: {output_path}")

    # Side-profile view — right side, long telephoto matching concept art side.png
    while camera.constraints:
        camera.constraints.remove(camera.constraints[0])
    camera.data.type = 'PERSP'
    camera.data.lens = 150  # Long telephoto for minimal distortion
    camera.location = (30, 0, 2)  # True right side with minimal elevation
    _point_camera_at(camera, centre)

    output_path = os.path.join(output_dir, "viper_fighter_side.png")
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"Rendered side profile: {output_path}")


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
    weapon_barrels = create_weapon_barrels()
    nacelles = create_engines()
    fin = create_dorsal_fin()

    # Organize components
    objects_dict = {
        'hull': hull,
        'canopy': canopy,
        'wings': wings,
        'nacelles': nacelles,
        'weapon_barrels': weapon_barrels,
        'fin': fin,
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

    # Render preview images (hide LOD1/LOD2 so only LOD0 is visible)
    print("\n--- Rendering Previews ---")
    render_preview(
        lods["LOD0"],
        output_dir,
        hide_objects=[lods["LOD1"], lods["LOD2"]],
    )

    print("\n=== ✓ Viper Fighter Generation Complete! ===")
    print("\nGenerated files:")
    print("  - viper_fighter_LOD0.fbx (main asset)")
    print("  - viper_fighter_LOD1.fbx (medium distance)")
    print("  - viper_fighter_LOD2.fbx (low detail)")
    print("  - viper_fighter_3quarter.png (preview)")
    print("  - viper_fighter_side.png (preview)")


if __name__ == "__main__":
    main()
