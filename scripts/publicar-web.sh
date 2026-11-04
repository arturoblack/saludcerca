#!/usr/bin/env bash
# Publica frontend/dist en el sitio web estático de Storage. Uso: scripts/publicar-web.sh <cuenta>
# Los archivos con hash se guardan un año en caché; index.html y sw.js se revalidan siempre.
set -euo pipefail
CUENTA="$1"
cd "$(dirname "$0")/../frontend/dist"
az storage blob service-properties update --account-name "$CUENTA" --auth-mode login \
  --static-website --index-document index.html --404-document index.html -o none
az storage blob upload-batch --account-name "$CUENTA" --auth-mode login -d '$web' -s . --overwrite \
  --pattern 'assets/*' --content-cache-control 'public, max-age=31536000, immutable' -o none
for f in $(find . -maxdepth 1 -type f -printf '%f\n'); do
  az storage blob upload --account-name "$CUENTA" --auth-mode login -c '$web' -f "$f" -n "$f" --overwrite \
    --content-cache-control 'no-cache' -o none
done
