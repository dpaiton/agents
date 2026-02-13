# Visual Style Guide

## Overview

The Unity Space Sim aesthetic is **NASA-inspired believable sci-fi**—realistic enough to feel grounded, stylized enough to be visually compelling. Think *The Expanse*, *Interstellar*, and real-world space hardware, not *Star Wars* or *Halo*.

**Core Philosophy:**
> "Like GTA's approach to driving—feels right without needing to be a simulation. Gameplay and visual appeal first, then plausibility."

We prioritize:
1. **Visual coherence** over strict realism
2. **Functional aesthetics** (form follows function, mostly)
3. **Consistent scale and proportions**
4. **Performance over fidelity** (optimized beauty)

---

## Visual References

### Primary Inspiration: NASA & Real Space Hardware

**Reference Sources:**
- NASA's ISS, Space Shuttle, SLS rocket
- SpaceX Dragon, Starship
- ESA/Roscosmos modules and vehicles
- Real satellite designs (Hubble, JWST, etc.)
- Concept art from NASA's future mission archives

**What to Borrow:**
- ✅ Modular, functional design language
- ✅ Surface details (panels, rivets, radiators, antennas)
- ✅ Material realism (worn metal, white thermal blankets, black solar panels)
- ✅ Practical lighting (RCS thrusters, running lights, solar arrays)
- ✅ Scale relationships (human-sized airlocks, cargo bays, cockpits)

**What to Avoid:**
- ❌ Overly futuristic/alien aesthetics
- ❌ Glowing neon accents (unless justified—nav lights OK)
- ❌ Impractical shapes (giant exposed glass canopies, fragile-looking spires)
- ❌ Excessive weathering (space is clean, just worn from micrometeorite impacts)

---

## Art Direction Principles

### 1. Form Follows Function (Mostly)

Ships and stations should **look** like they could work, even if the physics are simplified.

**Examples:**
- **Cargo ships** → Visible cargo bays, magnetic clamps, loading doors
- **Science vessels** → Sensor arrays, radiator fins, lab modules
- **Mining rigs** → Drilling arms, ore hoppers, industrial scaffolding
- **Fighter craft** → Compact, maneuverable, visible RCS thrusters

**Rule of Thumb:**
- Every major component should have a plausible purpose
- Players should be able to "read" the ship's function from its silhouette
- Details can be simplified, but the **story** of the design should be clear

---

### 2. NASA-Inspired Aesthetic

**Color Palette:**

| Color | Use | Hex Code | Notes |
|-------|-----|----------|-------|
| **White** | Thermal blankets, external panels | `#F0F0F0` | Primary hull color |
| **Off-White** | Aged panels, secondary surfaces | `#D8D8D8` | Variation for depth |
| **Aluminum** | Exposed metal, structural elements | `#A8A8A8` | Brushed metal look |
| **Matte Black** | Radiators, solar panels, optics | `#1A1A1A` | Heat dissipation surfaces |
| **Burnt Orange** | Insulation, thermal protection | `#C85A17` | Like Shuttle tiles |
| **Yellow** | Hazard markings, airlocks | `#FFD700` | Caution stripes |
| **Blue** | Agency markings, accent lights | `#0052A5` | NASA blue |
| **Red** | Navigation lights (port side) | `#FF0000` | Standard aviation red |
| **Green** | Navigation lights (starboard) | `#00FF00` | Standard aviation green |

**Material Guidelines:**
- **Metals:** Brushed aluminum, titanium (subtle anisotropy)
- **Panels:** Matte white with slight weathering (micro-scratches, dust)
- **Glass:** Minimal use, thick reinforced viewports only
- **Thermal blankets:** Gold foil (like real spacecraft, sparingly)
- **Radiators:** Black with visible panel structure

---

### 3. Believable Scale

**Scale Reference: 1 Unity unit = 1 meter**

| Asset Type | Typical Length | Poly Budget (LOD0) | Example |
|------------|----------------|-------------------|---------|
| **Fighter/Pod** | 5-10m | ~3-5k tris | Apollo CSM, Dragon capsule |
| **Small Ship** | 10-20m | ~5-10k tris | Cargo shuttle, science probe |
| **Medium Ship** | 20-50m | ~10-15k tris | Mining barge, transport |
| **Large Ship** | 50-100m | ~15-40k tris | Freighter, station module |
| **Capital Ship** | 100-500m | ~40-80k tris | Colony ship, battlecruiser |
| **Station** | 50-200m | ~20-60k tris | Modular ISS-like structures |

**Human Scale Reference:**
- Airlocks: 2m diameter (fits EVA suit)
- Hallways: 2-3m wide
- Cargo containers: Standard 20ft shipping container (6m x 2.4m x 2.4m)
- Cockpit seats: ~1m wide

**Visual Scale Cues:**
- Include recognizable elements: windows, airlocks, antennas
- Maintain consistent proportions across asset categories
- Use detail density to reinforce scale (larger ships = larger panel sizes)

---

### 4. Functional Surface Detail

**Detail Hierarchy:**
1. **Primary Silhouette** (large shapes: hull, wings, engines)
2. **Secondary Shapes** (panels, hatches, radiators)
3. **Tertiary Details** (rivets, vents, antennae)

**Detail Guidelines:**

| Ship Size | Primary Detail | Secondary Detail | Tertiary Detail |
|-----------|----------------|------------------|-----------------|
| **Small** (5-20m) | Clean panels | Hatches, thrusters | Minimal (decals OK) |
| **Medium** (20-50m) | Panel lines | Radiators, cargo doors | Rivets, vents |
| **Large** (50-100m) | Modular sections | Docking ports, arrays | Antennas, markings |
| **Capital** (100m+) | Superstructure | Modules, turrets | Running lights, comms |

**Practical Details to Include:**
- RCS thruster quads (small attitude control jets)
- Radiator panels (for heat dissipation)
- Docking ports (circular hatches with alignment guides)
- Antennae and sensor arrays
- Running lights (navigation lights: red/green/white)
- Panel lines and access hatches
- Thermal protection tiles (orange/brown, like Shuttle)

---

## Visual Examples

### Example 1: Small Cargo Ship

**Description:** 15m long, boxy cargo hauler

**Visual Elements:**
- **Silhouette:** Rectangular cargo bay with engines at rear, small cockpit at front
- **Color:** White hull with dark cargo bay doors, aluminum structural frame
- **Details:**
  - Cargo bay doors with yellow hazard stripes
  - 4x RCS thruster clusters (corners)
  - Small radiator panels (sides)
  - Blue running lights (top), red/green nav lights (sides)
  - Agency decal on hull (optional)
- **Materials:**
  - Hull: Matte white painted metal (slight weathering)
  - Frame: Brushed aluminum
  - Doors: Dark gray metal with yellow stripes
  - Windows: None (cockpit has small reinforced viewports)

**Reference Mood:** SpaceX Dragon cargo capsule meets shipping container

---

### Example 2: Mining Rig

**Description:** 30m industrial asteroid mining platform

**Visual Elements:**
- **Silhouette:** Central cylindrical body with extending mining arms
- **Color:** Dark gray/black industrial metal with orange safety markings
- **Details:**
  - Large drilling arm (articulated)
  - Ore hopper (visible cage/container)
  - Scaffolding and exposed structural beams
  - Bright work lights (white/yellow)
  - Massive radiator arrays (heat from drilling)
  - Minimal RCS thrusters (slow maneuvering)
- **Materials:**
  - Body: Worn dark metal (oil-stained, practical)
  - Arms: Hydraulic pistons, cables, industrial joints
  - Lights: Bright flood lamps
  - Radiators: Matte black panels

**Reference Mood:** Oil rig in space, International Space Station's Canadarm

---

### Example 3: Science Vessel

**Description:** 25m research ship with sensor arrays

**Visual Elements:**
- **Silhouette:** Sleek cylindrical body with protruding sensor booms
- **Color:** Clean white hull with blue NASA-style markings
- **Details:**
  - Large parabolic antenna (communications)
  - Multiple small sensor booms extending from body
  - Solar panel arrays (folding or fixed)
  - Small lab module windows (reinforced glass)
  - Minimal weaponry (research ship)
  - Extensive radiator coverage (power-hungry sensors)
- **Materials:**
  - Hull: Pristine white panels (well-maintained)
  - Sensors: Matte black optics, gold foil thermal blankets
  - Solar panels: Dark blue-black with visible cell grid
  - Windows: Thick glass with metal frames

**Reference Mood:** James Webb Space Telescope, Hubble, Voyager probes

---

## Lighting & Materials

### Lighting Setup (Unity)

**Exterior Lighting:**
- **Key Light:** Directional (Sun) - harsh, bright, no atmosphere diffusion
- **Fill Light:** Very subtle ambient (star field reflection)
- **Ship Lights:**
  - Navigation lights (red/green/white, small point lights)
  - Running lights (blue/white, subtle glow)
  - Work lights (bright white spots for cargo/mining operations)

**Material PBR Values:**

| Material | Base Color | Metallic | Smoothness | Notes |
|----------|------------|----------|------------|-------|
| **White Hull** | #F0F0F0 | 0.1 | 0.4 | Painted metal, slight scratches |
| **Aluminum** | #A8A8A8 | 0.9 | 0.6 | Brushed metal, anisotropic |
| **Matte Black** | #1A1A1A | 0.2 | 0.2 | Radiators, low reflectivity |
| **Glass** | #88CCFF | 0.0 | 0.95 | Reinforced viewports |
| **Gold Foil** | #FFD700 | 0.8 | 0.7 | Thermal blankets (sparingly) |
| **Thermal Tiles** | #C85A17 | 0.1 | 0.3 | Matte ceramic, like Shuttle |

**Weathering:**
- Subtle micro-scratches (normal map detail)
- Small dust/debris accumulation (albedo variation)
- No rust (space doesn't have oxygen/water)
- Impact craters from micro-meteorites (small dents, optional)

---

## Technical Constraints

### Performance Considerations

**Poly Budget Guidelines:**
- Use guidelines from VALIDATION_RULES.md
- These are **targets**, not strict limits
- Adjust based on gameplay needs and performance profiling

**Texture Resolution:**
- **Small ships (5-20m):** 1K albedo, 1K normal
- **Medium ships (20-50m):** 2K albedo, 2K normal
- **Large ships (50m+):** 2K albedo (with atlasing), 2K normal
- **Shared materials:** Use texture atlases where possible

**LOD Strategy:**
- LOD0: Full detail for close-up views
- LOD1: Simplified details, combined meshes
- LOD2: Silhouette only, minimal details

---

## Consistency Checklist

Before finalizing any asset, verify:

- ✅ Follows NASA-inspired aesthetic (no overly futuristic elements)
- ✅ Color palette matches style guide (white/gray/black with accent colors)
- ✅ Scale is believable (includes human-scale reference elements)
- ✅ Details serve a plausible purpose (no purely decorative "greebles")
- ✅ Materials use PBR values from guide
- ✅ Poly budget is within guidelines (see VALIDATION_RULES.md)
- ✅ LODs are generated and transitions are smooth
- ✅ Lighting works in both sunlight and shadow (space has harsh contrasts)

---

## Iteration & Feedback

**Design Review Process:**
1. **Concept Phase:** Visual mock reviewed for style consistency
2. **Geometry Phase:** Blender output reviewed for technical quality
3. **Unity Integration:** In-engine review for lighting/materials
4. **Gameplay Test:** Verify asset works in actual gameplay scenarios

**Common Feedback Themes:**
- "Too futuristic" → Add more NASA-inspired details, reduce glowing elements
- "Too plain" → Add functional surface details (panels, hatches, antennas)
- "Scale feels off" → Add human-scale reference (windows, airlocks)
- "Doesn't match style" → Review color palette and material choices

---

## Reference Library

**Recommended Resources:**
- [NASA Image Gallery](https://www.nasa.gov/multimedia/imagegallery/index.html)
- SpaceX Flickr (real hardware photos)
- ESA media library
- *The Expanse* art books (TV show design reference)
- *Apollo 13*, *Interstellar*, *Gravity* (film references for aesthetic)

**Internal References:**
- See `projects/unity-space-sim/assets/references/` for curated reference images
- Naming convention: `{category}_{subject}_{source}.jpg`
  - Example: `ship_cargo_spacex_dragon.jpg`

---

**Status:** Foundation documentation (Phase 1)
**Last Updated:** 2026-02-12
**Maintainer:** Architect Agent
