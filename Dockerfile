# Dockerfile para Reframe Endpoint
FROM python:3.11-slim

# Instalar dependências do sistema (FFmpeg e OpenCV)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivo de dependências
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p /tmp /app/storage

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expor porta (padrão 8080)
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/')"

# Comando de inicialização (Gunicorn)
CMD ["gunicorn", "-w", "1", "-k", "sync", "-b", "0.0.0.0:8080", "--timeout", "600", "app:app"]
