#!/usr/bin/env python3
"""Turn the VAB PDFs in this directory into a git history of plain text.

Each distinct PDF version (identified by its CreationDate) becomes one commit,
oldest first, dated with the day the PDF was generated. The text is split into
one file per VAB section (text/A/A-2.txt, text/E/E-Afghanistan-1.txt, ...) and
paragraphs are unwrapped onto single lines so that reflowed text does not show
up as a change. Page headers/footers, TOC page numbers, blank lines, indentation
and "...weggefallen..." markers are dropped, and spacing artefacts are normalised.

    ./build-history.py            # extract only, into text/ (no git changes)
    ./build-history.py --rebuild  # recreate the whole git history from the PDFs

Needs pdftotext and pdfinfo (poppler-utils).
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "text"

HEADER = re.compile(r"^\s*Verfahrenshinweise (der Ausländerbehörde|zum Aufenthalt in) Berlin\s*$")
FOOTER = re.compile(r"^\s*(Dieses PDF wurde erstellt am: [\d.]+)?\s*(Seite\s+\d+(\s+von)?\s+\d+|- \d+ -)?\s*$")
OLD_TOC_ENTRY = re.compile(r"^\s*([A-E]\.\S.*?)\s*\.{8,}\s*\d+\s*$")   # layout used until about 2012
LEADER = re.compile(r"\s*(?:\.{5,}\s*(\d+)?|\.{2,}\s*\d+)\s*$")          # TOC dot leaders + page number
TOC_ENTRY = re.compile(r"^\s*(VAB \S.*?)\s*\.{5,}\s*\d*\s*$")
HEADING = re.compile(r"^\s*((VAB )?[A-F][. ]\s?\d|(\d+[a-z]?\.)+(\d+[a-z]?)?\s+[A-ZÄÖÜ(„\"]|[-•▪◦o*] |\(\d+\) |[a-z]\) )")
GONE = re.compile(r"(\.\s*){3}w\s*e\s*g\s*g\s*e\s*f\s*a\s*l\s*l\s*e\s*n\s*(\.\s*){2}\.")
SPLIT_HEADER = re.compile(r"\s*(der Ausländerbehörde|zum Aufenthalt in) Berlin\s*$")


WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")
SPLIT_WORD = re.compile(r"(?<![\w.])([A-Za-zÄÖÜäöüß]+) ([a-zäöüß]+)(?!\w)")
SPACED = re.compile(r"(\S )+\S")
VOCAB = {}


def unsplit(l):
    """Rejoin words the PDF broke in two ("H err", "zu rzeit"), using word counts from all versions."""
    def join(m):
        a, b = m.group(1), m.group(2)
        whole = VOCAB.get(a + b, 0)
        if whole < 3:
            return m.group(0)
        for part in (a, b):
            if len(part) == 1 or VOCAB.get(part, 0) * 10 <= whole:
                return a + b
        return m.group(0)
    for _ in range(3):
        new = SPLIT_WORD.sub(join, l)
        if new == l:
            break
        l = new
    return l


def tidy(l):
    """Normalise spacing artefacts that differ between otherwise identical PDFs."""
    # letter-spaced words ("g e s i c h e r t      i s t .") keep wide gaps between words
    chunks = re.split(r" {2,}", l.strip())
    l = " ".join(c.replace(" ", "") if len(c) >= 5 and SPACED.fullmatch(c) else c for c in chunks)
    l = GONE.sub(" ", l)                         # "...weggefallen..." deletion markers
    l = re.sub(r"\s+", " ", l).strip()           # no indentation, single spaces
    l = re.sub(r" +([,;:)\]])", r"\1", l)        # "( FEWG ; x )" -> "(FEWG; x)"
    l = re.sub(r"([(\[]) +", r"\1", l)
    l = re.sub(r" +\.(?=\s|$|\d)", ".", l)       # "04 .07.2024", "Wort ."
    l = re.sub(r"(\d\.) (?=\d{4}\b)", r"\1", l) # "01.01. 2025"
    l = re.sub(r"(?<=\w) -(?=[a-zäöü])", "-", l) # "18-24 -jährige"
    return unsplit(l) if VOCAB else l
FULL_LINE = 95  # justified body lines are ~105-125 chars once spacing is collapsed


def pdf_meta(pdf):
    out = subprocess.run(["pdfinfo", "-isodates", str(pdf)], capture_output=True, text=True).stdout
    meta = dict(l.split(":", 1) for l in out.splitlines() if ":" in l)
    return meta.get("CreationDate", "").strip(), meta.get("Pages", "").strip()


def clean_pages(raw):
    """Drop page headers/footers and TOC page numbers; return a list of lines."""
    lines = []
    for page in raw.split("\f"):
        body = [l.rstrip() for l in page.split("\n")]
        body = [l for l in body if not (l.strip() and FOOTER.match(l))]
        for i, l in enumerate(body):          # first non-blank line is the running header
            if l.strip():
                if HEADER.match(l):
                    body[i] = ""
                elif l.strip() == "Verfahrenshinweise" and i + 1 < len(body) and SPLIT_HEADER.search(body[i + 1]):
                    body[i] = ""               # header interleaved with the first body line
                    body[i + 1] = SPLIT_HEADER.sub("", body[i + 1])
                break
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        lines.extend(body)                     # pages are joined without a gap
    out = []
    skip_number = False
    for l in lines:
        if skip_number and l.strip().isdigit():
            skip_number = False
            continue
        skip_number = False
        m = LEADER.search(l)
        if m:
            skip_number = m.group(1) is None   # page number wrapped onto the next line
            l = l[: m.start()]
        out.append(tidy(l))
    return out


def unwrap(lines):
    """Join hard-wrapped lines of a paragraph into one line."""
    # the pre-2011 layout has narrower pages, so derive "full line" from the document itself
    lengths = sorted(len(l.strip()) for l in lines if len(l.strip()) > 40)
    full = min(FULL_LINE, int(0.8 * lengths[int(0.9 * len(lengths))])) if lengths else FULL_LINE
    out = []
    joining = False
    for l in lines:
        s = l.strip()
        if joining and s and not HEADING.match(l):
            out[-1] += " " + s
        else:
            out.append(l)
        joining = len(s) >= full
    return [l for l in out if l.strip()]         # blank lines only reflect PDF spacing


def old_key(l):
    return re.sub(r"\s+", "", l).rstrip(".").upper()


def split_sections_old(raw, lines):
    """Old layout: the TOC lists "A.2. .... 11" and each section starts with a line "A.2."."""
    toc = []
    for l in raw.split("\n"):
        m = OLD_TOC_ENTRY.match(l)
        if m and old_key(m.group(1)) not in toc:
            toc.append(old_key(m.group(1)))
    pos = {k: i for i, k in enumerate(toc)}
    sections = {"00-Inhaltsverzeichnis": []}
    order = ["00-Inhaltsverzeichnis"]
    cur, cur_pos = order[0], -1
    toc_end = next((i for i, l in enumerate(lines) if toc and old_key(l) == toc[-1]), -1)
    for i, l in enumerate(lines):
        k = old_key(l)
        if i > toc_end and 0 < pos.get(k, -1) - cur_pos <= 3:   # sections follow the TOC order
            part, _, rest = l.strip().rstrip(".").partition(".")
            rest = rest.replace(".", " ")
            cur = part + " " + (rest.lower() if part in "ACD" else rest)
            cur_pos = pos[k]
            if cur not in sections:
                sections[cur] = []
                order.append(cur)
        sections[cur].append(l)
    return order, sections


def split_sections(raw, lines):
    names = {re.sub(r"\s+", " ", m.group(1)) for l in raw.split("\n") if (m := TOC_ENTRY.match(l))}
    if not names:
        return split_sections_old(raw, lines)
    sections = {"00-Inhaltsverzeichnis": []}
    order = ["00-Inhaltsverzeichnis"]
    cur = order[0]
    for l in lines:
        key = re.sub(r"\s+", " ", l.strip())
        if key in names:
            cur = key[4:]                       # drop "VAB "
            if cur not in sections:
                sections[cur] = []
                order.append(cur)
        sections[cur].append(l)
    return order, sections


def pdf_text(pdf):
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def extract(raw):
    order, sections = split_sections(raw, clean_pages(raw))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for name in order:
        body = unwrap(sections[name])
        if name.startswith("00-"):
            path = OUT / f"{name}.txt"
        else:
            slug = re.sub(r"[^\w]+", "-", name).strip("-")
            path = OUT / name[0] / f"{slug}.txt"
        path.parent.mkdir(exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(body).strip("\n") + "\n")
    (OUT / "00-Reihenfolge.txt").write_text("\n".join(order) + "\n", encoding="utf-8")
    return len(order) - 1


def update_readme(rows):
    """Rewrite the version table between the markers in README.md."""
    readme = ROOT / "README.md"
    start, end = "<!-- versions:start -->", "<!-- versions:end -->"
    if not readme.exists():
        return
    text = readme.read_text(encoding="utf-8")
    if start not in text or end not in text:
        return
    years = {}
    for day, pages in rows:
        years.setdefault(day[:4], []).append(f"{day[8:10]}.{day[5:7]}.")
    table = [f"{len(rows)} versions, from {rows[0][0]} ({rows[0][1]} pages) to {rows[-1][0]} ({rows[-1][1]} pages).",
             "", "| Year | Versions | Dates |", "|---|---|---|"]
    table += [f"| {y} | {len(d)} | {' '.join(d)} |" for y, d in sorted(years.items())]
    head, rest = text.split(start, 1)
    readme.write_text(head + start + "\n" + "\n".join(table) + "\n" + end + rest.split(end, 1)[1], encoding="utf-8")


def git(*args, env=None):
    subprocess.run(["git", "-C", str(ROOT), *args], check=True, env={**os.environ, **(env or {})},
                   stdout=subprocess.DEVNULL)


def main():
    rebuild = "--rebuild" in sys.argv
    versions = {}
    seen = set()
    for pdf in sorted(ROOT.glob("*.pdf")):
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest in seen:
            print(f"skip duplicate   {pdf.name}")
            continue
        seen.add(digest)
        created, pages = pdf_meta(pdf)
        if not created:
            print(f"skip unreadable  {pdf.name}")
            continue
        if created in versions:
            print(f"skip same version {pdf.name} (= {versions[created][0].name})")
            continue
        versions[created] = (pdf, pages)

    if rebuild:
        if (ROOT / ".git").exists():
            shutil.rmtree(ROOT / ".git")
        git("init", "-q", "-b", "main")

    raws = {created: pdf_text(pdf) for created, (pdf, _) in versions.items()}
    for raw in raws.values():                   # word counts over all versions, for unsplit()
        for w in WORD.findall(raw):
            VOCAB[w] = VOCAB.get(w, 0) + 1

    update_readme([(created[:10], versions[created][1]) for created in sorted(versions)])

    for created in sorted(versions):
        pdf, pages = versions[created]
        n = extract(raws[created])
        day = created[:10]
        print(f"{day}  {pages:>4} Seiten  {n:>3} Abschnitte  {pdf.name}")
        if rebuild:
            stamp = f"{day}T12:00:00+0000"
            git("add", "-A", "text")
            git("commit", "-q", "-m", f"VAB Stand {day[8:10]}.{day[5:7]}.{day[:4]} ({pages} Seiten)\n\nQuelle: {pdf.name}",
                env={"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp})
            git("tag", "-f", day)

    if rebuild:
        (ROOT / ".gitignore").write_text("*.pdf\n", encoding="utf-8")
        extras = [f for f in (".gitignore", "build-history.py", "download-versions.py", "download-missing.sh", "README.md") if (ROOT / f).exists()]
        git("add", *extras)
        git("commit", "-q", "-m", "Add extraction script and readme")


if __name__ == "__main__":
    main()
