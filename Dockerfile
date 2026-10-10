FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /workspace
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 1000 analyst \
    && chown analyst:analyst /workspace

COPY --chown=analyst:analyst . .
USER analyst

EXPOSE 8888
CMD ["python", "-m", "src.start_jupyter"]
