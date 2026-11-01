# Design

Derived from the shipped site. Sources of truth: `tools/assets/site.css`, `tools/assets/site.js`, `tools/build.py`.

## World

The school's own look, kept recognisable: olive textured header and footer, paper-texture ground, brown ink, rose and olive buttons, rounded photographs and circles, the white bird logo. Copy is Swedish and comes from the school's site.

## Tokens

- Olive: `--olive #79805a`, `--olive-deep #5f6645`, `--olive-ink #464c31`
- Rose: `--rose #e9938a`, `--rose-deep #c97074`
- Ink and text: `--ink #3f3100`, `--text #2a2413`, `--muted #5d5540`
- Ground: `--paper #efe7df`, `--band #f0e6dc`, `--line #cfc2b2`
- Type: Antroposof for display, Open Sans for body
- Layout: `--wrap 1200px`, `--radius 16px`, easing `--ease cubic-bezier(.16,1,.3,1)`

## Page structure

- Home: full hero, errands, teasers, quotes, poster, invitation, sideways gallery.
- Inner pages: `page_hero()` gives every page a photo, four birds, hanging blossoms, the title and the paper hill with three running girls. `subnav()` adds section tabs and `extras()` adds a quote or gallery where listed, then "Läs också". Pages with no photo of their own take one from `HERO_PHOTOS`. Lettered posters never sit behind a title; they follow the hero as `.poster-inline`.
- Content: photo and text sections alternate with `.band` backgrounds; text-only runs use one or two columns.

## Motion

- Birds and girls loop only while the hero is on screen. The girls are drawn on canvas: a two-bone run cycle, a hem and hair with their own delay, and a shadow on the hill.
- Blossoms hang in the top right corner, shorter toward the page centre so they stay clear of photo subjects. They sway, lean with scroll speed and drop a few petals.
- Photos shift inside their frames on scroll; the header carries a scroll-progress bird.
- An olive bird crosses each `.sec.band` in step with scrolling.
- Photos and list rows (calendar, staff, documents) rise once on arrival. Running text does not animate.
- `prefers-reduced-motion` removes all of it and leaves birds, girls and blossoms still.

## Rules

- Internal links end in `index.html`, so the site works from disk as well as from a server.
- The concept notice and `noindex` stay on every page. Forms state that nothing is sent.
- Build with `python tools/build.py` from inside `tools/`. Originals download into `src-assets/` on demand.
- Search covers pages, sections, staff and calendar events, ignores diacritics and tolerates typos. Shortcuts: `/` and Ctrl+K, arrows, Enter.
