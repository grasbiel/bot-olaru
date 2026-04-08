-- Observações registradas pelo técnico ao finalizar a visita
CREATE TABLE observacoes_visita (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visita_id   UUID NOT NULL REFERENCES visitas_tecnicas(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    conteudo    TEXT NOT NULL CHECK (length(conteudo) >= 10),
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_observacoes_visita ON observacoes_visita(visita_id);

-- Fotos tiradas pelo técnico durante/após a visita
CREATE TABLE fotos_visita (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visita_id   UUID NOT NULL REFERENCES visitas_tecnicas(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    url         TEXT NOT NULL,
    mime_type   VARCHAR(50) NOT NULL,
    tamanho_kb  INT,
    criado_em   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fotos_visita ON fotos_visita(visita_id);
