# ===========================================
# 🐳 Dockerfile — reframe-endpoint (versão final)
# ===========================================

# Imagem base leve e estável
FROM python:3.11-slim

# Evita prompts interativos durante o build
ENV DEBIAN_FRONTEND=noninteractive

# Atualiza e instala dependências do sistema
# Inclui libs necessárias para OpenCV, FFmpeg e renderização de vídeo
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
ENV MAX_WORKERS=2
ENV OUTPUT_PREFIX=reframes

# Define porta padrão (ajuste se necessário)
EXPOSE 8000

# Comando padrão de execução
# (ajuste conforme o nome do arquivo principal Python)
CMD ["python", "main.py"]
