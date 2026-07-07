# FileShare

**FileShare** is an educational REST API designed to provide practical experience with the Django ecosystem. This project focuses on building a robust backend solution for secure file storage and sharing. It incorporates asynchronous task processing via Celery, integrates with S3-compatible object storage, and leverages a modern toolchain to streamline development and deployment.

## Features (planned)

- User authentication with JWT (SimpleJWT)
- File upload/download with S3-compatible storage (MinIO)
- Asynchronous file processing via Celery + Redis
- File sharing with other users and temporary TTL links
- Admin panel for data management
- Fully containerised with Docker Compose (PostgreSQL, Redis, MinIO)
- Tested with pytest, linted with ruff

## Tech Stack (planned)

| Component          | Technology                         |
|--------------------|------------------------------------|
| Language           | Python 3.12.5                      |
| Web Framework      | Django 5.0.7 + DRF 3.15.2          |
| Database           | PostgreSQL 16.3                    |
| Cache / Broker     | Redis 7.2.5                        |
| Async Tasks        | Celery 5.4.0                       |
| Object Storage     | MinIO (RELEASE.2024-06-22)         |
| Storage Adapter    | django-storages 1.14.4 + boto3     |
| Testing            | pytest 8.2.2                       |
| Environment        | Docker Compose, Poetry, python-dotenv |