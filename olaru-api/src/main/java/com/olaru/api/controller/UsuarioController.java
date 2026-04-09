package com.olaru.api.controller;

import com.olaru.api.dto.SenhaRequest;
import com.olaru.api.dto.UsuarioRequest;
import com.olaru.api.entity.Equipe;
import com.olaru.api.entity.Perfil;
import com.olaru.api.entity.Usuario;
import com.olaru.api.repository.EquipeRepository;
import com.olaru.api.repository.UsuarioRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/usuarios")
@RequiredArgsConstructor
@Tag(name = "Usuários", description = "Gestão de usuários do painel administrativo")
public class UsuarioController {

    private final UsuarioRepository repository;
    private final EquipeRepository equipeRepository;
    private final PasswordEncoder passwordEncoder;

    @GetMapping
    @Operation(summary = "Listar todos os usuários ativos")
    public List<Usuario> listar() {
        return repository.findByAtivoTrue();
    }

    @GetMapping("/tecnicos")
    @Operation(summary = "Listar técnicos ativos (usado pelo kanban)")
    public List<Usuario> listarTecnicos() {
        return repository.findByPerfilAndAtivoTrue(Perfil.TECNICO);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Buscar usuário por ID")
    public ResponseEntity<Usuario> buscarPorId(@PathVariable UUID id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Criar novo usuário")
    public ResponseEntity<?> criar(@RequestBody UsuarioRequest request) {
        if (request.getSenha() == null || request.getSenha().isBlank()) {
            return ResponseEntity.badRequest().body("Senha é obrigatória na criação.");
        }
        if (request.getSenha().length() < 8) {
            return ResponseEntity.badRequest().body("A senha deve ter pelo menos 8 caracteres.");
        }
        if (repository.findByEmail(request.getEmail().trim().toLowerCase()).isPresent()) {
            return ResponseEntity.badRequest().body("E-mail já está em uso.");
        }

        Perfil perfil = parsePerfil(request.getPerfil());
        if (perfil == null) {
            return ResponseEntity.badRequest().body("Perfil inválido. Use: admin, gerente ou tecnico.");
        }

        Usuario usuario = Usuario.builder()
                .nome(request.getNome())
                .email(request.getEmail().trim().toLowerCase())
                .senha(passwordEncoder.encode(request.getSenha()))
                .perfil(perfil)
                .equipe(resolverEquipe(request.getEquipeId()))
                .ativo(true)
                .build();

        return ResponseEntity.ok(repository.save(usuario));
    }

    @PatchMapping("/{id}")
    @Operation(summary = "Atualizar dados do usuário")
    public ResponseEntity<?> atualizar(@PathVariable UUID id, @RequestBody UsuarioRequest request, Authentication auth) {
        // Impede que um admin remova seu próprio perfil (auto-rebaixamento causaria lockout)
        if (request.getPerfil() != null) {
            Usuario currentUser = (Usuario) auth.getPrincipal();
            if (currentUser.getId().equals(id)) {
                return ResponseEntity.badRequest().body("Não é permitido alterar o próprio perfil.");
            }
        }

        return repository.findById(id)
                .map(usuario -> {
                    if (request.getNome() != null) usuario.setNome(request.getNome());
                    if (request.getEmail() != null) usuario.setEmail(request.getEmail().trim().toLowerCase());
                    if (request.getPerfil() != null) {
                        Perfil perfil = parsePerfil(request.getPerfil());
                        if (perfil != null) usuario.setPerfil(perfil);
                    }
                    if (request.getEquipeId() != null) {
                        usuario.setEquipe(resolverEquipe(request.getEquipeId()));
                    }
                    return ResponseEntity.ok(repository.save(usuario));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PatchMapping("/{id}/senha")
    @Operation(summary = "Redefinir senha do usuário")
    public ResponseEntity<?> redefinirSenha(@PathVariable UUID id,
                                             @RequestBody @Valid SenhaRequest request) {
        return repository.findById(id)
                .map(usuario -> {
                    usuario.setSenha(passwordEncoder.encode(request.getNovaSenha()));
                    repository.save(usuario);
                    return ResponseEntity.ok().body("Senha atualizada com sucesso.");
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Desativar usuário (soft delete)")
    public ResponseEntity<Void> desativar(@PathVariable UUID id) {
        return repository.findById(id)
                .map(usuario -> {
                    usuario.setAtivo(false);
                    repository.save(usuario);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    // --- helpers ---

    private Perfil parsePerfil(String value) {
        if (value == null) return null;
        try {
            return Perfil.valueOf(value.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    private Equipe resolverEquipe(UUID equipeId) {
        if (equipeId == null) return null;
        return equipeRepository.findById(equipeId).orElse(null);
    }
}
