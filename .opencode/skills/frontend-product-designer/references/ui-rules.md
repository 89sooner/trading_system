# UI rules

## Visual direction

Use practical, polished b2b saas defaults unless the user asks for something else.

Preferred qualities:
- clear information hierarchy
- consistent spacing
- restrained color usage
- readable density
- simple, work-oriented components

Avoid by default:
- decorative gradients everywhere
- unnecessary glassmorphism
- random card nesting
- excessive icon noise
- styling that competes with the task content

## Component defaults

Prefer shadcn/ui for:
- buttons
- inputs
- dialogs
- dropdown menus
- tabs
- tables where a simple base is enough
- cards only when grouping meaningfully improves clarity

## Layout rules

- start with the page structure before choosing micro-styles
- use spacing, sectioning, alignment, dividers, and typography before adding extra containers
- prefer cardless layouts when the content can stay legible without boxes everywhere
- make the main action or page purpose visually obvious

## Responsive rules

Always think about:
- mobile first fit
- desktop readability
- overflow handling
- table fallback behavior
- filter and toolbar wrapping
- modal sizing

## State coverage

For data-driven surfaces, define and implement:
- loading state
- empty state
- error state
- success state when user feedback matters
- disabled state when actions are blocked

## Accessibility rules

- use semantic html first
- ensure interactive elements are keyboard reachable
- preserve visible focus states
- label controls clearly
- associate validation messages with their fields
- avoid relying on color alone to communicate status
