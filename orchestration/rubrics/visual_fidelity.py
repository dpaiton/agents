"""Visual fidelity evaluation rubric.

This rubric defines criteria for comparing a 3D render against
concept art reference images. Each criterion is scored on a 0-2 scale
and weighted to produce a maximum total score of 16.

Used by the visual validation tool to gate asset quality in the
Blender-to-Unity asset pipeline.
"""

from typing import List

from orchestration.rubrics import EvaluationCriterion


_SILHOUETTE_MATCH = EvaluationCriterion(
    name="Silhouette Match",
    description=(
        "The overall outline/silhouette of the render matches the concept art. "
        "Major structural elements (wings, fuselage, engines, fins) create the "
        "same profile shape when viewed from the same angle. Score 0 if the "
        "silhouette is unrecognizable, 1 if partially correct, 2 if closely matching."
    ),
    scale=(0, 2),
    weight=2.0,
)

_PROPORTIONS = EvaluationCriterion(
    name="Proportions",
    description=(
        "The relative sizes and aspect ratios of components match the concept art. "
        "Fuselage length-to-width ratio, wing span relative to body, engine size "
        "relative to fuselage, and cockpit placement are all proportionally correct. "
        "Score 0 if proportions are wrong, 1 if approximately correct, 2 if accurate."
    ),
    scale=(0, 2),
    weight=1.5,
)

_COMPONENT_COUNT = EvaluationCriterion(
    name="Component Count",
    description=(
        "The render has the correct number of each major component: wings, engines, "
        "weapons, fins, antennae. Count each visible component type and compare to "
        "concept art. Score 0 if counts are wrong (e.g., 2 wings vs 4), 1 if most "
        "counts match, 2 if all component counts match exactly."
    ),
    scale=(0, 2),
    weight=2.0,
)

_MATERIAL_FIDELITY = EvaluationCriterion(
    name="Material Fidelity",
    description=(
        "Surface materials, colors, and finish match the concept art's visual style. "
        "Metal textures, panel lines, color scheme (grey hull, dark engines, colored "
        "accents), and emission effects (engine glow, weapon tips) are consistent. "
        "Score 0 if materials look completely different, 1 if partially matching, "
        "2 if faithful to concept."
    ),
    scale=(0, 2),
    weight=1.0,
)

_OVERALL_IMPRESSION = EvaluationCriterion(
    name="Overall Impression",
    description=(
        "Holistic assessment: would a viewer identify the render as the same ship "
        "design shown in the concept art? Consider pose, attitude, design language, "
        "and visual identity. Score 0 if they look like different ships, 1 if the "
        "same general type but noticeably different, 2 if clearly the same design."
    ),
    scale=(0, 2),
    weight=1.5,
)


VISUAL_FIDELITY_RUBRIC: List[EvaluationCriterion] = [
    _SILHOUETTE_MATCH,
    _PROPORTIONS,
    _COMPONENT_COUNT,
    _MATERIAL_FIDELITY,
    _OVERALL_IMPRESSION,
]
