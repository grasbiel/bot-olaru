package com.olaru.api.controller;

import com.olaru.api.dto.VisitaRequest;
import com.olaru.api.entity.Cliente;
import com.olaru.api.entity.VisitaTecnica;
import com.olaru.api.repository.ClienteRepository;
import com.olaru.api.repository.VisitaTecnicaRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/visitas")
@RequiredArgsConstructor
@Tag(name = "Visitas Técnicas", description = "Endpoints para agendamento e kanban")
public class VisitaTecnicaController {

    private final VisitaTecnicaRepository repository;
    private final ClienteRepository clienteRepository;

    @GetMapping
    @Operation(summary = "Listar todas as visitas com filtro opcional de data")
    public List<VisitaTecnica> listar(@RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate data) {
        if (data != null) {
            return repository.findByDataVisitaOrderByCriadoEmDesc(data);
        }
        return repository.findAllByOrderByDataVisitaDescCriadoEmDesc();
    }

    @GetMapping("/disponibilidade")
    @Operation(summary = "Verificar disponibilidade de agenda")
    public ResponseEntity<Map<String, Object>> verificarDisponibilidade(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate data,
            @RequestParam String turno) {
        
        long agendados = repository.countByDataVisitaAndTurnoAndStatusNot(data, turno, "cancelada");
        boolean disponivel = agendados < 3; // Regra de negócio: máx 3 visitas por turno
        
        return ResponseEntity.ok(Map.of(
            "data", data,
            "turno", turno,
            "disponivel", disponivel,
            "agendamentos_atuais", agendados
        ));
    }

    @PostMapping
    @Operation(summary = "Agendar nova visita técnica")
    public ResponseEntity<?> agendar(@RequestBody VisitaRequest request) {
        Cliente cliente = clienteRepository.findByTelefone(request.getTelefone())
                .orElse(null);
        
        if (cliente == null) {
            return ResponseEntity.badRequest().body("Cliente não encontrado com o telefone: " + request.getTelefone());
        }

        VisitaTecnica visita = VisitaTecnica.builder()
                .cliente(cliente)
                .descricaoServico(request.getDescricaoServico())
                .endereco(request.getEndereco())
                .dataVisita(request.getDataVisita())
                .turno(request.getTurno())
                .status("pendente")
                .build();

        return ResponseEntity.ok(repository.save(visita));
    }

    @PatchMapping("/{id}/status")
    @Operation(summary = "Atualizar status da visita (Kanban)")
    public ResponseEntity<VisitaTecnica> atualizarStatus(@PathVariable UUID id, @RequestBody Map<String, String> body) {
        String novoStatus = body.get("status");
        return repository.findById(id)
                .map(visita -> {
                    visita.setStatus(novoStatus);
                    return ResponseEntity.ok(repository.save(visita));
                })
                .orElse(ResponseEntity.notFound().build());
    }
}
