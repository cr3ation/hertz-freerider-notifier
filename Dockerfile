FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /code
RUN apt-get update && apt-get install -y build-essential libpq-dev --no-install-recommends &&         pip install --upgrade pip
COPY requirements.txt /code/
RUN pip install -r requirements.txt
COPY . /code/

# Copy and make entrypoint scripts executable

COPY entrypoint.sh /code/entrypoint.sh
COPY entrypoint-worker-debug.sh /code/entrypoint-worker-debug.sh
COPY entrypoint-worker.sh /code/entrypoint-worker.sh
RUN chmod +x /code/entrypoint.sh
RUN chmod +x /code/entrypoint-worker-debug.sh
RUN chmod +x /code/entrypoint-worker.sh

# Set the entrypoint
ENTRYPOINT ["bash", "/code/entrypoint.sh"]
