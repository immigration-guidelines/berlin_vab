#!/usr/bin/env bash
# Download the VAB versions found after download-versions.py was first written.
# Run it in the folder that already holds the other PDFs: versions that are
# already there (same creation date inside the PDF) are skipped.
#
#   ./download-missing.sh
#
# Needs curl and pdfinfo (poppler-utils).

set -u
cd "$(dirname "$0")"
UA="Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
FDS="https://media.frag-den-staat.de/files/foi"

URLS=(
  # 2020-2021 versions from a second FragDenStaat request
  "$FDS/722222/20200617.pdf"
  "$FDS/722222/20200626.pdf"
  "$FDS/722222/20200907.pdf"
  "$FDS/722222/20201118.pdf"
  "$FDS/722222/20201218.pdf"
  "$FDS/722222/20210421.pdf"
  "$FDS/722222/20210521.pdf"
  "$FDS/715368/210927vab.pdf"
  # 03.12.2007, archived copy from einwanderer.net
  "https://web.archive.org/web/20240719161224id_/https://www.einwanderer.net/fileadmin/downloads/104a/berlin.pdf"
  # 28.02.2023, Studierendenwerk Berlin
  "https://www.stw.berlin/assets/sw-berlin/bereiche/international/Centre%20for%20Student%20Refugees%20Berlin/files/Verfahrenshinweise_fuer_Aufenthalt_in_Berlin.pdf"
)

created() { pdfinfo -isodates "$1" 2>/dev/null | awk '/^CreationDate/{print substr($2,1,10)}'; }

have=$(for f in *.pdf; do [ -e "$f" ] && created "$f"; done | sort -u)
tmp=$(mktemp -d .download.XXXXXX)
trap 'rm -rf "$tmp"' EXIT
new=0; failed=0; i=0

for url in "${URLS[@]}"; do
  i=$((i + 1))
  part="$tmp/$i.pdf"
  date=""
  for attempt in 1 2 3 4; do
    curl -sS -L -m 900 -A "$UA" -C - -o "$part" "$url"
    date=$(created "$part")
    [ -n "$date" ] && break
    sleep $((attempt * 10))
  done
  if [ -z "$date" ]; then
    echo "[$i/${#URLS[@]}] FAILED  $url"; failed=$((failed + 1)); continue
  fi
  if echo "$have" | grep -qx "$date"; then
    echo "[$i/${#URLS[@]}] have $date"; continue
  fi
  mv "$part" "$date-vab-berlin.pdf"
  have="$have"$'\n'"$date"
  new=$((new + 1))
  echo "[$i/${#URLS[@]}] saved $date-vab-berlin.pdf"
  sleep 2
done

echo
echo "$new new, $failed failed, $(ls *.pdf | wc -l) PDFs in $(pwd)"
