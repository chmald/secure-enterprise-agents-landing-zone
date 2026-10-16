FROM python:3.12-slim
WORKDIR /app
COPY src/demo-console/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/demo-console/ /app/
COPY config/profiles/ /config/profiles/
COPY infra/monitoring/queries/ /queries/
RUN useradd --uid 10001 --create-home console
USER 10001
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
