package com.olaru.api.dto;

import lombok.Data;
import java.time.LocalDate;

@Data
public class VisitaRequest {
    private String telefone;
    private String descricaoServico;
    private String endereco;
    private LocalDate dataVisita;
    private String turno;
}
