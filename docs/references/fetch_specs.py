#!/usr/bin/env python3
"""Fetch W3C editors'-draft ReSpec specs and render them to markdown.

Writes ``<name>.md`` into ``shacl12/`` / ``sparql12/`` beside this file.
Headings include ReSpec section numbers (``1.``, ``1.1``, ``A.``). Run via
``just fetch-specs``.
"""

from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from markdownify import markdownify as to_markdown

ROOT = Path(__file__).resolve().parent

SPECS: dict[str, dict[str, str]] = {
    "shacl12": {
        "core": "https://w3c.github.io/data-shapes/shacl12-core/",
        "sparql": "https://w3c.github.io/data-shapes/shacl12-sparql/",
        "node-expr": "https://w3c.github.io/data-shapes/shacl12-node-expr/",
        "rules": "https://w3c.github.io/data-shapes/shacl12-rules/",
        "ui": "https://w3c.github.io/data-shapes/shacl12-ui/",
    },
    "sparql12": {
        "query": "https://w3c.github.io/sparql-query/spec/",
        "update": "https://w3c.github.io/sparql-update/spec/",
    },
}

USER_AGENT = "fastshaql-spec-fetcher/1.0 (+https://github.com/robsyc/fastshaql)"

# Specref keys only — do not eat SPARQL ``[[ ]]`` punctuation.
_BIBKEY = r"[A-Za-z][\w.+-]*"
_BIBREF_PAIRED_RE = re.compile(
    rf"\[\[\[({_BIBKEY})\]\]\]\s+\[\[({_BIBKEY})\]\]", re.IGNORECASE
)
_BIBREF_RE = re.compile(rf"\[\[+!?({_BIBKEY})\]\]+")
_BIKESHED_DFN_RE = re.compile(r"\[=([^\[\]=]+)=\]")

_HEADING_TAGS = frozenset({"h2", "h3", "h4", "h5", "h6"})
_INTRO_IDS = frozenset({"abstract", "sotd", "toc"})
_CHROME_TAGS = frozenset({"nav", "header", "footer", "script", "style"})
_BANNER_CLASSES = frozenset({"def-header", "term-def-header"})
_ASIDE_KINDS = ("example", "note", "warning")
_CODE_TAGS = frozenset({"pre", "code", "script", "style"})

_NOTE_LEAD_RE = re.compile(
    r"^([ \t]*)\*\*(Note|Example|Warning):\*\*\n+[ \t]*(?=\S)", re.MULTILINE
)
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _kids(tag: Tag) -> list[Tag]:
    return [c for c in tag.children if isinstance(c, Tag)]


def _classes(value: object) -> set[str]:
    """Normalize BeautifulSoup class values (``class_`` may pass a bare str)."""
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {str(item) for item in value}
    return {str(value)}


def _resolve_includes(root: Tag, base_url: str, seen: set[str] | None = None) -> None:
    """Inline ReSpec ``data-include`` fragments (grammar tables, spec-family lists)."""
    seen = seen if seen is not None else set()
    for element in list(root.find_all(True, attrs={"data-include": True})):
        if not isinstance(element, Tag):
            continue
        relative = str(element.get("data-include") or "").strip()
        if not relative:
            continue
        url = urljoin(base_url, relative)
        if url in seen:
            element.attrs.pop("data-include", None)
            continue
        seen.add(url)
        try:
            fragment = fetch(url)
        except Exception as exc:
            print(f"WARN    include {url}: {exc}", file=sys.stderr)
            continue
        frag = BeautifulSoup(fragment, "html.parser")
        source = frag.body if frag.body is not None else frag
        element.clear()
        element.attrs.pop("data-include", None)
        for child in list(source.contents):
            element.append(child.extract())
        _resolve_includes(element, url, seen)


def _strip_chrome(root: Tag, soup: BeautifulSoup) -> None:
    for tag in list(root.find_all(_CHROME_TAGS)):
        tag.decompose()
    for tag in list(
        root.find_all(class_=lambda c: bool(_BANNER_CLASSES & _classes(c)))
    ):
        tag.decompose()
    for h1 in list(root.find_all("h1", id="appendix")):
        h1.decompose()
    for svg in list(root.find_all("svg")):
        title = svg.find("title")
        raw = svg.get("aria-label") or svg.get("title")
        label = str(raw).strip() if raw else ""
        if not label and isinstance(title, Tag):
            label = title.get_text(strip=True)
        em = soup.new_tag("em")
        em.string = f"[Diagram omitted{f': {label}' if label else ''}]"
        note = soup.new_tag("p")
        note.append(em)
        svg.replace_with(note)


def _prefer_turtle(root: Tag) -> None:
    """Drop JSON-LD tab panes when a Turtle sibling is present."""
    for parent in list(root.find_all(True)):
        kids = _kids(parent)
        if not any("turtle" in _classes(k.get("class")) for k in kids):
            continue
        for kid in kids:
            if "jsonld" in _classes(kid.get("class")):
                kid.decompose()


def _unnest_list_items(root: Tag) -> None:
    """html.parser nests omitted ``</li>``; lift inner items to siblings."""
    changed = True
    while changed:
        changed = False
        for item in list(root.find_all("li")):
            nested = item.find("li", recursive=False)
            if nested is None:
                continue
            item.insert_after(nested.extract())
            changed = True


def _wrap_turtle_divs(root: Tag, soup: BeautifulSoup) -> None:
    for div in list(root.find_all("div", class_="turtle")):
        pre, code = soup.new_tag("pre"), soup.new_tag("code")
        for child in list(div.contents):
            code.append(child.extract())
        pre.append(code)
        div.replace_with(pre)


def _surface_asides_and_notes(root: Tag, soup: BeautifulSoup) -> None:
    for aside in list(root.find_all("aside")):
        kind = next(
            (k for k in _ASIDE_KINDS if k in _classes(aside.get("class"))), None
        )
        title = aside.get("title")
        if kind and title:
            lead, strong = soup.new_tag("p"), soup.new_tag("strong")
            strong.string = f"{kind.capitalize()}: {title}"
            lead.append(strong)
            aside.insert(0, lead)
            del aside["title"]
    for note in list(root.find_all(class_="note")):
        if note.name not in ("p", "div"):
            continue
        if note.get_text(" ", strip=True).casefold().startswith("note"):
            continue
        strong = soup.new_tag("strong")
        strong.string = "Note:"
        note.insert(0, NavigableString(" "))
        note.insert(0, strong)


def _strip_unresolved_markup(root: Tag) -> None:
    """Resolve leftover ReSpec/Bikeshed shorthand (bibrefs skipped inside code)."""
    for node in list(root.find_all(string=True)):
        if isinstance(node, Comment) or not isinstance(node, NavigableString):
            continue
        parent = node.parent
        if not isinstance(parent, Tag):
            continue
        text = str(node)
        cleaned = _BIKESHED_DFN_RE.sub(r"\1", text)
        in_code = parent.name in _CODE_TAGS or parent.find_parent(_CODE_TAGS)
        if not in_code:
            cleaned = _BIBREF_PAIRED_RE.sub(
                lambda m: (
                    m.group(1)
                    if m.group(1).casefold() == m.group(2).casefold()
                    else m.group(0)
                ),
                cleaned,
            )
            cleaned = _BIBREF_RE.sub(r"\1", cleaned)
        if cleaned != text:
            node.replace_with(cleaned)


def _section_header(section: Tag) -> Tag | None:
    """First heading in a section, skipping empty legacy-id ``<span>`` anchors."""
    for child in _kids(section):
        if child.name in _HEADING_TAGS:
            return child
        if child.name == "span" and not child.get_text(strip=True):
            continue
        return None
    return None


def _ensure_conformance_heading(root: Tag, soup: BeautifulSoup) -> None:
    for section in root.find_all("section", id="conformance"):
        if _section_header(section) is None:
            heading = soup.new_tag("h2")
            heading.string = "Conformance"
            section.insert(0, heading)


def _wrap_stray_headings(section: Tag, soup: BeautifulSoup) -> None:
    """Wrap loose ``<hN>`` siblings as nested sections (ReSpec HTML outline)."""
    header = _section_header(section)
    kids = _kids(section)
    index = kids.index(header) + 1 if header is not None and header in kids else 0
    while index < len(kids):
        child = kids[index]
        if child.name in _HEADING_TAGS:
            level = int(child.name[1])
            wrapper = soup.new_tag("section")
            child.insert_before(wrapper)
            taken = [child]
            look = index + 1
            while look < len(kids):
                sibling = kids[look]
                if sibling.name in _HEADING_TAGS and int(sibling.name[1]) <= level:
                    break
                taken.append(sibling)
                look += 1
            for node in taken:
                wrapper.append(node.extract())
            kids = _kids(section)
            index = kids.index(wrapper) + 1
            continue
        index += 1
    for child in _kids(section):
        if child.name == "section":
            _wrap_stray_headings(child, soup)


def _is_intro(section: Tag) -> bool:
    current: Tag | None = section
    while current is not None and current.name != "body":
        if current.name == "section" and (
            "introductory" in _classes(current.get("class"))
            or current.get("id") in _INTRO_IDS
        ):
            return True
        parent = current.parent
        current = parent if isinstance(parent, Tag) else None
    return False


def _appendix_number(num: int) -> str:
    """1=A, 26=Z, 27=AA — same spreadsheet column mapping as ReSpec."""
    letters = ""
    while num > 0:
        num -= 1
        letters = chr(65 + num % 26) + letters
        num //= 26
    return letters


def _heading_depth(header: Tag) -> int:
    depth = 0
    current = header.parent if isinstance(header.parent, Tag) else None
    while current is not None and current.name != "body":
        if current.name == "section":
            depth += 1
        parent = current.parent
        current = parent if isinstance(parent, Tag) else None
    return min(depth + 1, 6)


def _number_sections(parent: Tag, prefix: str = "") -> None:
    """Mirror ReSpec structure.js: outline walk, rename headers, prepend secnos."""
    appendix_mode = False
    last_non_appendix = 0
    index = 1
    if prefix and not prefix.endswith("."):
        prefix += "."

    for section in _kids(parent):
        if section.name != "section":
            continue
        classes = _classes(section.get("class"))
        if "notoc" in classes:
            continue
        header = _section_header(section)
        if header is None:
            continue

        is_intro = _is_intro(section)
        if not is_intro:
            target = f"h{_heading_depth(header)}"
            if header.name != target:
                header.name = target

        is_appendix = "appendix" in classes
        if is_appendix and not prefix and not appendix_mode:
            last_non_appendix = index
            appendix_mode = True

        if is_intro:
            secno = ""
        elif appendix_mode:
            secno = _appendix_number(index - last_non_appendix + 1)
        else:
            secno = f"{prefix}{index}"

        if secno:
            if len(secno.split(".")) == 1:
                secno += "."
            header.insert(0, f"{secno} ")
            index += 1
        _number_sections(section, prefix=secno)


def _ref_label(target: Tag) -> str:
    if target.name in _HEADING_TAGS or target.name == "dfn":
        return target.get_text(" ", strip=True)
    if target.name == "span":
        for sibling in target.next_siblings:
            if isinstance(sibling, Tag) and sibling.name in _HEADING_TAGS:
                return sibling.get_text(" ", strip=True)
            if isinstance(sibling, Tag):
                break
        parent = target.find_parent("section")
        target = parent if isinstance(parent, Tag) else target
    if target.name == "section":
        header = _section_header(target) or target.find(_HEADING_TAGS)
        if isinstance(header, Tag):
            return header.get_text(" ", strip=True)
    return ""


def _fill_empty_section_refs(root: Tag) -> None:
    by_id = {
        str(el["id"]): el for el in root.find_all(True, id=True) if isinstance(el, Tag)
    }
    for anchor in root.find_all("a", href=True):
        href = str(anchor.get("href") or "")
        if not href.startswith("#") or len(href) < 2 or anchor.get_text(strip=True):
            continue
        target = by_id.get(href[1:])
        if target is None:
            continue
        label = _ref_label(target)
        if label:
            anchor.clear()
            anchor.string = label


def prepare_html(html: str, base_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.body if soup.body is not None else soup
    _resolve_includes(root, base_url)
    _strip_chrome(root, soup)
    _prefer_turtle(root)
    _unnest_list_items(root)
    _wrap_turtle_divs(root, soup)
    _surface_asides_and_notes(root, soup)
    _strip_unresolved_markup(root)
    _ensure_conformance_heading(root, soup)
    for section in _kids(root):
        if section.name == "section":
            _wrap_stray_headings(section, soup)
    _number_sections(root)
    _fill_empty_section_refs(root)
    return root.decode_contents()


def html_to_md(html: str, base_url: str) -> str:
    md = to_markdown(prepare_html(html, base_url), heading_style="ATX", bullets="-")
    md = _NOTE_LEAD_RE.sub(r"\1**\2:** ", md)
    return _MULTI_BLANK_RE.sub("\n\n", md).strip() + "\n"


def main() -> int:
    rc = 0
    for family, sources in SPECS.items():
        family_dir = ROOT / family
        family_dir.mkdir(parents=True, exist_ok=True)
        for name, url in sources.items():
            print(f"fetch  {family}/{name}  <-  {url}")
            try:
                html = fetch(url)
            except Exception as exc:
                print(f"FAIL    {family}/{name}: {exc}", file=sys.stderr)
                rc = 1
                continue
            stamp = (
                f"<!-- {url} — W3C editors' draft, fetched "
                f"{date.today().isoformat()} -->\n\n"
            )
            (family_dir / f"{name}.md").write_text(
                stamp + html_to_md(html, url), encoding="utf-8"
            )
    if rc:
        print("one or more specs failed; see errors above", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
