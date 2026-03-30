# Frontend principles

This file distills the operating ideas behind this skill into reusable rules.

## Core ideas

### 1. define the screen before the code
Do not jump into isolated component code when the request is vague. Clarify or infer:
- the screen type
- the primary user task
- the main sections
- the critical states

### 2. constrain the design early
Underspecified prompts often produce generic layouts. Decide early:
- type hierarchy
- spacing rhythm
- density level
- control style
- state coverage

### 3. prefer practical product surfaces
For internal tools, dashboards, and admin views, clarity beats decoration. Favor:
- strong information hierarchy
- predictable controls
- compact but readable copy
- deliberate spacing
- minimal chrome

### 4. preserve the repository language
When modifying an existing project, respect:
- dependency choices
- component primitives
- route structure
- state patterns
- design tokens
- testing conventions

### 5. verify real behavior
A screen is not done when the code compiles. Check:
- mobile and desktop layout
- interaction states
- validation and errors
- keyboard access
- runtime regressions

## Practical defaults

- next.js app router is the default for new work
- use typescript
- use tailwind for styling
- prefer shadcn/ui as the base primitive layer
- prefer server components unless interactivity requires client code
- use react-hook-form and zod for validated forms
- use playwright when browser verification meaningfully reduces risk

## figma note

Figma is helpful but not required. If figma is missing, infer a sensible wireframe from the product goal and proceed.
