# Aus dem DIENST-ORDNER bauen, damit der Wissensbestand mit ins Image kommt:
#   docker build -f mcp_server/Dockerfile -t foerderrecht-mcp .
#
# Der Bestand wird ins Image kopiert (unveränderlich, mit dem Code versioniert).
# Für neuen Inhalt: wissen/ neu bauen, Image neu bauen, neu deployen.
# Alternative: wissen/ als Volume mounten und WISSEN_DIR setzen (siehe mcp_server/README.md).
FROM python:3.12-slim

WORKDIR /app

COPY mcp_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server/server.py mcp_server/bundle.py ./
COPY wissen ./wissen

ENV WISSEN_DIR=/app/wissen \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/health',timeout=4).status==200 else 1)"

CMD ["python", "server.py"]
