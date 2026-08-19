# V.I.A Liceo Tame DESIGN.md

> Auto-generated design system — reverse-engineered via static analysis by skillui.
> Frameworks: None detected
> Colors: 20 · Fonts: 1 · Components: 0
> Icon library: not detected · State: not detected
> Primary theme: dark · Dark mode toggle: no · Motion: subtle

---

## 1. Visual Theme & Atmosphere

This is a **dark-themed** interface with a neutral tone. Depth is expressed through layered shadows and subtle surface color variation. Typography uses **sans-serif** throughout — a clean, modern choice that maintains consistency. Spacing follows a **4px base grid** (compact density), with scale: 2, 4, 6, 8, 10, 12, 14, 16px. Motion is subtle — smooth transitions (150-300ms) ease state changes without drawing attention.

---

## 2. Color Palette & Roles

| Token | Hex | Role | Use |
|---|---|---|---|
| background | `#222222` | background | Page background, darkest surface |
| texto-card | `#1a3d2b` | surface | Card and panel backgrounds |
| text-primary | `#ffffff` | text-primary | Headings and body text |
| text-muted | `#999999` | text-muted | Captions, placeholders, secondary info |
| border | `#555555` | border | Dividers, card borders, outlines |
| danger | `#c0392b` | danger | Error states, destructive actions |
| success | `#e4f2e0` | success | Success states, positive indicators |
| warning | `#c9a227` | warning | Warning states, caution indicators |
| unknown | `#eeeeee` | unknown | Palette color |
| unknown | `#888888` | unknown | Palette color |
| unknown | `#0d2318` | unknown | Palette color |
| unknown | `#285c1f` | unknown | Palette color |
| unknown | `#8a2c23` | unknown | Palette color |
| unknown | `#8a6d10` | unknown | Palette color |
| unknown | `#fbe4e2` | unknown | Palette color |
| unknown | `#666666` | unknown | Palette color |
| unknown | `#3a6b4a` | unknown | Palette color |
| unknown | `#fdf3d8` | unknown | Palette color |
| unknown | `#333333` | unknown | Palette color |
| unknown | `#fdf0ee` | unknown | Palette color |

### CSS Variable Tokens

```css
--texto-card: #1a3d2b;
--sombra-card: 0 8px 40px rgba(0,0,0,0.28);
--radio-card: 14px;
```


---

## 3. Typography Rules

**Font Stack:**
- **sans-serif** — Heading 1, Heading 2, Heading 3, Body, Caption

| Role | Font | Size | Weight |
|---|---|---|---|
| Heading 1 | sans-serif | 7rem | 700 |
| Heading 2 | sans-serif | 3.8rem | 700 |
| Heading 3 | sans-serif | 3.4rem | 700 |
| Body | sans-serif | 0.72rem | 400 |
| Caption | sans-serif | 1.05rem | 400 |

**Typographic Rules:**
- Use **sans-serif** for all text — do not mix font families
- Maintain consistent hierarchy: no more than 3-4 font sizes per screen
- Headings use bold (600-700), body uses regular (400)
- Line height: 1.5 for body text, 1.2 for headings
- Use color and opacity for secondary hierarchy, not additional font sizes


---

## 4. Component Stylings

No components detected. Scan `src/components/` or `components/` to populate this section.

---

## 5. Layout Principles

- **Base spacing unit:** 4px
- **Spacing scale:** 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24
- **Border radius:** 0 8px 8px 0, 0 6px 6px 0, 2px, 3px 3px 42% 42%/3px 3px 26% 26%, 3px 3px 38% 38%/3px 3px 22% 22%, 3px 3px 40% 40%/3px 3px 24% 24%, 3px, 4px, 4px 4px 48% 48%/4px 4px 28% 28%, 6px, 8px, 10px, 12px, 14px, 16px, 20px, 50px
- **Max content width:** 980px

**Spacing as Meaning:**
| Spacing | Use |
|---|---|
| 4-8px | Tight: related items within a group |
| 12-16px | Medium: between groups |
| 24-32px | Wide: between sections |
| 48px+ | Vast: major section breaks |


---

## 6. Depth & Elevation

### Flat — subtle depth hints

- `0 0 0 2px rgba(58,107,74,0.12)`

### Raised — cards, buttons, interactive elements

- `0 0 8px rgba(201,162,39,0.6)`
- `0 1px 6px rgba(13,35,24,0.06)`
- `0 0 0 3px rgba(201,162,39,0.22)`

### Floating — dropdowns, popovers, modals

- `0 2px 14px rgba(13,35,24,0.08)`
- `0 3px 18px rgba(0,0,0,0.06)`
- `0 2px 16px rgba(0,0,0,0.07)`

### Overlay — full-screen overlays, top-level dialogs

- `0 12px 36px rgba(0,0,0,0.14)`
- `0 12px 36px rgba(201,162,39,0.28)`
- `0 8px 28px rgba(0,0,0,0.18)`

### Z-Index Scale

`2, 100, 150, 200, 300, 400, 500, 9999`



---

## 7. Animation & Motion

This project uses **subtle motion**. Transitions smooth state changes without demanding attention.

### CSS Animations

- `@keyframes via-girar`
- `@keyframes via-aparecer`
- `@keyframes via-brillo`
- `@keyframes via-pulso`

### Motion Guidelines

- Duration: 150-300ms for micro-interactions, 300-500ms for page transitions
- Easing: `ease-out` for enters, `ease-in` for exits
- Always respect `prefers-reduced-motion`


---

## 8. Do's and Don'ts

### Do's

- Use `#222222` as the primary page background
- Use **sans-serif** for all UI text
- Follow the **4px** spacing grid for all margins, padding, and gaps
- Use the defined shadow tokens for elevation — see Section 6
- Use border-radius from the scale: 0 8px 8px 0, 0 6px 6px 0, 2px, 3px 3px 42% 42%/3px 3px 26% 26%, 3px 3px 38% 38%/3px 3px 22% 22%

### Don'ts

- Don't introduce colors outside this palette — extend the design tokens first
- Don't mix font families — use sans-serif consistently
- Don't use arbitrary spacing values — stick to multiples of 4px
- Don't create custom box-shadow values outside the system tokens
- Don't use arbitrary border-radius values — pick from the defined scale
- Don't use backdrop-blur or blur effects

### Anti-Patterns (detected from codebase)

- No blur or backdrop-blur effects
- No zebra striping on tables/lists


---

## 9. Responsive Behavior

No breakpoints detected. Consider adding responsive breakpoints to the design system.

---

## 10. Agent Prompt Guide

Use these as starting points when building new UI:

### Build a Card

```
Background: #1a3d2b
Border: 1px solid #555555
Radius: 4px 4px 48% 48%/4px 4px 28% 28%
Padding: 16px
Font: sans-serif
Use shadow tokens from Section 6.
```

### Build a Button

```
Primary: bg var(--accent), text white
Ghost: bg transparent, border #555555
Padding: 8px 16px
Radius: 4px 4px 48% 48%/4px 4px 28% 28%
Hover: opacity 0.9 or lighter shade
Focus: ring with var(--accent)
```

### Build a Page Layout

```
Background: #222222
Max-width: 980px, centered
Grid: 4px base
Responsive: mobile-first, breakpoints from Section 9
```

### Build a Stats Card

```
Surface: #1a3d2b
Label: #999999 (muted, 12px, uppercase)
Value: #ffffff (primary, 24-32px, bold)
Status: use success/warning/danger from Section 2
```

### Build a Form

```
Input bg: #222222
Input border: 1px solid #555555
Focus: border-color var(--accent)
Label: #999999 12px
Spacing: 16px between fields
Radius: 4px 4px 48% 48%/4px 4px 28% 28%
```

### General Component

```
1. Read DESIGN.md Sections 2-6 for tokens
2. Colors: only from palette
3. Font: sans-serif, type scale from Section 3
4. Spacing: 4px grid
5. Components: match patterns from Section 4
6. Elevation: shadow tokens
```
