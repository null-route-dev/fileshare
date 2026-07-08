FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install poetry poetry-plugin-export
COPY pyproject.toml poetry.lock ./
RUN poetry export --without-hashes --format=requirements.txt --output requirements.txt --only main

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt
COPY . .
RUN rm pyproject.toml poetry.lock
ENV PYTHONPATH="/app"
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]