"""Builds the static site in site/ from the school's real content (content/*.json)."""
import html as H
import json
import re
import shutil
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

from extract import ROOT, clean, load_pages

SITE = ROOT / "site"
SRC = ROOT / "src-assets"
ORIGIN = "https://rudolfsteinerskolan.se"
UPLOADS = ORIGIN + "/wp-content/uploads/"
KNACK = "https://idunsoft.knack.com/portal#ansokan-norrkoping/"
SCHOOLSOFT = "https://sms.schoolsoft.se/rudolfsteinerskolan"
SKOLSKJUTS = "https://norrkoping.se/skola-och-forskola/grundskola/skolskjuts"
INSTAGRAM = "https://www.instagram.com/rudolfsteinerskolaninorrkoping/"
FACEBOOK = "https://www.facebook.com/rudolfsteinerskolan.norrkoping/"

NAV = [
    ("Om oss", "om-oss", [
        ("Om oss", "om-oss"), ("Grundskola", "grundskola"), ("Fritidshem", "om-oss/fritidshemmet"),
        ("Förskola", "https://xn--waldorffrskolanppelblomman-uhc01c.se/"), ("Medarbetare", "om-oss/medarbetare"),
        ("Elevhälsa", "om-oss/elevhalsa"), ("Elevinflytande", "om-oss/elevinflytande"), ("Styrelse", "om-oss/styrelsen"),
        ("Fastighetsägare", "http://stathogabyggnadsstiftelse.se/"), ("Skollunch", "om-oss/vegetarisk-skollunch"),
    ]),
    ("Vår pedagogik", "waldorfpedagogik", []),
    ("Kontakta oss", "kontakta-oss", [
        ("Kontakta oss", "kontakta-oss"), ("Ansök till skolan", "ansok"), ("Lediga tjänster", "kontakta-oss/lediga-tjanster"),
    ]),
    ("Ansök", "ansok", []),
]
PARENTS = [
    ("För föräldrar", "for-foraldrar"), ("Kalendarium", "kalendarium"), ("Årstidsfester", "for-foraldrar/arstidsfester"),
    ("Elevhälsa", "om-oss/elevhalsa"), ("Föräldraföreningen", "for-foraldrar/foraldraforeningen"),
    ("Sjukanmälan & ledighetsansökan", "for-foraldrar/sjukanmalan"), ("Att vara waldorfförälder", "om-oss/att-vara-waldorfforalder"),
    ("Synpunkter & klagomål", "klagomalshantering"),
]
# Old WordPress addresses that the original site redirects.
REDIRECTS = {
    "om-oss/vegetarisk-mat": "om-oss/vegetarisk-skollunch",
    "om-oss/fritidshem": "om-oss/fritidshemmet",
    "om-oss/skolhalsovard": "om-oss/elevhalsa",
    "om-oss/foraldraengagemang": "for-foraldrar/foraldraforeningen",
    "waldorfforalder/foraldraforeningen": "for-foraldrar/foraldraforeningen",
}
LETTERED = re.compile(r"Julbasar|Oppet-hus|Jubileum|Vinstlotter|Gamla-elever")
ROUND_MEDIA = {"om-oss", "grundskola", "for-foraldrar", "for-foraldrar/arstidsfester"}

# Verbatim from /kalendarium/ (Kalendarium 26/27).
CAL_HT = """3 aug – Fritidshemmet öppnar
16 aug – Instäd kl. 17:00
17 aug – Skolstart och upprop kl. 10:00
20 aug – Skolfotografering
8 sep – Välkomstfest
V37 – Klass 3 – Växtfärgning
17-18 sep – Klass 4, Forntidsby
16-18 sep – Klass 5, Getsjötorp
14-18 sep – Klass 6, Idre
30 sep – Mikaelifirande
V39 – Projektvecka
7 okt – Friluftsdag, Orientering
8-9 okt – Studiedagar
17 okt – Höstfixardag
20 okt – Öppet hus kl. 17:00-18:30
V41-43 – Utvecklingssamtal åk FK-9
V44 – Höstlov
V45-48 – Ämneslärarsamtal åk 8-9
3 nov – Informationsmöte skolval
28 nov – Julbasar kl. 11-15
11 dec – Klass 3 Lucia
18 december – Julavslutning kl. 13:00""".split("\n")
CAL_VT = """21 dec – 6 jan – Jullov
7-8 jan – Studiedagar
27 jan – Friluftsdag, Vintersport
29 jan – Studiedag
V8 – Sportlov
V9-12 – Ämneslärarsamtal åk 7-9
25 mar – Månadsfest Hörsalen kl. 12:30
26 mar – Långfredag
V13 – Påsklov
17 apr – Vårfixardag
27 apr – Öppet hus kl. 17:00-18:30
30 apr – Valborgfirande och Vårfest
3 maj – Informationsmöte skolval
5 maj – Friluftsdag – Friidrott
6 maj – Kristihimmelfärd
7 maj – Klämdag
V21-22 – Klass 8 PRAO
Vecka 22 – Klass 9 – Tyskland
10 jun – Skolavslutning kl. 10:00
V24-26 – Sommarfrita
V27-30 – Fritidshemmet stängt""".split("\n")

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "maj": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12}
HOME_PHOTO = "2021/02/rudolfsteinerskolan-stathoga-herrgard-waldorf-appelblommor.jpg"
HOME_ALT = "Blommande äppelträd framför skolans röda hus på en grön kulle"
# The home hero turns through the school's own photos of its buildings: (photo, alt, focus, focus on phones, crop).
HOME_SLIDES = [
    (HOME_PHOTO, HOME_ALT, "62% 60%", "80% 60%", None),
    ("2021/05/Valkommen-till-rudolfsteinerskolan.jpg", "Skolans röda hus med skylten Välkommen till Rudolf Steinerskolan bakom tulpaner", "68% 40%", "70% 40%", None),
    ("2021/06/Rudolfsteinerskolan-skolgard-tradgard-utemiljo.jpg", "Rött skolhus med en rund rabatt av tulpaner på skolgården", "40% 48%", "30% 50%", None),
    # The original is two photos side by side; the right one, past the flagpole, shows the houses round the yard.
    ("2021/05/rudolfsteinerskolan-skolgard.jpg", "Skolgården med skolans ljusa och röda hus", "50% 45%", "45% 50%", (1012, 0, 1920, 500)),
]
# The logo cut into its lettering and its three swans, so the swans can glide (boxes in the 420x131 file).
LOGO_PARTS = [("word", (7, 1, 413, 33)), ("swan-1", (2, 83, 139, 128)), ("swan-2", (141, 73, 275, 112)), ("swan-3", (277, 49, 418, 112))]
# Pages whose original has no photo of its own (or only a lettered poster) borrow one from the school's gallery.
HERO_PHOTOS = {
    "kalendarium": ("2025/04/20241203_122415-scaled.jpg", "Adventsträdgård: ljus i äpplen längs en spiral av granris"),
    "om-oss/medarbetare": ("2021/05/Musiklektion-waldorf.jpg", "Lärare spelar gitarr för eleverna framför en griffeltavla med noter"),
    "waldorfpedagogik": ("2021/05/var-pedagogik-waldorf-skola-klassrum.jpg", "Akvareller på klassrumsväggen"),
    "ansok": (HOME_PHOTO, HOME_ALT),
    "50ar": (HOME_PHOTO, HOME_ALT),
    "klagomalshantering": ("2025/04/20210909_154648-1-scaled.jpg", "Kojor byggda av grenar i skogen"),
    "oppethus": ("2025/04/20210909_154648-1-scaled.jpg", "Kojor byggda av grenar i skogen"),
    "dokument": ("2025/04/IMG_20220307_092108-scaled.jpg", "Krittavla med en borg och åkrar målade i färg"),
    "sekretessinformation": ("2025/04/wladorf-klassrum-botanik-1.jpg", "Klassrum med botanikmålningar på tavlorna"),
    "artiklar": ("2025/04/1000011153.jpg", "Elever i siluett mot himlen på en fjälltopp"),
    "2021/08/28/mot-gamla-elever-fran-skolan-del-1": ("2025/04/1000011153.jpg", "Elever i siluett mot himlen på en fjälltopp"),
    "kontakta-oss/lediga-tjanster": ("2025/04/DSC_6553-scaled.jpg", "Lykta i form av en färgad dodekaeder på en fönsterbänk"),
    "julbasar": ("2021/05/Adventstradgard-waldorf.jpg", "Adventsträdgård med ljus i en spiral av granris"),
}
QUICK = [
    ("Sjukanmälan", "for-foraldrar/sjukanmalan"), ("Kalendarium", "kalendarium"), ("Skollunch", "om-oss/vegetarisk-skollunch"),
    ("Ansök", "ansok"), ("Öppet hus", "oppethus"), ("Medarbetare", "om-oss/medarbetare"), ("Julbasar", "julbasar"), ("Kontakta oss", "kontakta-oss"),
]
GALLERY = [
    ("2025/04/20241203_122415-scaled.jpg", "Adventsträdgård: ljus i äpplen längs en spiral av granris"),
    ("2025/04/IMG_20220307_092108-scaled.jpg", "Krittavla med en borg och åkrar målade i färg"),
    ("2025/04/20210909_154648-1-scaled.jpg", "Kojor byggda av grenar i skogen"),
    ("2025/04/wladorf-klassrum-botanik-1.jpg", "Klassrum med botanikmålningar på tavlorna"),
    ("2025/04/DSC_6553-scaled.jpg", "Lykta i form av en färgad dodekaeder på en fönsterbänk"),
    ("2025/04/IMG_20250320_060951.jpg", "Solnedgång över en sjö under en klassresa"),
    ("2025/04/1000011153.jpg", "Elever i siluett mot himlen på en fjälltopp"),
    ("2025/04/IMG_20250316_170508.jpg", "Nybakat bröd vid en lägereld"),
]
GALLERY_PAGES = {"om-oss", "waldorfpedagogik", "for-foraldrar/arstidsfester", "oppethus", "ansok", "kontakta-oss", "grundskola", "om-oss/fritidshemmet"}
PAGE_QUOTE = {"waldorfpedagogik": 0, "om-oss": 1, "om-oss/medarbetare": 2, "grundskola": 3}
DEFAULT_RELATED = [("Vår pedagogik", "waldorfpedagogik"), ("Kalendarium", "kalendarium"), ("Ansök", "ansok"), ("Om oss", "om-oss")]
PAGE_CARDS = {}  # path -> (photo, alt), filled in before the pages are rendered
PEOPLE = []
QUOTES = [
    ("Waldorfpedagogiken är en bildningsväg. Den är varken modern eller omodern. Den är tidlös.", "Åsa Gjesdahl", ""),
    ("Slöjden handlar om att utveckla självkänsla, frihet och autonomi – möjlighet att klara sig själv, och i en gemenskap vilja att kunna hjälpa andra.", "Helene Langborg", "lärare trä- och metallslöjd"),
    ("Som musiklärare låter jag eleverna göra sig egna erfarenheter genom övande och prövande, aktivt lyssnande och samspel. Det ger dem inte bara kunskaper, utan även självkännedom och känsla av sammanhang.", "Ida Lewald", "musiklärare"),
    ("Att försöka se varje barn och att möta det förutsättningslöst. Waldorfpedagogiken är i någon mån ögonblickets pedagogik, men också hjärtats.", "Pär Claesson", "klasslärare"),
]
ICONS = {
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.6 3.8 5.6 3.8 9s-1.2 6.400-3.800 9c-2.600-2.600-3.800-5.600-3.800-9S9.400 5.600 12 3z"/>',
    "health": '<path d="M12 20.500S4 15.600 4 9.600A4.300 4.300 0 0 1 12 7.400a4.300 4.300 0 0 1 8 2.200c0 6-8 10.900-8 10.900z"/><path d="M9 12h6M12 9v6"/>',
    "food": '<path d="M7 3v7a2.500 2.500 0 0 0 5 0V3M9.500 3v18"/><path d="M17 3c-1.800 1.300-2.500 3.700-2.500 6.500S15.500 14 17 14v7"/>',
    "cal": '<rect x="3.500" y="5" width="17" height="15.500" rx="2"/><path d="M3.500 10h17M8 3v4M16 3v4"/>',
    "bus": '<rect x="4" y="4" width="16" height="13.500" rx="2.500"/><path d="M4 11h16M7.500 17.500V20M16.500 17.500V20"/><circle cx="8" cy="14.300" r=".6"/><circle cx="16" cy="14.300" r=".6"/>',
    "search": '<circle cx="11" cy="11" r="6.500"/><path d="m16 16 4.500 4.500"/>',
    "chev": '<path d="m6 9.500 6 6 6-6"/>',
    "arrow": '<path d="M4 12h15M13 6l6 6-6 6"/>',
    "back": '<path d="M20 12H5M11 6l-6 6 6 6"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4.500 20.500c1-4 4-6 7.500-6s6.500 2 7.500 6"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "fb": '<path d="M14 21v-8h3l.500-3.500H14V7.500c0-1 .400-1.700 1.800-1.700h1.800V2.700c-.600-.100-1.700-.200-2.800-.200-2.600 0-4.300 1.600-4.300 4.500v2.500h-3V13h3v8z"/>',
    "file": '<path d="M6.500 3h7.500l4.500 4.500V21h-12z"/><path d="M14 3v4.500h4.500M9.500 13h5M9.500 16.500h5"/>',
    "ig": '<rect x="3.500" y="3.500" width="17" height="17" rx="4.500"/><circle cx="12" cy="12" r="4"/><circle cx="17" cy="7" r=".6"/>',
}


def icon(name, size=22):
    return f'<svg class="i" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>'


BIRD = """<svg class="bird" viewBox="0 0 140 70" aria-hidden="true"><path class="wing far" d="M70 34C60 25 50 15 34 6c3 12 12 24 26 32z"/><path class="body" d="M3 57C14 47 34 41 54 36c20-5 34-8 49-10 11-2 22-5 29-4 4 .500 6 2 5 3.500-5 2-14 2-22 4-13 3-25 8-38 14-22 9-49 15-74 13z"/><path class="wing near" d="M76 34C60 26 44 15 18 3c5 17 19 32 44 39z"/></svg>"""


def flock(cls="", n=3):
    birds = "".join(f'<div class="fly f{i}">{BIRD}</div>' for i in range(n))
    return f'<div class="flock {cls}" aria-hidden="true">{birds}</div>'


# ---------- images ----------

used = {}


def fetch(rel):
    dest = SRC / "img" / rel.replace("/", "_")
    if not dest.exists():
        url = UPLOADS + urllib.parse.quote(rel)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        dest.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def img_url(rel, width=1400, crop=None):
    """Writes a resized webp and returns its path relative to site/."""
    rel = H.unescape(rel).strip("'\" ")
    name = re.sub(r"[^a-zA-Z0-9]+", "-", rel.rsplit(".", 1)[0]).lower().strip("-")
    if crop:
        name += "-c" + "-".join(map(str, crop))
    out = f"assets/img/{name}-{width}.webp"
    if out not in used:
        target = SITE / out
        if not target.exists():
            im = Image.open(fetch(rel))
            if crop:
                im = im.crop(crop)
            im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            im.save(target, "WEBP", quality=78, method=5)
        with Image.open(target) as t:
            used[out] = t.size
    return out


def picture(rel, base, width=1400, alt="", cls="", lazy=True, crop=None, attrs=""):
    u = img_url(rel, width, crop)
    w, h = used[u]
    load = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    c = f' class="{cls}"' if cls else ""
    return f'<img{c} src="{base}{u}" width="{w}" height="{h}" alt="{H.escape(alt, True)}"{load}{attrs}>'


def logo_art(base):
    """The header logo, put back together from its parts at their places in the original."""
    parts = "".join(
        f'<img class="logo-{n}" src="{base}assets/logo-{n}.png" alt="" style="left:{x0 / 4.2:.2f}%;top:{y0 / 1.31:.2f}%;width:{(x1 - x0) / 4.2:.2f}%">'
        for n, (x0, y0, x1, y1) in LOGO_PARTS
    )
    return f'<span class="logo-art">{parts}</span>'


# ---------- links and text ----------


def href(target, base):
    if target.startswith(("http", "mailto", "tel")):
        return target
    return f"{base}{target}/" if target else f"{base}"


def fix_link(url, base):
    url = H.unescape(url).strip()
    url = re.sub(r"^https?://(www\.)?(staging\.)?rudolfsteinerskolan\.se", "", url) if "wp-content" not in url else url
    if url.startswith("/") or url == "":
        path = url.strip("/")
        path = REDIRECTS.get(path, path)
        hash_part = ""
        return f"{base}{path}/{hash_part}" if path else base
    if url.startswith("tel:"):
        return "tel:" + re.sub(r"[^\d+]", "", url[4:])
    return url


def fix_html(h, base):
    h = re.sub(r'href="([^"]*)"', lambda m: f'href="{H.escape(fix_link(m.group(1), base), True)}"', h)
    h = re.sub(r"<(em|strong)>\s*</\1>", " ", h)
    h = re.sub(r"(<br>\s*)+$", "", h.strip())
    h = re.sub(r"<strong>\s*<br>\s*</strong>", "<br>", h)
    h = re.sub(r"(?<![\w.:\">])([\w.\-åäöÅÄÖ]+@[\w.\-]+\.\w+)", r'<a href="mailto:\1">\1</a>', h)
    return re.sub(r"\s+", " ", h).strip()


def slug(text):
    t = text.lower().translate(str.maketrans("åäöé", "aaoe"))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def plain(h):
    return H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def external(url):
    return url.startswith("http") and "wp-content" not in url


def button(text, url, kind="", base=""):
    target = ' target="_blank" rel="noopener"' if external(url) else ""
    return f'<a class="btn {kind}" href="{H.escape(url, True)}"{target}>{H.escape(H.unescape(text))}</a>'


# ---------- page chrome ----------


def page(path, title, body, desc="", cls=""):
    depth = len([p for p in path.split("/") if p])
    base = "../" * depth
    nav_items = ""
    for label, target, sub in NAV:
        cur = ' aria-current="page"' if target == path else ""
        if sub:
            links = "".join(
                f'<li><a href="{href(t, base)}"{" target=_blank rel=noopener" if t.startswith("http") else ""}>{H.escape(l)}</a></li>'
                for l, t in sub
            )
            nav_items += f'<li class="has-sub"><a href="{href(target, base)}"{cur}>{label}</a><button class="sub-toggle" aria-expanded="false" aria-label="Visa undermeny för {label}">{icon("chev", 16)}</button><ul class="sub">{links}</ul></li>'
        else:
            nav_items += f'<li><a href="{href(target, base)}"{cur}>{label}</a></li>'
    parents = "".join(f'<li><a href="{href(t, base)}">{H.escape(l)}</a></li>' for l, t in PARENTS)
    quick = "".join(f'<li><a href="{href(t, base)}">{H.escape(l)}</a></li>' for l, t in QUICK)
    if path:
        body += extras(path, base)
    head_desc = H.escape(desc or "Rudolf Steinerskolan är en waldorfskola i en grön oas nära Norrköpings stadskärna.", True)
    return f"""<!doctype html>
<html lang="sv" data-base="{base}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{H.escape(title)} – Rudolf Steinerskolan (portfoliokoncept)</title>
<meta name="description" content="{head_desc}">
<link rel="icon" href="{base}assets/favicon.png">
<link rel="stylesheet" href="{base}assets/site.css">
<script>document.documentElement.classList.add('js')</script>
</head>
<body class="{cls}">
<a class="skip" href="#content">Fortsätt till innehållet</a>
<div class="topbar"><div class="wrap">
<p class="concept">Portfoliokoncept – inte skolans officiella webbplats</p>
<ul>
<li><a href="{SCHOOLSOFT}" target="_blank" rel="noopener">{icon("globe", 16)} SchoolSoft</a></li>
<li class="has-sub"><a href="{href("for-foraldrar", base)}">{icon("user", 16)} Föräldrar</a><button class="sub-toggle" aria-expanded="false" aria-label="Visa undermeny för föräldrar">{icon("chev", 14)}</button><ul class="sub">{parents}</ul></li>
</ul>
</div></div>
<header class="site-head"><div class="wrap">
<a class="logo" href="{base or './'}" aria-label="Rudolf Steinerskolan, startsidan">{logo_art(base)}</a>
<button class="menu-toggle" aria-expanded="false" aria-controls="mainnav">{icon("menu", 26)}<span>Meny</span></button>
<nav id="mainnav" aria-label="Huvudmeny"><ul class="main">{nav_items}
<li class="only-small"><a href="{href("for-foraldrar", base)}">Föräldrar</a></li>
<li class="only-small"><a href="{href("kalendarium", base)}">Kalendarium</a></li>
<li class="only-small"><a href="{SCHOOLSOFT}" target="_blank" rel="noopener">SchoolSoft</a></li>
</ul></nav>
<button class="search-toggle" aria-expanded="false" aria-controls="search" aria-label="Sök">{icon("search", 22)}</button>
</div>
<div class="scrollbird" aria-hidden="true">{BIRD}</div>
<div id="search" class="search" role="search" hidden><div class="wrap">
<div class="search-box">{icon("search", 22)}<label class="vh" for="q">Sök på webbplatsen</label><input id="q" type="search" autocomplete="off" placeholder="Sök sidor, medarbetare och datum"><button class="search-clear" type="button" aria-label="Rensa sökningen" hidden>{icon("close", 18)}</button></div>
<p id="search-count" aria-live="polite"></p>
<ul id="results"></ul>
<div id="search-quick"><h3>Vanliga genvägar</h3><ul>{quick}</ul></div>
</div></div>
</header>
<div class="search-scrim" hidden></div>
<main id="content">
{body}
</main>
<footer class="site-foot"><div class="wrap foot-grid">
<div>
<h2>Kontakta oss</h2>
<p>Besöksadress: Spårgatan 17, 602 23 Norrköping<br>Postadress: Box 744, 601 16 Norrköping</p>
<p>Kansli: <a href="tel:011182118">011-18 21 18</a><br><a href="mailto:info@rudolfsteinerskolan.se">info@rudolfsteinerskolan.se</a></p>
</div>
<div class="foot-logo"><img src="{base}assets/logo.png" width="420" height="131" alt="Rudolf Steinerskolan"></div>
<div>
<h2>Snabblänkar</h2>
<ul>
<li><a href="{SCHOOLSOFT}" target="_blank" rel="noopener">SchoolSoft</a></li>
<li><a href="{href("for-foraldrar/sjukanmalan", base)}">Sjukanmälan</a></li>
<li><a href="{href("sekretessinformation", base)}">Sekretess</a></li>
<li><a href="{href("dokument", base)}">Dokument</a></li>
<li><a href="{href("klagomalshantering", base)}">Synpunkter och klagomål</a></li>
</ul>
<p class="social"><a href="{FACEBOOK}" target="_blank" rel="noopener" aria-label="Facebook">{icon("fb", 22)}</a><a href="{INSTAGRAM}" target="_blank" rel="noopener" aria-label="Instagram">{icon("ig", 22)}</a></p>
</div>
</div>
<div class="wrap foot-note"><p>Portfoliokoncept, inte skolans officiella webbplats. Texter och bilder kommer från <a href="{ORIGIN}/" target="_blank" rel="noopener">rudolfsteinerskolan.se</a>.</p><a class="totop" href="#content">Till toppen</a></div>
</footer>
<script>window.BASE={json.dumps(base)}</script>
<script src="{base}assets/data.js"></script>
<script src="{base}assets/site.js"></script>
</body>
</html>
"""


def group_of(path):
    groups = [[(l, t) for l, t in sub if not t.startswith("http")] for _, _, sub in NAV if sub] + [PARENTS]
    return next((g for g in groups if any(t == path for _, t in g)), None)


def subnav(path, base):
    group = group_of(path)
    if not group:
        return ""
    links = "".join(
        f'<li><a href="{href(t, base)}"{" aria-current=page" if t == path else ""}>{H.escape(l)}</a></li>' for l, t in group
    )
    return f'<nav class="wrap subnav" aria-label="I det här avsnittet"><ul>{links}</ul></nav>'


def drift_gallery(base):
    cells = "".join(f'<li class="frame">{picture(s, base, 900, a)}</li>' for s, a in GALLERY)
    return f'<ul class="drift-row" data-drift tabindex="0" aria-label="Bilder från skolan">{cells}</ul>'


def extras(path, base):
    """What every inner page ends with: a teacher's voice or the gallery where they fit, then where to go next."""
    out = ""
    if path in PAGE_QUOTE:
        q, a, r = QUOTES[PAGE_QUOTE[path]]
        out += f'<section class="quotes page-quote" aria-label="Röster från skolan"><div class="wrap narrow"><figure class="quote"><blockquote>{q}</blockquote><figcaption>{a}{", " + r if r else ""}</figcaption></figure></div></section>'
    if path in GALLERY_PAGES:
        out += f'<section class="drift page-drift" aria-label="Bilder från skolan">{drift_gallery(base)}</section>'
    group = group_of(path)
    options = [x for x in (group or []) if x[1] != path]
    if group:
        at = [t for _, t in group].index(path)
        options = [group[(at + k) % len(group)] for k in range(1, len(group))]
    options = [x for x in options + DEFAULT_RELATED if x[1] != path and x[1] in PAGE_CARDS]
    picked, seen = [], set()
    for label, target in options:
        if target not in seen:
            seen.add(target)
            picked.append((label, target))
    cards = ""
    for label, target in picked[:3]:
        src, alt = PAGE_CARDS[target]
        cards += f'<li class="rel"><a href="{href(target, base)}"><span class="frame">{picture(src, base, 900, alt)}</span><strong>{H.escape(label)}</strong></a></li>'
    return out + f'<section class="related wrap" aria-labelledby="rel-title"><h2 id="rel-title">Läs också</h2><ul>{cards}</ul></section>'


def write(path, html_text):
    target = SITE / path / "index.html" if path else SITE / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Explicit index.html so the pages also work when opened straight from disk.
    html_text = re.sub(r'href="((?:[^"#:]*/)?)(#[^"]*)?"', lambda m: m[0] if not m[1] else f'href="{m[1]}index.html{m[2] or ""}"', html_text)
    target.write_text(html_text, encoding="utf-8", newline="\n")


# ---------- generic page ----------


def sectionize(blocks):
    """Splits blocks into an intro and heading-led sections, pairing photos with their section."""
    title, banner, intro_btn = None, None, None
    intro, sections, cur, pending = [], [], None, []
    for b in blocks:
        if b["t"] == "h" and b["tag"] == "h1" and title is None:
            title = plain(b["html"])
            if pending and banner is None:
                banner = pending.pop(0)
            continue
        if b["t"] == "img":
            if title is None and banner is None and not intro:
                banner = b
            elif cur is not None and not cur["media"] and cur["body"]:
                cur["media"].append(b)
            else:
                pending.append(b)
            continue
        if b["t"] == "h":
            cur = {"h": plain(b["html"]), "html": b["html"], "media": pending, "body": []}
            pending = []
            sections.append(cur)
            continue
        if cur is None:
            if b["t"] == "btn" and intro_btn is None and not intro:
                intro_btn = b
            else:
                if pending and banner is None:
                    banner = pending.pop(0)
                intro.append(b)
        else:
            cur["body"].append(b)
    for extra in pending:
        if sections:
            sections[-1]["media"].append(extra)
        elif banner is None:
            banner = extra
    return title, banner, intro_btn, intro, sections


def render_blocks(blocks, base, about=""):
    out, in_list = [], False
    for b in blocks:
        if b["t"] == "li":
            if not in_list:
                out.append("<ul class=\"list\">")
                in_list = True
            out.append(f"<li>{fix_html(b['html'], base)}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if b["t"] == "p":
            out.append(f"<p>{fix_html(b['html'], base)}</p>")
        elif b["t"] == "btn":
            link = button(b["text"], fix_link(b["href"], base))
            if about and plain(b["text"]).lower() == "läs mer":
                link = link.replace("</a>", f'<span class="vh"> om {H.escape(about)}</span></a>')
            if out and out[-1].endswith("</a></p>") and out[-1].startswith('<p class="btn-row">'):
                out[-1] = out[-1][:-4] + " " + link + "</p>"
            else:
                out.append(f'<p class="btn-row">{link}</p>')
    if in_list:
        out.append("</ul>")
    return "".join(out)


def page_hero(path, title, base, banner=None, alt="", btn=None):
    """The home page's sky on every inner page: a photo, the birds and the children on their hill."""
    poster = ""
    src = banner["src"] if banner else None
    if src and LETTERED.search(src):
        poster = f'<div class="wrap poster-inline"><div class="frame natural">{picture(src, base, 1800, alt)}</div></div>'
        src = None
    if not src:
        src, alt = HERO_PHOTOS.get(path, (HOME_PHOTO, HOME_ALT))
    action = f'<div class="title-action">{button(btn["text"], fix_link(btn["href"], base), "big rose")}</div>' if btn else ""
    return f"""<section class="page-hero" aria-labelledby="page-title">
<div class="hero-media" data-hero-img>{picture(src, base, 1800, alt, lazy=False)}</div>
<div class="hero-shade"></div>
{flock("loop", 4)}
<div class="blossoms" data-blossoms aria-hidden="true"></div>
<div class="wrap title-row"><h1 id="page-title">{H.escape(title)}</h1>{action}</div>
<div class="hill" data-hill><svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-hidden="true"><path d="" data-hill-path/></svg><canvas class="kids"></canvas></div>
</section>{subnav(path, base)}{poster}"""


def media_html(media, base, round_media, heading):
    if not media:
        return ""
    if LETTERED.search(media[0]["src"]):
        return f'<div class="sec-media"><div class="frame natural">{picture(media[0]["src"], base, 1100)}</div></div>'
    if round_media:
        return f'<div class="sec-media"><div class="frame round" data-parallax="0.1">{picture(media[0]["src"], base, 700)}</div></div>'
    imgs = "".join(
        f'<div class="frame" data-parallax="0.1">{picture(m["src"], base, 1100)}</div>' for m in media[:2]
    )
    extra = len(media) > 1 and " two" or ""
    return f'<div class="sec-media{extra}">{imgs}</div>'


def render_sections(sections, base, round_media):
    out, i = [], 0
    n = 0
    while i < len(sections):
        s = sections[i]
        if s["media"]:
            side = "flip" if n % 2 else ""
            band = " band" if n % 2 else ""
            out.append(
                f'<section class="sec{band}"><div class="wrap sec-grid {side}">{media_html(s["media"], base, round_media, s["h"])}'
                f'<div class="sec-text"><h2 id="{slug(s["h"])}">{H.escape(s["h"])}</h2>{render_blocks(s["body"], base, s["h"])}</div></div></section>'
            )
            n += 1
            i += 1
            continue
        # Runs of text-only sections read together in one calm column grid.
        run = []
        while i < len(sections) and not sections[i]["media"]:
            run.append(sections[i])
            i += 1
        cols = " cols" if len(run) > 1 and sum(len(plain(render_blocks(r["body"], base))) for r in run) / len(run) < 900 else " single"
        cells = "".join(
            f'<div class="cell"><h2 id="{slug(r["h"])}">{H.escape(r["h"])}</h2>{render_blocks(r["body"], base, r["h"])}</div>' for r in run
        )
        band = " band" if n % 2 else ""
        out.append(f'<section class="sec{band}"><div class="wrap text-run{cols}">{cells}</div></section>')
        n += 1
    return "".join(out)


def generic(path, data, overrides=None):
    o = overrides or {}
    base = "../" * len([p for p in path.split("/") if p])
    title, banner, btn, intro, sections = sectionize(data["blocks"])
    title = title or data["title"]
    # Everyday questions come first on the long overview page; the headings stay the school's own.
    if path == "om-oss":
        first = ("Årskurs F-9", "Elevhälsa", "Skollunch", "Fritidshemmet")
        sections.sort(key=lambda x: first.index(x["h"]) if x["h"] in first else len(first))
    title = H.unescape(title)
    if "banner" in o:
        banner = o["banner"]
    body = page_hero(path, o.get("title", title), base, banner, o.get("banner_alt", ""), btn)
    body += o.get("before", "")
    if intro:
        body += f'<div class="wrap intro prose">{render_blocks(intro, base)}</div>'
    body += o.get("after_intro", "")
    if len(sections) >= 6:
        items = "".join(f'<li><a href="#{slug(x["h"])}">{H.escape(x["h"])}</a></li>' for x in sections)
        body += f'<nav class="wrap toc" aria-labelledby="toc-title"><h2 id="toc-title">På den här sidan</h2><ul>{items}</ul></nav>'
    body += render_sections(sections, base, path in ROUND_MEDIA)
    body += o.get("after", "")
    desc = plain(render_blocks(intro or (sections[0]["body"] if sections else []), base))[:155]
    return page(path, o.get("title", title), body, desc)


# ---------- calendar ----------


def monday_of_week(week, year):
    jan4 = date(year, 1, 4)
    return jan4 + timedelta(days=(week - 1) * 7 - jan4.weekday())


def school_year(month):
    return 2026 if month >= 8 else 2027


def parse_entry(line):
    m = re.match(r"(?:V|Vecka )(\d+)(?:-(\d+))? – (.+)", line)
    if m:
        a, b = int(m[1]), int(m[2] or m[1])
        year = 2026 if a >= 32 else 2027
        return monday_of_week(a, year), monday_of_week(b, year) + timedelta(days=6), m[0].split(" – ")[0], m[3]
    m = re.match(r"(\d+)(?:-(\d+))? ([a-zåäö]+)(?: – (\d+) ([a-zåäö]+))? – (.+)", line)
    mon = MONTHS[m[3][:3]]
    start = date(school_year(mon), mon, int(m[1]))
    end = start
    if m[2]:
        end = date(start.year, mon, int(m[2]))
    if m[4]:
        mon2 = MONTHS[m[5][:3]]
        end = date(school_year(mon2), mon2, int(m[4]))
    label = line[: line.rfind(" – " + m[6])]
    return start, end, label, m[6]


def calendar_entries():
    return [(t, *parse_entry(l)) for t, lines in (("HT26", CAL_HT), ("VT27", CAL_VT)) for l in lines]


def calendar_page(data):
    base = "../"
    rows = {"HT26": "", "VT27": ""}
    for term, start, end, label, text in calendar_entries():
        rows[term] += (
            f'<li class="cal-row" data-start="{start}" data-end="{end}"><span class="cal-date">{H.escape(label)}</span>'
            f'<span class="cal-text">{H.escape(text)}</span></li>'
        )
    body = page_hero("kalendarium", "Kalendarium 26/27", base)
    body += f"""<div class="wrap cal-grid">
<section aria-labelledby="ht"><h2 id="ht">Höstterminen 2026</h2><ol class="cal-list">{rows["HT26"]}</ol></section>
<section aria-labelledby="vt"><h2 id="vt">Vårterminen 2027</h2><ol class="cal-list">{rows["VT27"]}</ol></section>
</div>
<section class="sec band"><div class="wrap sec-grid"><div class="sec-media"><div class="frame round" data-parallax="0.1">{picture("2021/05/Adventstradgard-waldorf.jpg", base, 700, "Adventsträdgård med ljus i en spiral av granris")}</div></div>
<div class="sec-text"><h2>Årstidsfester</h2><p>I likhet med waldorfskolor över hela världen, firar vi högtider och tar del av vårt kulturarv. Här kan du läsa mer om Mikaeli, julbasar, adventsträdgård och alla våra andra årstidsfester.</p><p class="btn-row">{button("Läs mer", "../for-foraldrar/arstidsfester/")}</p></div></div></section>"""
    return page("kalendarium", "Kalendarium", body, "Skolans kalendarium för läsåret 2026/27.")


# ---------- staff ----------


def staff_page(data):
    base = "../../"
    cards, photo = [], None
    for b in data["blocks"]:
        if b["t"] == "img":
            photo = b["src"]
        elif b["t"] == "p" and "<strong>" in b["html"]:
            parts = [plain(p) for p in re.split(r"<br>", b["html"])]
            parts = [p for p in parts if p]
            name, rest = parts[0], parts[1:]
            mail = rest.pop() if rest and "@" in rest[-1] else ""
            role = " ".join(rest)
            pic = (
                picture(photo, base, 300, "")
                if photo
                else f'<span class="no-photo" aria-hidden="true">{"".join(w[0] for w in name.split()[:2])}</span>'
            )
            m = f'<a href="mailto:{mail}">{mail}</a>' if mail else ""
            search = H.escape(f"{name} {role}".lower(), True)
            PEOPLE.append({"n": name, "r": role, "m": mail})
            cards.append(f'<li class="person" data-search="{search}"><div class="portrait">{pic}</div><div><h2>{H.escape(name)}</h2><p>{H.escape(role)}</p>{m}</div></li>')
            photo = None
    body = page_hero("om-oss/medarbetare", "Medarbetare på Rudolf Steinerskolan", base)
    body += f"""<div class="wrap staff-tools"><label for="staff-q">Sök medarbetare</label><input id="staff-q" type="search" placeholder="Namn, ämne eller årskurs" autocomplete="off"><p id="staff-empty" class="muted" hidden>Ingen medarbetare matchar sökningen.</p></div>
<ul class="wrap staff">{"".join(cards)}</ul>"""
    return page("om-oss/medarbetare", "Medarbetare", body, "Klasslärare, ämneslärare, rektorer, elevhälsa och övriga medarbetare på Rudolf Steinerskolan.")


# ---------- documents ----------


def documents_page(data):
    base = "../"
    rows = ""
    for b in data["blocks"]:
        m = re.search(r'href="([^"]+)"', b.get("html", ""))
        if not m:
            continue
        url = fix_link(m[1], base)
        pdf = url.lower().endswith(".pdf")
        kind = '<span class="doc-kind">PDF</span>' if pdf else icon("arrow", 18)
        target = ' target="_blank" rel="noopener"' if pdf else ""
        rows += f'<li class="doc-row"><a href="{H.escape(url, True)}"{target}>{icon("file", 24)}<span>{H.escape(plain(b["html"]))}</span>{kind}</a></li>'
    body = page_hero("dokument", "Dokument", base) + f'<section class="sec"><ul class="wrap docs">{rows}</ul></section>'
    return page("dokument", "Dokument", body, "Skolans värdegrundsplan, likabehandlingsplan och övriga dokument.")


# ---------- lunch ----------


def lunch_page(data):
    base = "../../"
    blocks = data["blocks"]
    i = next(k for k, b in enumerate(blocks) if b["t"] == "h" and "Veckans matsedel" in b["html"])
    j = next(k for k, b in enumerate(blocks) if k > i and b["t"] == "h")
    days = [plain(b["html"]) for b in blocks[i + 1 : j]]
    rows = "".join(
        f'<tr data-day="{n}"><th scope="row">{H.escape(days[n * 2])}</th><td>{H.escape(days[n * 2 + 1])}</td></tr>'
        for n in range(len(days) // 2)
    )
    menu = f'<section class="sec band"><div class="wrap"><h2>Veckans matsedel</h2><table class="menu"><tbody>{rows}</tbody></table></div></section>'
    trimmed = {"title": data["title"], "blocks": blocks[:i] + blocks[j:]}
    return generic("om-oss/vegetarisk-skollunch", trimmed, {"after_intro": menu})


# ---------- forms ----------


def demo_note(base):
    return f'<p class="form-status" role="status" hidden>Det här är ett portfoliokoncept, så inget skickades. Använd <a href="{ORIGIN}/" target="_blank" rel="noopener">skolans riktiga webbplats</a> för att anmäla dig eller lämna synpunkter.</p>'


def open_house_form(base):
    slots = "".join(
        f'<label class="choice"><input type="radio" name="tid" required value="{s}"> {s}</label>'
        for s in ("17:00-17:30", "17:30-18:00", "18:00-18:30", "18:30-19:00")
    )
    grades = "".join(
        f'<label class="choice"><input type="checkbox" name="arskurs" value="{s}"> {s}</label>'
        for s in ("Förskolan Äppelblomman", "Årskurs F-6", "Högstadiet")
    )
    return f"""<section class="sec band"><div class="wrap narrow"><h2>Skicka gärna in intresseanmälan</h2>
<form class="demo-form"><label for="oh-name">Ditt namn</label><input id="oh-name" required autocomplete="name">
<fieldset><legend>Välj vilken tid du önskar besöka oss på Öppet hus:</legend>{slots}</fieldset>
<fieldset><legend>Välj vilken årskurs du är intresserad av veta mer om (du kan välja flera alternativ):</legend>{grades}</fieldset>
<label for="oh-mail">Din e-post</label><input id="oh-mail" type="email" required autocomplete="email">
<label class="choice"><input type="checkbox" required> Jag godkänner att mina personuppgifter kommer att bearbetas av Rudolf Steinerskolan</label>
<button class="btn big" type="submit">Skicka</button>{demo_note(base)}</form></div></section>"""


def complaint_form(base):
    return f"""<section class="sec band"><div class="wrap narrow"><h2>Skicka dina synpunkter eller klagomål här</h2>
<form class="demo-form"><label for="k-name">Ditt namn</label><input id="k-name" autocomplete="name">
<label for="k-mail">Din e-post:</label><input id="k-mail" type="email" autocomplete="email">
<label for="k-other">Kontaktuppgifter (om inte e-post):</label><input id="k-other">
<fieldset><legend>Önskar ni lämna ett klagomål eller synpunkt (tydliggör vilket alternativ då dessa ärenden behandlas olika):</legend>
<label class="choice"><input type="radio" name="typ" required> Synpunkter</label><label class="choice"><input type="radio" name="typ" required> Klagomål</label></fieldset>
<label for="k-msg">Ditt meddelande (valfritt):</label><textarea id="k-msg" rows="6"></textarea>
<label class="choice"><input type="checkbox" required> Jag godkänner att mina personuppgifter kommer att bearbetas av Rudolf Steinerskolan</label>
<button class="btn big" type="submit">Skicka</button>{demo_note(base)}</form></div></section>"""


# ---------- home ----------


def home_page():
    base = ""
    teasers = [
        ("Om Rudolf Steinerskolan", "Rudolf Steinerskolan är en Waldorfskola som ligger i en grön oas nära Norrköpings stadskärna.", "om-oss/", "2021/05/Musiklektion-waldorf.jpg", "Lärare spelar gitarr för eleverna framför en griffeltavla med noter"),
        ("Vår pedagogik", "I över 100 år har Waldorfpedagogiken låtit miljontals barn utvecklas till självständiga och engagerade individer världen över.", "waldorfpedagogik/", "2021/05/var-pedagogik-waldorf-skola-klassrum.jpg", "Akvareller på klassrumsväggen"),
        ("Kontakta oss", "Om du vill komma på besök eller kontakta oss når du oss via telefon eller mejl.", "kontakta-oss/", "2021/05/waldorf-virkade-dockor2.jpg", "Tre virkade tomtar med röda och gula luvor"),
    ]
    teaser_html = "".join(
        f"""<article class="teaser t{n}"><div class="frame" data-parallax="0.14">{picture(src, base, 900, alt)}</div>
<h2>{t}</h2><p>{d}</p><a class="btn" href="{u}">Läs mer<span class="vh"> om {t}</span></a></article>"""
        for n, (t, d, u, src, alt) in enumerate(teasers)
    )
    quotes = "".join(
        f'<figure class="quote{" on" if n == 0 else ""}"{"" if n == 0 else " hidden"}><blockquote>{q}</blockquote><figcaption>{a}{", " + r if r else ""}</figcaption></figure>'
        for n, (q, a, r) in enumerate(QUOTES)
    )
    errands = [
        ("Schoolsoft portal", "Schoolsoft är vårt intranät för elever och vårdnadshavare.", SCHOOLSOFT, "globe"),
        ("Sjukanmälan", "Glöm inte att anmäla frånvaro varje dag när eleven är sjuk.", "for-foraldrar/sjukanmalan/", "health"),
        ("Veckans lunchmeny", "Varje dag serveras vällagad skollunch.", "om-oss/vegetarisk-skollunch/", "food"),
        ("Kalendarium", "Här kan du hålla dig uppdaterad om vad som händer.", "kalendarium/", "cal"),
        ("Info om skolskjuts", "Här hittar du information om busskort och skolskjuts.", SKOLSKJUTS, "bus"),
    ]
    errand_html = "".join(
        f'<li><a href="{u}"{" target=_blank rel=noopener" if u.startswith("http") else ""}>{icon(i, 30)}<strong>{t}</strong><span>{d}</span></a></li>'
        for t, d, u, i in errands
    )
    slides = "".join(
        picture(src, base, 1920, alt, "on" if n == 0 else "", lazy=n > 0, crop=crop,
                attrs=f' style="--pos:{pos};--pos-s:{pos_s}"' + (' aria-hidden="true"' if n else ""))
        for n, (src, alt, pos, pos_s, crop) in enumerate(HOME_SLIDES)
    )
    body = f"""<section class="hero" aria-labelledby="hero-title">
<div class="hero-media" data-hero-img data-slides>{slides}</div>
<div class="hero-shade"></div>
{flock("loop", 5)}
<div class="blossoms" data-blossoms aria-hidden="true"></div>
<div class="wrap hero-grid">
<div class="hero-copy">
<h1 id="hero-title"><span>Välkommen till</span> Rudolf Steinerskolan</h1>
<p>Rudolf Steinerskolan är en kulturbärande skola mitt i samhället. Undervisningen bedrivs med väl genomtänkt pedagogik och erbjuder en bred sammanhållen studiegång där humaniora, naturvetenskap, musik, konst och hantverk bildar en enhet.</p>
<p class="btn-row"><a class="btn big" href="{KNACK}" target="_blank" rel="noopener">Ansök här</a> <a class="btn big rose" href="om-oss/">Om oss</a></p>
</div>
</div>
<div class="hill" data-hill><svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-hidden="true"><path d="" data-hill-path/></svg><canvas class="kids"></canvas></div>
</section>
<aside class="next-up wrap" aria-labelledby="next-title"><h2 id="next-title">På gång</h2><ol id="next-events"><li><a href="kalendarium/">Se hela kalendariet</a></li></ol><a class="more" href="kalendarium/">Hela kalendariet {icon("arrow", 18)}</a></aside>
<nav class="errands wrap" aria-label="Snabblänkar"><ul>{errand_html}</ul></nav>
<section class="teasers wrap" aria-label="Lär känna skolan">{teaser_html}</section>
<section class="quotes" aria-label="Röster från skolan" data-quotes><div class="wrap narrow">{quotes}
<div class="quote-nav"><button type="button" data-q="-1" aria-label="Föregående citat">{icon("back", 22)}</button><span id="quote-count" aria-live="polite">1 / {len(QUOTES)}</span><button type="button" data-q="1" aria-label="Nästa citat">{icon("arrow", 22)}</button></div>
</div></section>
<section class="poster wrap" aria-label="Julbasar" data-until="2026-11-28">
<a class="frame natural poster-frame" href="julbasar/">{picture("2021/11/Julbasar-hemsida-scaled.png", base, 1800, "Välkommen till Julbasar, lördag 28 november klockan 11 till 15. Fri entré.")}</a>
<p class="poster-date">Lördag 28 november kl. 11-15. Fri entré.</p>
</section>
<section class="invite"><div class="wrap narrow"><h2>Söker du en lugn och trivsam skolmiljö med engagerade och trygga pedagoger där lärandet går hand i hand med barnets utveckling?</h2>
<p class="btn-row"><a class="btn big" href="{KNACK}" target="_blank" rel="noopener">Ansök här</a> <a class="btn big rose" href="waldorfpedagogik/">Läs mer</a></p></div></section>
<section class="drift band" aria-labelledby="drift-title"><div class="wrap drift-head"><h2 id="drift-title">Norrköpings Waldorfskola ett stenkast från centrum, omgiven av en blomstrande trädgård</h2><a class="btn" href="{INSTAGRAM}" target="_blank" rel="noopener">Följ på Instagram</a></div>
{drift_gallery(base)}</section>"""
    return page("", "Välkommen", body, cls="home")


# ---------- main ----------


def build():
    for sub in ("assets/img",):
        (SITE / sub).mkdir(parents=True, exist_ok=True)
    pages = load_pages()
    for key in ("om-oss/skolans-historia", "om-oss/hogtider-fester-aktiviteter", ""):
        pages.pop(key, None)

    # Corrections from the newest source: the school's 2026 poster and calendar.
    jul = pages["julbasar"]["blocks"]
    for b in jul:
        if b["t"] == "p":
            b["html"] = (
                b["html"].replace("Den 30 november kl. 11-14", "Lördag den 28 november kl. 11-15")
                .replace("kl. 13:30", "kl. 14:30").replace("<br></br>", "")
            )
    jul[:] = [b for b in jul if plain(b.get("html", "x")) and "&lt;br" not in b.get("html", "")]
    grund = pages["grundskola"]["blocks"]
    for k, b in enumerate(grund):
        if b["t"] == "p" and plain(b["html"]).startswith("Läs mer om waldorfpedagogik här"):
            grund[k] = {"t": "btn", "href": "/waldorfpedagogik/", "text": "Läs mer om waldorfpedagogik"}
    next_open = '<div class="wrap note-wrap"><p class="note">Höstens öppna hus var den 20 oktober. Nästa Öppet hus är tisdag den 27 april kl. 17:00-18:30.</p></div>'

    special = {
        "kalendarium": lambda d: calendar_page(d),
        "dokument": lambda d: documents_page(d),
        "kontakta-oss/lediga-tjanster": lambda d: generic("kontakta-oss/lediga-tjanster", d, {"after": f'<div class="wrap empty-actions"><p class="btn-row">{button("Kontakta oss", "../")}</p></div>'}),
        "om-oss/medarbetare": lambda d: staff_page(d),
        "om-oss/vegetarisk-skollunch": lambda d: lunch_page(d),
        "julbasar": lambda d: generic("julbasar", d, {"title": "Julbasar 28/11", "banner": {"src": "2021/11/Julbasar-hemsida-scaled.png"}, "banner_alt": "Välkommen till Julbasar, lördag 28 november klockan 11 till 15. Fri entré."}),
        "oppethus": lambda d: generic("oppethus", d, {"before": next_open, "after_intro": open_house_form("../")}),
        "klagomalshantering": lambda d: generic("klagomalshantering", d, {"after": complaint_form("../")}),
        "ansok": lambda d: generic("ansok", d, {"title": "Ansök"}),
        "artiklar": lambda d: generic("artiklar", {"title": "Nyheter", "blocks": [{"t": "h", "tag": "h1", "html": "Nyheter"}, {"t": "h", "tag": "h2", "html": "Möt gamla elever från skolan – del 1"}, {"t": "p", "tag": "p", "html": "Rudolf Steinerskolan i Norrköping har funnits i nästan 50 år. Nu har vi träffat några av de elever som gått på skolan tidigare. Vad gör de nu och hur ser de på sin tid på ”Kullen”?"}, {"t": "btn", "href": "/2021/08/28/mot-gamla-elever-fran-skolan-del-1/", "text": "Läs mer"}]}),
    }
    for path, data in pages.items():
        banner = sectionize(data["blocks"])[1]
        own = banner["src"] if banner and not LETTERED.search(banner["src"]) else None
        PAGE_CARDS[path] = (own, "") if own else HERO_PHOTOS.get(path, (HOME_PHOTO, HOME_ALT))

    index = []
    for path, data in pages.items():
        if path == "oppethus":
            data["blocks"] = [b for b in data["blocks"] if not (b["t"] == "p" and re.search(r"Ditt namn|Välj vilken|17:00-17:30|Förskolan Äppelblomman|Din e-post|Jag godkänner|Skicka gärna|^×$", plain(b["html"])))]
        if path == "klagomalshantering":
            cut = next((k for k, b in enumerate(data["blocks"]) if b["t"] == "h" and "Skicka dina" in b["html"]), None)
            if cut is not None:
                data["blocks"] = data["blocks"][:cut]
        write(path, special.get(path, lambda d: generic(path, d))(data))
        text = " ".join(plain(b.get("html") or b.get("text") or "") for b in data["blocks"])
        written = (SITE / path / "index.html").read_text(encoding="utf-8")
        secs = [
            {"h": x["h"], "id": slug(x["h"]), "x": " ".join(plain(b.get("html") or b.get("text") or "") for b in x["body"])[:1500]}
            for x in sectionize(data["blocks"])[4]
            if f'id="{slug(x["h"])}"' in written
        ]
        index.append({"t": data["title"].replace("START", "Startsidan"), "u": path, "x": text[:6000], "s": secs})

    posts = json.loads((ROOT / "content/posts.json").read_text(encoding="utf-8"))
    for p in posts:
        path = p["link"].replace(ORIGIN, "").strip("/")
        blocks = clean(p["content"]["rendered"])
        title = H.unescape(p["title"]["rendered"])
        blocks = [b for b in blocks if not (b["t"] == "h" and b["tag"] == "h1")]
        # The original sets its whole introduction as a heading; here it reads as the lead paragraph.
        blocks = [{"t": "p", "tag": "p", "html": b["html"]} if b["t"] == "h" and b["tag"] == "h5" else b for b in blocks]
        blocks.insert(0, {"t": "h", "tag": "h1", "html": title})
        write(path, generic(path, {"title": title, "blocks": blocks}))
        index.append({"t": title, "u": path, "x": " ".join(plain(b.get("html") or "") for b in blocks)[:6000]})

    write("", home_page())

    index.append({"t": "Startsidan", "u": "", "x": "Välkommen till Rudolf Steinerskolan"})
    events = [
        {"s": str(s), "e": str(e), "d": label, "t": text}
        for _, s, e, label, text in calendar_entries()
    ]
    (SITE / "assets/data.js").write_text(
        "window.SEARCH=" + json.dumps(index, ensure_ascii=False) + ";\nwindow.EVENTS=" + json.dumps(events, ensure_ascii=False) + ";\nwindow.PEOPLE=" + json.dumps(PEOPLE, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    for name in ("site.css", "site.js"):
        shutil.copy(ROOT / "tools/assets" / name, SITE / "assets" / name)

    # Brand files, taken unchanged from the school's site.
    logo = Image.open(fetch("2021/02/RudolfSteinerskolan-Logotyp-white-1000px-e1614496411406.png"))
    logo.save(SITE / "assets/logo.png")
    for n, box in LOGO_PARTS:
        logo.crop(box).save(SITE / f"assets/logo-{n}.png")
    Image.open(fetch("2021/03/Favicon_fagel.png")).save(SITE / "assets/favicon.png")
    Image.open(fetch("2021/03/Bakgrund-papper-ljusare.jpg")).convert("RGB").save(SITE / "assets/paper.webp", "WEBP", quality=70)
    head = Image.open(fetch("2021/03/Header-RS4-scaled.jpg")).convert("RGB")
    head.resize((1600, round(head.height * 1600 / head.width))).save(SITE / "assets/header.webp", "WEBP", quality=70)
    for old in (SITE / "assets/img").glob("*.webp"):
        if f"assets/img/{old.name}" not in used:
            old.unlink()
    print("pages:", len(index), "images:", len(used))


if __name__ == "__main__":
    build()
