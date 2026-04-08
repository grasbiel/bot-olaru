package com.olaru.api.controller;

import com.olaru.api.entity.Equipe;
import com.olaru.api.repository.EquipeRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/equipes")
@RequiredArgsConstructor
@Tag(name = "Equipes", description = "Endpoints para gestão de equipes de campo")
public class EquipeController {

    private final EquipeRepository repository;

    @GetMapping
    @Operation(summary = "Listar equipes ativas")
    public List<Equipe> listar() {
        return repository.findByAtivoTrue();
    }

    @GetMapping("/{id}")
    @Operation(summary = "Buscar equipe por ID")
    public ResponseEntity<Equipe> buscarPorId(@PathVariable UUID id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Cadastrar nova equipe")
    public Equipe salvar(@RequestBody @Valid Equipe equipe) {
        return repository.save(equipe);
    }

    @PatchMapping("/{id}")
    @Operation(summary = "Atualizar dados da equipe")
    public ResponseEntity<Equipe> atualizar(@PathVariable UUID id, @RequestBody Equipe dados) {
        return repository.findById(id)
                .map(equipe -> {
                    if (dados.getNome() != null) equipe.setNome(dados.getNome());
                    if (dados.getTelefoneWhatsapp() != null) equipe.setTelefoneWhatsapp(dados.getTelefoneWhatsapp());
                    if (dados.getEspecialidade() != null) equipe.setEspecialidade(dados.getEspecialidade());
                    if (dados.getAtivo() != null) equipe.setAtivo(dados.getAtivo());
                    return ResponseEntity.ok(repository.save(equipe));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Desativar equipe (soft delete)")
    public ResponseEntity<Void> desativar(@PathVariable UUID id) {
        return repository.findById(id)
                .map(equipe -> {
                    equipe.setAtivo(false);
                    repository.save(equipe);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
