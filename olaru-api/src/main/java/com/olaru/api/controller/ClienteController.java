package com.olaru.api.controller;

import com.olaru.api.entity.Cliente;
import com.olaru.api.repository.ClienteRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/clientes")
@RequiredArgsConstructor
@Tag(name = "Clientes", description = "Endpoints para gestão de leads e clientes")
public class ClienteController {

    private final ClienteRepository repository;

    @GetMapping
    @Operation(summary = "Listar todos os clientes")
    public List<Cliente> listar() {
        return repository.findAll();
    }

    @GetMapping("/telefone/{telefone}")
    @Operation(summary = "Buscar cliente por telefone")
    public ResponseEntity<Cliente> buscarPorTelefone(@PathVariable String telefone) {
        return repository.findByTelefone(telefone)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Registrar novo lead/cliente")
    public Cliente salvar(@RequestBody Cliente cliente) {
        // Lógica de On Conflict do SQL original (via JPA)
        return repository.findByTelefone(cliente.getTelefone())
                .map(existente -> {
                    existente.setNome(cliente.getNome());
                    return repository.save(existente);
                })
                .orElseGet(() -> repository.save(cliente));
    }
}
