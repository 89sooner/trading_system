# Architecture rules

## Framework default

Use next.js app router for new work unless the repository clearly uses a different structure.

## Rendering rules

- default to server components
- add `use client` only when local interaction, browser apis, refs, event handlers, or client-only hooks are required
- do not mark entire pages as client components when a small interactive child is sufficient

## Data fetching

- fetch on the server first when practical
- keep data orchestration near the page or server boundary
- avoid moving fetch logic into client components without a clear need

## Route structure

Use app router conventions where relevant:
- `page.tsx` for route content
- `layout.tsx` for shared route chrome
- `loading.tsx` for async route loading states
- `error.tsx` for recoverable route errors
- split large areas into route-safe reusable components

## State boundaries

- keep transient ui state local when possible
- avoid adding a new state library unless the project already uses one or the need is clear
- derive state from server data and route params before adding extra client state

## Forms

Default to:
- react-hook-form for field management
- zod for schema validation

For forms, include:
- field-level validation feedback
- submit pending state
- server failure handling
- success handling when it affects the flow

## Reuse rules

- preserve public component apis unless the user asked for a breaking redesign
- prefer extending existing patterns over creating parallel component families
- minimize change surface in established repositories
