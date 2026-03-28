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
    @Operation(summary = "Listar todas as máquinas")
    public List<Maquina> listar() {
        return repository.findAll();
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
        return repository.findByNomeContainingIgnoreCase(nome)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Cadastrar nova máquina")
    public Maquina salvar(@RequestBody Maquina maquina) {
        return repository.save(maquina);
    }
}
