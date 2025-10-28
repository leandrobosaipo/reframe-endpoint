# 🧪 Guia de Teste do Servidor Reframe-Endpoint

## 📍 URL do Servidor
**URL Pública**: `https://codigo5-reframe-endpoint.ujhifl.easypanel.host`

## 🚨 Status Atual
- **Status**: ❌ Serviço não está rodando (Erro 502)
- **Problema**: "Service is not reachable"
- **Causa**: Aplicação não está respondendo ou há erro de configuração

## 🔍 Como Testar (Quando Funcionando)

### 1. **Health Check** (Endpoint Principal)
```bash
# Teste básico
curl https://codigo5-reframe-endpoint.ujhifl.easypanel.host/

# Resposta esperada:
{
  "service": "reframe-endpoint",
  "queue_size": 0,
  "workers": 2,
  "version": "1.0.0"
}
```

### 2. **Teste de Autenticação**
```bash
# Teste sem token (deve falhar se API_TOKEN estiver configurado)
curl -X POST https://codigo5-reframe-endpoint.ujhifl.easypanel.host/v1/video/reframe \
  -H "Content-Type: application/json" \
  -d '{"input_url": "https://exemplo.com/video.mp4"}'

# Teste com token válido
curl -X POST https://codigo5-reframe-endpoint.ujhifl.easypanel.host/v1/video/reframe \
  -H "Content-Type: application/json" \
  -H "X-Api-Token: SEU_TOKEN_AQUI" \
  -d '{"input_url": "https://exemplo.com/video.mp4"}'
```

### 3. **Listar Jobs**
```bash
curl -H "X-Api-Token: SEU_TOKEN_AQUI" \
  https://codigo5-reframe-endpoint.ujhifl.easypanel.host/v1/video/jobs
```

### 4. **Verificar Status de um Job**
```bash
curl -H "X-Api-Token: SEU_TOKEN_AQUI" \
  https://codigo5-reframe-endpoint.ujhifl.easypanel.host/v1/video/status/job_abc123def4
```

### 5. **Download de Vídeo Processado**
```bash
curl -H "X-Api-Token: SEU_TOKEN_AQUI" \
  https://codigo5-reframe-endpoint.ujhifl.easypanel.host/v1/video/download/job_abc123def4
```

## 🛠️ Troubleshooting - Erro 502

### Possíveis Causas:

#### 1. **Aplicação não está rodando**
- Verificar se o container está ativo no Easypanel
- Verificar logs de deploy

#### 2. **Erro de configuração**
- Verificar se as variáveis de ambiente estão configuradas
- Verificar se o Gunicorn está configurado corretamente

#### 3. **Problema de dependências**
- Verificar se o build foi concluído com sucesso
- Verificar se todas as dependências foram instaladas

#### 4. **Problema de porta**
- Verificar se a aplicação está rodando na porta 8080
- Verificar se o Easypanel está configurado para a porta correta

## 🔧 Passos para Resolver

### 1. **Verificar Status no Easypanel**
- Acesse o painel do Easypanel
- Vá para a aba **Deployments**
- Verifique se o último deploy foi bem-sucedido
- Verifique os logs de build

### 2. **Verificar Logs da Aplicação**
- Na aba **Logs** do Easypanel
- Procure por erros de inicialização
- Verifique se o Gunicorn está iniciando

### 3. **Verificar Variáveis de Ambiente**
- Na aba **Environment** do Easypanel
- Confirme se todas as variáveis estão configuradas:
  ```bash
  SPACES_REGION=nyc3
  SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com
  SPACES_BUCKET=codigo5
  SPACES_KEY=***sua_chave***
  SPACES_SECRET=***seu_segredo***
  API_TOKEN=seu_token_seguro
  MAX_WORKERS=2
  OUTPUT_PREFIX=reframes
  ```

### 4. **Verificar Configuração de Porta**
- Confirme se a aplicação está configurada para porta 8080
- Verifique se o Easypanel está mapeando a porta correta

### 5. **Reiniciar o Serviço**
- No Easypanel, reinicie o serviço
- Aguarde alguns minutos para o restart completo

## 📋 Checklist de Verificação

- [ ] Build do Docker concluído com sucesso
- [ ] Container está rodando
- [ ] Variáveis de ambiente configuradas
- [ ] Aplicação responde na porta 8080
- [ ] Gunicorn está iniciando sem erros
- [ ] Logs não mostram erros críticos

## 🎯 Próximos Passos

1. **Verificar logs no Easypanel** para identificar o problema específico
2. **Corrigir configurações** conforme necessário
3. **Reiniciar o serviço** após correções
4. **Testar novamente** com os comandos acima

## 📞 Comandos de Teste Rápido

```bash
# Teste básico de conectividade
curl -I https://codigo5-reframe-endpoint.ujhifl.easypanel.host/

# Teste com timeout
curl --max-time 10 https://codigo5-reframe-endpoint.ujhifl.easypanel.host/

# Teste com verbose para debug
curl -v https://codigo5-reframe-endpoint.ujhifl.easypanel.host/
```

---

**Última atualização**: $(date)
**Status**: ❌ Serviço offline (Erro 502)
**Próximo passo**: Verificar logs no Easypanel
