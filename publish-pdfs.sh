#!/usr/bin/env bash
# Publish the source PDFs to the PDF repository (github.com/brinlyau/vabpdfs).
#
# Copies every PDF from this folder plus the download scripts into a clone of
# the PDF repository, writes that repository's README (with a list of the
# versions), and commits. Nothing is pushed unless --push is given.
#
#   ./publish-pdfs.sh                      # clone to ../vabpdfs if needed, copy, commit
#   ./publish-pdfs.sh /path/to/vabpdfs     # use an existing clone
#   ./publish-pdfs.sh --push               # also push the commit
#
# Needs git and pdfinfo (poppler-utils).

set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
REMOTE="https://github.com/brinlyau/vabpdfs.git"
TEXT_REPO_URL="${TEXT_REPO_URL:-}"       # set this to link the text-history repository in the README

push=0; dest=""
for arg in "$@"; do
  case "$arg" in
    --push) push=1 ;;
    -h|--help) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) dest="$arg" ;;
  esac
done
dest="${dest:-$SRC/../vabpdfs}"

if [ ! -d "$dest/.git" ]; then
  echo "Cloning $REMOTE into $dest (about 400 MB)"
  git clone "$REMOTE" "$dest"
fi
dest="$(cd "$dest" && pwd)"
if [ -n "$(git -C "$dest" status --porcelain)" ]; then
  echo "error: $dest has uncommitted changes; commit or discard them first" >&2
  exit 1
fi

# Copy PDFs under their dated names. A PDF whose name does not match the date
# inside it is renamed on the way, and unreadable files are refused.
copied=0
for pdf in "$SRC"/*.pdf; do
  date=$(pdfinfo -isodates "$pdf" 2>/dev/null | awk '/^CreationDate/{print substr($2,1,10)}')
  if [ -z "$date" ]; then
    echo "skip unreadable $(basename "$pdf")" >&2
    continue
  fi
  target="$dest/$date-vab-berlin.pdf"
  if [ ! -e "$target" ]; then
    cp "$pdf" "$target"
    copied=$((copied + 1))
    echo "add $date-vab-berlin.pdf"
  fi
done

cp "$SRC/download-versions.py" "$SRC/download-missing.sh" "$dest/"

# README for the PDF repository
{
  cat <<EOF
# VAB Berlin – source PDFs

Every version we could find of the *Verfahrenshinweise zum Aufenthalt in Berlin* (VAB), the Berlin immigration office's internal guidance on residence, asylum and naturalisation law. The office publishes it as one PDF and replaces it several times a year without keeping old versions online.

Each file is named \`YYYY-MM-DD-vab-berlin.pdf\` after the day the PDF was generated. The files are unmodified.

EOF
  if [ -n "$TEXT_REPO_URL" ]; then
    printf 'The text of every version, as a git history that shows what changed between them, is at <%s>.\n\n' "$TEXT_REPO_URL"
  fi
  cat <<'EOF'
## Adding a version

If you have a version that is not listed below, open a pull request that adds the PDF to this repository.

- Add the PDF unmodified, as it was published.
- Name it `YYYY-MM-DD-vab-berlin.pdf`, using the date printed on its first page ("Dieses PDF wurde erstellt am", or "Erstellt am" in versions before 2011).
- Say in the pull request where the file came from.

After the pull request is merged, the text history is regenerated from the full set of PDFs.

## Downloading from the original sources

`download-versions.py` fetches the PDFs from where they were found: the Landesamt für Einwanderung, the Wayback Machine, freedom-of-information releases on FragDenStaat, and copies kept by refugee councils. It needs `curl` and `pdfinfo` (poppler-utils) and skips versions already in the folder.

## Versions

EOF
  ls "$dest" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}-vab-berlin\.pdf$' | awk '
    { y = substr($0, 1, 4); d[y] = d[y] " " substr($0, 9, 2) "." substr($0, 6, 2) "."; n[y]++; total++ }
    END {
      printf "%d versions.\n\n| Year | Versions | Dates |\n|---|---|---|\n", total
      for (y = 2000; y < 2100; y++) if (n[y]) printf "| %d | %d |%s |\n", y, n[y], d[y]
    }'
} > "$dest/README.md"

git -C "$dest" add -A
if git -C "$dest" diff --cached --quiet; then
  echo "Nothing to commit: $dest is already up to date."
else
  git -C "$dest" commit -q -m "Add $copied PDF(s), update scripts and README"
  echo "Committed in $dest: $(git -C "$dest" log --oneline -1)"
fi

if [ "$push" = 1 ]; then
  git -C "$dest" push
else
  echo "Not pushed. Review with: git -C $dest show --stat   then: git -C $dest push"
fi
