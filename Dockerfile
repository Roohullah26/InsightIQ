# InsightIQ container image for Hugging Face Spaces (Docker SDK).
# Spaces run containers as UID 1000 and route traffic to port 7860.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install dependencies first so this layer is cached between code-only rebuilds.
COPY --chown=user requirements.txt .
RUN pip install --user --upgrade -r requirements.txt

COPY --chown=user . .
RUN mkdir -p "$HOME/app/data"

ENV INSIGHTIQ_DATA_DIR=/home/user/app/data \
    FORWARDED_ALLOW_IPS=*
EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
