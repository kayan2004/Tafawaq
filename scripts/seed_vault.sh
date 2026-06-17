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
  jwt_secret="${JWT_SECRET:-dev-jwt-secret-change-in-prod}" \
  elevenlabs_api_key="${ELEVEN_LABS_API_KEY:-${ELEVENLABS_API_KEY:-placeholder-set-real-key}}" \
  resend_api_key="${RESEND_API_KEY:-}" \
  reset_password_from_email="${RESET_PASSWORD_FROM_EMAIL:-onboarding@resend.dev}" \
  reset_password_token_secret="${RESET_PASSWORD_TOKEN_SECRET:-dev-reset-password-secret-change-in-prod}" \
  langfuse_public_key="${LANGFUSE_PUBLIC_KEY:-pk-lf-dev0000-0000-0000-0000-000000000000}" \
  langfuse_secret_key="${LANGFUSE_SECRET_KEY:-sk-lf-dev0000-0000-0000-0000-000000000000}"
  # ^ Dev defaults match the LANGFUSE_INIT_PROJECT_*_KEY values docker-compose.yml
  # passes to the langfuse service, so this key pair works out of the box.
  # For a real deployment: run Langfuse once, create a project, copy its API
  # keys from Settings -> API Keys, and override LANGFUSE_PUBLIC_KEY /
  # LANGFUSE_SECRET_KEY (here and in docker-compose.yml) before redeploying.

echo "[vault-seed] Secrets written successfully."
