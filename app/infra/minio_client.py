"""MinIO object storage helpers for raw PDF access."""
import io

from minio import Minio

from app.infra.vault import AppSecrets

PAST_EXAMS_BUCKET = "past-exams"


def get_minio_client(secrets: AppSecrets) -> Minio:
    return Minio(
        "minio:9000",
        access_key=secrets.minio_access_key,
        secret_key=secrets.minio_secret_key,
        secure=False,  # dev-mode: no TLS within Docker network
    )


def upload_pdf(client: Minio, bucket: str, filename: str, data: bytes) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(bucket, filename, io.BytesIO(data), length=len(data))


def get_pdf_bytes(client: Minio, bucket: str, filename: str) -> bytes:
    response = client.get_object(bucket, filename)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
