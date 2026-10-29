FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code

# psycopg[binary] and Pillow come as wheels, so no compilers or libpq-dev are needed.
# DEV=1 (compose.dev.yml) adds the development tools: debugpy, pytest and ruff.
ARG DEV=0
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt && if [ "$DEV" = "1" ]; then pip install -r requirements-dev.txt; fi

# The app runs as an ordinary user, who owns /code (collectstatic writes staticfiles/ there)
RUN useradd --create-home --uid 1000 app && chown app:app /code
COPY --chown=app:app . .
USER app

# The hashed, compressed static files are part of the image. collectstatic reads the settings but needs
# neither the real secret key nor a database.
RUN SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["sh", "/code/docker-entrypoint.sh"]
CMD ["app"]
