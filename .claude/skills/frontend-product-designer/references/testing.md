# Testing and verification

## Minimum verification mindset

Do not treat “code generated” as “done.” At minimum, reason through:
- happy path
- empty state
- error state
- loading state
- disabled state when relevant
- mobile and desktop layout

## Manual verification checklist

Check these when browser automation is not available:
- primary action is obvious
- spacing and hierarchy remain clear on mobile and desktop
- forms show validation feedback
- long text does not break the layout
- tables, filters, dialogs, and menus remain usable
- keyboard interaction still makes sense

## When to use playwright

Use playwright when:
- the task includes important user flows
- the screen has interactive forms or filters
- responsive regressions are likely
- the user explicitly asks for verification
- the cost of a silent ui bug is meaningful

## What to verify with playwright

- page renders without layout breakage
- key buttons and links work
- form validation and submit states work
- modal or drawer open/close behavior works
- mobile width and desktop width both remain usable
- accessibility-adjacent issues such as focus loss are checked when practical

## Reporting pattern

After verification, report:
- what flows were checked
- what issues were found
- what was fixed
- what still needs human review
