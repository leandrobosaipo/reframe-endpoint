# ===========================================
# 🐳 Dockerfile — reframe-endpoint (versão final)
# ===========================================

# Imagem base leve e estável
FROM python:3.11-slim

# Evita prompts interativos durante o build
ENV DEBIAN_FRONTEND=noninteractive

# Atualiza e instala dependências do sistema
# Inclui libs necessárias para OpenCV, FFmpeg e renderização de vídeo
# Compatível com Debian Trixie (python:3.11-slim)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgl1 \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Define diretório de trabalho
WORKDIR /app

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Define variáveis de ambiente padrões
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV MAX_WORKERS=2
ENV OUTPUT_PREFIX=reframes

# Define porta padrão (compatível com Easypanel)
EXPOSE 8080

# Healthcheck para monitoramento
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/', timeout=5)"

# Comando de inicialização com Gunicorn (padrão para produção Flask)
CMD ["gunicorn", "-w", "1", "-k", "sync", "-b", "0.0.0.0:8080", "--timeout", "600", "app:app"]
