# Dockerfile Fixes and Improvements

## Completed Tasks
- [x] Fixed deprecated `apt-key add` command by replacing with `gpg --dearmor`
- [x] Added proper GPG key handling for Microsoft SQL Server ODBC driver
- [x] Improved curl commands with `-fsSL` flags for better error handling
- [x] Added production environment variables (DEBUG=False, SECRET_KEY, ALLOWED_HOSTS)
- [x] Ensured collectstatic runs with proper environment settings
- [x] Fixed apt sources.list to include signed-by keyring reference for proper GPG verification

## Current Dockerfile Status
The Dockerfile now properly:
- Installs Microsoft ODBC Driver 17 for SQL Server using modern GPG key methods
- Sets production-appropriate environment variables
- Collects static files correctly
- Runs with gunicorn for production deployment

## Future Improvements
- [ ] Consider using multi-stage build to reduce final image size
- [ ] Add health check endpoint for container orchestration
- [ ] Optimize Python dependencies installation (use requirements.txt caching)
- [ ] Add proper SECRET_KEY management (use environment variables or secrets)
- [ ] Consider adding database migration step in Dockerfile
- [ ] Add proper user permissions for security (non-root user)

## Testing
- [ ] Test Docker build locally (requires Docker Desktop running)
- [ ] Test deployment on Render platform
- [ ] Verify database connectivity in containerized environment
