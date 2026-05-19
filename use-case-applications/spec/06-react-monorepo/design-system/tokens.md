# Design tokens

All styling in both UIs uses these CSS custom properties. No hardcoded colors, spacing, or typography values in component code. The tokens are defined in `shared/ui/tokens.css` and consumed via Tailwind's `theme.extend` configuration.

## Color palette

```css
:root {
  /* Primary — used for interactive elements, links, focus rings */
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-primary-700: #1d4ed8;
  --color-primary-900: #1e3a5f;

  /* Neutral — used for text, borders, backgrounds */
  --color-neutral-50: #f8fafc;
  --color-neutral-100: #f1f5f9;
  --color-neutral-200: #e2e8f0;
  --color-neutral-400: #94a3b8;
  --color-neutral-600: #475569;
  --color-neutral-800: #1e293b;
  --color-neutral-900: #0f172a;

  /* Signal strength colors — used on signal cards */
  --color-signal-strong: #16a34a;    /* green-600 */
  --color-signal-moderate: #ca8a04;  /* yellow-600 */
  --color-signal-weak: #9ca3af;      /* gray-400 */
  --color-signal-gap: #dc2626;       /* red-600 */

  /* Compliance — used for banners and restricted content */
  --color-compliance-bg: #fef3c7;    /* amber-100 */
  --color-compliance-border: #f59e0b; /* amber-500 */
  --color-compliance-text: #92400e;  /* amber-800 */

  /* Provenance — used for provenance badges */
  --color-provenance-bg: #f0f9ff;    /* sky-50 */
  --color-provenance-border: #7dd3fc; /* sky-300 */
  --color-provenance-text: #0c4a6e;  /* sky-900 */
}
```

## Typography

```css
:root {
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  --text-xs: 0.75rem;    /* 12px — provenance badges, metadata */
  --text-sm: 0.875rem;   /* 14px — secondary text, table cells */
  --text-base: 1rem;     /* 16px — body text */
  --text-lg: 1.125rem;   /* 18px — section headers */
  --text-xl: 1.25rem;    /* 20px — page titles */
  --text-2xl: 1.5rem;    /* 24px — entity names */
}
```

## Spacing

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-12: 3rem;     /* 48px */
}
```

## Component-specific tokens

```css
:root {
  /* Signal card */
  --signal-card-radius: 0.5rem;
  --signal-card-padding: var(--space-4);
  --signal-card-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  /* Capability palette */
  --palette-item-height: 2.5rem;
  --palette-item-radius: 0.375rem;
  --palette-icon-size: 1.25rem;

  /* Compliance banner */
  --banner-padding: var(--space-3) var(--space-4);
  --banner-radius: 0.375rem;

  /* Provenance badge */
  --badge-padding: var(--space-1) var(--space-2);
  --badge-radius: 9999px;
  --badge-font-size: var(--text-xs);
}
```

## Usage in components

Components reference tokens via Tailwind utilities mapped to these variables:

```tsx
// Signal card uses signal strength color
<div className="border-l-4" style={{ borderColor: `var(--color-signal-${signal.strength})` }}>

// Compliance banner uses compliance tokens
<div className="bg-[var(--color-compliance-bg)] border border-[var(--color-compliance-border)] text-[var(--color-compliance-text)]">

// Provenance badge uses provenance tokens
<span className="bg-[var(--color-provenance-bg)] border border-[var(--color-provenance-border)] text-[var(--color-provenance-text)]">
```

## Dark mode

Not in Phase 1 scope. The token structure supports it (add `:root[data-theme="dark"]` overrides) but the workshop focuses on the architectural patterns, not the visual polish.
