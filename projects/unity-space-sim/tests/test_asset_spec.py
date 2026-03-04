"""Tests for the spaceship asset-spec JSON Schema.

Validates that:
1. The schema itself is a valid JSON Schema (draft 2020-12).
2. The Viper fighter spec conforms to the schema.
3. Required fields are enforced.
4. Enum constraints are enforced.
5. Numeric range constraints are enforced.
"""

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "projects" / "unity-space-sim" / "docs" / "asset-spec-schema.json"
VIPER_SPEC_PATH = (
    REPO_ROOT / "projects" / "unity-space-sim" / "blender" / "specs" / "viper_fighter.json"
)


@pytest.fixture
def schema():
    """Load the asset-spec JSON Schema."""
    with open(SCHEMA_PATH) as f:
        return json.load(f)


@pytest.fixture
def viper_spec():
    """Load the Viper fighter spec."""
    with open(VIPER_SPEC_PATH) as f:
        return json.load(f)


class TestSchemaValidity:
    """Verify the schema itself is well-formed."""

    def test_schema_is_valid_json(self, schema):
        """Schema file parses as valid JSON."""
        assert isinstance(schema, dict)

    def test_schema_has_draft_2020_12(self, schema):
        """Schema declares JSON Schema draft 2020-12."""
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"

    def test_schema_has_required_defs(self, schema):
        """Schema defines all expected reusable sub-schemas."""
        defs = schema.get("$defs", {})
        expected = [
            "vector3",
            "rgba_color",
            "pbr_material",
            "component_geometry",
            "modifier",
            "taper",
            "metadata",
            "concept_art_reference",
            "feature_checklist_entry",
            "proportion_entry",
            "lod_strategy",
            "lod_level",
            "material_assignment",
            "generation_script",
            "dimensions_box",
            "dimensions_cylinder",
            "position",
            "sweep",
        ]
        for name in expected:
            assert name in defs, f"Missing $def: {name}"


class TestViperSpecValidation:
    """Validate the Viper fighter spec against the schema."""

    def test_viper_spec_validates(self, schema, viper_spec):
        """Viper fighter JSON validates against the asset-spec schema."""
        jsonschema.validate(instance=viper_spec, schema=schema)

    def test_viper_has_all_top_level_sections(self, viper_spec):
        """Viper spec contains all expected top-level sections."""
        expected_keys = [
            "metadata",
            "concept_art_references",
            "feature_checklist",
            "physical_characteristics",
            "proportions_reference",
            "geometry",
            "materials",
            "material_assignments",
            "lod_strategy",
            "generation_script",
            "required_script_changes",
        ]
        for key in expected_keys:
            assert key in viper_spec, f"Missing top-level key: {key}"

    def test_viper_metadata(self, viper_spec):
        """Metadata fields are populated correctly."""
        meta = viper_spec["metadata"]
        assert meta["name"] == "Viper-Class Fighter"
        assert "fighter" in meta["type"].lower()

    def test_viper_geometry_count(self, viper_spec):
        """Viper spec has the expected number of top-level components."""
        # Fuselage, Wings, Engine nacelles, Weapon barrels, Cockpit canopy, Dorsal fin
        assert len(viper_spec["geometry"]) == 6

    def test_viper_materials_count(self, viper_spec):
        """Viper spec defines 7 PBR materials."""
        assert len(viper_spec["materials"]) == 7

    def test_viper_lod_levels(self, viper_spec):
        """Viper spec defines 3 LOD levels."""
        levels = viper_spec["lod_strategy"]["levels"]
        assert len(levels) == 3
        assert levels[0]["level"] == 0
        assert levels[1]["level"] == 1
        assert levels[2]["level"] == 2

    def test_viper_feature_checklist_includes_exclusions(self, viper_spec):
        """Feature checklist includes items with count=0 (excluded features)."""
        checklist = viper_spec["feature_checklist"]
        excluded = [f for f in checklist if f["count"] == 0]
        assert len(excluded) >= 2, "Should have at least 2 excluded features (chin guns, turret)"

    def test_viper_nacelle_sub_components(self, viper_spec):
        """Engine nacelles have sub-components defined."""
        nacelles = next(g for g in viper_spec["geometry"] if g["name"] == "Engine nacelles")
        assert "sub_components" in nacelles
        sub_names = [s["name"] for s in nacelles["sub_components"]]
        assert "Nacelle body" in sub_names
        assert "Rear nozzle ring" in sub_names
        assert "Exhaust glow" in sub_names

    def test_viper_wing_angular_offsets(self, viper_spec):
        """Wings define 4 angular offsets for cruciform X-configuration."""
        wings = next(g for g in viper_spec["geometry"] if g["name"] == "Wings")
        assert "angular_offsets" in wings
        assert len(wings["angular_offsets"]) == 4


class TestSchemaConstraints:
    """Verify the schema rejects invalid data."""

    def test_rejects_missing_metadata(self, schema, viper_spec):
        """Schema rejects spec with missing metadata."""
        invalid = {k: v for k, v in viper_spec.items() if k != "metadata"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_missing_geometry(self, schema, viper_spec):
        """Schema rejects spec with missing geometry."""
        invalid = {k: v for k, v in viper_spec.items() if k != "geometry"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_invalid_primitive_type(self, schema, viper_spec):
        """Schema rejects an unknown primitive type."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["geometry"][0]["primitive"] = "dodecahedron"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_metallic_out_of_range(self, schema, viper_spec):
        """Schema rejects metallic value > 1.0."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["materials"][0]["metallic"] = 1.5
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_negative_roughness(self, schema, viper_spec):
        """Schema rejects negative roughness."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["materials"][0]["roughness"] = -0.1
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_color_channel_out_of_range(self, schema, viper_spec):
        """Schema rejects color channel value > 1.0."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["materials"][0]["base_color"]["r"] = 2.0
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_empty_geometry_array(self, schema, viper_spec):
        """Schema rejects an empty geometry array."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["geometry"] = []
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_invalid_lod_method(self, schema, viper_spec):
        """Schema rejects an unknown LOD method."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["lod_strategy"]["method"] = "unknown_method"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_additional_top_level_properties(self, schema, viper_spec):
        """Schema rejects unexpected top-level properties."""
        invalid = json.loads(json.dumps(viper_spec))
        invalid["unexpected_field"] = "should fail"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)

    def test_rejects_missing_material_name(self, schema, viper_spec):
        """Schema rejects a material without a name."""
        invalid = json.loads(json.dumps(viper_spec))
        del invalid["materials"][0]["name"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid, schema=schema)
