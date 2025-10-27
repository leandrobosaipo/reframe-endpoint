# ✅ Checklist de Deploy - Reframe Endpoint

## 🔴 ANTES DO PUSH PARA GITHUB

### Arquivos que foram criados/atualizados:
- [x] ✅ `.gitignore` - Criado para ignorar arquivos desnecessários
- [x] ✅ `.env.example` - Criado com todas as variáveis necessárias
- [x] ✅ `requirements.txt` - Adicionado `gunicorn`
- [x] ✅ `README.md` - Documentação completa criada
- [x] ✅ `REQUISITOS.md` - Documento de requisitos técnicos

## 📝 PRÓXIMOS PASSOS

### 1. Inicializar Repositório Git (se ainda não foi feito)

```bash
# Se você já está em um repositório git
git status

# Se não está, inicialize:
git init
```

### 2. Adicionar e commitar os arquivos

```bash
# Adicionar todos os arquivos
git add .

# Commit inicial
git commit -m "feat: adiciona documentação completa e prepara para deploy

- Adiciona .gitignore
- Adiciona .env.example
- Adiciona gunicorn ao requirements.txt
- Documenta API no README.md
- Cria documento de requisitos de produto"
```

### 3. Conectar com GitHub

```bash
# Adicionar remote (substitua com seu usuário)
git remote add origin https://github.com/SEU-USUARIO/reframe-endpoint.git

# Push inicial
git branch -M main
git push -u origin main
```

### 4. Configurar Easypanel

#### 4.1 Criar novo app
1. Acesse https://easypanel.io
2. Vá em "New App" → "Connect GitHub"
3. Selecione o repositório `reframe-endpoint`

#### 4.2 Adicionar variáveis de ambiente

No painel do Easypanel, adicione estas variáveis:

```bash
SPACES_REGION=nyc3
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
SPACES_BUCKET=seu-bucket
SPACES_KEY=SUA_ACCESS_KEY
SPACES_SECRET=SUA_SECRET_KEY
MAX_WORKERS=2
OUTPUT_PREFIX=reframes
```

**⚠️ IMPORTANTE:** Substitua `seu-bucket`, `SUA_ACCESS_KEY` e `SUA_SECRET_KEY` pelos seus valores reais.

#### 4.3 Configurar build
- O Easypanel detectará automaticamente:
  - `Procfile` → para rodar gunicorn
  - `nixpacks.toml` → para instalar ffmpeg
  - `requirements.txt` → para instalar dependências Python

#### 4.4 Deploy
- Clique em "Deploy"
- Aguarde o build (pode levar alguns minutos)
- Verifique os logs se houver erros

### 5. Testar o Deploy

#### 5.1 Health Check
```bash
curl https://seu-app.easypanel.app/
```

**Resposta esperada:**
```json
{
  "service": "reframe-endpoint",
  "queue_size": 0,
  "workers": 2
}
```

#### 5.2 Teste de Upload
```bash
curl -X POST https://seu-app.easypanel.app/v1/test/upload
```

**Resposta esperada:**
```json
{
  "status": "success",
  "message": "Upload funcionando!",
  "url": "https://...",
  "key": "test/..."
}
```

#### 5.3 Teste de Reframing
```bash
curl -X POST https://seu-app.easypanel.app/v1/video/reframe \
  -H "Content-Type: application/json" \
  -d '{
    "input_url": "https://example.com/video.mp4"
  }'
```

## 🐛 Troubleshooting

### Erro: Build Failed
- Verifique os logs no Easypanel
- Confirme que todos os arquivos foram commitados
- Verifique se `gunicorn` está em `requirements.txt`

### Erro: Port already in use
- O Easypanel gerencia a porta automaticamente
- Verifique se há outro container rodando

### Erro: Spaces upload failed
- Verifique as credenciais no Easypanel
- Teste o endpoint `/v1/test/upload`
- Confirme que o bucket tem permissões públicas

### Erro: ffmpeg not found
- Verifique `nixpacks.toml` no repositório
- FFmpeg deve ser instalado automaticamente

## 📊 Status Atual

### Arquivos que ficarão no Git:
```
✅ app.py
✅ reframe_mediapipe_falante_v7.py
✅ storage/spaces.py
✅ requirements.txt
✅ Procfile
✅ nixpacks.toml
✅ .gitignore
✅ .env.example
✅ README.md
✅ REQUISITOS.md
✅ CHECKLIST_DEPLOY.md
```

### Arquivos que NÃO ficarão no Git:
```
❌ .env (com credenciais)
❌ __pycache__/
❌ *.mp4 (vídeos)
❌ /tmp/
```

## 🎯 Conclusão

O projeto está **100% pronto** para deploy! Siga os passos acima para:

1. ✅ Fazer push para GitHub
2. ✅ Configurar no Easypanel
3. ✅ Fazer deploy público
4. ✅ Testar a API

**Tempo estimado:** 15-30 minutos

**Próxima iteração sugerida:**
- Adicionar CORS para controle de acesso
- Implementar Rate Limiting
- Adicionar autenticação via API keys
- Melhorar logging e monitoramento

---

✨ **Boa sorte com o deploy!**

