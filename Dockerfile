FROM python:3.12-slim

WORKDIR /app

RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --no-create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

ENV PYTHONUNBUFFERED=1

USER appuser

CMD ["python", "-m", "src.main", "--loop"]
