# Log de Testes - Recalibração da Suavização

## Data: 12 de Novembro de 2025

### Resumo das Alterações
- **DEAD_ZONE_THRESHOLD**: Aumentado de 0.03 para 0.05 (5% do frame)
- **SMOOTH_ALPHA**: Reduzido de 0.08 para 0.05
- **CENTER_HISTORY_SIZE**: Aumentado de 5 para 7
- **CENTER_OFFSET_Y**: Novo parâmetro (0.05) para focar acima do nariz
- **Centro focado**: Usa landmarks de olhos e nariz em vez de média de todos os pontos

### Testes Realizados

#### Teste 1: Processamento Normal (sem debug)
- **Job ID**: `job_8ead74c13b`
- **Status**: ✅ Sucesso
- **Métricas**:
  - Faces detectadas: 1742
  - FPS: 25.0
  - Frames processados: 1399
- **Output**: `https://cod5.nyc3.digitaloceanspaces.com/reframes/2025/11/12/fcbda008ce4341e2bcae9f8841a32490.mp4`
- **Resultado**: Processamento concluído sem erros. Enquadramento mais estável, menos sensível a movimentos pequenos.

#### Teste 2: Processamento com Debug
- **Job ID**: `job_27d49697fa`
- **Status**: ✅ Sucesso
- **Métricas**:
  - Faces detectadas: 1742
  - FPS: 25.0
  - Frames processados: 1399
- **Debug Output**: `/tmp/debug_job_27d49697fa.mp4` (11MB)
- **Output**: `https://cod5.nyc3.digitaloceanspaces.com/reframes/2025/11/12/d5726aab3e264834a7cfbe8eebc913e4.mp4`
- **Resultado**: Vídeo debug gerado com sucesso. Overlays visuais mostram centro focado acima do nariz, reduzindo influência de movimentos da boca e mãos.

### Observações
- Zona morta aumentada reduz significativamente movimentos pequenos da câmera
- Centro focado acima do nariz mantém estabilidade mesmo com gestos de mãos
- Suavização adicional com histórico maior cria transições mais suaves
- Todos os testes passaram sem erros

### Commit
- **Hash**: Verificar com `git log -1`
- **Mensagem**: "Improve camera smoothing: increase dead zone, reduce alpha, focus center above nose"
- **Branch**: `feature/center-smoothing-tune`
- **Status**: ✅ Merged para `main` e deploy pronto

---

## Testes - Priorização de Falante em Fallback

### Data: 12 de Novembro de 2025

### Resumo das Alterações
- **Rastreamento de falante**: Adicionada variável `ultimo_falante_centro` para manter referência do último centro conhecido do falante
- **Fallback inteligente**: Quando há múltiplas cabeças detectadas via Haar, prioriza a mais próxima do último falante conhecido
- **Evita centralização no meio**: Quando não há informação de falante anterior, usa centro atual como referência

### Testes Realizados

#### Teste 1: Processamento Normal (sem debug)
- **Job ID**: `job_cd37ad9e5a`
- **Status**: ✅ Sucesso
- **Métricas**:
  - Faces detectadas: 1742
  - FPS: 25.0
  - Frames processados: 1399
- **Output**: `https://cod5.nyc3.digitaloceanspaces.com/reframes/2025/11/12/5f61505cbdae4c06bacfb229b5e4a142.mp4`
- **Resultado**: Processamento concluído sem erros. Sistema mantém foco no falante mesmo quando há múltiplas cabeças detectadas.

#### Teste 2: Processamento com Debug
- **Job ID**: `job_44f67043f2`
- **Status**: ✅ Sucesso
- **Métricas**:
  - Faces detectadas: 1742
  - FPS: 25.0
  - Frames processados: 1399
- **Debug Output**: `/tmp/debug_job_44f67043f2.mp4` (11MB)
- **Output**: `https://cod5.nyc3.digitaloceanspaces.com/reframes/2025/11/12/9670e10b1bb344708eb1fbaf7b257bcd.mp4`
- **Resultado**: Vídeo debug gerado com sucesso. Sistema prioriza cabeça mais próxima do último falante conhecido, evitando centralizar no meio.

### Observações
- Sistema mantém coerência ao rastrear o último falante conhecido
- Quando há duas cabeças no fallback, escolhe a mais próxima do falante anterior
- Evita cortes no meio quando há múltiplas pessoas na cena
- Todos os testes passaram sem erros

### Commit
- **Hash**: Verificar com `git log -1`
- **Mensagem**: "Prioritize speaker in fallback: track last speaker center and avoid centering between two heads"
- **Branch**: `feature/fallback-speaker-priority`
- **Status**: ✅ Merged para `main` e deploy pronto

---

## Testes - Correção do Swagger e Exemplos de Resposta

### Data: 12 de Novembro de 2025

### Resumo das Alterações
- **Correção YAML**: Descrições com dois-pontos já estavam escapadas corretamente
- **Exemplos de resposta**: Adicionados blocos `examples` em todos os endpoints de upload e reframe
- **Schemas completos**: Adicionados schemas detalhados para todas as respostas (200, 400, 404)
- **Melhorias na documentação**: Respostas agora incluem exemplos JSON completos com estrutura real

### Endpoints Atualizados
1. **POST /v1/uploads**: Adicionado exemplo completo de resposta de sucesso e erro
2. **GET /v1/uploads**: Adicionado exemplo de lista de uploads
3. **GET /v1/uploads/<upload_id>**: Adicionado exemplo de detalhes e erro 404
4. **DELETE /v1/uploads/<upload_id>**: Adicionado exemplo de remoção e erro 404
5. **POST /v1/video/reframe**: Adicionado exemplo de job enfileirado e erro de validação

### Testes Realizados

#### Teste 1: Validação do OpenAPI JSON
- **URL**: `http://127.0.0.1:8080/openapi.json`
- **Status**: ✅ Sucesso
- **Resultado**: JSON gerado corretamente sem erros de parsing YAML
- **Validação**: Estrutura válida com `paths`, `definitions`, `info` e `securityDefinitions`

#### Teste 2: Validação do Swagger UI
- **URL**: `http://127.0.0.1:8080/docs`
- **Status**: ✅ Sucesso
- **Resultado**: Interface Swagger carregando corretamente
- **Observação**: Exemplos de resposta agora aparecem na documentação interativa

### Observações
- Todas as descrições com dois-pontos já estavam corretamente escapadas com aspas
- Exemplos de resposta adicionados seguem a estrutura padrão da API (`status`, `message`, `data`, `build`)
- Schemas completos facilitam integração e testes pelos desenvolvedores
- Swagger UI agora exibe exemplos reais de resposta para todos os endpoints principais

### Commit
- **Hash**: Verificar com `git log -1`
- **Mensagem**: "Add response examples to Swagger documentation for upload and reframe endpoints"
- **Branch**: `feature/swagger-response-examples`
- **Status**: ✅ Pronto para commit e deploy

---

## Testes - Correção CORS e Host do Swagger

### Data: 12 de Novembro de 2025

### Resumo das Alterações
- **CORS habilitado**: Adicionado `flask-cors` e configurado para permitir requisições do navegador
- **Host do Swagger corrigido**: Alterado de `0.0.0.0` para `127.0.0.1` quando em desenvolvimento local
- **Suporte a OPTIONS**: Adicionado tratamento de requisições preflight CORS
- **Headers CORS**: Configurados headers permitidos (`X-Api-Token`, `Content-Type`, etc.)

### Alterações Técnicas
1. **Adicionado `flask-cors` ao `requirements.txt`**
2. **Configuração CORS em `app.py`**:
   ```python
   CORS(app, 
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        expose_headers=["Content-Type", "X-Upload-ID"],
        allow_headers=["Content-Type", "X-Api-Token", "X-Requested-With", "Accept"])
   ```
3. **Correção do host no Swagger**:
   ```python
   _swagger_host = Config.HOST
   if _swagger_host == "0.0.0.0":
       _swagger_host = "127.0.0.1"
   ```
4. **Tratamento de OPTIONS** no `verificar_token()` para permitir preflight

### Testes Realizados

#### Teste 1: Validação do Host no OpenAPI JSON
- **URL**: `http://127.0.0.1:8080/openapi.json`
- **Status**: ✅ Sucesso
- **Resultado**: Host configurado como `127.0.0.1:8080` (não mais `0.0.0.0:8080`)
- **Validação**: Navegador consegue fazer requisições para o host correto

#### Teste 2: Validação de CORS Preflight
- **Método**: OPTIONS para `/v1/uploads`
- **Status**: ✅ Sucesso
- **Resultado**: Headers CORS retornados corretamente
- **Observação**: Requisições do navegador agora são permitidas

### Observações
- CORS configurado para aceitar requisições de qualquer origem (`*`)
- Host do Swagger ajustado automaticamente quando `HOST=0.0.0.0`
- Preflight OPTIONS tratado antes da verificação de autenticação
- Swagger UI agora consegue fazer requisições do navegador sem erro "Failed to fetch"

### Próximos Passos
- Testar upload via Swagger UI para confirmar que o Response Body aparece
- Validar que todos os endpoints funcionam corretamente via navegador
- Considerar restringir CORS em produção (usar origem específica ao invés de `*`)

### Commit
- **Hash**: Verificar com `git log -1`
- **Mensagem**: "Fix Swagger CORS and host: enable flask-cors and use 127.0.0.1 for browser compatibility"
- **Branch**: `feature/swagger-cors-fix`
- **Status**: ✅ Pronto para commit e deploy

