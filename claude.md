# 📋 Especificação de Arquitetura e Requisitos Técnicos: SaaS Construtech (IA + Gestão)
### Versão 2.0 — Correções e melhorias marcadas com `[CORRIGIDO]`, `[NOVO]` ou `[REVISADO]`

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
| Hospedagem | Hostinger VPS |
| Migrations de Banco | Flyway [NOVO] |

> **Containerização:** Recomenda-se fortemente o uso de **Docker + Docker Compose** para orquestrar os serviços localmente e na VPS. Isso garante ambiente reproduzível, facilita deploys e isola as dependências de cada serviço.

> **Gerenciamento de Segredos:** Todas as variáveis sensíveis (chaves de API, senhas de banco, tokens) devem ser armazenadas em arquivo `.env` não versionado (`.gitignore`). Nunca hardcoded no código-fonte. Considere usar **HashiCorp Vault** para ambientes de produção mais exigentes.

> **SSL/HTTPS:** Configurar certificado SSL via **Let's Encrypt (Certbot)** no Nginx. Todo tráfego HTTP deve ser redirecionado para HTTPS.

### 2.1 Estratégia de Migrations (Flyway) [NOVO]

Todas as alterações de schema do banco de dados devem ser controladas via **Flyway**, integrado ao Spring Boot. Nenhuma alteração manual no banco de produção é permitida.

- Criar diretório `src/main/resources/db/migration/`
- Nomear arquivos no padrão: `V1__criar_tabelas_principais.sql`, `V2__adicionar_status_lead.sql`, etc.
- O Spring Boot aplica as migrations automaticamente ao iniciar (`spring.flyway.enabled=true`)
- Para o banco de desenvolvimento, usar `spring.flyway.clean-on-validation-error=false` (NUNCA em produção)
- Migrations são **irreversíveis** — sempre criar uma nova migration em vez de editar uma existente

---

## 3. Modelagem de Dados (Esquema PostgreSQL)

Todas as tabelas usam chaves primárias do tipo `UUID` (geradas via `gen_random_uuid()`) para segurança e portabilidade.

### 3.1 Trigger Global para `atualizado_em` [NOVO]

Antes de criar qualquer tabela, definir a função de trigger que atualiza automaticamente o campo `atualizado_em`. Sem este trigger, o campo nunca é atualizado após a inserção.

```sql
-- Função reutilizável por todas as tabelas
CREATE OR REPLACE FUNCTION fn_atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 3.2 Tabelas Principais

```sql
-- Clientes capturados pelo robô ou cadastrados manualmente
CREATE TABLE clientes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(255),
    telefone        VARCHAR(20) UNIQUE NOT NULL,
    origem          VARCHAR(100),                    -- ex: 'whatsapp_robo', 'cadastro_manual'
    status_lead     VARCHAR(30) DEFAULT 'novo'       -- [NOVO] funil de qualificação
                        CHECK (status_lead IN ('novo', 'em_qualificacao', 'qualificado',
                                               'lead_morno', 'pendente_revisao', 'convertido', 'perdido')),
    resumo_conversa TEXT,                            -- [NOVO] resumo gerado pela IA para economia de tokens
    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_clientes_atualizado_em
  BEFORE UPDATE ON clientes
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Máquinas disponíveis para locação
CREATE TABLE maquinas (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                    VARCHAR(255) NOT NULL,
    descricao               TEXT,
    quantidade_total        INT NOT NULL CHECK (quantidade_total >= 0),
    quantidade_disponivel   INT NOT NULL CHECK (quantidade_disponivel >= 0),
    valor_diaria            NUMERIC(10, 2),
    ativo                   BOOLEAN DEFAULT TRUE,    -- soft delete / inativação
    criado_em               TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em           TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_quantidade CHECK (quantidade_disponivel <= quantidade_total)  -- [NOVO]
);

CREATE TRIGGER trg_maquinas_atualizado_em
  BEFORE UPDATE ON maquinas
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Equipes de campo
CREATE TABLE equipes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                VARCHAR(255) NOT NULL,
    telefone_whatsapp   VARCHAR(20),
    especialidade       VARCHAR(255),
    ativo               BOOLEAN DEFAULT TRUE,
    criado_em           TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ DEFAULT NOW()   -- [NOVO]
);

CREATE TRIGGER trg_equipes_atualizado_em
  BEFORE UPDATE ON equipes
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

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
                            CHECK (status IN ('pendente', 'confirmada', 'em_andamento', 'concluida', 'cancelada')),
    criado_em           TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_visitas_atualizado_em
  BEFORE UPDATE ON visitas_tecnicas
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

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

CREATE TRIGGER trg_locacoes_atualizado_em
  BEFORE UPDATE ON locacoes
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();
```

### 3.3 Tabelas de Suporte

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
    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()    -- [NOVO]
);

CREATE TRIGGER trg_usuarios_atualizado_em
  BEFORE UPDATE ON usuarios
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Configurações de agenda lidas pelo robô
CREATE TABLE configuracoes_agenda (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chave           VARCHAR(100) UNIQUE NOT NULL,  -- ex: 'horario_inicio', 'dias_uteis'
    valor           TEXT NOT NULL,
    descricao       TEXT,
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_config_agenda_atualizado_em
  BEFORE UPDATE ON configuracoes_agenda
  FOR EACH ROW EXECUTE FUNCTION fn_atualizar_timestamp();

-- Histórico de mensagens por conversa (para auditoria e contexto)
CREATE TABLE conversas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    conteudo        TEXT NOT NULL,
    tipo            VARCHAR(20) DEFAULT 'texto' CHECK (tipo IN ('texto', 'audio', 'imagem', 'documento')),
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Feriados nacionais e municipais consultados pelo robô [NOVO]
CREATE TABLE feriados (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data        DATE NOT NULL UNIQUE,
    descricao   VARCHAR(255) NOT NULL,
    tipo        VARCHAR(20) DEFAULT 'nacional' CHECK (tipo IN ('nacional', 'municipal', 'estadual')),
    origem      VARCHAR(20) DEFAULT 'manual'   CHECK (origem IN ('manual', 'brasilapi')),
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Observações registradas pelo técnico ao finalizar visita [NOVO]
CREATE TABLE observacoes_visita (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visita_id   UUID NOT NULL REFERENCES visitas_tecnicas(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    conteudo    TEXT NOT NULL CHECK (length(conteudo) >= 10),
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Fotos tiradas pelo técnico durante/após a visita [NOVO]
CREATE TABLE fotos_visita (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visita_id   UUID NOT NULL REFERENCES visitas_tecnicas(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    url         TEXT NOT NULL,          -- URL pública no storage (S3-compatible / Backblaze)
    mime_type   VARCHAR(50) NOT NULL,   -- ex: 'image/jpeg'
    tamanho_kb  INT,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log — rastreia quem alterou o quê e quando [NOVO]
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tabela          VARCHAR(100) NOT NULL,  -- ex: 'visitas_tecnicas'
    registro_id     UUID NOT NULL,          -- ID do registro alterado
    usuario_id      UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    acao            VARCHAR(20) NOT NULL CHECK (acao IN ('INSERT', 'UPDATE', 'DELETE')),
    dados_antes     JSONB,                  -- snapshot do registro antes da alteração
    dados_depois    JSONB,                  -- snapshot do registro após a alteração
    ip_origem       VARCHAR(45),
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.4 Tabelas do Framework Agno (Memória da IA) [NOVO]

O framework Agno utiliza `PostgresDb` para persistência. Estas tabelas **devem existir** antes de inicializar o agente, caso contrário o Python falha ao iniciar.

```sql
-- Sessões de conversa do agente (gerenciada pelo Agno)
CREATE TABLE agent_sessions (
    session_id      VARCHAR(255) PRIMARY KEY,
    user_id         VARCHAR(255),           -- telefone do cliente (E.164)
    agent_id        VARCHAR(255),
    memory          JSONB,
    agent_data      JSONB,
    user_data       JSONB,
    session_data    JSONB,
    created_at      BIGINT,
    updated_at      BIGINT
);

-- Memória de longo prazo do agente por usuário (gerenciada pelo Agno)
CREATE TABLE agent_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     VARCHAR(255) NOT NULL,      -- telefone do cliente (E.164)
    memory      TEXT NOT NULL,              -- fato extraído: "prefere atendimento à tarde"
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_sessions_user ON agent_sessions(user_id);
CREATE INDEX idx_agent_memory_user   ON agent_memory(user_id);
```

### 3.5 Índices de Performance

```sql
-- Consultas frequentes pelo robô
CREATE INDEX idx_clientes_telefone    ON clientes(telefone);
CREATE INDEX idx_clientes_status_lead ON clientes(status_lead);              -- [NOVO]
CREATE INDEX idx_visitas_data         ON visitas_tecnicas(data_visita, status);
CREATE INDEX idx_visitas_equipe       ON visitas_tecnicas(equipe_id, data_visita);
CREATE INDEX idx_locacoes_maquina     ON locacoes(maquina_id, status);
CREATE INDEX idx_conversas_cliente    ON conversas(cliente_id, criado_em DESC);
CREATE INDEX idx_audit_log_tabela     ON audit_log(tabela, registro_id);      -- [NOVO]
CREATE INDEX idx_fotos_visita         ON fotos_visita(visita_id);              -- [NOVO]
CREATE INDEX idx_feriados_data        ON feriados(data);                       -- [NOVO]
```

### 3.6 Política de Retenção de Dados [NOVO]

Para conformidade com LGPD e controle de crescimento do banco:

- Tabela `conversas`: registros com mais de **12 meses** podem ser excluídos via cron job mensal.
- Tabela `audit_log`: retenção de **24 meses** (exigência de rastreabilidade B2B).
- Tabela `fotos_visita`: URLs de fotos com mais de **24 meses** devem ser movidas para storage de arquivamento (tier mais barato no Backblaze B2).
- Implementar via `pg_cron` ou script Python agendado no cron da VPS.

---

## 4. Engenharia de IA e Qualificação de Leads (Marketing Conversacional)

A IA não é apenas um chatbot de suporte; ela é o **Primeiro Atendimento (SDR)** focado em transformar curiosos em oportunidades reais de negócio.

### 4.1 O Funil de Qualificação (Roteiro de Atendimento)

O robô deve conduzir a conversa seguindo estas fases lógicas, adaptando-se ao ritmo do cliente:

1. **Fase de Abertura (Conexão e Nome):**
   - Saudação calorosa e profissional.
   - Identificar o nome do cliente e a empresa (se aplicável).
   - *Gatilho:* Validar se é um cliente recorrente ou um novo lead.

2. **Fase de Descoberta (Identificação da Dor/Necessidade):**
   - Entender o contexto: "Qual o desafio da sua obra hoje?" ou "O que você está construindo no momento?".
   - Distinguir se ele precisa de **Serviço Técnico** (instalação, manutenção) ou **Locação de Equipamento**.
   - *Foco Marketing:* Identificar se o problema é urgente ou planejado.

3. **Fase de Qualificação Técnica (Oportunidade):**
   - Coletar detalhes do projeto: Tamanho da obra, localização exata e prazo de início.
   - Se for locação, usar `verificar_estoque`.
   - Se for serviço, entender a complexidade para preparar o técnico.

4. **Fase de Autoridade e Próximo Passo (Comprometimento):**
   - Verificar disponibilidade na agenda (`consultar_disponibilidade_agenda`).
   - Propor a visita técnica como a solução definitiva para o diagnóstico.
   - *Regra de Ouro:* Nunca finalizar sem um agendamento ou um compromisso de retorno.

5. **Fase de Fechamento e Handoff:**
   - Registrar a visita (`registrar_visita_tecnica`).
   - Explicar que um consultor sênior entrará em contato para formalizar valores.
   - Transferir para humano (`iniciar_handoff_humano`) se houver objeções complexas ou perguntas de preço.

### 4.2 Regras de Ouro de Atendimento (System Prompt)

- **Fale como um Especialista:** Use termos técnicos de construção civil de forma natural (ex: canteiro de obra, cronograma, fundação).
- **Uma Pergunta por Vez:** Nunca envie blocos de texto. Mantenha a conversa fluida.
- **Gestão de Expectativa:** NUNCA garanta preços. Diga: "Nossos valores são personalizados conforme o tempo de uso e a logística da sua obra".
- **Captura de Leads:** Se o cliente parar de responder em uma fase avançada, o sistema deve marcar como `lead_morno` via `UPDATE clientes SET status_lead = 'lead_morno'`.
- **Empatia:** Se o cliente relatar um problema urgente (ex: máquina quebrada ou vazamento), pule a burocracia e acione o handoff humano imediatamente com a etiqueta `URGENTE`.

### 4.3 Padrões de Codificação e Melhores Práticas Agno [REVISADO]

Para garantir que a IA seja verdadeiramente "inteligente" e lembre-se do cliente em diferentes contatos:

1. **Memória Persistente de Fatos:**
   - Sempre habilitar `update_memory_on_run=True`. Isso permite que a IA extraia fatos (ex: "O cliente prefere atendimento à tarde") e os salve automaticamente na tabela `agent_memory`.
   - Utilizar `user_id` (telefone do cliente no formato E.164) em todas as chamadas `agent.run()`, permitindo que a memória seja vinculada à pessoa e não apenas à conversa.

2. **Gestão de Sessão e Histórico:**
   - Habilitar `add_history_to_context=True` com uma janela de 10-12 mensagens.
   - Utilizar `PostgresDb` para persistência nas tabelas `agent_sessions` e `agent_memory` (definidas na Seção 3.4).

3. **Desenvolvimento de Tools (Skills):**
   - As ferramentas devem ser granulares. Cada função deve fazer apenas uma coisa (ex: ou consulta estoque, ou agenda visita).
   - Sempre incluir `Docstrings` detalhadas nas funções das tools, pois a IA as utiliza para entender quando e como chamar a ferramenta.
   - Ao finalizar uma ação, atualizar o `status_lead` do cliente na tabela `clientes`.

4. **Resiliência de Modelos:**
   - Utilizar um `Model Factory` para permitir a troca entre Groq (velocidade) e Gemini (contexto longo/produção) sem alteração de código.

### 4.4 Economia de Tokens (Cost Management)

> **Memória Curta — Atenção:** Enviar apenas as últimas 5 mensagens pode causar problemas de contexto. Recomenda-se a seguinte estratégia híbrida:
> - **Resumo fixo no início:** O campo `resumo_conversa` na tabela `clientes` (gerado automaticamente na primeira mensagem ou atualizado a cada 10 mensagens) contém dados essenciais como nome, tipo de interesse e endereço. [CORRIGIDO — campo agora existe no schema]
> - **Janela deslizante:** As últimas **8 mensagens** (equilíbrio entre custo e contexto).
> - **Limite de tokens:** Manter em **200 tokens** de resposta (150 pode truncar respostas com endereços ou datas longas).

### 4.5 Estimativa de Custo de IA [NOVO]

Para previsibilidade financeira do produto, estimar o custo por conversa e monitorar o gasto mensal.

| Modelo | Custo estimado/1k tokens | Tokens médios/conversa | Custo/conversa |
|---|---|---|---|
| GPT-4o Mini (input) | ~$0.00015 | ~800 | ~$0.00012 |
| GPT-4o Mini (output) | ~$0.00060 | ~200 | ~$0.00012 |
| Whisper (áudio) | ~$0.006/min | ~1 min médio | ~$0.006 |
| **Total estimado/conversa** | | | **~$0.006** |

- Com 300 conversas/mês: custo estimado de IA ≈ **~$1,80/mês**.
- Configurar alerta no monitoramento quando gasto de tokens ultrapassar **$20/mês** (indicador de uso anormal).
- Rever modelo utilizado se custo/conversa ultrapassar **$0.05** de forma consistente.

### 4.6 Fluxo de Fallback da IA [REVISADO]

Definir comportamento explícito quando a IA falhar ou retornar erro:

1. **Erro de API da IA (timeout/500):** Responder ao cliente: *"Estou com uma instabilidade, mas já registramos seu contato. Em breve te retornamos!"* e atualizar `status_lead = 'pendente_revisao'` na tabela `clientes`.
2. **Loop detectado (3 mensagens sem progressão):** Acionar `iniciar_handoff_humano("loop_detectado")` automaticamente.
3. **Palavras-chave de urgência** (`urgente`, `emergência`, `acidente`): Transferir imediatamente para humano e notificar o gerente via WhatsApp.

---

## 5. Fluxo de Integração e Segurança (WhatsApp)

### 5.1 Gatilhos de Ativação e Tipos de Mídia

- O robô **ignora** mensagens de grupos.
- Para **imediatamente** se a etiqueta `pausar_robo` for adicionada no Chatwoot.
- Só inicia o fluxo se a primeira mensagem contiver a palavra `"anúncio"` (case-insensitive) **ou** se a etiqueta `robo_ativo` estiver ativa no contato.
- **Áudios** recebidos são transcritos pelo Whisper antes de serem enviados à IA.
- **Imagens:** Receber e salvar a URL da mídia no registro da conversa. Informar ao cliente que o atendente humano analisará a imagem.
- **Documentos (PDF/DOC):** Tratamento idêntico ao de imagens — salvar referência e acionar handoff humano se necessário.
- **Mensagens de Localização:** Extrair latitude/longitude e salvar como endereço da visita, confirmando com o cliente antes de registrar.
- **Stickers/Reações:** Ignorar silenciosamente, sem resposta.

> **Trigger "anúncio":** Aceitar variações como `"anuncio"` (sem acento) e normalizar o texto recebido antes da verificação para evitar falhas por digitação do usuário.

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
5. **Deduplicação de Mensagens:** Armazenar os últimos `message_id` recebidos em Redis com TTL de 60s para evitar processamento duplicado em caso de reentrega do webhook.

### 5.4 Fuso Horário e Horário Comercial

- Toda lógica de horário deve operar no fuso `America/Sao_Paulo`.
- O robô deve verificar o horário atual antes de responder mensagens iniciadas fora do horário comercial. Se fora do horário, enviar mensagem padrão de fora do expediente e registrar o lead para retorno no próximo dia útil.
- Consultar a tabela `feriados` antes de confirmar qualquer agendamento.

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

### 6.2 CORS [NOVO]

Configurar `WebMvcConfigurer` no Spring Boot para permitir requisições do frontend Angular:

```java
@Configuration
public class CorsConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            .allowedOrigins(
                "http://localhost:4200",          // desenvolvimento local
                "https://app.olaru.com.br"        // produção
            )
            .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)               // necessário para cookie httpOnly do refresh token
            .maxAge(3600);
    }
}
```

### 6.3 Rate Limiting na API REST [NOVO]

Adicionar dependência `bucket4j-spring-boot-starter` e configurar rate limiting por token JWT:

- **Endpoints de escrita** (POST, PUT, PATCH, DELETE): máximo **30 requests/minuto** por usuário.
- **Endpoints de leitura** (GET): máximo **120 requests/minuto** por usuário.
- **Endpoint de login** (`POST /api/v1/auth/login`): máximo **5 tentativas/minuto** por IP — retornar `429 Too Many Requests` após exceder.
- Usar Redis como backend do Bucket4j para compartilhar contadores entre instâncias.

### 6.4 Versionamento, Paginação e Documentação da API [REVISADO]

- Prefixar todos os endpoints com `/api/v1/` para facilitar versionamento futuro.
- Usar **Springdoc OpenAPI (Swagger UI)** para documentação automática dos endpoints.
- Todas as listagens devem suportar paginação via `Pageable` do Spring Data:
  - Parâmetros: `page` (0-based), `size` (padrão 20, máximo 100), `sort` (ex: `criado_em,desc`)
  - Resposta sempre no formato `Page<T>` com campos: `content`, `totalElements`, `totalPages`, `number`, `size`

**Catálogo completo de endpoints:**

```
# Autenticação
POST   /api/v1/auth/login              # Login com email + senha → JWT
POST   /api/v1/auth/refresh            # Renovar access token via refresh token (cookie httpOnly)
POST   /api/v1/auth/logout             # Invalidar sessão

# Health (público — sem autenticação)
GET    /api/v1/health                  # Saúde do serviço Spring Boot
GET    /actuator/health                # Spring Actuator
GET    /actuator/prometheus            # Métricas Prometheus

# Dashboard
GET    /api/v1/dashboard/indicadores   # KPIs: novos leads, visitas do dia, máquinas, handoffs

# Clientes / Leads
GET    /api/v1/clientes                # Lista paginada (filtros: status_lead, origem)
GET    /api/v1/clientes/{id}           # Detalhe do cliente
POST   /api/v1/clientes                # Cadastro manual
PATCH  /api/v1/clientes/{id}           # Atualização parcial

# Visitas Técnicas
GET    /api/v1/visitas                 # Lista paginada (filtros: status, data, equipe_id)
POST   /api/v1/visitas                 # Criar nova visita
GET    /api/v1/visitas/{id}            # Detalhe da visita
PATCH  /api/v1/visitas/{id}            # Atualização parcial
PATCH  /api/v1/visitas/{id}/status     # Mudar status (ex: pendente → confirmada)
POST   /api/v1/visitas/{id}/observacoes  # Registrar observação ao finalizar
POST   /api/v1/visitas/{id}/fotos      # Upload de foto (multipart/form-data)
GET    /api/v1/visitas/{id}/fotos      # Listar fotos da visita

# Máquinas
GET    /api/v1/maquinas                # Lista paginada (filtros: ativo, disponivel)
POST   /api/v1/maquinas                # Cadastrar máquina
GET    /api/v1/maquinas/{id}           # Detalhe
PATCH  /api/v1/maquinas/{id}           # Atualizar
DELETE /api/v1/maquinas/{id}           # Soft delete (ativo = false)

# Equipes
GET    /api/v1/equipes                 # Lista paginada
POST   /api/v1/equipes                 # Criar equipe
GET    /api/v1/equipes/{id}            # Detalhe
PATCH  /api/v1/equipes/{id}            # Atualizar
DELETE /api/v1/equipes/{id}            # Soft delete (ativo = false)

# Locações
GET    /api/v1/locacoes                # Lista paginada (filtros: status, maquina_id)
POST   /api/v1/locacoes                # Criar locação
GET    /api/v1/locacoes/{id}           # Detalhe
PATCH  /api/v1/locacoes/{id}/status    # Mudar status

# Usuários (somente admin)
GET    /api/v1/usuarios                # Lista de usuários do painel
POST   /api/v1/usuarios                # Criar usuário
PATCH  /api/v1/usuarios/{id}           # Atualizar
PATCH  /api/v1/usuarios/{id}/senha     # Redefinir senha

# Configurações do Robô (somente admin)
GET    /api/v1/configuracoes           # Listar todas as chaves
PATCH  /api/v1/configuracoes/{chave}   # Atualizar valor de uma chave

# Feriados (somente admin)
GET    /api/v1/feriados                # Listar feriados cadastrados
POST   /api/v1/feriados                # Cadastrar feriado manualmente
DELETE /api/v1/feriados/{id}           # Remover feriado

# Relatórios (admin + gerente)
GET    /api/v1/relatorios/leads        # Leads por período → CSV/XLSX
GET    /api/v1/relatorios/visitas      # Visitas por período → CSV/XLSX
```

### 6.5 Tratamento de Erros Padronizado

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

### 6.6 Notificações em Tempo Real (WebSocket / SSE)

Para atualizar o Kanban do gerente quando um técnico clicar em "Cheguei" ou "Finalizar":
- Usar **Server-Sent Events (SSE)** no Spring Boot como abordagem mais simples, ou **WebSocket (STOMP)** se bidirecionalidade for necessária.
- O frontend Angular se inscreve no canal de eventos e atualiza o card da visita sem recarregar a página.

---

## 7. Interface Web (Frontend Angular)

Arquitetura de telas com controle de acesso por tipo de usuário (RBAC).

### 7.1 Área do Dono/Gerência

- **Dashboard:** Indicadores chave (novos leads hoje, visitas do dia, máquinas disponíveis) e tabela de novos leads com botão para abrir a conversa no Chatwoot.
- **Configurações:** Definição de regras de agenda (horário de almoço, fins de semana, feriados) lidas pelo robô via tabela `configuracoes_agenda`. [CORRIGIDO — typo removido]
- **Visitas Técnicas:** Tela em formato **Kanban** para arrastar e soltar os cards entre colunas (`Pendente → Confirmada → Em Andamento → Concluída`).
- **Locações:** Controle visual do estoque de máquinas.
- **Relatórios:** Exportação de leads e visitas em CSV/XLSX por período.

### 7.2 Área Operacional (Técnicos em Campo)

- Tela simples **"Minhas Visitas"** otimizada para uso em celular (layout mobile-first).
- Botões de **"Cheguei no Local"** e **"Finalizar Visita"** que atualizam o Kanban do gerente em tempo real via SSE/WebSocket.
- Campo de observações ao finalizar a visita (mínimo 10 caracteres), com possibilidade de tirar foto (upload de imagem via câmera do celular).
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

### 8.2 Tracing Distribuído [NOVO]

Para rastrear requisições que cruzam os dois serviços (Python → Java), propagar um `trace_id` via header HTTP:

- **Python/FastAPI:** Gerar `X-Trace-Id` (UUID v4) na entrada do webhook e propagá-lo em todas as chamadas ao Spring Boot.
- **Java/Spring Boot:** Ler o header `X-Trace-Id` em um filtro global e incluí-lo em todos os logs como campo MDC (`MDC.put("traceId", traceId)`).
- Isso permite correlacionar no Grafana/Loki o ciclo completo: mensagem WhatsApp → IA Python → API Java.

### 8.3 Monitoramento e Alertas

- Expor métricas do FastAPI via `/metrics` (Prometheus format) usando `prometheus-fastapi-instrumentator`.
- Expor métricas do Spring Boot via **Spring Actuator** (`/actuator/prometheus`).
- Configurar alertas mínimos:
  - Fila de mensagens do WhatsApp travada há mais de 5 minutos.
  - Taxa de erros da IA acima de 10% em 1 hora.
  - Banco de dados inacessível.
  - **Gasto mensal de tokens de IA ultrapassou $20** (alerta de custo). [NOVO]
  - **Taxa de erros HTTP 5xx na API > 1% em 5 minutos.** [NOVO]
  - **Disco da VPS acima de 80% de uso.** [NOVO]

### 8.4 Health Check Endpoints [NOVO]

Ambos os serviços devem expor endpoints de health que o Nginx e o Docker Compose usam para verificar disponibilidade:

```python
# Python/FastAPI
@app.get("/health")
async def health():
    return {"status": "ok", "service": "middleware-python"}
```

```java
// Spring Boot — já exposto via Actuator
// GET /actuator/health → {"status": "UP", "components": {...}}
// Configurar em application.yml:
# management.endpoint.health.show-details=always
# management.endpoints.web.exposure.include=health,prometheus
```

Configurar no `docker-compose.yml`:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### 8.5 Backup

- Configurar backup automático do PostgreSQL com `pg_dump` diariamente (cron job na VPS).
- Enviar o dump comprimido para storage externo (ex: Backblaze B2 ou S3-compatible).
- Reter backups dos últimos 30 dias.

---

## 9. Plano de Validação (Testes)

### 9.1 Testes Unitários [NOVO]

**Python/FastAPI (pytest):**

```bash
# Instalar dependências de teste
pip install pytest pytest-asyncio httpx pytest-cov

# Executar com cobertura
pytest --cov=app --cov-report=html tests/
```

Cobertura mínima exigida: **70%** das funções do middleware Python.
Testar obrigatoriamente: lógica de horário comercial, deduplicação de mensagens, parsing de localização, validação do webhook secret.

**Java/Spring Boot (JUnit 5 + Mockito):**

```java
// Estrutura de testes
src/test/java/
  ├── unit/
  │   ├── service/VisitaServiceTest.java    // mockar repositório
  │   ├── service/MaquinaServiceTest.java
  │   └── security/JwtUtilTest.java
  └── integration/
      ├── controller/VisitaControllerTest.java  // @SpringBootTest + MockMvc
      └── repository/ClienteRepositoryTest.java // @DataJpaTest
```

Cobertura mínima exigida: **80%** nos serviços de domínio.

**Angular (Jest):**

```bash
# Executar testes
ng test --code-coverage

# Cobertura mínima
# statements: 70%, branches: 60%, lines: 70%
```

Testar obrigatoriamente: `AuthGuard`, `RoleGuard`, `NotificationService`, `OfflineQueueService`, pipe `RelativeTime`.

### 9.2 Testes de Segurança Anti-Ban

- Confirmar que o evento `"digitando..."` aparece via fila do Python antes de cada mensagem.
- Enviar 10 mensagens em sequência e verificar que o Python responde devagar, uma a uma (intervalo de 15-25s).
- Simular reinicialização do processo e confirmar que o contador de mensagens diárias persiste no Redis.

### 9.3 Testes de Banco de Dados

- Confirmar que o campo `telefone` é `UNIQUE` e que cadastros repetidos apenas atualizam o nome.
- Verificar que não é possível criar uma locação para máquina com `quantidade_disponivel = 0`.
- Verificar que `quantidade_disponivel` nunca excede `quantidade_total` (constraint da Seção 3.2).
- Testar que os índices criados estão sendo utilizados nas queries mais frequentes (via `EXPLAIN ANALYZE`).
- Verificar que o trigger `fn_atualizar_timestamp()` atualiza o campo `atualizado_em` corretamente. [NOVO]
- Verificar que a migration Flyway roda sem erros em banco limpo. [NOVO]

### 9.4 Testes de IA

- Forçar perguntas de preço/orçamento e validar que a IA desvia corretamente.
- Enviar áudio e validar a transcrição pelo Whisper antes de chegar à IA.
- Testar o fluxo de loop: enviar 3 mensagens sem progressão e verificar se o handoff humano é acionado.
- Simular falha na API da IA (timeout) e verificar se a mensagem de fallback é enviada.
- Verificar que o `status_lead` é atualizado corretamente em cada fase do funil. [NOVO]

### 9.5 Testes de Agenda

- Tentar agendar visita no domingo ou feriado — a IA deve recusar e negociar novo horário.
- Tentar agendar em horário de almoço — a IA deve verificar `configuracoes_agenda` e propor alternativa.
- Testar conflito de agenda: duas visitas no mesmo horário para a mesma equipe — o sistema não deve permitir.

### 9.6 Testes de Autenticação e RBAC

- Tentar acessar endpoint de gerente com token de técnico — deve retornar `403 Forbidden`.
- Testar expiração do access token e fluxo de refresh automático.
- Testar que senha incorreta retorna `401` e não vaza informação sobre o usuário existente.
- Verificar rate limiting: 6ª tentativa de login em 1 minuto deve retornar `429`. [NOVO]
- Testar CORS: requisição de origem não listada deve ser bloqueada. [NOVO]

### 9.7 Testes de Carga (Básico)

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
- [ ] Monitoramento básico ativo (logs + alertas de fila + custo de IA).
- [ ] Documentação da API gerada pelo Swagger disponível internamente.
- [ ] Usuários criados com perfis corretos (admin, gerente, técnico).
- [ ] Testes de fumaça executados em produção após deploy.
- [ ] Migrations Flyway aplicadas com sucesso em produção. [NOVO]
- [ ] CORS configurado com domínio de produção correto. [NOVO]
- [ ] Rate limiting ativo no endpoint de login. [NOVO]
- [ ] Health check respondendo em ambos os serviços. [NOVO]
- [ ] Trigger `fn_atualizar_timestamp()` criado antes das tabelas. [NOVO]
- [ ] Tabelas `agent_sessions` e `agent_memory` criadas antes de iniciar o Python. [NOVO]
- [ ] Política de retenção de dados configurada (cron de limpeza). [NOVO]
- [ ] Pipeline de CI/CD configurado e testado. [NOVO]

---

## 11. Pipeline de CI/CD [NOVO]

Configurar pipeline automatizado com **GitHub Actions** (ou equivalente) para garantir que nenhum código quebrado chegue à produção.

### 11.1 Pipeline do Pull Request (toda PR)

```yaml
# .github/workflows/pr.yml
name: PR Checks
on: [pull_request]
jobs:
  backend-java:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { java-version: '17', distribution: 'temurin' }
      - run: ./mvnw test                        # JUnit 5
      - run: ./mvnw verify -P coverage          # Jacoco — falha se < 80%

  backend-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=app --cov-fail-under=70

  frontend-angular:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci
      - run: ng test --watch=false --code-coverage
      - run: ng build --configuration production  # verificar build sem erros
```

### 11.2 Pipeline de Deploy (merge na branch `main`)

```yaml
# .github/workflows/deploy.yml
name: Deploy Production
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build e push imagens Docker
        run: |
          docker build -t olaru-java ./backend-java
          docker build -t olaru-python ./middleware-python
          docker build -t olaru-angular ./frontend
      - name: Deploy via SSH na VPS
        run: |
          ssh ${{ secrets.VPS_USER }}@${{ secrets.VPS_HOST }} \
            "cd /opt/olaru && docker compose pull && docker compose up -d --wait"
      - name: Smoke test pós-deploy
        run: |
          curl -f https://app.olaru.com.br/api/v1/health || exit 1
```

---

## 12. Decisões em Aberto (Pendências)

| # | Decisão | Opção A | Opção B | Impacto |
|---|---|---|---|---|
| 1 | Fila de WhatsApp | Redis Streams | asyncio.Queue | Redis é mais resiliente a reinicializações; asyncio é mais simples |
| 2 | Tempo real no Kanban | SSE | WebSocket (STOMP) | SSE é unidirecional e mais simples; WebSocket é bidirecional |
| 3 | Modelo de IA principal | GPT-4o Mini (custo) | GPT-4o (precisão) | Mini: ~$0.006/conv; 4o: ~$0.06/conv |
| 4 | App do técnico | PWA | App nativo | PWA elimina loja de apps mas tem limitações de câmera no iOS |
| 5 | Feriados | BrasilAPI (automático) | Cadastro manual | API é mais conveniente; manual dá mais controle |
| 6 | Tema do painel | Dark (conforme §13) | Light com toggle | Dark reduz fadiga; Light é mais familiar para não-técnicos |
| 7 | Drag-and-drop Kanban | CDK Angular (nativo) | @dnd-kit | CDK é zero-dep; @dnd-kit tem melhor suporte touch+teclado |
| 8 | Notificações push (técnico) | Web Push API (PWA) | WhatsApp via robô | Web Push requer permissão de browser; WhatsApp usa tokens do robô |
| 9 | Idioma do sistema | Português (BR) fixo | i18n pt-BR + es | i18n adiciona ~15% de custo inicial mas permite expansão |
| 10 | Onboarding novo admin | Wizard guiado (1ª entrada) | Vídeo tutorial externo | Wizard reduz suporte; adiciona ~1 sprint de desenvolvimento |
| 11 | Multi-tenancy | Single-tenant (atual) | Multi-tenant desde início | Multi-tenant exige `empresa_id` em todas as tabelas; avaliar escala do negócio antes de decidir |

---

## 13. LGPD — Conformidade e Privacidade de Dados [NOVO]

> **Atenção:** Esta seção é juridicamente obrigatória. A plataforma coleta nome, telefone, endereço e histórico de conversas de cidadãos brasileiros via WhatsApp, o que a sujeita integralmente à **Lei Geral de Proteção de Dados (Lei nº 13.709/2018)**.

### 13.1 Base Legal

O tratamento de dados pessoais dos clientes se apoia nas seguintes bases legais da LGPD:

- **Art. 7º, V — Execução de contrato:** coleta de nome, telefone e endereço para prestação do serviço contratado (locação de maquinário ou visita técnica).
- **Art. 7º, IX — Legítimo interesse:** uso do histórico de conversas para melhoria do atendimento e qualificação do lead.

### 13.2 Dados Coletados e Finalidade

| Dado | Finalidade | Retenção |
|---|---|---|
| Nome e telefone | Identificação e contato | Enquanto cliente ativo + 5 anos |
| Endereço da obra | Agendamento de visita | Enquanto visita ativa + 2 anos |
| Histórico de conversas | Contexto de atendimento | 12 meses |
| Fotos da visita | Documentação técnica | 24 meses |
| Audit log | Rastreabilidade operacional | 24 meses |

### 13.3 Direitos do Titular

Implementar endpoints para atender os direitos garantidos pelo Art. 18 da LGPD:

```
GET    /api/v1/lgpd/meus-dados/{telefone}   # Exportar todos os dados do titular
DELETE /api/v1/lgpd/esquecimento/{telefone} # Apagar dados (direito ao esquecimento)
GET    /api/v1/lgpd/portabilidade/{telefone} # Exportar em formato JSON estruturado
```

> **Atenção:** O endpoint de esquecimento deve verificar se há locações ativas ou visitas pendentes antes de apagar. Caso positivo, retornar erro explicando que o dado é necessário para conclusão do contrato.

### 13.4 Segurança e Notificação de Incidentes

- Dados pessoais em trânsito: sempre via HTTPS (TLS 1.2+).
- Senhas: sempre com hash `bcrypt` (custo mínimo 12).
- Em caso de vazamento de dados: notificar a ANPD em até **72 horas** e os titulares afetados.
- Manter registro de todas as operações de tratamento de dados (`audit_log`).

### 13.5 Política de Privacidade

- Disponibilizar Política de Privacidade em URL pública antes do primeiro contato via WhatsApp.
- A primeira mensagem do robô deve incluir link para a política e opção de opt-out (`"Digite SAIR para não receber mais mensagens"`).

---

## 14. Princípios de UI/UX Design (Frontend Angular)

> **Instrução para o agente de CLI:** Esta seção define TODAS as regras visuais, estruturais e de comportamento do frontend Angular. Antes de gerar qualquer componente, leia esta seção por completo. As regras aqui têm precedência sobre padrões genéricos de Angular Material ou Bootstrap. Referência visual interativa: `olaru-uiux-spec.html`.

---

### 14.1 Sistema de Design Tokens

Criar o arquivo `src/styles/_tokens.scss` com todas as variáveis abaixo. Este arquivo deve ser importado no `styles.scss` global com `@use 'tokens' as *`. **Nunca usar valores de cor, espaçamento ou tipografia hardcoded nos componentes — sempre referenciar um token.**

#### 14.1.1 Paleta de Cores

```scss
// src/styles/_tokens.scss

:root {
  // --- Cores de Marca ---
  --color-brand:          #F0A500;  // âmbar — cor primária de ação
  --color-brand-hover:    #D4920A;  // brand escurecido 10% para hover
  --color-brand-subtle:   rgba(240, 165, 0, 0.10); // fundo de badges brand

  // --- Backgrounds ---
  --color-bg:             #0D0F14;  // fundo raiz da aplicação
  --color-surface:        #161820;  // cards, painéis, sidebars
  --color-surface-2:      #1E2028;  // superfície elevada (inputs, hover rows)
  --color-surface-3:      #252830;  // superfície mais elevada (dropdowns, tooltips)

  // --- Bordas ---
  --color-border:         #2A2D38;  // borda padrão entre elementos
  --color-border-focus:   #F0A500;  // borda de foco em inputs e botões

  // --- Texto ---
  --color-text:           #E8EAF0;  // texto primário
  --color-text-secondary: #9CA3AF;  // texto de apoio, labels, metadados
  --color-text-disabled:  #4B5563;  // texto desabilitado

  // --- Semânticas de Estado ---
  --color-success:        #10B981;
  --color-success-subtle: rgba(16, 185, 129, 0.10);
  --color-warning:        #F59E0B;
  --color-warning-subtle: rgba(245, 158, 11, 0.10);
  --color-danger:         #EF4444;
  --color-danger-subtle:  rgba(239, 68, 68, 0.10);
  --color-info:           #3B82F6;
  --color-info-subtle:    rgba(59, 130, 246, 0.10);

  // --- Status de Visitas (Kanban) ---
  --color-status-pendente:     #6B7280;
  --color-status-confirmada:   #3B82F6;
  --color-status-andamento:    #F0A500;
  --color-status-concluida:    #10B981;
  --color-status-cancelada:    #EF4444;
}
```

> **Regra:** Não usar `--color-brand` para textos de corpo. Usar apenas para botões primários, ícones de destaque, e bordas de foco.

#### 14.1.2 Escala de Espaçamento (Base 4px)

```scss
:root {
  --spacing-1:  4px;
  --spacing-2:  8px;
  --spacing-3:  12px;
  --spacing-4:  16px;
  --spacing-5:  20px;
  --spacing-6:  24px;
  --spacing-8:  32px;
  --spacing-10: 40px;
  --spacing-12: 48px;
  --spacing-16: 64px;
}
```

> **Regra:** Nunca usar valores de espaçamento arbitrários (ex: `13px`, `22px`, `7px`). Se o design exigir, arredondar para o múltiplo de 4px mais próximo.

#### 14.1.3 Border Radius

```scss
:root {
  --radius-sm:   4px;    // badges, chips, tags
  --radius-md:   6px;    // botões, inputs, selects
  --radius-lg:   10px;   // cards, painéis, tabelas
  --radius-xl:   14px;   // modals, drawers, bottom sheets
  --radius-full: 9999px; // pills (usar com moderação)
}
```

#### 14.1.4 Sombras (Elevação)

```scss
:root {
  --shadow-0: none;
  --shadow-1: 0 1px 3px rgba(0, 0, 0, 0.40);
  --shadow-2: 0 4px 12px rgba(0, 0, 0, 0.50);
  --shadow-3: 0 8px 32px rgba(0, 0, 0, 0.60);
}
```

#### 14.1.5 Transições

```scss
:root {
  --transition-fast:   150ms ease;
  --transition-base:   200ms ease-out;
  --transition-slow:   250ms ease-in-out;
  --transition-kanban: 100ms ease;
}
```

---

### 14.2 Tipografia

#### 14.2.1 Fontes

Adicionar no `index.html` dentro do `<head>`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
```

#### 14.2.2 Escala Tipográfica

```scss
:root {
  --font-body:  'DM Sans', sans-serif;
  --font-mono:  'Space Mono', monospace;
  --text-xs:    11px;
  --text-sm:    12px;
  --text-base:  14px;
  --text-md:    16px;
  --text-lg:    20px;
  --text-xl:    24px;
  --text-2xl:   32px;
  --text-data:  28px;
  --font-light:    300;
  --font-regular:  400;
  --font-medium:   500;
  --font-semibold: 600;
  --font-bold:     700;
  --leading-tight:   1.2;
  --leading-base:    1.5;
  --leading-relaxed: 1.7;
}
```

#### 14.2.3 Classes de Texto Globais

Adicionar em `src/styles/_typography.scss`:

```scss
.text-heading-1 { font-family: var(--font-body); font-size: var(--text-2xl); font-weight: var(--font-bold); line-height: var(--leading-tight); color: var(--color-text); }
.text-heading-2 { font-family: var(--font-body); font-size: var(--text-xl); font-weight: var(--font-semibold); line-height: var(--leading-tight); color: var(--color-text); }
.text-body      { font-family: var(--font-body); font-size: var(--text-base); font-weight: var(--font-regular); line-height: var(--leading-base); color: var(--color-text); }
.text-secondary { font-family: var(--font-body); font-size: var(--text-base); color: var(--color-text-secondary); }
.text-caption   { font-family: var(--font-body); font-size: var(--text-xs); font-weight: var(--font-medium); letter-spacing: 0.06em; text-transform: uppercase; color: var(--color-text-secondary); }
.text-data      { font-family: var(--font-mono); font-size: var(--text-data); font-weight: var(--font-bold); color: var(--color-brand); line-height: 1; }
.text-mono      { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-text-secondary); }
```

---

### 14.3 Estrutura de Arquivos do Frontend

```
src/
├── app/
│   ├── core/
│   │   ├── guards/
│   │   │   ├── auth.guard.ts
│   │   │   └── role.guard.ts
│   │   ├── interceptors/
│   │   │   └── auth.interceptor.ts
│   │   ├── services/
│   │   │   ├── auth.service.ts
│   │   │   ├── notification.service.ts
│   │   │   ├── offline-queue.service.ts
│   │   │   └── sse.service.ts
│   │   └── models/
│   │       ├── visita.model.ts
│   │       ├── cliente.model.ts
│   │       ├── maquina.model.ts
│   │       └── usuario.model.ts
│   ├── shared/
│   │   ├── components/
│   │   │   ├── skeleton/
│   │   │   ├── empty-state/
│   │   │   ├── error-state/
│   │   │   ├── toast/
│   │   │   ├── confirm-dialog/
│   │   │   ├── status-badge/
│   │   │   └── offline-banner/
│   │   └── pipes/
│   │       └── relative-time.pipe.ts
│   ├── features/
│   │   ├── auth/login/
│   │   ├── dashboard/
│   │   ├── visitas/
│   │   │   ├── kanban/
│   │   │   └── form/
│   │   ├── maquinas/
│   │   ├── relatorios/
│   │   ├── configuracoes/
│   │   └── campo/minhas-visitas/
│   └── app.routes.ts
└── styles/
    ├── _tokens.scss
    ├── _typography.scss
    ├── _reset.scss
    └── styles.scss
```

---

### 14.4 Roteamento e Guards (RBAC no Frontend)

```typescript
// src/app/app.routes.ts
export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent) },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      { path: 'dashboard',     canActivate: [roleGuard(['admin', 'gerente'])], loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent) },
      { path: 'visitas',       canActivate: [roleGuard(['admin', 'gerente'])], loadComponent: () => import('./features/visitas/kanban/kanban.component').then(m => m.KanbanComponent) },
      { path: 'maquinas',      canActivate: [roleGuard(['admin', 'gerente'])], loadComponent: () => import('./features/maquinas/maquinas.component').then(m => m.MaquinasComponent) },
      { path: 'relatorios',    canActivate: [roleGuard(['admin', 'gerente'])], loadChildren: () => import('./features/relatorios/relatorios.routes').then(m => m.relatoriosRoutes) },
      { path: 'configuracoes', canActivate: [roleGuard(['admin'])],            loadChildren: () => import('./features/configuracoes/configuracoes.routes').then(m => m.configuracoesRoutes) },
      { path: 'campo',         canActivate: [roleGuard(['tecnico'])],          loadComponent: () => import('./features/campo/minhas-visitas/minhas-visitas.component').then(m => m.MinhasVisitasComponent) },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: '**', redirectTo: 'dashboard' }
    ]
  }
];
```

> **Regra:** `authGuard` verifica JWT no `sessionStorage`. Se expirado, tenta refresh via cookie `httpOnly`. Se falhar, redireciona para `/login`. `roleGuard` lê o campo `perfil` do payload JWT decodificado. Após login: admin/gerente → `/dashboard`, técnico → `/campo`.

---

### 14.5 Componentes Compartilhados (Shared)

#### 14.5.1 Skeleton Screen

```typescript
// src/app/shared/components/skeleton/skeleton.component.ts
@Component({
  selector: 'app-skeleton',
  standalone: true,
  template: `<div class="skeleton-block" [style.width]="width" [style.height]="height" [style.border-radius]="radius"></div>`,
  styles: [`
    .skeleton-block {
      background: linear-gradient(90deg, var(--color-surface-2) 25%, var(--color-border) 50%, var(--color-surface-2) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.4s infinite;
    }
    @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
    @media (prefers-reduced-motion: reduce) { .skeleton-block { animation: none; opacity: 0.5; } }
  `]
})
export class SkeletonComponent {
  @Input() width  = '100%';
  @Input() height = '16px';
  @Input() radius = 'var(--radius-sm)';
}
```

#### 14.5.2 Empty State

```typescript
// src/app/shared/components/empty-state/empty-state.component.ts
@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
    <div class="empty-state">
      <span class="empty-icon">{{ icon }}</span>
      <p class="empty-title">{{ title }}</p>
      <p class="empty-description">{{ description }}</p>
      @if (actionLabel) { <button class="btn-primary" (click)="action.emit()">{{ actionLabel }}</button> }
    </div>
  `
})
export class EmptyStateComponent {
  @Input() icon = '📭'; @Input() title = 'Nenhum item encontrado';
  @Input() description = ''; @Input() actionLabel = '';
  @Output() action = new EventEmitter<void>();
}
```

#### 14.5.3 Serviço de Notificações (Toast)

```typescript
// src/app/core/services/notification.service.ts
export type ToastType = 'success' | 'error' | 'warning' | 'info';
export interface Toast { id: string; type: ToastType; message: string; duration: number; undoFn?: () => void; }

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private toastsSubject = new BehaviorSubject<Toast[]>([]);
  toasts$ = this.toastsSubject.asObservable();
  success(message: string, undoFn?: () => void) { this.add({ type: 'success', message, duration: 5000, undoFn }); }
  error(message: string)   { this.add({ type: 'error',   message, duration: 0 }); }
  warning(message: string) { this.add({ type: 'warning', message, duration: 5000 }); }
  info(message: string)    { this.add({ type: 'info',    message, duration: 4000 }); }
  private add(toast: Omit<Toast, 'id'>) {
    const id = crypto.randomUUID();
    const current = this.toastsSubject.value;
    if (current.length >= 3) current.shift();
    this.toastsSubject.next([...current, { ...toast, id }]);
    if (toast.duration > 0) setTimeout(() => this.dismiss(id), toast.duration);
  }
  dismiss(id: string) { this.toastsSubject.next(this.toastsSubject.value.filter(t => t.id !== id)); }
}
```

Posicionamento dos toasts: **desktop** `bottom: 24px; right: 24px` · **mobile** `top: 16px; left: 50%; transform: translateX(-50%)`.

#### 14.5.4 Modal de Confirmação Destrutiva

```typescript
// src/app/shared/components/confirm-dialog/confirm-dialog.component.ts
@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  template: `
    <div class="overlay" (click)="cancel()">
      <div class="dialog" (click)="$event.stopPropagation()" role="dialog" [attr.aria-label]="title">
        <h3>{{ title }}</h3>
        <p>{{ message }}</p>
        <div class="dialog-actions">
          <button class="btn-outline" (click)="cancel()">Voltar</button>
          <button class="btn-danger"  (click)="confirm()">{{ confirmLabel }}</button>
        </div>
      </div>
    </div>
  `
})
export class ConfirmDialogComponent {
  @Input() title = 'Tem certeza?'; @Input() message = '';
  @Input() confirmLabel = 'Confirmar';  // DEVE ser verbo da ação: "Cancelar Visita", "Excluir Máquina"
  @Output() confirmed = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();
  confirm() { this.confirmed.emit(); }
  cancel()  { this.cancelled.emit(); }
}
```

#### 14.5.5 Status Badge

```typescript
// src/app/shared/components/status-badge/status-badge.component.ts
@Component({
  selector: 'app-status-badge',
  standalone: true,
  template: `<span class="badge" [ngClass]="'badge--' + status">{{ label }}</span>`,
  styles: [`
    .badge { display: inline-flex; align-items: center; gap: 4px; font-size: var(--text-xs); font-weight: var(--font-semibold); padding: 3px 8px; border-radius: var(--radius-sm); border: 1px solid; }
    .badge--pendente   { background: var(--color-surface-2);     color: var(--color-status-pendente);   border-color: var(--color-status-pendente); }
    .badge--confirmada { background: var(--color-info-subtle);   color: var(--color-status-confirmada); border-color: var(--color-info); }
    .badge--andamento  { background: var(--color-brand-subtle);  color: var(--color-status-andamento);  border-color: var(--color-brand); }
    .badge--concluida  { background: var(--color-success-subtle);color: var(--color-status-concluida);  border-color: var(--color-success); }
    .badge--cancelada  { background: var(--color-danger-subtle); color: var(--color-status-cancelada);  border-color: var(--color-danger); }
    .badge--urgente    { background: var(--color-danger-subtle); color: var(--color-danger);             border-color: var(--color-danger); }
    .badge--locacao    { background: var(--color-brand-subtle);  color: var(--color-brand);              border-color: var(--color-brand); }
    .badge--servico    { background: var(--color-info-subtle);   color: var(--color-info);               border-color: var(--color-info); }
  `]
})
export class StatusBadgeComponent {
  @Input({ required: true }) status!: string;
  @Input({ required: true }) label!: string;
}
```

---

### 14.6 Telas e Componentes por Feature

#### 14.6.1 Dashboard (`/dashboard`)

1. **Barra de saudação** — `"Bom dia/tarde/noite, {nome}"` com base no horário local + data atual.
2. **Grid de KPIs (4 cards):** Novos Leads Hoje · Visitas do Dia · Máquinas Disponíveis · Handoffs Pendentes.
3. **Tabela de Novos Leads** — paginação client-side (10 itens). Colunas: Nome, Tipo, Status, Há quanto tempo, Ação (botão "Abrir no Chatwoot").
4. **Lista de Equipes em Campo** — status em tempo real via SSE.

**Implementar skeleton para todos os 4 cards** enquanto `GET /api/v1/dashboard/indicadores` carrega. Ao receber evento SSE `novo_lead` ou `visita_atualizada`, atualizar apenas o dado afetado sem recarregar a página.

#### 14.6.2 Kanban de Visitas (`/visitas`)

**Dependência:** `@angular/cdk/drag-drop`

**Colunas (fixa, nesta ordem):** Pendente · Confirmada · Em Andamento · Concluída · Cancelada.

**Cada card exibe (sem expandir):** Nome do cliente · Endereço · Equipe (ou "Sem equipe" em warning) · Turno · Badge de tipo.

```typescript
// Transições permitidas — frontend bloqueia antes de chamar a API:
const transicoesPermitidas: Record<string, string[]> = {
  'pendente':     ['confirmada', 'cancelada'],
  'confirmada':   ['em_andamento', 'cancelada'],
  'em_andamento': ['concluida', 'cancelada'],
  'concluida':    [],
  'cancelada':    [],
};
// Sequência: validar → Optimistic UI → PATCH /api/v1/visitas/{id}/status → rollback se erro
```

**Suporte a teclado:** `Tab` navegar · `Space` pegar · `Arrow Left/Right` mover coluna · `Enter/Space` soltar · `Escape` cancelar. ARIA: `role="listitem"`, `aria-grabbed`, `aria-dropeffect`.

**SSE:** evento `tecnico_chegou` → mover para `em_andamento` + borda pulsando 3s · evento `visita_finalizada` → mover para `concluida`.

#### 14.6.3 Área do Técnico — Minhas Visitas (`/campo`)

> Testar SEMPRE em viewport 360×800 antes de qualquer outra resolução.

1. **Banner offline** (fixo no topo): invisível quando online · âmbar com contador de ações pendentes quando offline.
2. **Lista de visitas do dia** ordenada por horário crescente.
3. **Card de visita ativa:** botão `"📍 Cheguei no Local"` (status `confirmada`) · botão `"✅ Finalizar Visita"` (status `em_andamento`) · botão `"Ver no Mapa"` (Google Maps intent).
4. **Modal de finalização:** `textarea` de observações (mínimo 10 caracteres) + `<input type="file" accept="image/*" capture="environment">` para foto.

**Touch targets:** `min-height: 48px` em todos os botões · espaçamento mínimo de `8px` entre botões adjacentes · `font-size: 16px` nos inputs (evita zoom no iOS).

**Offline:** Ações salvas no `IndexedDB` → UI atualizada otimisticamente → sincronização via Background Sync ao reconectar.

#### 14.6.4 Tela de Login (`/login`)

- `type="email"` + `autocomplete="email"` · `type="password"` + `autocomplete="current-password"`.
- Botão desabilitado durante a requisição (evitar duplo envio).
- Erro 401: mensagem genérica `"E-mail ou senha incorretos"` — nunca informar qual dos dois está errado.
- Após sucesso: admin/gerente → `/dashboard` · técnico → `/campo`.

---

### 14.7 Estados de Interface — Regras Globais

**Todo componente com dados remotos deve implementar os 5 estados abaixo. Sem exceção.**

```typescript
interface ComponentState<T> {
  status: 'idle' | 'loading' | 'success' | 'error' | 'empty';
  data:   T | null;
  error:  string | null;
}
// Template: @switch (state.status) { @case ('loading') {...} @case ('error') {...} @case ('empty') {...} @case ('success') {...} }
```

**Estado Disabled:** opacidade `0.4` · `cursor: not-allowed` · `[title]` com o motivo · nunca ocultar o elemento.

**Estado Offline:** `OfflineBannerComponent` no layout root de `/campo` · detectar via `navigator.onLine` + eventos `online/offline` · sync automático ao reconectar.

---

### 14.8 Acessibilidade — Regras Obrigatórias (WCAG 2.1 AA)

| Contexto | Contraste mínimo |
|---|---|
| Texto normal (< 18px) | 4.5:1 |
| Texto grande (≥ 18px bold ou ≥ 24px) | 3:1 |
| Componentes UI (bordas, ícones) | 3:1 |

```scss
// src/styles/_reset.scss — foco visível global
:focus-visible { outline: 2px solid var(--color-brand); outline-offset: 3px; border-radius: var(--radius-sm); }
:focus:not(:focus-visible) { outline: none; }

// Respeitar preferências de movimento reduzido
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

- `<button>` para ações · `<a [routerLink]>` para navegação · `<label for>` em todos os inputs.
- Ícones sem texto: `aria-label="descrição"` ou `aria-hidden="true"` se decorativo.
- Fotos: `alt="Foto da visita em {endereco} em {data}"`.

---

### 14.9 Responsividade e PWA

**Breakpoints:**

| Nome | Min-width | Contexto |
|---|---|---|
| xs | — | Técnico em campo (360px) |
| sm | 480px | Mobile grande |
| md | 768px | Tablet |
| lg | 1024px | Desktop |
| xl | 1280px | Desktop largo |

**Regras de layout:**

| Elemento | Mobile (xs/sm) | Desktop (md+) |
|---|---|---|
| Sidebar | Bottom navigation (4 ícones) | Sidebar lateral colapsável (240px) |
| Dashboard KPIs | 2 colunas | 4 colunas |
| Kanban | Scroll horizontal | Todas as colunas visíveis |
| Tabela de leads | Cards verticais | Tabela com colunas |

**Checklist PWA (`ngsw-config.json` via `ng add @angular/pwa`):**

```json
{
  "index": "/index.html",
  "assetGroups": [{ "name": "app-shell", "installMode": "prefetch", "resources": { "files": ["/favicon.ico", "/index.html", "/*.css", "/*.js"] } }],
  "dataGroups": [{ "name": "visitas-api", "urls": ["/api/v1/visitas**"], "cacheConfig": { "strategy": "freshness", "maxSize": 50, "maxAge": "1h", "timeout": "5s" } }]
}
```

`manifest.webmanifest`:

```json
{
  "name": "OLARU — Campo", "short_name": "OLARU",
  "start_url": "/campo", "display": "standalone",
  "background_color": "#0D0F14", "theme_color": "#F0A500",
  "icons": [
    { "src": "icons/icon-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icons/icon-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

> **iOS Safari:** Testar `capture="environment"` em iPhone físico — pode não funcionar em PWA instalada.

---

### 14.10 Performance Percebida

**Optimistic UI no Kanban:** mover card imediatamente → toast success com "Desfazer" (5s) → PATCH em background → rollback se erro.

**Lazy Loading obrigatório:** `/relatorios` e `/configuracoes` devem ser lazy. `/dashboard`, `/login` e `/campo` devem ser eager.

**Core Web Vitals (meta para Lighthouse CI):**

| Métrica | Meta |
|---|---|
| LCP | < 2.5s |
| INP | < 100ms |
| CLS | < 0.1 |
| Bundle inicial (gzip) | < 300KB |

---

### 14.11 Checklist de UI/UX para Deploy

- [ ] `src/styles/_tokens.scss` criado com todas as variáveis CSS da Seção 14.1
- [ ] Fontes DM Sans e Space Mono no `index.html` com `font-display: swap`
- [ ] 5 estados de UI implementados em todos os componentes com dados remotos
- [ ] `NotificationService` integrado em todos os fluxos de CRUD
- [ ] `ConfirmDialogComponent` em todas as ações destrutivas com `confirmLabel` descritivo
- [ ] Kanban com suporte a teclado e ARIA completo
- [ ] Contraste WCAG AA validado para todas as combinações de texto/fundo
- [ ] Touch targets ≥ 48×48px em todos os botões da área `/campo`
- [ ] `font-size: 16px` em todos os inputs mobile
- [ ] PWA configurado: manifest, ngsw, ícones 192×512
- [ ] Modo offline: IndexedDB + Background Sync + `OfflineBannerComponent`
- [ ] `prefers-reduced-motion` aplicado globalmente
- [ ] Lazy loading em `/relatorios` e `/configuracoes`
- [ ] Lighthouse CI no pipeline com metas definidas
- [ ] Câmera mobile testada em dispositivo iOS físico
- [ ] Optimistic UI no Kanban com rollback em caso de erro
- [ ] Redirect pós-login por perfil implementado

---

> **Referência visual:** Abrir o arquivo `olaru-uiux-spec.html` no navegador para visualizar mockups, wireframes e paleta de cores interativamente. Este `.md` é a fonte de verdade para implementação; o `.html` é a referência visual para humanos.
