#!/bin/sh
# Seed Vault KV v2 with application secrets.
# Run once by the vault-seed container before the API boots.
# Real secret values should be passed via environment variables.
# Dev defaults are safe for local development only.

set -e

echo "[vault-seed] Writing secrets to Vault at ${VAULT_ADDR}..."

vault kv put \
  -address="${VAULT_ADDR}" \
  secret/lebanese-math-coach \
  anthropic_api_key="${ANTHROPIC_API_KEY:-placeholder-set-real-key}" \
  voyage_api_key="${VOYAGE_API_KEY:-placeholder-set-real-key}" \
  db_url="postgresql+asyncpg://postgres:devpassword@db:5432/lebanese_math" \
  db_password="devpassword" \
  minio_access_key="${MINIO_ACCESS_KEY:-minioadmin}" \
  minio_secret_key="${MINIO_SECRET_KEY:-minioadmin}" \
  jwt_secret="${JWT_SECRET:-dev-jwt-secret-change-in-prod}"

echo "[vault-seed] Secrets written successfully."
