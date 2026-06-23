import uuid
from botocore.client import Config
from botocore.exceptions import ClientError
import boto3

from app.config import settings


def _make_client(for_presign: bool = False):
    endpoint = settings.S3_ENDPOINT_URL or None
    if for_presign and settings.MINIO_PUBLIC_URL:
        endpoint = settings.MINIO_PUBLIC_URL

    kwargs = {
        "service_name": "s3",
        "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        "config": Config(signature_version="s3v4"),
    }
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client(**kwargs)


def upload_resume(file_bytes: bytes, candidate_id: str) -> str:
    key = f"resumes/{candidate_id}/{uuid.uuid4()}.pdf"
    client = _make_client()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType="application/pdf",
    )
    return key


def get_presigned_url(key: str, expires: int = 3600) -> str:
    client = _make_client(for_presign=True)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )


def ensure_bucket_exists() -> None:
    client = _make_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            client.create_bucket(Bucket=settings.S3_BUCKET)
        else:
            raise
