import boto3
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Create MinIO bucket if it does not exist"

    def handle(self, *args, **options):
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            self.stdout.write(f'Bucket "{bucket_name}" already exists.')
        except Exception:
            s3_client.create_bucket(Bucket=bucket_name)
            self.stdout.write(self.style.SUCCESS(f'Bucket "{bucket_name}" created.'))
