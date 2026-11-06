#!/usr/bin/env bash
# Load credentials injected by the Vault Agent into the process environment,
# then exec the container command. Local/docker-compose runs skip when the
# secrets file is absent.
set -euo pipefail

VAULT_SECRETS_FILE="${VAULT_SECRETS_FILE:-/vault/secrets/secrets.txt}"
PARSED_SECRETS_FILE="${PARSED_SECRETS_FILE:-/tmp/vault_env}"

parse_vault_secrets() {
  local source_file="$1"
  local dest_file="$2"

  if grep -q "data: map" "${source_file}"; then
    # Go-map dump from the injector: data: map[KEY1:val1 KEY2:val2]
    grep "^data: map" "${source_file}" \
      | sed 's/.*data: map\[//; s/\].*$//' \
      | sed 's/^\([A-Z][A-Z0-9_]*\):/\1=/; s/ \([A-Z][A-Z0-9_]*\):/\n\1=/g' \
      | grep '=' > "${dest_file}"
  else
    # Already KEY=VALUE (or KEY:VALUE) lines
    sed -E 's/^[[:space:]]*//; /^$/d; /^#/d; s/^([A-Z][A-Z0-9_]*)[:=]/\1=/' \
      "${source_file}" > "${dest_file}"
  fi
}

export_vault_secrets() {
  local file="$1"
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ -z "${line}" || "${line}" == \#* ]] && continue
    [[ "${line}" != *=* ]] && continue
    local key="${line%%=*}"
    local value="${line#*=}"
    # Strip surrounding quotes if present
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    export "${key}=${value}"
  done < "${file}"
}

if [[ -f "${VAULT_SECRETS_FILE}" ]]; then
  echo "Loading secrets from ${VAULT_SECRETS_FILE}"
  parse_vault_secrets "${VAULT_SECRETS_FILE}" "${PARSED_SECRETS_FILE}"
  export_vault_secrets "${PARSED_SECRETS_FILE}"
else
  echo "Vault secrets file not found at ${VAULT_SECRETS_FILE}; using process environment"
fi

exec "$@"
