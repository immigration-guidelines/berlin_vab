# VAB Berlin – version history as text

The *Verfahrenshinweise zum Aufenthalt in Berlin* (VAB) are the Berlin immigration office's (Landesamt für Einwanderung) internal guidance on residence, asylum and naturalisation law. The office publishes them as a single PDF of roughly 1,000 pages and replaces it several times a year without a change log.

This repository turns each PDF version into plain text and stores it as one git commit, so that `git diff` shows what changed between versions.

## What is in here

| Path | Contents |
|---|---|
| `text/` | The VAB as text, one file per section. This is what the commits track. |
| `build-history.py` | Script that extracts the text from the PDFs and builds the git history. |
| `download-versions.py` | Script that downloads every known copy of the PDF into this folder. |
| `publish-pdfs.sh` | Script that copies the PDFs, the download scripts and a generated README into a clone of the PDF repository and commits there. |
| `download-missing.sh` | Smaller script with only the sources found last, for a folder that already has the rest. |
| `*.pdf` | The source PDFs. They are git-ignored here and published separately at [brinlyau/vabpdfs](https://github.com/brinlyau/vabpdfs). |

Each version is one commit, dated and tagged with the day its PDF was generated (for example `2026-08-31`). `git tag` lists all versions.

### Layout of `text/`

| Folder | Covers | Example |
|---|---|---|
| `A/` | Aufenthaltsgesetz, one file per paragraph | `A/A-18g.txt` is § 18g (Blue Card) |
| `B/` | Ordinances (AufenthV, BeschV) | `B/B-BeschV-2-9-Zuwanderung-von-Fachkräften.txt` |
| `C/` | FreizügG/EU (EU free movement) | `C/C-6.txt` |
| `D/` | Asylgesetz | `D/D-71.txt` |
| `E/` | Country-specific instructions | `E/E-Syrien-2.txt` |
| `S/` | Staatsangehörigkeitsgesetz (naturalisation) | `S/S-10.txt` |

`text/00-Inhaltsverzeichnis.txt` is the overall table of contents and `text/00-Reihenfolge.txt` lists the sections in document order.

## Getting the PDFs

All source PDFs are downloadable from **<https://github.com/brinlyau/vabpdfs>**, one file per version, named by the date the PDF was generated.

## Contributing a version

If you have a version that is missing from the table below, open a pull request against [brinlyau/vabpdfs](https://github.com/brinlyau/vabpdfs) that adds the PDF. Nothing needs to change in this repository: once the PDF is merged, the text history here is regenerated from the full set of PDFs.

- Add the PDF unmodified, as it was published.
- Name it `YYYY-MM-DD-vab-berlin.pdf`, using the date printed on its first page ("Dieses PDF wurde erstellt am", or "Erstellt am" in versions before 2011).
- Say in the pull request where the file came from.

## Viewing changes

Which sections changed in each version:

```
git log --stat
```

What changed between two versions, in one section:

```
git diff --word-diff 2026-02-25 2026-08-31 -- text/A/A-2.txt
```

The full history of one section:

```
git log -p --word-diff -- text/A/A-18g.txt
```

Every change that mentions a term, across all versions:

```
git log -p --word-diff -G'Blaue Karte' -- text
```

Each paragraph is a single long line, so `--word-diff` (or a viewer that highlights changes within a line) is much easier to read than the plain line diff.

## How the text differs from the PDF

The text is cleaned up so that diffs show changes in wording rather than changes in layout:

- Paragraphs are joined onto one line each, so reflowed text is not reported as a change.
- Page headers, page footers, page numbers in tables of contents, blank lines and indentation are dropped.
- `...weggefallen...` markers are removed. The office uses them to mark deleted text for one version only, so they would otherwise show up as a change twice.
- Spacing that the PDF introduces is repaired: words split in two (`H err` becomes `Herr`), letter-spaced words, and stray spaces around punctuation.

This makes the text unsuitable for quoting. Use the PDF when the exact wording or page matters.

Some noise remains, in a few percent of changed lines:

- The PDF sometimes splits numbers (`3 60 Euro`), and these are left as they are.
- Paragraphs are detected by line length, so a paragraph is occasionally joined or split differently between two versions.
- When the office restructures a section, moved paragraphs appear as removed and re-added.

## Rebuilding the history

This is what the maintainer runs after new PDFs arrive.

`./download-versions.py` fetches every known version that is missing from the folder, including the current one from berlin.de; `./download-versions.py --list` prints the URLs. To add a single PDF by hand:

1. Download the current PDF from the [VAB page of the Landesamt für Einwanderung](https://www.berlin.de/einwanderung/service/downloads/artikel.875097.php) and put it in this folder. The file name does not matter; the version date is read from the PDF itself.
2. Rebuild the history:

   ```
   ./build-history.py --rebuild
   ```

`--rebuild` deletes `.git` and recreates every commit from the PDFs in the folder, so the versions stay in chronological order even when an older one is added later. It also means any commits made by hand are lost, and commit hashes change on every rebuild. The tags (dates) stay the same.

Running `./build-history.py` without the flag only extracts the newest version into `text/` and leaves git alone.

Duplicate PDFs and PDFs with the same creation date are skipped automatically.

### Requirements

- Python 3.8 or newer
- `pdftotext` and `pdfinfo` from poppler-utils
- git

## Versions and sources

This table is rewritten by `build-history.py` on every run; each date is also a git tag.

<!-- versions:start -->
79 versions, from 2007-09-14 (540 pages) to 2026-08-31 (985 pages).

| Year | Versions | Dates |
|---|---|---|
| 2007 | 2 | 14.09. 05.12. |
| 2008 | 1 | 27.10. |
| 2009 | 1 | 30.09. |
| 2010 | 3 | 02.02. 22.04. 16.06. |
| 2011 | 4 | 11.01. 15.04. 20.10. 08.12. |
| 2012 | 3 | 09.03. 02.08. 21.11. |
| 2013 | 5 | 18.02. 02.05. 11.07. 11.09. 04.12. |
| 2014 | 4 | 05.03. 22.05. 29.08. 08.10. |
| 2015 | 6 | 03.03. 29.05. 24.08. 15.10. 03.11. 03.12. |
| 2016 | 8 | 05.01. 22.02. 17.03. 05.08. 12.09. 07.11. 05.12. 28.12. |
| 2017 | 6 | 20.03. 01.06. 01.08. 08.08. 23.10. 11.12. |
| 2018 | 5 | 19.03. 30.04. 01.08. 22.10. 27.11. |
| 2019 | 5 | 11.03. 08.07. 16.08. 23.08. 29.11. |
| 2020 | 7 | 06.01. 04.03. 17.06. 26.06. 07.09. 18.11. 18.12. |
| 2021 | 4 | 21.04. 21.05. 14.06. 27.09. |
| 2022 | 3 | 08.02. 05.05. 01.06. |
| 2023 | 2 | 28.02. 29.12. |
| 2024 | 4 | 19.03. 26.03. 13.06. 16.07. |
| 2025 | 4 | 18.02. 18.06. 30.09. 23.12. |
| 2026 | 2 | 25.02. 31.08. |
<!-- versions:end -->

The PDFs come from:

- the [VAB page of the Landesamt für Einwanderung](https://www.berlin.de/einwanderung/service/downloads/artikel.875097.php) (current version)
- the Wayback Machine, under `berlin.de/einwanderung/_assets/20191129.pdf` (2021 onwards; the file name has not changed since 2019), `berlin.de/labo/_assets/zuwanderung/vab.pdf` (2019–2020), `berlin.de/formularserver/formular.php?157323` (2010–2015) and `berlin.de/imperia/md/content/labo/auslaenderangelegenheiten/vaabhbln.pdf` (2008–2009)
- two freedom-of-information requests on FragDenStaat: [one](https://fragdenstaat.de/anfrage/altere-versionen-der-verfahrenshinweise-der-auslanderbehorde-berlin-2/) released 32 versions from March 2015 to March 2020, [another](https://fragdenstaat.de/anfrage/interne-weisungen-erfassung-und-auswertung-geleisteter-arbeit-dienstaufsichtsbeschwerden-47/) later ones up to September 2021
- copies kept by refugee councils and legal sites (Flüchtlingsrat Niedersachsen and einwanderer.net for 2007, Flüchtlingsrat Berlin for 2013) and the Studierendenwerk Berlin (2023)

Versions up to 2010 use an older layout with narrower pages. Their sections are named after the old numbering (`A.2.` becomes `A/A-2.txt`), so parts A, C and D line up with later versions, while the ordinance (B) and country (E) files have different names before and after the change.
