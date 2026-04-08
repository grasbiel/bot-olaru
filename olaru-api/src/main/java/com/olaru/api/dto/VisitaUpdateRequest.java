package com.olaru.api.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.UUID;

@Data
public class VisitaUpdateRequest {
    private String descricaoServico;
    private String endereco;
    private LocalDate dataVisita;
    private String turno;
    private UUID tecnicoId;
}
