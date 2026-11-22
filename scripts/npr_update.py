#!/usr/bin/env python3
"""Find NPR stories by Esme Nicholson that aren't on the site yet, and optionally add them as tiles.

    python3 scripts/npr_update.py                      # list new stories, change nothing
    python3 scripts/npr_update.py --apply              # add every new story
    python3 scripts/npr_update.py --apply --only 1,4   # add only these numbers from the list
    python3 scripts/npr_update.py --apply --skip 2,3   # add all except these numbers

"New" means: on Esme's NPR author page, dated on or after the newest NPR tile already on
the site, and not already linked from the site. Older stories that were left out on purpose
are never suggested again.

Writes index.html (new tiles, in date order) and data/articles.json (kept in page order).
Standard library only; fetches with curl.
"""
import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys

AUTHOR_URL = "https://www.npr.org/people/913987374/esme-nicholson"
BROADCASTER = "National Public Radio"
FALLBACK_IMAGE = "images/npr_og.png"
GRID_ANCHOR = '<div class="work__grid">'
CARD_RE = re.compile(r'[ \t]*<article class="card">.*?</article>', re.S)
SOTW_SUFFIX = ": State of the World from NPR"
MAX_PAGES = 15


def fetch(url):
    out = subprocess.run(
        ["curl", "-sSfL", "--max-time", "30", "-A", "Mozilla/5.0", url],
        capture_output=True, check=True,
    )
    return out.stdout.decode("utf-8", "replace")


def clean(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def story_id(url):
    """NPR's stable story id (e.g. nx-s1-5471235, g-s1-19581, 1191724399) or the bare URL."""
    m = re.search(r"npr\.org/(?:sections/[^/]+/)?\d{4}/\d{2}/\d{2}/([^/?#]+)", url)
    return m.group(1) if m else url.rstrip("/")


def ordinal_date(d):
    n = d.day
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return "%d%s %s" % (n, suffix, d.strftime("%B %Y"))


def parse_card_date(text):
    return datetime.datetime.strptime(re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text.strip()), "%d %B %Y").date()


# ---------- the site ----------

def read_site_cards(src):
    cards = []
    for m in CARD_RE.finditer(src):
        block = m.group(0)
        cards.append(dict(
            start=m.start(), end=m.end(),
            url=re.search(r'<a href="([^"]+)"', block).group(1),
            broadcaster=clean(re.search(r'<p class="card__broadcaster">(.*?)</p>', block, re.S).group(1)),
            date=parse_card_date(clean(re.search(r'<time class="card__date">(.*?)</time>', block, re.S).group(1))),
        ))
    return cards


# ---------- NPR ----------

def parse_listing(page):
    items = []
    for block in re.findall(r'<article class="item[^"]*".*?</article>', page, re.S):
        link = re.search(r'<h2 class="title"><a href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        date = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})', block)
        teaser = re.search(r'<p class="teaser">(.*?)</p>', block, re.S)
        teaser = clean(teaser.group(1)) if teaser else ""
        items.append(dict(
            url=link.group(1),
            title=clean(link.group(2)),
            listed=date.group(1) if date else "",
            teaser=re.sub(r"^[A-Z][a-z]+ \d{1,2}, \d{4}\s*•\s*", "", teaser),
        ))
    return items


def author_items_since(cutoff):
    """Author-page items dated >= cutoff. Page 1 has 24 items, /archive pages 15; paginate by count."""
    items, seen = [], 0
    for page_no in range(MAX_PAGES):
        url = AUTHOR_URL if page_no == 0 else "%s/archive?start=%d" % (AUTHOR_URL, seen)
        page_items = parse_listing(fetch(url))
        if not page_items:
            break
        seen += len(page_items)
        items.extend(i for i in page_items if i["listed"] >= cutoff.isoformat())
        if page_items[-1]["listed"] and page_items[-1]["listed"] < cutoff.isoformat():
            break
    return items


def norm_show(program):
    program = re.sub(r"^Heard on\s+", "", program).strip()
    return "Weekend Edition" if program.startswith("Weekend Edition") else program


def article_details(item):
    s = fetch(item["url"])
    def find(pattern):
        m = re.search(pattern, s, re.S)
        return m.group(1) if m else None
    og_title = html.unescape(find(r'<meta property="og:title" content="([^"]*)"') or "")
    og_image = find(r'<meta property="og:image" content="([^"]*)"') or ""
    published = find(r'"datePublished":"(\d{4}-\d{2}-\d{2})') or item["listed"]
    program_block = find(r'<div class="program-block">(.*?)</div>')
    audio = set(re.findall(r'data-embed-url="https://www\.npr\.org/player/embed/[^/"]+/([^"]+)"', s))

    # Thumbnail: the lead photo's uncropped frame (crop/WxH+0+0), resized to 1200 wide.
    # Portrait originals use NPR's own 16:9 crop instead. No photo -> NPR logo fallback.
    image = FALLBACK_IMAGE
    if "brightspotcdn" in og_image and "?url=" in og_image:
        key = og_image.split("?url=", 1)[1]
        frames = re.findall(r"crop/(\d+)x(\d+)\+0\+0/resize/[^\"' ]*?\?url=" + re.escape(key), s)
        frames = [(int(w), int(h)) for w, h in frames]
        best = max(frames, key=lambda f: f[0] * f[1]) if frames else None
        if best and best[0] >= best[1]:
            crop, w, h = "%dx%d+0+0" % best, best[0], best[1]
        else:
            m = re.search(r"crop/((\d+)x(\d+)\+\d+\+\d+)/", og_image)
            crop, w, h = m.group(1), int(m.group(2)), int(m.group(3))
        image = "https://npr.brightspotcdn.com/dims3/default/strip/false/crop/%s/resize/1200x%d!/?url=%s" % (
            crop, round(1200 * h / w), key)

    return dict(item,
                published=published,
                program=norm_show(clean(program_block)) if program_block else "",
                podcast=og_title.endswith(SOTW_SUFFIX),
                audio=audio,
                image=image)


def assign_shows(stories):
    """Radio pieces: their program. Podcast episodes: State of the World Podcast.
    Web articles: the program of the radio piece whose audio they embed, else Feature."""
    by_audio = {a: s["program"] for s in stories if s["program"] for a in s["audio"]}
    for s in stories:
        if s["program"]:
            s["show"] = s["program"]
        elif s["podcast"]:
            s["show"] = "State of the World Podcast"
        else:
            s["show"] = next((by_audio[a] for a in s["audio"] if a in by_audio), "Feature")


# ---------- output ----------

def esc(text):
    return html.escape(text, quote=False).replace('"', "&quot;")


def card_html(s, indent):
    i = indent
    return (
        f'{i}<article class="card">\n'
        f'{i}    <a href="{s["url"]}" class="card__link" target="_blank" rel="noopener noreferrer">\n'
        f'{i}        <div class="card__image">\n'
        f'{i}            <img src="{s["image"]}" alt="{esc(s["title"])}" loading="lazy">\n'
        f'{i}        </div>\n'
        f'{i}        <div class="card__content">\n'
        f'{i}            <h3 class="card__title">{esc(s["title"])}</h3>\n'
        f'{i}            <p class="card__show">{esc(s["show"])}</p>\n'
        f'{i}            <p class="card__broadcaster">{BROADCASTER}</p>\n'
        f'{i}            <time class="card__date">{ordinal_date(s["date"])}</time>\n'
        f'{i}        </div>\n'
        f'{i}    </a>\n'
        f'{i}</article>'
    )


def insert_cards(src, site_cards, stories):
    """Put each new card before the first existing card with an older date (existing order untouched)."""
    indent = re.match(r"[ \t]*", src[site_cards[0]["start"]:]).group(0) if site_cards else " " * 20
    inserts = {}  # offset -> [card text]
    for s in sorted(stories, key=lambda s: s["date"], reverse=True):
        target = next((c for c in site_cards if c["date"] < s["date"]), None)
        if target:
            inserts.setdefault(target["start"], []).append(card_html(s, indent) + "\n\n")
        else:
            end = site_cards[-1]["end"] if site_cards else src.index(GRID_ANCHOR) + len(GRID_ANCHOR)
            inserts.setdefault(end, []).append("\n\n" + card_html(s, indent))
    for offset in sorted(inserts, reverse=True):
        src = src[:offset] + "".join(inserts[offset]) + src[offset:]
    return src


def sync_articles_json(path, page_src, stories):
    data = json.load(open(path, encoding="utf-8"))
    by_id = {story_id(e["url"]): e for e in data}
    for s in stories:
        by_id[story_id(s["url"])] = dict(
            title=s["title"], show=s["show"], broadcaster=BROADCASTER, date=ordinal_date(s["date"]),
            url=s["url"], image=s["image"], description=s["teaser"])
    out = []
    for n, c in enumerate(read_site_cards(page_src), 1):
        entry = by_id.get(story_id(c["url"]))
        if entry is None:
            print("warning: no articles.json entry for %s" % c["url"], file=sys.stderr)
            continue
        entry = {k: v for k, v in entry.items() if k != "id"}
        out.append(dict(id=n, **entry))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return len(out)


def pick(numbers, total):
    chosen = {int(n) for n in numbers.split(",") if n.strip()}
    bad = sorted(n for n in chosen if not 1 <= n <= total)
    if bad:
        sys.exit("no such story number(s): %s" % bad)
    return chosen


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the new tiles (default: list only)")
    ap.add_argument("--only", help="comma-separated story numbers to add")
    ap.add_argument("--skip", help="comma-separated story numbers to leave out")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                    help="site folder (default: this repo)")
    args = ap.parse_args()

    index_path = os.path.join(args.root, "index.html")
    data_path = os.path.join(args.root, "data", "articles.json")
    src = open(index_path, encoding="utf-8").read()
    site_cards = read_site_cards(src)
    npr_dates = [c["date"] for c in site_cards if c["broadcaster"] == BROADCASTER]
    if not npr_dates:
        sys.exit("no NPR tiles found in %s" % index_path)
    cutoff = max(npr_dates)
    on_site = {story_id(c["url"]) for c in site_cards}

    listing = author_items_since(cutoff)
    fresh, seen = [], set()
    for item in listing:
        sid = story_id(item["url"])
        if sid not in on_site and sid not in seen:
            seen.add(sid)
            fresh.append(item)
    print("Newest NPR tile on the site: %s. Author-page items since then: %d. Not yet on the site: %d."
          % (ordinal_date(cutoff), len(listing), len(fresh)))
    if not fresh:
        return

    stories = [article_details(item) for item in fresh]
    assign_shows(stories)
    for s in stories:
        s["date"] = datetime.date.fromisoformat(s["published"])

    audio_owner = {}
    for n, s in enumerate(stories, 1):
        same = sorted({audio_owner[a] for a in s["audio"] if a in audio_owner})
        for a in s["audio"]:
            audio_owner.setdefault(a, n)
        note = "  (same audio as #%s)" % ",".join(map(str, same)) if same else ""
        thumb = "logo " if s["image"] == FALLBACK_IMAGE else "photo"
        print("%3d. %-19s %-26s %s  %s%s\n     %s" % (
            n, ordinal_date(s["date"]), s["show"], thumb, s["title"], note, s["url"]))

    if not args.apply:
        print("\nList only. Re-run with --apply (optionally --only/--skip) to add tiles.")
        return

    chosen = set(range(1, len(stories) + 1))
    if args.only:
        chosen = pick(args.only, len(stories))
    if args.skip:
        chosen -= pick(args.skip, len(stories))
    to_add = [s for n, s in enumerate(stories, 1) if n in chosen]
    if not to_add:
        print("Nothing selected.")
        return

    new_src = insert_cards(src, site_cards, to_add)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_src)
    count = sync_articles_json(data_path, new_src, to_add)
    print("\nAdded %d tile(s). index.html now has %d tiles; articles.json has %d entries."
          % (len(to_add), len(read_site_cards(new_src)), count))


if __name__ == "__main__":
    main()
