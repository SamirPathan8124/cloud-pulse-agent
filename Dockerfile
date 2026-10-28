FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/ agent/
COPY infra/ infra/
RUN useradd --create-home app
USER app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "worker:app", "--app-dir", "agent", "--host", "0.0.0.0", "--port", "8000"]
