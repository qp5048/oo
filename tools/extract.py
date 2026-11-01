"""Turns the WordPress page HTML in content/pages.json into plain block lists."""
import html as H
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {"br", "img", "hr", "input", "meta", "link", "source"}
INLINE = {"a", "strong", "b", "em", "i", "br"}
SKIP = {"script", "style", "form", "noscript", "svg", "button", "select", "textarea"}
BLOCK = {"h1": "h", "h2": "h", "h3": "h", "h4": "h", "h5": "h", "h6": "h", "p": "p", "li": "li"}


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.cur = None
        self.skip = 0
        self.a_stack = []
        self.loose_a = None

    def start_block(self, kind, tag):
        self.flush()
        self.cur = {"t": kind, "tag": tag, "html": ""}

    def flush(self):
        if self.cur is not None:
            text = self.cur["html"].strip()
            plain = re.sub(r"<[^>]+>", "", text).strip()
            if plain:
                self.cur["html"] = re.sub(r"\s+", " ", text)
                self.blocks.append(self.cur)
            self.cur = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP:
            if tag not in VOID:
                self.skip += 1
            return
        if self.skip:
            return
        if tag == "img":
            src = a.get("data-orig-src") or a.get("src") or ""
            if "uploads" in src and not src.startswith("data:"):
                self.flush_loose()
                was = self.cur
                self.blocks.append({"t": "img", "src": src.split("/uploads/")[-1], "alt": a.get("alt", "")})
                self.cur = was
            return
        if tag in BLOCK:
            self.start_block(BLOCK[tag], tag)
            return
        if tag == "a":
            href = a.get("href", "")
            cls = a.get("class", "")
            if "fusion-button" in cls or self.cur is None:
                self.flush()
                self.loose_a = {"t": "btn", "href": href, "text": ""}
            elif self.cur is not None:
                self.cur["html"] += f'<a href="{H.escape(href, True)}">'
                self.a_stack.append(tag)
            return
        if self.cur is not None and tag in INLINE:
            n = {"b": "strong", "i": "em"}.get(tag, tag)
            self.cur["html"] += f"<{n}>"

    def flush_loose(self):
        if self.loose_a is not None:
            self.loose_a["text"] = re.sub(r"\s+", " ", self.loose_a["text"]).strip()
            if self.loose_a["text"]:
                self.blocks.append(self.loose_a)
            self.loose_a = None

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in BLOCK:
            self.flush()
            return
        if tag == "a":
            if self.loose_a is not None:
                self.flush_loose()
            elif self.a_stack and self.cur is not None:
                self.a_stack.pop()
                self.cur["html"] += "</a>"
            return
        if self.cur is not None and tag in INLINE and tag != "br":
            n = {"b": "strong", "i": "em"}.get(tag, tag)
            self.cur["html"] += f"</{n}>"

    def handle_data(self, data):
        if self.skip:
            return
        if self.loose_a is not None:
            self.loose_a["text"] += data
        elif self.cur is not None:
            self.cur["html"] += H.escape(data, False)
        elif data.strip():
            self.cur = {"t": "p", "tag": "p", "html": H.escape(data, False)}
            self.flush()


def clean(rendered):
    s = re.sub(r"\[/?fusion[^\]]*\]", " ", rendered)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    p = Parser()
    p.feed(s)
    p.flush()
    p.flush_loose()
    return p.blocks


def load_pages():
    pages = json.loads((ROOT / "content/pages.json").read_text(encoding="utf-8"))
    out = {}
    for p in pages:
        link = p["link"].replace("https://rudolfsteinerskolan.se", "").strip("/")
        out[link] = {"title": H.unescape(p["title"]["rendered"]), "blocks": clean(p["content"]["rendered"])}
    return out


if __name__ == "__main__":
    import sys
    pages = load_pages()
    for k in sys.argv[1:]:
        print("=====", k, pages[k]["title"])
        for b in pages[k]["blocks"]:
            print(b["t"], b.get("tag", ""), (b.get("src") or b.get("href", "")), "|", (b.get("html") or b.get("text") or "")[:110])
