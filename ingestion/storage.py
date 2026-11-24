import logging
import os
from pathlib import Path
from typing import Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def save(self, key: str, content: bytes) -> str: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, key: str, content: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)


class S3Storage:
    def __init__(self, bucket: str, endpoint_url: str | None, region: str) -> None:
        self.bucket = bucket
        config = Config(
            retries={"max_attempts": 5, "mode": "standard"},
            s3={"addressing_style": "path"} if endpoint_url else {},
        )
        self.client = boto3.client(
            "s3", endpoint_url=endpoint_url, region_name=region, config=config
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
                raise  # e.g. 403: wrong credentials, do not hide it
            logger.info("Bucket %s not found, creating it", self.bucket)
            self.client.create_bucket(Bucket=self.bucket)

    def save(self, key: str, content: bytes) -> str:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=content, ContentType="application/gzip"
        )
        return f"s3://{self.bucket}/{key}"


def build_storage() -> Storage:
    backend = os.environ.get("STORAGE_BACKEND", "local")

    if backend == "local":
        return LocalStorage(Path(os.environ.get("LOCAL_DATA_DIR", "data")))

    if backend == "s3":
        storage = S3Storage(
            bucket=os.environ.get("S3_BUCKET", "velib-raw"),
            endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
            region=os.environ.get("S3_REGION", "us-east-1"),
        )
        if os.environ.get("S3_CREATE_BUCKET", "false").lower() == "true":
            storage.ensure_bucket()
        return storage

    raise ValueError(f"STORAGE_BACKEND must be 'local' or 's3', got {backend!r}")