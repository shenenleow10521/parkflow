---
name: ParkFlow
description: A cinematic, mechanical and credible operating case for a members-first mall Priority Zone.
colors:
  night: "#0a111c"
  night-raised: "#0d1624"
  concrete: "#111b2a"
  concrete-raised: "#16233a"
  structure: "#22324a"
  structure-strong: "#2f4360"
  chalk: "#ebf0f6"
  chalk-muted: "#b8c5d6"
  fog: "#8696ad"
  sign-blue: "#2f6fe0"
  sign-blue-high: "#7ea8ff"
  bay-free: "#34e58a"
  bay-wait: "#ffb21f"
  bay-stop: "#ff5a66"
  bay-held: "#b48cff"
  member-gold: "#e3c35a"
  case-white: "#ffffff"
  case-canvas: "#f7f8fb"
  case-ink: "#111827"
  case-muted: "#344054"
  case-gold: "#80620a"
typography:
  display:
    fontFamily: "Barlow Condensed, Roboto Condensed, Arial Narrow, sans-serif"
    fontSize: "clamp(54px, min(7vw, 10.4vh), 104px)"
    fontWeight: 700
    lineHeight: 0.88
    letterSpacing: "-0.012em"
  headline:
    fontFamily: "Barlow Condensed, Roboto Condensed, Arial Narrow, sans-serif"
    fontSize: "clamp(40px, 5.4vw, 70px)"
    fontWeight: 600
    lineHeight: 0.98
  body:
    fontFamily: "Barlow, Segoe UI, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Barlow Semi Condensed, Roboto Condensed, Arial Narrow, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1
rounded:
  control: "12px"
  card: "18px"
  compact: "8px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "28px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.sign-blue}"
    textColor: "#ffffff"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "52px"
  button-secondary:
    backgroundColor: "{colors.night}"
    textColor: "{colors.chalk}"
    rounded: "{rounded.control}"
    padding: "0 22px"
    height: "52px"
  card:
    backgroundColor: "{colors.concrete}"
    textColor: "{colors.chalk}"
    rounded: "{rounded.card}"
    padding: "28px"
---

# Design System: ParkFlow

## Overview

**Creative North Star: "The Operating Car Park"**

ParkFlow should feel like walking through a well-run premium parking facility at night: legible signage, visible machinery and exact status signals. The front half may be cinematic and spatial; the business half becomes restrained and investment-committee credible. The system rejects generic SaaS polish, speculative-startup theatre, static consulting templates, control/forecast conflation and animation that competes with the case.

The B3 and B4 business sections deliberately switch to a white investment-memo mode. Dark ink, cool grey rules, flat surfaces and an accessible deep gold make the change of register unmistakable without abandoning ParkFlow's typography or sign blue.

**Key Characteristics:**

- Cinematic entrance, operational detail, sober conclusion.
- Physical metaphors only when they clarify how the service works.
- Evidence, assumptions and hypotheses are visibly separated.
- Member gold is rare; status colors always retain operational meaning.

## Colors

The palette is concrete, chalk and parking-sign light, with strict semantic status colors.

### Primary

- **Parking Sign Blue:** Commands, navigation and the main action.
- **High-Visibility Blue:** Focus, live controls and selected states.

### Secondary

- **Member Gold:** Membership value and board-level business emphasis, never decoration.
- **Case Gold:** The darker gold used for labels and financial emphasis on white backgrounds.

### Tertiary

- **Bay Free / Wait / Stop / Held:** Operational states only.

### Neutral

- **Night and Raised Night:** Page and inset operational surfaces.
- **Concrete and Raised Concrete:** Cards, equipment and business-case panels.
- **Chalk, Muted Chalk and Fog:** Primary, secondary and source text.
- **Structure and Strong Structure:** Dividers, rails and input boundaries.
- **Case White, Canvas and Ink:** B3/B4 backgrounds, flat financial surfaces and high-contrast business text.

### Named Rules

**The Signal Rule.** Green, amber, red and violet communicate status; never use them as arbitrary decoration.

**The Gold Reserve Rule.** Member gold appears on no more than one primary business message per viewport.

## Typography

**Display Font:** Barlow Condensed (with condensed sans-serif fallbacks)  
**Body Font:** Barlow (with Segoe UI and system sans-serif fallbacks)  
**Label/Mono Font:** Barlow Semi Condensed

**Character:** Highway-sign clarity meets a disciplined operating dashboard. Condensed figures save space without feeling like a technology demo.

### Hierarchy

- **Display:** Hero promise and one decisive close only.
- **Headline:** Section decisions, capped at roughly 19 characters per line.
- **Title:** Card and module claims.
- **Body:** Explanations, kept near 62 characters per line.
- **Label:** Levels, measures, sources and operational status.

### Named Rules

**The Answer-First Rule.** Headlines state the decision or outcome; explanatory prose follows.

## Elevation

Depth is mostly structural: dark tonal layers and 1px rails. Shadows are reserved for illuminated controls, floating signage and the navigation bar when it separates from the page.

### Shadow Vocabulary

- **Sign Glow:** Blue diffuse shadow for the primary action and active lift state.
- **Equipment Drop:** Deep neutral shadow for signs and floating machinery.
- **Inset Edge:** A fine light inset that suggests manufactured surfaces.

### Named Rules

**The Physical Depth Rule.** If an element does not plausibly float in the car-park world, it receives no drop shadow.

## Components

### Buttons

- **Shape:** Firm but touch-friendly, with a 12px radius and 52px height.
- **Primary:** Sign blue with white type and a restrained blue glow.
- **Hover / Focus:** Small tonal shift; 2px high-visibility focus ring.
- **Secondary:** Transparent night surface with a strong structural border.

### Chips

- **Style:** Compact status pills using status color plus a low-opacity tint.
- **State:** Text and dot always agree; labels never rely on color alone.

### Cards / Containers

- **Corner Style:** 18px for primary panels; 8–14px for nested equipment.
- **Background:** Concrete surfaces separated by structural rails.
- **Shadow Strategy:** Flat by default.
- **Border:** One pixel, never a decorative colored stripe.
- **Internal Padding:** 20–30px depending on density.

### Inputs / Fields

- **Style:** Dark equipment surface, structural track and white/blue control.
- **Focus:** High-visibility blue ring.
- **Error / Disabled:** Stop red only for genuine failure; fog for disabled state.

### Navigation

Fixed, compact and transparent at entry; it gains a blurred night surface and bottom rail after scroll. Mobile retains brand and one decisive action.

### Live Capacity Sign

The signature component shows deterministic bookable capacity. It must never imply that an advisory forecast controls the gate.

## Do's and Don'ts

### Do:

- **Do** make the member guarantee legible before discussing forecasting.
- **Do** show entry and exit verification as one closed operational loop.
- **Do** distinguish measured evidence, planning assumptions and hypotheses.
- **Do** make the front cinematic and the business case restrained.
- **Do** switch B3/B4 to white investment-memo mode with flat panels and cool grey rules.
- **Do** use direct B3/B4 headings such as “Value Proposition”, “Business Impact” and “Pilot Investment”; place the argument in a smaller subtitle.
- **Do** support WCAG 2.1 AA focus and `prefers-reduced-motion` behavior.

### Don't:

- **Don't** use generic SaaS landing-page clichés.
- **Don't** make ParkFlow feel like a speculative startup disconnected from Sime Darby Property.
- **Don't** turn the business case into a static consulting-template wall of boxes.
- **Don't** conflate deterministic control with probabilistic forecasting.
- **Don't** use excessive animation, especially in financial and go-to-market sections.
- **Don't** use conclusion-style slogans as the main heading on commercial slides.
