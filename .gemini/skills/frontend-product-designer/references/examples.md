# Prompt and output examples

Use these patterns when the user has no figma, no designer, or only partial requirements.

## Example 1: no figma, new admin page

### Input style
Create a user management page. There is no figma and no designer. It should support search, status filters, a table, row click to view details, and a create button.

### Expected behavior
1. summarize the screen purpose
2. propose the page structure before code
3. identify reusable components
4. implement with next.js, typescript, tailwind, and shadcn/ui
5. include loading, empty, and error states

## Example 2: vague improvement request

### Input style
Make this settings page better.

### Expected behavior
Do not jump straight into random styling changes. First:
- infer the user task
- describe the hierarchy problems
- propose a better structure
- then implement focused improvements
- keep regressions low

## Example 3: form generation

### Input style
Build a profile edit form with validation.

### Expected behavior
Default to react-hook-form and zod. Include:
- field-level validation
- pending submit state
- server error handling
- success feedback if relevant

## Example 4: figma-free master prompt shape

Recommended prompt shape:
- state that figma is absent
- describe the product goal
- list key actions or data shown
- state the preferred tone such as practical b2b saas
- request structure first, implementation second, verification third

## Suggested output shape

1. screen interpretation
2. structure proposal
3. component plan
4. code
5. state handling summary
6. verification notes
