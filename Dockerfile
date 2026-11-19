# Production image for managed Docker hosts (Render, Railway).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

# formulario.py does `import git` at module level, and GitPython refuses to
# initialize without the git executable on PATH.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
      -r requirements.txt \
      "streamlit==1.45.0" \
      gitpython \
      pillow

COPY . .

# SQLite database and local backups live here; mount a disk/volume on this path.
RUN mkdir -p /app/persistent_data

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c 'import os,sys,urllib.request; p=os.environ.get("PORT","8501"); sys.exit(0 if urllib.request.urlopen("http://127.0.0.1:%s/_stcore/health" % p, timeout=4).read().strip()==b"ok" else 1)'

CMD ["sh", "-c", "exec streamlit run formulario.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true --server.enableCORS=true --server.enableXsrfProtection=true --browser.gatherUsageStats=false"]
