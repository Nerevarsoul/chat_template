FROM python:3.11.2-slim-bullseye

RUN apt-get update && \
    apt-get install -y gcc=4:10.2.1-1 python3-dev && \
    pip install poetry==1.4.1 poetry-core==1.5.2

WORKDIR /src

COPY pyproject.toml poetry.lock .

RUN poetry install

COPY . .

ENV PYTHONPATH=/src

EXPOSE 8081

CMD ["poetry", "run", "python", "app/main.py"]
