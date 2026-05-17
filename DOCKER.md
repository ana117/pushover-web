# Docker Deployment Guide

## Quick Start with Docker Compose

The easiest way to deploy Pushover Web is using Docker Compose:

### 1. Clone or prepare the project
```bash
cd pushover-web
```

### 2. Configure environment variables (optional)
```bash
cp .env.example .env
# Edit .env and set your own SECRET_KEY and timezone
```

### 3. Build and run
```bash
docker-compose up -d
```

The application will be available at `http://localhost:8000`

## Manual Docker Build

### Build the image
```bash
docker build -t pushover-web:latest .
```

### Run the container
```bash
docker run -d \
  --name pushover-web \
  -p 8000:8000 \
  -e SECRET_KEY="your-secret-key" \
  -e LOCAL_TIMEZONE_OFFSET_HOURS=7 \
  -v pushover-data:/app/instance \
  pushover-web:latest
```

## Environment Variables

- `SECRET_KEY`: Secret key for session security (generate a strong random key for production)
- `LOCAL_TIMEZONE_OFFSET_HOURS`: UTC offset for displaying timestamps (default: 7 for WIB)
- `DATABASE_PATH`: Path to SQLite database (default: /app/instance/pushover_web.sqlite3)

## Container Ports

- **8000**: Default HTTP port (configurable via docker-compose.yml or -p flag)

## Persistent Data

The SQLite database is stored in a Docker volume (`pushover-data`). This persists data even when the container is stopped or restarted.

### Backup database
```bash
docker run --rm -v pushover-data:/app/instance -v $(pwd):/backup \
  ubuntu cp /app/instance/pushover_web.sqlite3 /backup/pushover_web.sqlite3
```

### Restore database
```bash
docker run --rm -v pushover-data:/app/instance -v $(pwd):/backup \
  ubuntu cp /backup/pushover_web.sqlite3 /app/instance/pushover_web.sqlite3
```

## Health Check

The container includes a health check that pings the application every 30 seconds. You can see the health status with:

```bash
docker ps  # Shows (healthy) or (unhealthy) status
```

## Logs

View container logs:
```bash
docker-compose logs -f pushover-web
# or
docker logs -f pushover-web
```

## Production Recommendations

1. **Generate a strong SECRET_KEY**: Use `python -c "import secrets; print(secrets.token_hex(32))"`
2. **Use a reverse proxy**: Put Nginx or Caddy in front for SSL/TLS
3. **Set appropriate timezone**: Adjust `LOCAL_TIMEZONE_OFFSET_HOURS` for your location
4. **Scale workers**: Increase `--workers` in Dockerfile CMD if needed
5. **Monitor logs**: Set up log aggregation (ELK, Splunk, etc.)

## Stopping and Removing

```bash
# Stop the container
docker-compose down

# Remove volume (WARNING: deletes database)
docker-compose down -v
```

## Troubleshooting

### Container won't start
```bash
docker logs pushover-web
```

### Database permission issues
Ensure the `instance` directory has proper permissions:
```bash
docker-compose exec pushover-web chmod -R 755 /app/instance
```

### Can't connect to application
Check if port 8000 is already in use:
```bash
netstat -tlnp | grep 8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```
