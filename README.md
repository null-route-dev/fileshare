# FileShare — File Storage API

**FileShare** is an educational REST API designed to provide practical experience with the Django ecosystem. This project focuses on building a robust backend solution for secure file storage and sharing. It incorporates asynchronous task processing via Celery, integrates with S3-compatible object storage, and leverages a modern toolchain to streamline development and deployment.

## Tech Stack
- Python
- Django
- DRF
- PostgreSQL
- Redis
- MinIO (S3-compatible storage)
- django-storages + boto3
- Celery
- Pillow
- Pytest
- JWT Authentication (SimpleJWT)
- Ruff

## Features

### Implemented
- User registration and authentication (JWT-based)
- File upload, download, list, and delete
- S3-compatible storage integration (MinIO)
- File ownership and access control
- Admin panel for data management
- Async database operations
- Comprehensive test coverage
- Docker containerization
- CI/CD pipeline (GitHub Actions)
- Linting with Ruff

### Planned
- File sharing with other users (SharedAccess)
- Temporary TTL links
- File filtering and search

## API Endpoints

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/token/` | Login — get JWT tokens |
| POST | `/api/token/refresh/` | Refresh JWT access token |
| POST | `/api/users/register/` | Register new user |

### Protected (JWT required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/profile/` | Get current user profile |
| PUT/PATCH | `/api/users/profile/` | Update user profile |
| GET | `/api/files/` | List all user files |
| POST | `/api/files/` | Upload a file |
| GET | `/api/files/{id}/` | Get file metadata |
| GET | `/api/files/{id}/download/` | Download a file |
| PUT/PATCH | `/api/files/{id}/` | Update file metadata |
| DELETE | `/api/files/{id}/` | Delete a file |

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

1. Register a user: `POST /api/users/register/`
2. Login: `POST /api/token/` — receive `access_token` and `refresh_token`
3. Include token in requests: `Authorization: Bearer <access_token>`
4. Refresh token when expired: `POST /api/token/refresh/`

## Installation

### Local Development

```bash
# Clone repository
git clone https://github.com/null-route-dev/fileshare.git
cd fileshare

# Install Poetry
pip install poetry

# Install dependencies
poetry install

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
# Generate SECRET_KEY:
poetry run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Start backing services (PostgreSQL, Redis, MinIO)
docker-compose up -d db redis minio

# Run migrations
poetry run python manage.py migrate

# Create MinIO bucket
poetry run python manage.py create_minio_bucket

# Create superuser (admin panel access)
poetry run python manage.py createsuperuser

# Start development server
poetry run python manage.py runserver
```

### Docker Development

```bash
# Clone repository
git clone https://github.com/null-route-dev/fileshare.git
cd fileshare

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
# Generate SECRET_KEY:
poetry run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Build and run with Docker Compose
docker-compose up -d --build

# Create superuser (admin panel access)
docker exec -it fileshare-web python manage.py createsuperuser

# Check application health
curl http://localhost:8000/api/

# Check logs
docker-compose logs -f web

# Stop
docker-compose down

# Stop and remove volumes (data)
docker-compose down -v
```

## Testing

```bash
# Run all tests
poetry run pytest -v

# Run specific test file
poetry run pytest files/tests.py -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | required |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `DB_NAME` | Database name | `fileshare` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `DB_HOST` | Database host | `db` (Docker) / `localhost` (local) |
| `DB_PORT` | Database port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `AWS_ACCESS_KEY_ID` | MinIO access key | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | MinIO secret key | `minioadmin` |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket name | `media` |
| `AWS_S3_ENDPOINT_URL` | MinIO endpoint | `http://minio:9000` |

## Linting

```bash
# Check code style
poetry run ruff check .

# Auto-fix issues
poetry run ruff check --fix .

# Check formatting
poetry run ruff format --check .

# Auto-format code
poetry run ruff format .
```