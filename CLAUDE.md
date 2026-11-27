# Esme Nicholson portfolio

Static site with no build step: `index.html`, `css/styles.css`, `js/main.js`, `images/`. (The README's npm instructions are out of date; there is no `package.json`.)

- **Selected Work tiles** are hardcoded `<article class="card">` blocks inside `<div class="work__grid">` in `index.html`, newest first across all broadcasters.
- **`data/articles.json`** mirrors the tiles in the same order. The page doesn't load it, but keep it in sync.
- **Deploy:** changes go live by pushing `main` to GitHub (`origin`). The contact form uses Netlify Forms, so the live site is most likely built by Netlify from `main`. Commit and push only when the user asks.

## Adding Esme's new NPR stories (the usual job)

1. **Check:** `python3 scripts/npr_update.py`
   Lists stories on her NPR author page that aren't on the site yet. It only looks at stories dated on or after the newest NPR tile on the site, so older stories that were left out on purpose don't come back. It changes nothing.
2. **Ask the user which to add.** The site is a selection, not a full archive. Point out stories that are on the list twice: a radio piece plus a web article about the same news. The script marks some of these "(same audio as #n)"; others are only visible as near-identical headlines on the same day.
3. **Add:** `python3 scripts/npr_update.py --apply` adds everything listed. Use `--only 1,4` or `--skip 2,3` with the list's numbers to add a subset. The script inserts tiles in date order and rewrites `data/articles.json` to match.
4. **Review:** NPR headlines are used word for word, so check them for typos (one had "though" for "through"). Look over `git diff`, then offer to commit and push.

The script uses only the standard library, fetches with `curl`, and takes about 1–2 seconds per new story. `--root <folder>` runs it against a copy of the site, which is useful for testing.

## Tile format

The script follows these rules. Use the same ones when editing tiles by hand.

```html
                    <article class="card">
                        <a href="{NPR URL}" class="card__link" target="_blank" rel="noopener noreferrer">
                            <div class="card__image">
                                <img src="{image}" alt="{headline}" loading="lazy">
                            </div>
                            <div class="card__content">
                                <h3 class="card__title">{headline}</h3>
                                <p class="card__show">{show}</p>
                                <p class="card__broadcaster">National Public Radio</p>
                                <time class="card__date">18th November 2026</time>
                            </div>
                        </a>
                    </article>
```

- **Show:** the "Heard on …" program on the NPR page. Weekend Edition Saturday or Sunday becomes `Weekend Edition`. State of the World episodes (their og:title ends ": State of the World from NPR") become `State of the World Podcast`. A web-only article gets the show of the radio piece whose audio it embeds, and `Feature` if it has none.
- **Date:** the article's `datePublished`, written as an ordinal day, full month and year.
- **Image:** the NPR lead photo, uncropped and resized to 1200 wide:
  `https://npr.brightspotcdn.com/dims3/default/strip/false/crop/{W}x{H}+0+0/resize/1200x{1200*H/W}!/?url={source}`.
  For a portrait original, use NPR's own 16:9 crop from `og:image` instead. Stories without a photo use `images/npr_og.png`.

## Adding SWP podcast episodes (links supplied by the user)

There is no script for these; the user pastes the episode URLs.

- **Tile:** title from the page's `<h1>` with curly apostrophes made straight and any "Megatrends Afrika: " prefix dropped. Show `Podcast`, broadcaster `Stiftung Wissenschaft & Politik`, date from the page's `datePublished`. Insert tiles in date order.
- **Thumbnail:** a local copy saved as `images/swp_NN_og.jpg`, numbering on from the highest existing number. The image is SWP's own 464×464 square (the publication photo, centre-cropped). Look for it in this order:
  1. The episode page: an `<img … height="464">` whose filename contains the episode's photo ID (e.g. `2024eP02_455481016`).
  2. The podcast listing, https://www.swp-berlin.org/en/service/swp-podcasts, which shows the 10 latest episodes, each with its square.
  3. If neither has it, make it yourself: take the original photo (`/assets/swp/Publikationsbilder/…` or `/publications/products/Podcast/…`), centre-crop it to a square with `sips -c`, then resize it to 464×464 with `sips -z`. This gives the same framing as SWP's version.
- Download images into an empty scratchpad folder first, and check that each one is a 464×464 JPEG before copying it into `images/`.

## NPR source

- **Author page:** https://www.npr.org/people/913987374/esme-nicholson, with 24 stories on the first page.
- **Older stories:** `…/esme-nicholson/archive?start=N`, where N is the number of stories already seen. Archive pages hold 15, so N is 24, 39, 54 and so on. Paging by fixed steps of 24 skips stories.
- **Show name:** the program is in `<div class="program-block">` on each article page.

## Previewing

In the Claude desktop app, `preview_start` can't read this folder because macOS privacy protection blocks access to `~/Documents`. To preview, copy `index.html`, `css`, `js` and `images` to the scratchpad and open that `index.html` as a `file://` URL. The browser pane only shows a static snapshot, so check structure and image URLs with scripts rather than page tools.
