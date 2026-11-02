#!/usr/bin/env bash
# Reúne el estado de los contenedores de SaludCerca en diagnostico.txt para revisarlo.
# Uso:  cd ~/code/saludcerca && bash diagnostico.sh
cd "$(dirname "$0")"
OUT=diagnostico.txt
FILES="-f docker-compose.yml"
[ -n "$(docker compose -f docker-compose.yml -f docker-compose.pruebas.yml ps -q mailpit 2>/dev/null)" ] && FILES="$FILES -f docker-compose.pruebas.yml"
[ -n "$(docker compose -f docker-compose.yml -f docker-compose.floci.yml ps -q floci-az 2>/dev/null)" ] && FILES="$FILES -f docker-compose.floci.yml"
{
  echo "=== fecha: $(date)"
  echo "=== archivos compose detectados: $FILES"
  echo "=== docker compose ps"
  docker compose $FILES ps 2>&1
  echo; echo "=== /api/health"
  curl -s --max-time 5 http://localhost:8000/api/health 2>&1 || echo "API no responde en :8000"
  echo; echo "=== Mailpit (mensajes recibidos)"
  curl -s --max-time 5 "http://localhost:8025/api/v1/messages?limit=10" 2>&1 | head -c 3000 || echo "Mailpit no responde en :8025"
  echo; echo "=== logs api (últimas 120 líneas)"
  docker compose $FILES logs api --tail 120 2>&1
  echo; echo "=== logs mailpit / oidc (últimas 20)"
  docker compose $FILES logs mailpit oidc --tail 20 2>&1
} > "$OUT"
echo "Listo: $(pwd)/$OUT"
