import boto3
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile
from os import getenv
from dotenv import load_dotenv

load_dotenv()

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = getenv('AWS_S3_BUCKET_NAME')

    async def upload_file(self, file: UploadFile) -> str:
        # Generate UUID for filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

        # Read file content
        file_content = await file.read()

        # Upload to S3
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=unique_filename,
            Body=file_content,
            ContentType=file.content_type
        )

        # Return the S3 URL
        return f"https://{self.bucket_name}.s3.{getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/{unique_filename}"

    def download_file(self, s3_url: str) -> Tuple[bytes, str]:
        """
        Download file from S3 and return file content and content type
        """
        # Extract the key from the S3 URL
        # URL format: https://bucket-name.s3.region.amazonaws.com/key
        key = s3_url.split('/')[-1]

        # Download file from S3
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=key
        )

        # Get file content and content type
        file_content = response['Body'].read()
        content_type = response.get('ContentType', 'application/octet-stream')

        return file_content, content_type

# Create a singleton instance
s3_service = S3Service()
