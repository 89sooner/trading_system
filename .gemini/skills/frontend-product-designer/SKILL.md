---
name: frontend-product-designer
description: design, refine, and implement production-ready frontends for react and next.js products with strong structure, consistent design rules, practical b2b saas defaults, figma-aware implementation, and browser verification loops. use when building or improving pages, dashboards, forms, admin tools, landing pages, component systems, or ui flows, especially when requirements are vague, figma is missing, or the team needs consistent next.js app router, typescript, tailwind, shadcn/ui, form, accessibility, responsive, and playwright-friendly conventions.
---

# frontend product designer

Use this skill to turn vague or partially specified frontend requests into deliberate, production-ready UI work that fits a modern React and Next.js team workflow.

This skill is not tied to a specific model. Apply it with any capable coding model when the task benefits from better frontend structure, stronger defaults, and a more reliable implementation and verification loop.

## Default stack

Use these defaults unless the user, repository, or uploaded code clearly requires something else.

- next.js app router
- react
- typescript
- tailwind css
- shadcn/ui for common ui primitives
- react-hook-form and zod for forms that need validation
- playwright for browser-based verification when available

## Operating principles

Always follow these principles unless the repository or user explicitly overrides them.

- design the screen around the user task before choosing low-level components
- prefer practical b2b saas clarity over decorative styling
- prefer server components; add client components only when browser-only interaction or client-only hooks are required
- preserve existing repository patterns before introducing new abstractions
- include loading, empty, error, and success states when they matter to the flow
- prioritize semantic html, keyboard navigation, and accessible labels
- make responsive behavior intentional rather than incidental
- avoid generic “nice-looking” output without first defining structure, hierarchy, and constraints

## Core workflow

Follow this order unless the user already supplied the missing parts.

1. determine the working mode
- if the user provides figma frames, mockups, screenshots, or design captures, follow the figma-informed workflow
- if the user has no figma or no designer, follow the requirements-to-ui workflow
- if the user is modifying an existing screen, follow the refinement workflow

2. identify the surface and user goal
- classify the task: page, dashboard, admin tool, form, settings flow, table view, detail view, landing page, or component
- identify the primary user action: search, filter, compare, submit, review, create, edit, approve, or monitor
- identify whether the request is net-new, redesign, or targeted refinement

3. establish implementation constraints early
- confirm or infer the stack from the repository; otherwise use the default stack in this skill
- define layout rhythm, typography roles, spacing expectations, and state coverage before writing code
- keep the design language restrained: clear hierarchy, compact copy, predictable controls, and limited visual noise

4. choose the right workflow

### figma-informed workflow
- read `references/figma-workflow.md`
- identify the exact frame or screen state to implement
- preserve the visual hierarchy, spacing rhythm, type scale, control density, and component relationships
- adapt the design safely to the repository's design system and technical constraints instead of copying pixels blindly
- if figma and the existing design system conflict, explain the conflict briefly and choose the safer product-facing option

### requirements-to-ui workflow
- read `references/examples.md` for prompt and output patterns when the user gives only text requirements
- when figma is missing, do not stall; design from the product goal and the required actions
- propose the screen structure first
- then decompose into components
- then implement
- if the request is underspecified, infer a sensible b2b saas structure instead of asking the user to become a designer

### refinement workflow
- read `references/architecture.md`, `references/ui-rules.md`, and `references/code-style.md`
- preserve public api and existing behavior unless the user asked for broader redesign
- minimize regression risk
- improve hierarchy, consistency, state handling, and responsiveness before introducing new patterns

5. implement with team-oriented frontend rules
- follow `references/architecture.md` for next.js structure and rendering decisions
- follow `references/ui-rules.md` for visual defaults and component choices
- follow `references/code-style.md` for code organization and naming
- follow `references/testing.md` for manual and playwright-oriented verification

6. verify before declaring success
- inspect responsive behavior at mobile and desktop widths
- verify keyboard access, labels, and focus behavior on interactive surfaces
- verify loading, empty, error, validation, and success states where relevant
- if playwright or browser automation is available, run a verification loop using `references/playwright-workflow.md`
- when working from figma or screenshots, compare the result against the reference and note any intentional deviations

## Team rules captured from this conversation

Apply these defaults unless the repository clearly uses different standards.

- use next.js app router patterns for new work
- use typescript
- use tailwind css for styling
- prefer shadcn/ui for foundational ui primitives
- prefer server components unless interactivity requires a client component
- avoid unnecessary `use client`
- avoid broad framework or design-system substitutions in an existing codebase
- include loading, empty, and error states on data-driven screens
- keep layout and copy practical, scannable, and work-oriented
- default to modern b2b saas surfaces instead of flashy marketing aesthetics unless the user asks otherwise
- structure work as screen design first, component plan second, implementation third, and verification fourth

## Response pattern

When the request is not fully specified, respond in this order.

1. product and screen interpretation
- summarize the screen purpose, target user action, and surface type in 2 to 4 sentences

2. proposed structure
- list the main sections, states, and interaction zones before writing code

3. component plan
- identify reusable components and note which should remain server or client components

4. implementation
- produce the next.js, react, typescript, and tailwind code

5. verification notes
- state what was checked for responsive behavior, accessibility, and interaction
- if playwright was used, summarize findings and fixes

## Required reference files

Load these as needed.

- `references/architecture.md`
- `references/ui-rules.md`
- `references/code-style.md`
- `references/testing.md`
- `references/examples.md`
- `references/figma-workflow.md`
- `references/playwright-workflow.md`
- `references/frontend-principles.md`

## Special handling for figma-free requests

If the user says they do not have figma, do not ask them to produce one.

Instead:
- infer a sensible information architecture from the product goal
- propose a wireframe-level structure in text
- implement a clean first version
- then refine spacing, typography, hierarchy, and responsiveness
- optionally run browser verification when tooling is available

## Special handling for figma-based requests

If the user provides a figma link, frame description, screenshot, or export:
- identify the target frame and important states
- preserve visual hierarchy and spacing rhythm
- map the design onto repository-safe components and tokens
- do not overfit to a static mockup if it harms responsiveness or accessibility

## Special handling for browser verification

When the task benefits from end-to-end confidence and browser tooling is available:
- execute the relevant user flow
- look for layout breaks, invalid states, inaccessible interactions, and responsive issues
- fix the issues found
- re-run verification
- report what changed and what remains risky
