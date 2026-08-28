# Build from the REPO ROOT so the bundle can be baked in:
#   docker build -f mcp_server/Dockerfile -t gdv-okf-mcp .
#
# The OKF bundle is copied into the image (immutable, versioned with the code).
# To ship updated content: refresh the bundle (scripts/refresh.sh), rebuild, redeploy.
# Alternative: mount the bundle as a volume and set BUNDLE_DIR (see mcp_server/README.md).
FROM python:3.12-slim

WORKDIR /app

COPY mcp_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server/server.py mcp_server/bundle.py ./
COPY bundles/gdv-stellungnahmen ./bundle

ENV BUNDLE_DIR=/app/bundle \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Container healthcheck hits the /health route the server exposes.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/health',timeout=4).status==200 else 1)"

CMD ["python", "server.py"]
