package com.olaru.api.dto;

import lombok.Data;
import java.util.UUID;

@Data
public class UsuarioRequest {
    private String nome;
    private String email;
    private String senha;    // obrigatório na criação, opcional na atualização
    private String perfil;   // "admin", "gerente" ou "tecnico"
    private UUID equipeId;
}
