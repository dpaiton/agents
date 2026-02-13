# Visual Prompt Guide

## Overview

This guide provides templates and best practices for generating **concept art and visual mockups** using AI image generation tools (Midjourney, DALL-E, Stable Diffusion, etc.) for Unity Space Sim assets.

**Goal:** Generate NASA-inspired, believable sci-fi concept art that aligns with our style guide and provides clear visual reference for Blender geometry generation.

---

## Prompt Structure

### Standard Prompt Template

```
[SUBJECT] in [STYLE], [COMPOSITION], [TECHNICAL DETAILS], [REFERENCE MODIFIERS]
```

**Breakdown:**

1. **SUBJECT** - What you're generating (e.g., "small cargo spacecraft")
2. **STYLE** - Aesthetic direction (e.g., "NASA-inspired realistic sci-fi")
3. **COMPOSITION** - Camera angle and framing (e.g., "3/4 view, white background")
4. **TECHNICAL DETAILS** - Specific visual elements (e.g., "modular design, white hull")
5. **REFERENCE MODIFIERS** - Quality and reference cues (e.g., "like SpaceX Dragon")

---

## Core Style Keywords

### Recommended Keywords (Always Include)

| Keyword | Purpose | Notes |
|---------|---------|-------|
| `NASA-inspired` | Sets realistic, functional aesthetic | Primary style anchor |
| `believable sci-fi` | Balances realism with visual appeal | Prevents overly futuristic designs |
| `clean industrial design` | Establishes functional aesthetic | Avoids fantasy/alien elements |
| `white hull with gray panels` | Matches color palette | See STYLE_GUIDE.md |
| `technical blueprint style` | (For wireframes) Engineering reference | Use for geometry planning |
| `concept art` | Signals artistic intent | Better composition than "photograph" |
| `detailed technical illustration` | High detail for reference | Use for close-up views |

### Keywords to Avoid

| Keyword | Why Avoid | Better Alternative |
|---------|-----------|-------------------|
| `futuristic` | Too abstract, encourages glowing neon | `NASA-inspired modern` |
| `alien` | Wrong aesthetic direction | `functional industrial` |
| `fantasy` | Breaks believability | `realistic sci-fi` |
| `cinematic` | Too dramatic, poor reference clarity | `technical illustration` |
| `photorealistic` | Can look uncanny/fake | `realistic concept art` |
| `sleek` | Encourages impractical smooth shapes | `modular functional design` |

---

## Prompt Templates by Asset Type

### 1. Cargo Ship (Small-Medium)

**Basic Prompt:**
```
Small cargo spacecraft in NASA-inspired realistic sci-fi style,
3/4 view on white background, white hull with dark gray cargo bay doors,
modular rectangular design with visible thrusters and radiator panels,
clean industrial aesthetic like SpaceX Dragon meets shipping container,
technical concept art, detailed illustration
```

**Variations:**

**Wireframe/Blueprint:**
```
Technical blueprint of small cargo spacecraft, orthographic views
(front, side, top), white background, clean line art,
engineering schematic style, modular boxy design with cargo bay,
NASA technical drawing aesthetic, precise measurements visible
```

**Detail Study:**
```
Close-up detail view of cargo spacecraft docking port, NASA-inspired
industrial design, white painted metal with yellow hazard stripes,
visible panel lines and mechanical details, technical illustration,
white background, realistic sci-fi engineering
```

---

### 2. Mining Rig (Industrial)

**Basic Prompt:**
```
Industrial asteroid mining spacecraft in NASA-inspired realistic sci-fi style,
3/4 view on white background, dark gray hull with exposed scaffolding,
large articulated mining arm with drill, ore hopper visible,
utilitarian design like oil rig in space, technical concept art,
detailed industrial aesthetic with work lights and radiators
```

**Variations:**

**Functional Detail:**
```
Mining spacecraft drilling arm mechanism, NASA-inspired industrial engineering,
dark metal with hydraulic pistons and cables, technical cutaway illustration,
showing internal mechanics, realistic sci-fi equipment design,
white background, detailed technical drawing
```

**In-Context Scene:**
```
Industrial mining spacecraft approaching asteroid, NASA-inspired realistic style,
showing scale with asteroid debris, spacecraft has extended drilling arm,
dark industrial hull with bright work lights, space environment background,
concept art for believable sci-fi mining operation
```

---

### 3. Science Vessel

**Basic Prompt:**
```
Science research spacecraft in NASA-inspired realistic sci-fi style,
3/4 view on white background, clean white hull with blue agency markings,
large parabolic antenna and sensor arrays extending from body,
sleek cylindrical design like Hubble telescope and Voyager probe,
technical concept art, solar panels visible, detailed illustration
```

**Variations:**

**Sensor Array Detail:**
```
Close-up of spacecraft sensor boom array, NASA-inspired technical design,
matte black optical sensors with gold thermal blankets, white hull background,
detailed technical illustration, realistic sci-fi instrument cluster,
showing folding mechanisms and mounting points
```

**Blueprint Style:**
```
Technical schematic of science spacecraft, orthographic projection,
white background, blue line art, showing sensor arrays in deployed and stowed positions,
NASA technical drawing style, precise engineering blueprint,
annotations for antenna size and sensor types
```

---

### 4. Station Module

**Basic Prompt:**
```
Modular space station habitation module in NASA-inspired realistic sci-fi style,
3/4 view on white background, white cylindrical hull with docking ports at ends,
visible radiator panels and solar arrays, clean industrial design like ISS modules,
technical concept art, windows showing internal sections, detailed illustration,
scale reference showing airlocks and antennae
```

**Variations:**

**Docking Port Detail:**
```
Space station docking port close-up, NASA-inspired engineering design,
circular hatch with alignment guides and yellow hazard markings,
white metal with mechanical latches visible, technical illustration,
realistic sci-fi industrial hardware, white background
```

**Assembly View:**
```
Exploded view technical diagram of station module, white background,
showing hull sections, internal structure, and docking mechanisms,
NASA technical illustration style, blue and gray color scheme,
engineering assembly diagram for modular space station
```

---

## Composition Guidelines

### Camera Angles

| Angle | Use Case | Prompt Syntax |
|-------|----------|---------------|
| **3/4 View** | Standard reference, shows form | `3/4 perspective view` |
| **Side Profile** | Silhouette clarity | `side profile view` or `orthographic side view` |
| **Top-Down** | Layout and proportions | `top-down view` or `plan view` |
| **Orthographic Multi-View** | Engineering reference | `orthographic projection, front side top views` |
| **Isometric** | Technical clarity | `isometric view, 30-degree angle` |
| **Detail Close-Up** | Specific components | `close-up detail view of [component]` |

### Background Options

| Background | When to Use | Prompt Syntax |
|------------|-------------|---------------|
| **White** | Clean reference, easy to extract | `white background` (default) |
| **Transparent** | (Post-process) For overlays | `white background` then remove in editor |
| **Space** | In-context visualization | `in space environment, stars visible` |
| **Grid** | Scale reference | `white background with measurement grid` |
| **Hangar** | Scale + lighting reference | `in spacecraft hangar, neutral lighting` |

---

## Quality & Technical Modifiers

### Image Quality

```
--ar 16:9           # Aspect ratio (wide for side views)
--ar 1:1            # Square (for orthographic views)
--ar 3:4            # Tall (for vertical ships)
--q 2               # Quality (Midjourney: higher detail)
--stylize 50        # Lower stylization (more literal)
--chaos 0           # Deterministic output
```

**Prompt Additions:**
- `high detail, 4K resolution` - For detailed reference
- `clean lines, precise geometry` - For technical accuracy
- `professional concept art` - Quality signal
- `trending on ArtStation` - (Optional) Quality/style signal

---

## Example Workflow: Small Cargo Ship

### Step 1: Initial Concept

**Prompt:**
```
Small cargo spacecraft in NASA-inspired realistic sci-fi style,
3/4 view on white background, white hull with dark cargo bay doors,
boxy modular design with visible thrusters, clean industrial aesthetic,
technical concept art, detailed illustration --ar 16:9 --stylize 50
```

**Expected Output:** Wide concept art showing overall ship design

---

### Step 2: Orthographic Reference

**Prompt:**
```
Technical blueprint of small cargo spacecraft, orthographic views
showing front side and top, white background, clean line art,
NASA engineering schematic style, boxy modular design with labeled components,
precise technical drawing --ar 16:9 --stylize 25
```

**Expected Output:** Multi-view technical drawing for geometry planning

---

### Step 3: Detail Studies

**Prompt A (Cargo Bay):**
```
Close-up of cargo spacecraft bay doors, NASA-inspired industrial design,
white painted metal with yellow hazard stripes, visible hinges and latches,
technical illustration, white background, realistic sci-fi engineering detail
--ar 1:1 --q 2
```

**Prompt B (Thrusters):**
```
Spacecraft RCS thruster cluster detail, NASA-inspired technical design,
four small attitude control jets in quad configuration, white hull background,
technical illustration showing nozzle details, realistic engineering
--ar 1:1 --q 2
```

**Expected Output:** High-detail reference for Blender modeling

---

### Step 4: In-Context Visualization

**Prompt:**
```
Small cargo spacecraft in space docking with station, NASA-inspired realistic style,
white hull visible with dark cargo doors open, showing scale and function,
space background with Earth visible, concept art for sci-fi game,
cinematic but believable lighting --ar 16:9
```

**Expected Output:** Context for how asset will be used in-game

---

## Reference Integration

### Combining with Real Reference

**Technique:** Include real spacecraft in prompt for style anchoring

```
Small cargo spacecraft in the style of SpaceX Dragon capsule,
NASA-inspired realistic design, 3/4 view, white background,
modular white hull with visible thrusters and solar panels,
technical concept art like official NASA renders --ar 16:9
```

**Reference Keywords:**
- `like SpaceX Dragon` - Cargo ships
- `like ISS module` - Station components
- `like Space Shuttle` - Larger crewed vessels
- `like Hubble telescope` - Science instruments
- `like lunar lander` - Industrial/functional aesthetic

---

## Common Issues & Fixes

### Issue: Too Futuristic (Glowing Lines, Alien Shapes)

**Fix:** Add grounding keywords
```
Before: "futuristic cargo ship, sleek design"
After:  "cargo spacecraft in NASA-inspired realistic style,
         modular industrial design like ISS, white hull with gray panels"
```

---

### Issue: Too Plain/Boring

**Fix:** Add functional details
```
Before: "simple white spacecraft"
After:  "white spacecraft with visible radiator panels, RCS thrusters,
         docking ports, solar arrays, and agency markings, NASA-inspired design"
```

---

### Issue: Wrong Scale (Looks Too Large or Small)

**Fix:** Include scale reference
```
Before: "space station"
After:  "space station module with visible airlocks and windows showing interior,
         similar size to ISS Destiny module, human scale visible"
```

---

### Issue: Unclear Silhouette

**Fix:** Request specific view
```
Before: "3/4 view of spacecraft"
After:  "3/4 view AND side profile silhouette of spacecraft on white background,
         clear form, technical illustration"
```

Or generate separate silhouette:
```
"Side profile silhouette of cargo spacecraft, black solid shape on white background,
 clear readable form, no details, showing overall proportions"
```

---

## Advanced Techniques

### Variation Testing

Generate multiple variations quickly:

```
Small cargo spacecraft, NASA-inspired style, 3/4 view, white background,
[VARIATION: boxy and modular | cylindrical with arms | hybrid design],
technical concept art --ar 16:9
```

Run 3-4 times with different variations, compare results.

---

### Color Exploration

Test different color schemes:

```
Science spacecraft in NASA-inspired style, 3/4 view, white background,
[COLOR SCHEME: all white hull | white with blue accents | gray and orange thermal tiles],
technical concept art --ar 16:9
```

---

### Detail Density Control

```
Low Detail:  "simple clean spacecraft design, minimal surface details"
Medium Detail: "spacecraft with visible panels and functional components"
High Detail: "highly detailed spacecraft with panel lines, rivets, antennas,
              and mechanical components visible"
```

---

## Output Checklist

Before finalizing concept art, verify:

- ✅ Matches NASA-inspired aesthetic (not too futuristic)
- ✅ Color palette aligns with STYLE_GUIDE.md (white/gray/black base)
- ✅ Scale feels believable (includes reference elements if needed)
- ✅ Functional details present (thrusters, radiators, antennas, etc.)
- ✅ Clear silhouette (recognizable function from shape)
- ✅ Clean background (white or easily removable)
- ✅ High enough resolution for reference (minimum 1024px, prefer 2048px+)
- ✅ Multiple views available if needed (3/4 + orthographic)

---

## File Management

**Naming Convention:**
```
{category}_{asset_name}_{view}_{iteration}.png

Examples:
- ship_cargo_small_3quarter_v1.png
- ship_cargo_small_ortho_v1.png
- ship_cargo_small_detail_cargobay_v1.png
- station_hab_module_side_v2.png
```

**Storage Location:**
```
projects/unity-space-sim/assets/concepts/
├── ships/
│   ├── cargo/
│   │   ├── small/
│   │   │   ├── cargo_small_3quarter_v1.png
│   │   │   ├── cargo_small_ortho_v1.png
│   │   │   └── cargo_small_details_v1.png
│   │   └── medium/
│   └── science/
├── stations/
└── props/
```

---

## Next Steps

1. Generate concept art using prompts from this guide
2. Review concepts against STYLE_GUIDE.md for consistency
3. Create orthographic blueprints for geometry planning
4. Use approved concepts as reference for GEOMETRY_PROMPT_GUIDE.md
5. Pass visual reference to Blender engineer for geometry generation

---

**Status:** Foundation documentation (Phase 1)
**Last Updated:** 2026-02-12
**Maintainer:** Architect Agent
