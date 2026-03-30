# 📋 Especificação de Arquitetura e Requisitos Técnicos: SaaS Construtech (IA + Gestão)
### Versão Revisada — Melhorias e Complementos Destacados com `[NOVO]` ou `[REVISADO]`

---

## 1. Visão Geral do Sistema

O sistema é uma plataforma B2B multicanal para empresas de engenharia e locação de maquinário. A arquitetura é dividida em dois nós principais de processamento:

1. **Middleware de Atendimento (Python/FastAPI):** Um agente autônomo que atua via WhatsApp (Evolution API/Chatwoot), responsável por qualificação de leads, processamento de áudio (Whisper) e agendamento.
2. **Painel Administrativo (Java/Spring Boot + Angular):** Uma aplicação web (CRM) para gestão de Equipes, Máquinas, Visitas e dashboard analítico.

> **Princípio de Responsabilidade Única:** Cada serviço deve ter uma fronteira clara. O Middleware Python **não** deve acessar diretamente as entidades do painel administrativo — toda comunicação entre os dois nós deve passar por endpoints REST bem definidos ou eventos assíncronos (ex: fila de mensagens). Isso facilita manutenção e escalabilidade futura.

---

## 2. Infraestrutura e Stack Tecnológico

Todo o ecossistema será instalado em uma VPS (Hostinger), garantindo comunicação rápida entre os serviços.

| Componente | Tecnologia |
|---|---|
| Banco de Dados | PostgreSQL 15+ |
| Motor Cognitivo (Microserviço) | Python 3.11+ com FastAPI |
| Orquestração de IA | Framework `Agno` |
| Backend de Gestão (API RESTful) | Java 17+ com Spring Boot 3.x + Spring Data JPA |
| Frontend | Angular 17+ (standalone components) |
| Cache | Redis (sessões de conversa e rate limiting) |
| Proxy Reverso | Nginx (SSL termination, roteamento) |
| A hospedagem será feita na hostinger |

> ** Containerização:** Recomenda-se fortemente o uso de **Docker + Docker Compose** para orquestrar os serviços localmente e na VPS. Isso garante ambiente reproduzível, facilita deploys e isola as dependências de cada serviço.

> ** Gerenciamento de Segredos:** Todas as variáveis sensíveis (chaves de API, senhas de banco, tokens) devem ser armazenadas em arquivo `.env` não versionado (`.gitignore`). Nunca hardcoded no código-fonte. Considere usar **HashiCorp Vault** para ambientes de produção mais exigentes.

> ** SSL/HTTPS:** Configurar certificado SSL via **Let's Encrypt (Certbot)** no Nginx. Todo tráfego HTTP deve ser redirecionado para HTTPS.

---

## 3. Modelagem de Dados (Esquema PostgreSQL)

Todas as tabelas usam chaves primárias do tipo `UUID` (geradas via `gen_random_uuid()`) para segurança e portabilidade.

### 3.1 Tabelas Principais

```sql
-- Clientes capturados pelo robô ou cadastrados manualmente
CREATE TABLE clientes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255),
    telefone        VARCHAR(20) UNIQUE NOT NULL,
    origem          VARCHAR(100),       -- ex: 'whatsapp_robo', 'cadastro_manual'
    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()  -- [NOVO]
);

-- Máquinas disponíveis para locação
CREATE TABLE maquinas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                    VARCHAR(255) NOT NULL,
    descricao               TEXT,
    quantidade_total        INT NOT NULL CHECK (quantidade_total >= 0),
    quantidade_disponivel   INT NOT NULL CHECK (quantidade_disponivel >= 0),
    valor_diaria            NUMERIC(10, 2),
    ativo                   BOOLEAN DEFAULT TRUE,   -- [NOVO] soft delete / inativação
    criado_em               TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ DEFAULT NOW()
);

-- Equipes de campo
CREATE TABLE equipes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                VARCHAR(255) NOT NULL,
    telefone_whatsapp   VARCHAR(20),
    especialidade       VARCHAR(255),
    ativo               BOOLEAN DEFAULT TRUE,
    criado_em           TIMESTAMPTZ DEFAULT NOW()
);

-- Visitas técnicas agendadas
CREATE TABLE visitas_tecnicas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    equipe_id           UUID REFERENCES equipes(id) ON DELETE SET NULL,
    descricao_servico   TEXT,
    endereco            TEXT,
    data_visita         DATE NOT NULL,
    turno               VARCHAR(20) CHECK (turno IN ('manha', 'tarde', 'integral')),
    status              VARCHAR(30) NOT NULL DEFAULT 'pendente'
                            CHECK (status IN ('pendente', 'confirmada', 'em_andamento', 'concluida', 'cancelada')),  -- [REVISADO] enum explícito
    criado_em           TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Locações de máquinas
CREATE TABLE locacoes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          UUID NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    maquina_id          UUID NOT NULL REFERENCES maquinas(id) ON DELETE RESTRICT,
    endereco_entrega    TEXT,
    data_inicio         DATE NOT NULL,
    data_fim            DATE,
    status              VARCHAR(30) NOT NULL DEFAULT 'solicitada'
                            CHECK (status IN ('solicitada', 'confirmada', 'ativa', 'encerrada', 'cancelada')),
    criado_em           TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.2 Tabelas de Suporte

```sql
-- Usuários do painel administrativo (RBAC)
CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    senha_hash      VARCHAR(255) NOT NULL,
    perfil          VARCHAR(30) NOT NULL CHECK (perfil IN ('admin', 'gerente', 'tecnico')),
    equipe_id       UUID REFERENCES equipes(id) ON DELETE SET NULL,
    ativo           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Configurações de agenda lidas pelo robô
CREATE TABLE configuracoes_agenda (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chave           VARCHAR(100) UNIQUE NOT NULL,  -- ex: 'horario_inicio', 'dias_uteis'
    valor           TEXT NOT NULL,
    descricao       TEXT,
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Histórico de mensagens por conversa (para auditoria e contexto)
CREATE TABLE conversas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    conteudo        TEXT NOT NULL,
    tipo            VARCHAR(20) DEFAULT 'texto' CHECK (tipo IN ('texto', 'audio', 'imagem', 'documento')),
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.3 Índices de Performance

```sql
-- Consultas frequentes pelo robô
CREATE INDEX idx_clientes_telefone ON clientes(telefone);
CREATE INDEX idx_visitas_data ON visitas_tecnicas(data_visita, status);
CREATE INDEX idx_visitas_equipe ON visitas_tecnicas(equipe_id, data_visita);
CREATE INDEX idx_locacoes_maquina ON locacoes(maquina_id, status);
CREATE INDEX idx_conversas_cliente ON conversas(cliente_id, criado_em DESC);
```

> **Constraint de Disponibilidade:** Adicionar trigger ou check no backend para garantir que `quantidade_disponivel <= quantidade_total` e que não seja possível criar uma locação com `quantidade_disponivel = 0`.

---

## 4. Engenharia de IA e Orquestração (Framework Agno)

A IA atua apenas como o "cérebro" da conversa, focada em regras de negócio e economia de tokens.

## 4. Engenharia de IA e Qualificação de Leads (Marketing Conversacional)

A IA não é apenas um chatbot de suporte; ela é o **Primeiro Atendimento (SDR)** focado em transformar curiosos em oportunidades reais de negócio.

### 4.1 O Funil de Qualificação (Roteiro de Atendimento)

O robô deve conduzir a conversa seguindo estas fases lógicas, adaptando-se ao ritmo do cliente:

1.  **Fase de Abertura (Conexão e Nome):**
    *   Saudação calorosa e profissional.
    *   Identificar o nome do cliente e a empresa (se aplicável).
    *   *Gatilho:* Validar se é um cliente recorrente ou um novo lead.

2.  **Fase de Descoberta (Identificação da Dor/Necessidade):**
    *   Entender o contexto: "Qual o desafio da sua obra hoje?" ou "O que você está construindo no momento?".
    *   Distinguir se ele precisa de **Serviço Técnico** (instalação, manutenção) ou **Locação de Equipamento**.
    *   *Foco Marketing:* Identificar se o problema é urgente ou planejado.

3.  **Fase de Qualificação Técnica (Oportunidade):**
    *   Coletar detalhes do projeto: Tamanho da obra, localização exata e prazo de início.
    *   Se for locação, usar `verificar_estoque`.
    *   Se for serviço, entender a complexidade para preparar o técnico.

4.  **Fase de Autoridade e Próximo Passo (Comprometimento):**
    *   Verificar disponibilidade na agenda (`consultar_disponibilidade_agenda`).
    *   Propor a visita técnica como a solução definitiva para o diagnóstico.
    *   *Regra de Ouro:* Nunca finalizar sem um agendamento ou um compromisso de retorno.

5.  **Fase de Fechamento e Handoff:**
    *   Registrar a visita (`registrar_visita_tecnica`).
    *   Explicar que um consultor sênior entrará em contato para formalizar valores.
    *   Transferir para humano (`iniciar_handoff_humano`) se houver objeções complexas ou perguntas de preço.

### 4.2 Regras de Ouro de Atendimento (System Prompt)

*   **Fale como um Especialista:** Use termos técnicos de construção civil de forma natural (ex: canteiro de obra, cronograma, fundação).
*   **Uma Pergunta por Vez:** Nunca envie blocos de texto. Mantenha a conversa fluida.
*   **Gestão de Expectativa:** NUNCA garanta preços. Diga: "Nossos valores são personalizados conforme o tempo de uso e a logística da sua obra".
*   **Captura de Leads:** Se o cliente parar de responder em uma fase avançada, o sistema deve marcar como `lead_morno`.
*   **Empatia:** Se o cliente relatar um problema urgente (ex: máquina quebrada ou vazamento), pule a burocracia e acione o handoff humano imediatamente com a etiqueta `URGENTE`.

### 4.4 Padrões de Codificação e Melhores Práticas Agno [NOVO]

Para garantir que a IA seja verdadeiramente "inteligente" e lembre-se do cliente em diferentes contatos, devemos seguir estes padrões:

1.  **Memória Persistente de Fatos:**
    *   Sempre habilitar `update_memory_on_run=True`. Isso permite que a IA extraia fatos (ex: "O cliente prefere atendimento à tarde") e os salve automaticamente.
    *   Utilizar `user_id` (telefone do cliente) em todas as chamadas `agent.run()`, permitindo que a memória seja vinculada à pessoa e não apenas à conversa.

2.  **Gestão de Sessão e Histórico:**
    *   Habilitar `add_history_to_context=True` com uma janela de 10-12 mensagens.
    *   Utilizar `PostgresDb` para persistência, separando as tabelas de sessão (`agent_sessions`) e memória (`agent_memory`).

3.  **Desenvolvimento de Tools (Skills):**
    *   As ferramentas devem ser granulares. Cada função deve fazer apenas uma coisa (ex: ou consulta estoque, ou agenda visita).
    *   Sempre incluir `Docstrings` detalhadas nas funções das tools, pois a IA as utiliza para entender quando e como chamar a ferramenta.

4.  **Resiliência de Modelos:**
    *   Utilizar um `Model Factory` para permitir a troca entre Groq (velocidade) e Gemini (contexto longo/produção) sem alteração de código.

### 4.3 Economia de Tokens (Cost Management)

> ** Memória Curta — Atenção:** Enviar apenas as últimas 5 mensagens pode causar problemas de contexto. Recomenda-se a seguinte estratégia híbrida:
> - **Resumo fixo no início:** Um campo `resumo_conversa` (gerado automaticamente na primeira mensagem ou atualizado a cada 10 mensagens) que contém dados essenciais como nome, tipo de interesse e endereço.
> - **Janela deslizante:** As últimas **8 mensagens** (equilíbrio entre custo e contexto).
> - **Limite de tokens:** Manter em **200 tokens** de resposta (150 pode truncar respostas com endereços ou datas longas).

### 4.4 Fluxo de Fallback da IA

Definir comportamento explícito quando a IA falhar ou retornar erro:

1. **Erro de API da IA (timeout/500):** Responder ao cliente: _"Estou com uma instabilidade, mas já registramos seu contato. Em breve te retornamos!"_ e criar um lead com status `pendente_revisao`.
2. **Loop detectado (3 mensagens sem progressão):** Acionar `iniciar_handoff_humano("loop_detectado")` automaticamente.
3. **Palavras-chave de urgência** (`urgente`, `emergência`, `acidente`): Transferir imediatamente para humano e notificar o gerente via WhatsApp.

---

## 5. Fluxo de Integração e Segurança (WhatsApp)

### 5.1 Gatilhos de Ativação e Tipos de Mídia

- O robô **ignora** mensagens de grupos.
- Para **imediatamente** se a etiqueta `pausar_robo` for adicionada no Chatwoot.
- Só inicia o fluxo se a primeira mensagem contiver a palavra `"anúncio"` (case-insensitive) **ou** se a etiqueta `robo_ativo` estiver ativa no contato.
- **Áudios** recebidos são transcritos pelo Whisper antes de serem enviados à IA.
- ** Imagens:** Receber e salvar a URL da mídia no registro da conversa. Informar ao cliente que o atendente humano analisará a imagem.
- ** Documentos (PDF/DOC):** Tratamento idêntico ao de imagens — salvar referência e acionar handoff humano se necessário.
- ** Mensagens de Localização:** Extrair latitude/longitude e salvar como endereço da visita, confirmando com o cliente antes de registrar.
- ** Stickers/Reações:** Ignorar silenciosamente, sem resposta.

> ** Trigger "anúncio":** Considerar também aceitar variações como `"anuncio"` (sem acento) e normalizar o texto recebido antes da verificação para evitar falhas por digitação do usuário.

### 5.2 Validação do Webhook (Segurança)

A Evolution API envia um `webhook_secret` no header das requisições. O FastAPI deve validar esse header **antes** de processar qualquer mensagem:

```python
# Exemplo de validação no FastAPI
WEBHOOK_SECRET = os.getenv("EVOLUTION_WEBHOOK_SECRET")

@app.post("/webhook/whatsapp")
async def receber_mensagem(request: Request):
    secret = request.headers.get("X-Webhook-Secret")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    # processar...
```

### 5.3 O Escudo Anti-Ban (Fila de Processamento em Python)

Para proteger o número do cliente contra bloqueios, a segurança não é feita pela IA. O código Python (FastAPI) atua como um escudo protetor:

1. **Fila de Espera (Message Queue):** A IA processa múltiplas mensagens, mas o Python enfileira as respostas e envia para a Evolution API com atraso de **10 a 20 segundos** entre cada uma (usar `random.uniform(10, 20)` para imprevisibilidade).
2. **Simulação Automática de Digitação:** O gerenciador da fila dispara `sendPresence` (`"digitando..."`) obrigatoriamente antes de liberar cada mensagem.
3. **Limite de Segurança Diário (Throttling):** O script conta os envios diários. Se se aproximar do limite (ex: 200/dia para chips novos), entra em modo passivo. Usar **Redis** para armazenar esse contador com TTL de 24h, em vez de variável em memória (que se perde ao reiniciar o processo).
4. **Aquecimento Exigido:** É obrigatório o uso de um chip físico com histórico humano prévio antes da conexão via QR Code.
5. ** Deduplicação de Mensagens:** Armazenar os últimos `message_id` recebidos em Redis com TTL de 60s para evitar processamento duplicado em caso de reentrega do webhook.

### 5.4 Fuso Horário e Horário Comercial

- Toda lógica de horário deve operar no fuso `America/Sao_Paulo`.
- O robô deve verificar o horário atual antes de responder mensagens iniciadas fora do horário comercial. Se fora do horário, enviar mensagem padrão de fora do expediente e registrar o lead para retorno no próximo dia útil.

---

## 6. Backend de Gestão — API RESTful (Java/Spring Boot)

### 6.1 Autenticação e Autorização (RBAC)

- Autenticação via **JWT (JSON Web Token)** com refresh token.
- Perfis: `admin`, `gerente`, `tecnico`.
- Usar **Spring Security** com filtros de autenticação e autorização baseados em roles.
- Tokens JWT com validade de **1 hora** (access token) e **7 dias** (refresh token).

| Endpoint | Admin | Gerente | Técnico |
|---|---|---|---|
| Dashboard / Leads | ✅ | ✅ | ❌ |
| Gerenciar Máquinas | ✅ | ✅ | ❌ |
| Kanban de Visitas | ✅ | ✅ | ❌ |
| Minhas Visitas | ❌ | ❌ | ✅ |
| Configurações do Robô | ✅ | ❌ | ❌ |

### 6.2 Versionamento e Documentação da API

- Prefixar todos os endpoints com `/api/v1/` para facilitar versionamento futuro.
- Usar **Springdoc OpenAPI (Swagger UI)** para documentação automática dos endpoints.
- Exemplo de endpoints principais:
  - `GET /api/v1/visitas?status=pendente&data=2025-07-10`
  - `PATCH /api/v1/visitas/{id}/status`
  - `GET /api/v1/dashboard/indicadores`
  - `GET /api/v1/maquinas?disponivel=true`

### 6.3 Tratamento de Erros Padronizado

Adotar o padrão **RFC 7807 (Problem Details)** para respostas de erro:

```json
{
  "type": "/erros/recurso-nao-encontrado",
  "title": "Visita não encontrada",
  "status": 404,
  "detail": "Não existe visita com ID abc-123.",
  "instance": "/api/v1/visitas/abc-123"
}
```

### 6.4 Notificações em Tempo Real (WebSocket / SSE)

Para atualizar o Kanban do gerente quando um técnico clicar em "Cheguei" ou "Finalizar":
- Usar **Server-Sent Events (SSE)** no Spring Boot como abordagem mais simples, ou **WebSocket (STOMP)** se bidirecionalidade for necessária.
- O frontend Angular se inscreve no canal de eventos e atualiza o card da visita sem recarregar a página.

---

## 7. Interface Web (Frontend Angular)

Arquitetura de telas com controle de acesso por tipo de usuário (RBAC).

### 7.1 Área do Dono/Gerência

- **Dashboard:** Indicadores chave (novos leads hoje, visitas do dia, máquinas disponíveis) e tabela de novos leads com botão para abrir a conversa no Chatwoot.
- **Configurações:** Definição de regras de agenda (horário de a lmoço, fins de semana, feriados) lidas pelo robô via tabela `configuracoes_agenda`.
- **Visitas Técnicas:** Tela em formato **Kanban** para arrastar e soltar os cards entre colunas (`Pendente → Confirmada → Em Andamento → Concluída`).
- **Locações:** Controle visual do estoque de máquinas.
- **Relatórios:** Exportação de leads e visitas em CSV/XLSX por período.

### 7.2 Área Operacional (Técnicos em Campo)

- Tela simples **"Minhas Visitas"** otimizada para uso em celular (layout mobile-first).
- Botões de **"Cheguei no Local"** e **"Finalizar Visita"** que atualizam o Kanban do gerente em tempo real via SSE/WebSocket.
- Campo de observações ao finalizar a visita, com possibilidade de tirar foto (upload de imagem via câmera do celular).
- Indicador offline: se o técnico perder conexão, as ações são enfileiradas localmente e sincronizadas quando a conexão retornar.

### 7.3 Tela de Login e Gestão de Sessão

- Tela de login com email e senha.
- Armazenar o access token no **sessionStorage** e o refresh token em cookie **httpOnly** (mais seguro que localStorage).
- Guard no Angular para rotas protegidas, redirecionando para login se o token expirar.

---

## 8. Observabilidade e Operações

### 8.1 Logging Estruturado

- **Python/FastAPI:** Usar `structlog` ou logging padrão com saída em JSON. Logar cada mensagem recebida, resposta enviada e chamada de ferramenta da IA com `correlation_id` único por conversa.
- **Java/Spring Boot:** Usar `SLF4J + Logback` com output JSON. Configurar níveis: `ERROR` em produção, `DEBUG` em desenvolvimento.
- Centralizar logs com **Loki + Grafana** ou simplesmente rotacionar arquivos de log com `logrotate` na VPS.

### 8.2 Monitoramento e Alertas

- Expor métricas do FastAPI via `/metrics` (Prometheus format) usando `prometheus-fastapi-instrumentator`.
- Expor métricas do Spring Boot via **Spring Actuator** (`/actuator/prometheus`).
- Configurar alertas mínimos:
  - Fila de mensagens do WhatsApp travada há mais de 5 minutos.
  - Taxa de erros da IA acima de 10% em 1 hora.
  - Banco de dados inacessível.

### 8.3 Backup

- Configurar backup automático do PostgreSQL com `pg_dump` diariamente (cron job na VPS).
- Enviar o dump comprimido para storage externo (ex: Backblaze B2 ou S3-compatible).
- Reter backups dos últimos 30 dias.

---

## 9. Plano de Validação (Testes)

### 9.1 Testes de Segurança Anti-Ban

- Confirmar que o evento `"digitando..."` aparece via fila do Python antes de cada mensagem.
- Enviar 10 mensagens em sequência e verificar que o Python responde devagar, uma a uma (intervalo de 15-25s).
- Simular reinicialização do processo e confirmar que o contador de mensagens diárias persiste no Redis.

### 9.2 Testes de Banco de Dados

- Confirmar que o campo `telefone` é `UNIQUE` e que cadastros repetidos apenas atualizam o nome.
- Verificar que não é possível criar uma locação para máquina com `quantidade_disponivel = 0`.
- Testar que os índices criados estão sendo utilizados nas queries mais frequentes (via `EXPLAIN ANALYZE`).

### 9.3 Testes de IA

- Forçar perguntas de preço/orçamento e validar que a IA desvia corretamente.
- Enviar áudio e validar a transcrição pelo Whisper antes de chegar à IA.
- Testar o fluxo de loop: enviar 3 mensagens sem progressão e verificar se o handoff humano é acionado.
- Simular falha na API da IA (timeout) e verificar se a mensagem de fallback é enviada.

### 9.4 Testes de Agenda

- Tentar agendar visita no domingo ou feriado — a IA deve recusar e negociar novo horário.
- Tentar agendar em horário de almoço — a IA deve verificar `configuracoes_agenda` e propor alternativa.
- Testar conflito de agenda: duas visitas no mesmo horário para a mesma equipe — o sistema não deve permitir.

### 9.5 Testes de Autenticação e RBAC

- Tentar acessar endpoint de gerente com token de técnico — deve retornar `403 Forbidden`.
- Testar expiração do access token e fluxo de refresh automático.
- Testar que senha incorreta retorna `401` e não vaza informação sobre o usuário existente.

### 9.6 Testes de Carga (Básico)

- Usar **Locust** ou **k6** para simular 50 conversas simultâneas no webhook do FastAPI.
- Verificar que a fila do Python não trava e que os logs não apresentam erros de concorrência.

---

## 10. Checklist de Deploy em Produção

- [ ] Variáveis sensíveis em `.env` (nunca no código).
- [ ] HTTPS configurado com Let's Encrypt no Nginx.
- [ ] Webhook secret da Evolution API validado no FastAPI.
- [ ] Backup automático do PostgreSQL configurado e testado.
- [ ] Chip físico com histórico humano conectado (aquecimento).
- [ ] Limite diário de mensagens configurado no Redis.
- [ ] Monitoramento básico ativo (logs + alertas de fila).
- [ ] Documentação da API gerada pelo Swagger disponível internamente.
- [ ] Usuários criados com perfis corretos (admin, gerente, técnico).
- [ ] Testes de fumaça executados em produção após deploy.

---

## 11. Decisões em Aberto (Pendências)

| # | Decisão | Impacto |
|---|---|---|
| 1 | Usar Redis Streams ou fila em memória (asyncio.Queue) para a fila de WhatsApp? | Redis é mais resiliente a reinicializações; asyncio é mais simples de implantar |
| 2 | SSE ou WebSocket para atualizações do Kanban? | SSE é unidirecional e mais simples; WebSocket permite enviar dados do browser ao servidor |
| 3 | Qual modelo da OpenAI usar para o Agno? | GPT-4o Mini é mais barato; GPT-4o é mais preciso para fluxos complexos |
| 4 | O técnico precisa de app nativo ou PWA é suficiente? | PWA elimina publicação em loja de apps, mas tem limitações de câmera em iOS |
| 5 | Feriados nacionais/municipais serão cadastrados manualmente ou via API (BrasilAPI)? | API automática é mais conveniente; manual dá mais controle |
