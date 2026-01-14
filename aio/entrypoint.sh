#!/bin/bash
set -euo pipefail

get_env() {
  for var in "$@"; do
    value="${!var:-}"
    if [ -n "$value" ]; then
      echo "$value"
      return
    fi
  done
}

check_postgres() {
  local db_host db_user db_name db_pass
  db_host=$(get_env PGHOST)
  db_user=$(get_env PGUSER POSTGRES_USER)
  db_name=$(get_env PGDATABASE POSTGRES_DB)
  db_pass=$(get_env PGPASSWORD POSTGRES_PASSWORD)

  if [ -z "$db_host" ]; then
    return 0
  fi

  PGPASSWORD="$db_pass" psql -h "$db_host" -U "$db_user" -d "$db_name" -c '\q' >/dev/null 2>&1
}

until check_postgres; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "PostgreSQL is up - continuing..."

# Ensure Django sees the app URL values when running inside the AIO container.
# If APP_URL is provided, set PUBLIC_URL, FRONTEND_URL and CSRF_TRUSTED_ORIGINS
# only when they are not already set so user can override individually.
if [ -n "${APP_URL:-}" ]; then
  # Remove :80 or :443 from APP_URL if present
  APP_URL_NOPORT=$(echo "$APP_URL" | sed -E 's#(https?://[^:/]+)(:80|:443)?#\1#')
  if [ -z "${CSRF_TRUSTED_ORIGINS:-}" ]; then
    if [[ "$APP_URL" != "$APP_URL_NOPORT" ]]; then
      export CSRF_TRUSTED_ORIGINS="$APP_URL,$APP_URL_NOPORT"
    else
      export CSRF_TRUSTED_ORIGINS="$APP_URL"
    fi
  fi
  export PUBLIC_URL="${PUBLIC_URL:-$APP_URL}"
  export FRONTEND_URL="${FRONTEND_URL:-$APP_URL}"
  export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-$APP_URL}"
  echo "Exported PUBLIC_URL, FRONTEND_URL, CSRF_TRUSTED_ORIGINS from APP_URL: $APP_URL"
fi

# Apply Django migrations
echo "Running migrations..."
cd /code/backend/server
python3 manage.py migrate --noinput

# Create superuser if vars set
if [ -n "${DJANGO_ADMIN_USERNAME:-}" ] && [ -n "${DJANGO_ADMIN_PASSWORD:-}" ] && [ -n "${DJANGO_ADMIN_EMAIL:-}" ]; then
  echo "Creating superuser if needed..."
  python3 manage.py shell << EOF
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
User = get_user_model()
if not User.objects.filter(username='${DJANGO_ADMIN_USERNAME}').exists():
    u = User.objects.create_superuser(username='${DJANGO_ADMIN_USERNAME}', email='${DJANGO_ADMIN_EMAIL}', password='${DJANGO_ADMIN_PASSWORD}')
    EmailAddress.objects.create(user=u, email='${DJANGO_ADMIN_EMAIL}', verified=True, primary=True)
    print('Superuser created')
else:
    print('Superuser exists')
EOF
fi

# Download countries (best-effort)
python3 manage.py download-countries || true

exec "$@"
