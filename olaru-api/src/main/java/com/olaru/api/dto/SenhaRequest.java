package com.olaru.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class SenhaRequest {
    @NotBlank
    @Size(min = 8, message = "A senha deve ter pelo menos 8 caracteres.")
    private String novaSenha;
}
