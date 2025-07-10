FROM python:3.10-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      wkhtmltopdf libpangocairo-1.0-0 && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501

# Use shell form so $PORT (an env var Render provides) is substituted
CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0