package com.olaru.api.controller;

import com.olaru.api.entity.Maquina;
import com.olaru.api.repository.MaquinaRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/maquinas")
@RequiredArgsConstructor
@Tag(name = "Máquinas", description = "Endpoints para gestão de estoque e equipamentos")
public class MaquinaController {

    private final MaquinaRepository repository;

    @GetMapping
    @Operation(summary = "Listar máquinas ativas")
    public List<Maquina> listar() {
        return repository.findByAtivoTrue();
    }

    @GetMapping("/{id}")
    @Operation(summary = "Buscar máquina por ID")
    public ResponseEntity<Maquina> buscarPorId(@PathVariable UUID id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/estoque/{nome}")
    @Operation(summary = "Consultar estoque por nome")
    public ResponseEntity<Maquina> consultarEstoque(@PathVariable String nome) {
        return repository.findByNomeContainingIgnoreCaseAndAtivoTrue(nome)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Cadastrar nova máquina")
    public Maquina salvar(@RequestBody Maquina maquina) {
        return repository.save(maquina);
    }

    @PutMapping("/{id}")
    @Operation(summary = "Atualizar máquina existente")
    public ResponseEntity<Maquina> atualizar(@PathVariable UUID id, @RequestBody Maquina maquina) {
        return repository.findById(id)
                .map(m -> {
                    m.setNome(maquina.getNome());
                    m.setDescricao(maquina.getDescricao());
                    m.setQuantidadeTotal(maquina.getQuantidadeTotal());
                    m.setQuantidadeDisponivel(maquina.getQuantidadeDisponivel());
                    m.setValorDiaria(maquina.getValorDiaria());
                    m.setAtivo(maquina.getAtivo());
                    return ResponseEntity.ok(repository.save(m));
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Desativar máquina (soft delete)")
    public ResponseEntity<Void> desativar(@PathVariable UUID id) {
        return repository.findById(id)
                .map(m -> {
                    m.setAtivo(false);
                    repository.save(m);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
