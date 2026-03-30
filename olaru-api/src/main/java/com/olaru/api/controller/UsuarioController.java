package com.olaru.api.controller;

import com.olaru.api.entity.Perfil;
import com.olaru.api.entity.Usuario;
import com.olaru.api.repository.UsuarioRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/usuarios")
@RequiredArgsConstructor
@Tag(name = "Usuários", description = "Gestão de usuários e perfis")
public class UsuarioController {

    private final UsuarioRepository repository;

    @GetMapping("/tecnicos")
    @Operation(summary = "Listar todos os técnicos ativos")
    public List<Usuario> listarTecnicos() {
        return repository.findByPerfilAndAtivoTrue(Perfil.TECNICO);
    }
}
