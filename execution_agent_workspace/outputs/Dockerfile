FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "build_agent/main.py", "<repository_full_name>", "<sha>", "<root_path>"]