# 🐳 Deploy com Docker - Reframe Endpoint

## 📦 O Que Foi Adicionado

Para usar Docker no Easypanel, foram adicionados os seguintes arquivos:

### 1. **Dockerfile**
- Base: Python 3.11 slim
- Instala FFmpeg e dependências do OpenCV
- Instala todas as dependências Python
- Configura Gunicorn para produção
- Healthcheck integrado

### 2. **.dockerignore**
- Otimiza o build ignorando arquivos desnecessários
- Reduz o tamanho da imagem Docker
- Acelera upload ao registry

### 3. **docker-compose.yml**
- Para testar localmente o mesmo ambiente
- Configura todas as variáveis de ambiente
- Mapeia volumes para persistência

---

## 🚀 Como o Easypanel Usa o Docker

### Detecção Automática

O Easypanel detecta automaticamente o `Dockerfile` e o usa preferencialmente sobre Nixpacks.

**Ordem de prioridade:**
1. ✅ **Dockerfile** (se existir) → Usa este
2. ⚙️ Nixpacks (Procfile + nixpacks.toml)

---

## 🧪 Testar Localmente com Docker

### Opção 1: Docker Compose (Recomendado)

```bash
# 1. Copiar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# 2. Build e iniciar
docker-compose up --build

# 3. Testar
curl http://localhost:8080/
```

### Opção 2: Docker Build Direto

```bash
# 1. Build da imagem
docker build -t reframe-endpoint .

# 2. Rodar container
docker run -d \
  -p 8080:8080 \
  -e SPACES_KEY=sua-key \
  -e SPACES_SECRET=sua-secret \
  -e SPACES_BUCKET=cod5 \
  --name reframe-endpoint \
  reframe-endpoint

# 3. Testar
curl http://localhost:8080/
```

### Opção 3: Teste Rápido

```bash
# Build + Run em um comando
docker build -t reframe-endpoint . && \
docker run -p 8080:8080 --env-file .env reframe-endpoint
```

---

## 📊 Vantagens do Dockerfile

### ✅ Maior Controle
- Define exatamente quais pacotes instalar
- Versão específica do Python (3.11)
- Dependências de sistema explicitas

### ✅ Otimização
- Base slim (image menor)
- Cache de layers
- Build mais rápido em deploys subsequentes

### ✅ Consistência
- Mesmo ambiente em dev/prod
- Sem surpresas de dependências
- Testável localmente

### ✅ Healthcheck
- Monitora saúde do container
- Restart automático se falhar
- Debugging mais fácil

---

## 🔧 Configuração do Easypanel

### Ao Criar o App

1. **Easypanel detecta** o Dockerfile automaticamente
2. **Faz build** da imagem Docker
3. **Deploy** o container

### Configurações Importantes

**Porta:** O Dockerfile expõe a porta `8080`, mas o Easypanel configura automaticamente.

**Variáveis de Ambiente:** Configure no painel do Easypanel (mesmo processo do guia principal).

**Recursos:** Defina CPU/RAM conforme necessário (recomendado: 2GB RAM mínimo).

---

## 📝 Estrutura do Dockerfile

```dockerfile
# Base
FROM python:3.11-slim

# Dependências de sistema
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6...

# Dependências Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código
COPY . .

# Comando
CMD ["gunicorn", "...", "app:app"]
```

---

## 🐛 Troubleshooting Docker

### Erro: "unable to locate package ffmpeg"
**Causa:** Cache de apt desatualizado  
**Solução:** O Dockerfile já faz `apt-get update` antes de instalar

### Erro: "ModuleNotFoundError: cv2"
**Causa:** Bibliotecas do OpenCV não instaladas  
**Solução:** Dockerfile instala `libsm6 libxext6 libxrender-dev libgomp1`

### Erro: "port already in use"
**Causa:** Porta 8080 já em uso  
**Solução:** Mude a porta no docker-compose.yml ou pare outros containers

### Erro: "out of memory"
**Causa:** Container sem memória suficiente  
**Solução:** Aumente recursos no Easypanel (mínimo 2GB RAM)

### Build muito lento
**Causa:** Baixando muitas dependências  
**Solução:** Use cache do Docker (`docker build --cache-from reframe-endpoint`)

---

## 🔍 Verificar Build Local

```bash
# Ver tamanho da imagem
docker images reframe-endpoint

# Verificar layers
docker history reframe-endpoint

# Inspecionar imagem
docker inspect reframe-endpoint

# Ver logs
docker logs reframe-endpoint
```

---

## 📊 Comparação: Nixpacks vs Dockerfile

| Aspecto | Nixpacks | Dockerfile |
|---------|----------|------------|
| Configuração | Procfile + nixpacks.toml | Dockerfile |
| Flexibilidade | Limitada | Alta |
| Controle | Automático | Manual |
| Tamanho | Variável | Otimizado |
| Depuração | Difícil | Fácil |
| Teste Local | Limitado | Completo |

**Recomendação:** Use Dockerfile para mais controle e testabilidade.

---

## 🚀 Próximos Passos

1. **Testar localmente** com docker-compose
2. **Push para GitHub** (Dockerfile já commitado)
3. **Deploy no Easypanel** (detecção automática do Dockerfile)
4. **Monitorar logs** no painel do Easypanel

---

## 📚 Referências

- **Dockerfile:** Veja `Dockerfile` no repositório
- **Docker Compose:** Veja `docker-compose.yml`
- **Guia Easypanel:** Veja `GUIA_EASYPANEL.md`
- **Documentação Docker:** https://docs.docker.com/

---

✨ **Deploy mais confiável com Docker!**
