# Code style rules

## File and component organization

- prefer small, purposeful components over one giant page file
- keep page-level composition readable
- extract repeated ui patterns into reusable components when the repetition is real, not hypothetical

## Naming

- use descriptive component names
- use descriptive prop names
- use clear event and action names
- keep hook names aligned with react conventions

## Client and server discipline

- do not add `use client` by default
- isolate client behavior in the smallest sensible boundary
- keep server-safe code server-safe

## Styling discipline

- use tailwind utility classes consistently
- avoid ad hoc style systems when tailwind already covers the need
- do not hardcode one-off visual values repeatedly if a shared token or existing pattern exists

## Implementation behavior

- preserve repository conventions when visible in the codebase
- avoid unnecessary memoization unless it solves a measured or obvious problem
- prefer straightforward, readable react code over clever abstractions
- do not introduce a new architecture layer without a clear payoff

## Output expectations

When generating code for a user, try to include:
- the main implementation file
- any extracted reusable components that materially improve readability
- a short note about state handling and responsive behavior
