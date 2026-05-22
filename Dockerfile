FROM python:3.12-slim

WORKDIR /app

COPY . /app

# Install optional dependencies (none required for offline parsing)
# If you want LLM calls, install openai client:
# RUN pip install --no-cache-dir openai

CMD ["python", "main.py", "--log", "sample.log"]

