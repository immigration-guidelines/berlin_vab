#!/usr/bin/env python3
"""Download every known copy of the VAB PDF into this folder.

Each file is saved as YYYY-MM-DD-vab-berlin.pdf, where the date is the day the
PDF was generated (read from the PDF itself). Versions that are already in the
folder are skipped, so the script can be re-run after an interruption.

    ./download-versions.py            # fetch everything that is missing
    ./download-versions.py 2014 2020  # only sources whose URL or date contains one of these
    ./download-versions.py --list     # print the URLs and exit

Afterwards run ./build-history.py --rebuild to turn the PDFs into git history.

Needs curl and pdfinfo (poppler-utils). The servers are slow; a full run takes
well over an hour.
"""
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"

# Freedom-of-information release on FragDenStaat: the file name is the version date.
FDS = "https://media.frag-den-staat.de/files/foi/468059/{}.pdf"
FDS_VERSIONS = """
20150303 20150529 20150824 20151015 20151103 20151203
20160105 20160222 20160317 20160805 20160912 20161107 20161205 20161228
20170320 20170601 20170801 20170808 20171023 20171211
20180319 20180430 20180801 20181022 20181127
20190311 20190708 20190816 20190823 20191129
20200106 20200304
""".split()

# A second request on FragDenStaat released later versions under another folder.
FDS2 = "https://media.frag-den-staat.de/files/foi/722222/{}.pdf"
FDS2_VERSIONS = "20200617 20200626 20200907 20201118 20201218 20210421 20210521 20210614 20210927".split()

# Wayback Machine captures (one per distinct file). The version date is only known after download.
WAYBACK = "https://web.archive.org/web/{}id_/{}"
WAYBACK_CAPTURES = {
    "http://www.berlin.de/imperia/md/content/labo/auslaenderangelegenheiten/vaabhbln.pdf":
        "20081203022905 20091122132953",
    "http://www.berlin.de/formularserver/formular.php?157323":
        "20100309201956 20100510022336 20100710224534 20110123195635 20110526153302 20111115083507 "
        "20120125062441 20120325211209 20120923193729 20121123075820 20130324214033 20130526001419 "
        "20130725190143 20130925034118 20140124144743 20140526213018 20140830221259 20140925123939 "
        "20141202160628 20150715043141",
    "https://www.einwanderer.net/fileadmin/downloads/104a/berlin.pdf":
        "20240719161224",   # the 03.12.2007 version
    "https://www.berlin.de/labo/_assets/zuwanderung/vab.pdf":
        "20190115024812 20201111190118",
    "https://www.berlin.de/einwanderung/_assets/20191129.pdf":
        "20210802140200 20220222145636 20220518045530 20220624073226 20240217070749 20250528221932 "
        "20251019084143 20260114061026 20260315235737 20260903153256",
    "https://www.berlin.de/einwanderung/_assets/20191129.pdf?ts=1694007484": "20240326020430",
    "https://www.berlin.de/einwanderung/_assets/20191129.pdf?ts=1700578535": "20240714115804",
    "https://www.berlin.de/einwanderung/_assets/20191129.pdf?ts=1705017643": "20240520092626",
    "https://www.berlin.de/einwanderung/_assets/20191129.pdf?ts=1721124707": "20241006010003",
    "https://www.berlin.de/einwanderung/_assets/20191129.pdf?ts=1730453815": "20250822091854",
}

# Single copies: (version date if known, URL)
OTHER = [
    ("2007-09-14", "https://www.nds-fluerat.org/wp-content/uploads/2007/09/vaabhbln.pdf"),
    ("2013-02-18", "https://fluechtlingsrat-berlin.de/wp-content/uploads/weisung.pdf"),
    ("2021-09-27", "https://media.frag-den-staat.de/files/foi/715368/210927vab.pdf"),
    ("2023-02-28", "https://www.stw.berlin/assets/sw-berlin/bereiche/international/"
                   "Centre%20for%20Student%20Refugees%20Berlin/files/Verfahrenshinweise_fuer_Aufenthalt_in_Berlin.pdf"),
    (None, "https://www.berlin.de/einwanderung/_assets/20191129.pdf"),   # the current version
]


def sources():
    """Yield (version date or None, label, URL)."""
    for v in FDS_VERSIONS:
        yield f"{v[:4]}-{v[4:6]}-{v[6:]}", f"fragdenstaat {v}", FDS.format(v)
    for v in FDS2_VERSIONS:
        yield f"{v[:4]}-{v[4:6]}-{v[6:]}", f"fragdenstaat {v}", FDS2.format(v)
    for url, stamps in WAYBACK_CAPTURES.items():
        for ts in stamps.split():
            yield None, f"wayback {ts}", WAYBACK.format(ts, url)
    for date, url in OTHER:
        yield date, url.split("/")[2], url


def created(pdf):
    out = subprocess.run(["pdfinfo", "-isodates", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("CreationDate:"):
            return line.split(":", 1)[1].strip()[:10]
    return None


def fetch(url, dest):
    """Download with resume; return True once pdfinfo can read the file."""
    for attempt in range(4):
        cmd = ["curl", "-sS", "-L", "-m", "900", "-A", UA, "-C", "-", "-o", str(dest), url]
        if "berlin.de/einwanderung" in url and "web.archive.org" not in url:
            # berlin.de answers the first request with a bot check that sets a cookie
            jar = str(dest) + ".cookies"
            subprocess.run(["curl", "-sS", "-m", "60", "-A", UA, "-c", jar, "-o", "/dev/null", url])
            time.sleep(3)
            cmd[1:1] = ["-b", jar]
        subprocess.run(cmd)
        if dest.exists() and created(dest):
            return True
        time.sleep(10 * (attempt + 1))
    return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    todo = [s for s in sources() if not args or any(a in (s[0] or "") + s[1] + s[2] for a in args)]
    if "--list" in sys.argv:
        print("\n".join(url for _, _, url in todo))
        return

    have = {created(p) for p in ROOT.glob("*.pdf")}
    added = failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, (date, label, url) in enumerate(todo, 1):
            prefix = f"[{i}/{len(todo)}] {label}"
            if date in have:
                print(f"{prefix}: have {date}")
                continue
            part = Path(tmp) / f"{i}.pdf"
            if not fetch(url, part):
                print(f"{prefix}: FAILED  {url}")
                failed += 1
                continue
            date = created(part)
            if date in have:
                print(f"{prefix}: have {date}")
                continue
            shutil.move(part, ROOT / f"{date}-vab-berlin.pdf")
            have.add(date)
            added += 1
            print(f"{prefix}: saved {date}-vab-berlin.pdf")
            time.sleep(2)
    print(f"\n{added} new, {failed} failed, {len(have)} versions in {ROOT}")


if __name__ == "__main__":
    main()
