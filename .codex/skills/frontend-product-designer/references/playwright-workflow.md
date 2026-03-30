# Playwright verification workflow

Use this file when browser automation is available or when the user explicitly asks for a verification loop.

## Verification loop

1. run or open the target screen
2. exercise the main flow
3. inspect layout, interaction, and state behavior
4. fix the discovered issues
5. re-run verification
6. report findings, fixes, and remaining risk

## High-value checks

### Layout
- mobile width remains usable
- desktop width preserves hierarchy
- tables, filters, buttons, and toolbars do not overflow badly
- dialogs and drawers size correctly

### Interaction
- key buttons work
- links navigate correctly
- filters update results correctly
- modals open and close correctly
- menus and tabs behave predictably

### Forms
- invalid input shows useful feedback
- pending submit state is visible
- double submission is prevented when relevant
- server failures are surfaced clearly

### Accessibility-adjacent checks
- focus remains visible
- keyboard usage is still possible for core actions
- control labeling is not obviously broken

## Reporting format

Summarize:
- what was tested
- what issues were found
- what fixes were applied
- what remains for human review
