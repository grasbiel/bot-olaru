package com.olaru.api.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class TokenDto {
    private String token;
    private String tipo;
    private UsuarioResumoDto usuario;

    @Data
    @AllArgsConstructor
    public static class UsuarioResumoDto {
        private String nome;
        private String email;
        private String perfil;
    }
}
