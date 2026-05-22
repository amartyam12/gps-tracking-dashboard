FROM python:3.12-slim

WORKDIR /app

# Install Python deps
# (No lockfile in repo; keep it simple)
RUN pip install --no-cache-dir \
    flask \
    python-dotenv \
    langchain-groq \
    langchain-core

# Copy app source
COPY . /app

ENV PYTHONUNBUFFERED=1

# The UI runs on localhost:5000 inside container
EXPOSE 5000

# Use .env file if you mount/copy it; otherwise provide GROQ_API_KEY and CHAT_MODEL as env vars.
CMD ["python3", "ui.py"]

