# Figma-informed workflow

Use this file when the user provides figma frames, screenshots, exports, or other visual references.

## Goals

- preserve the intended hierarchy and density
- map the design onto maintainable product code
- keep the result responsive and accessible

## Process

1. identify the exact target frame or state
- determine whether the user wants a page, a component, or a flow
- identify hover, selected, validation, modal, loading, and empty states if visible

2. extract the structural signal
- major sections
- toolbar and action areas
- navigation patterns
- content grouping
- repeated component patterns

3. preserve the right things
- spacing rhythm
- typography hierarchy
- button prominence
- control density
- visual grouping

4. adapt safely
- use repository-safe tokens and component primitives
- do not overfit to a static pixel-perfect mockup when responsiveness would suffer
- if a figma detail conflicts with accessibility or component reusability, favor the safer product implementation and explain it briefly

5. implement and compare
- build the screen
- compare against the reference
- note intentional deviations

## If the user only has a figma link

Ask for or use the most relevant frame description when possible, but proceed using the available context. A screenshot or export usually improves fidelity.
