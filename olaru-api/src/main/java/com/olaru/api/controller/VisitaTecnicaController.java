package com.olaru.api.controller;

import com.olaru.api.dto.VisitaRequest;
import com.olaru.api.dto.VisitaUpdateRequest;
import com.olaru.api.entity.*;
import com.olaru.api.repository.*;
import com.olaru.api.security.SseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/visitas")
@RequiredArgsConstructor
@Tag(name = "Visitas Técnicas", description = "Endpoints para agendamento, kanban e finalização")
public class VisitaTecnicaController {

    private final VisitaTecnicaRepository repository;
    private final ClienteRepository clienteRepository;
    private final UsuarioRepository usuarioRepository;
    private final ObservacaoVisitaRepository observacaoRepository;
    private final FotoVisitaRepository fotoRepository;
    private final SseService sseService;

    @Value("${app.upload.dir:./uploads}")
    private String uploadDir;

    @Value("${app.upload.base-url:http://localhost:8080}")
    private String baseUrl;

    // -------------------------------------------------------------------------
    // Streaming em tempo real
    // -------------------------------------------------------------------------

    @GetMapping("/stream")
    @Operation(summary = "Inscrever-se para atualizações em tempo real (SSE)")
    public SseEmitter stream() {
        return sseService.subscribe();
    }

    // -------------------------------------------------------------------------
    // Listagens
    // -------------------------------------------------------------------------

    @GetMapping
    @Operation(summary = "Listar todas as visitas com filtro opcional de data")
    public List<VisitaTecnica> listar(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate data) {
        if (data != null) return repository.findByDataVisitaOrderByCriadoEmDesc(data);
        return repository.findAllByOrderByDataVisitaDescCriadoEmDesc();
    }

    @GetMapping("/minhas")
    @Operation(summary = "Listar visitas do técnico logado para o dia atual")
    public List<VisitaTecnica> listarMinhasVisitas(Authentication authentication) {
        return repository.findByTecnicoEmailAndDataVisitaOrderByCriadoEmDesc(
                authentication.getName(), LocalDate.now());
    }

    // -------------------------------------------------------------------------
    // CRUD individual
    // -------------------------------------------------------------------------

    @GetMapping("/{id}")
    @Operation(summary = "Buscar visita por ID")
    public ResponseEntity<VisitaTecnica> buscarPorId(@PathVariable UUID id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    @Operation(summary = "Agendar nova visita técnica")
    public ResponseEntity<?> agendar(@RequestBody VisitaRequest request) {
        Cliente cliente = clienteRepository.findByTelefone(request.getTelefone()).orElse(null);
        if (cliente == null) {
            return ResponseEntity.badRequest().body("Cliente não encontrado: " + request.getTelefone());
        }

        VisitaTecnica visita = VisitaTecnica.builder()
                .cliente(cliente)
                .descricaoServico(request.getDescricaoServico())
                .endereco(request.getEndereco())
                .dataVisita(request.getDataVisita())
                .turno(request.getTurno())
                .status("pendente")
                .build();

        VisitaTecnica salva = repository.save(visita);
        sseService.broadcast("visita-atualizada", "novo-agendamento");
        return ResponseEntity.ok(salva);
    }

    @PatchMapping("/{id}")
    @Operation(summary = "Atualizar dados da visita")
    public ResponseEntity<VisitaTecnica> atualizar(@PathVariable UUID id,
                                                    @RequestBody VisitaUpdateRequest dados) {
        return repository.findById(id)
                .map(visita -> {
                    if (dados.getDescricaoServico() != null) visita.setDescricaoServico(dados.getDescricaoServico());
                    if (dados.getEndereco() != null) visita.setEndereco(dados.getEndereco());
                    if (dados.getDataVisita() != null) visita.setDataVisita(dados.getDataVisita());
                    if (dados.getTurno() != null) visita.setTurno(dados.getTurno());
                    if (dados.getTecnicoId() != null) {
                        usuarioRepository.findById(dados.getTecnicoId()).ifPresent(visita::setTecnico);
                    }
                    VisitaTecnica salva = repository.save(visita);
                    sseService.broadcast("visita-atualizada", "edicao");
                    return ResponseEntity.ok(salva);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PatchMapping("/{id}/atribuir")
    @Operation(summary = "Atribuir técnico a uma visita")
    public ResponseEntity<VisitaTecnica> atribuirTecnico(@PathVariable UUID id,
                                                          @RequestBody Map<String, UUID> body) {
        return repository.findById(id)
                .map(visita -> {
                    usuarioRepository.findById(body.get("tecnicoId")).ifPresent(visita::setTecnico);
                    VisitaTecnica salva = repository.save(visita);
                    sseService.broadcast("visita-atualizada", "atribuicao");
                    return ResponseEntity.ok(salva);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @PatchMapping("/{id}/status")
    @Operation(summary = "Atualizar status da visita (Kanban)")
    public ResponseEntity<VisitaTecnica> atualizarStatus(@PathVariable UUID id,
                                                          @RequestBody Map<String, String> body) {
        return repository.findById(id)
                .map(visita -> {
                    visita.setStatus(body.get("status"));
                    VisitaTecnica salva = repository.save(visita);
                    sseService.broadcast("visita-atualizada", body.get("status"));
                    return ResponseEntity.ok(salva);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    // -------------------------------------------------------------------------
    // Disponibilidade de agenda (usada pelo bot)
    // -------------------------------------------------------------------------

    @GetMapping("/disponibilidade")
    @Operation(summary = "Verificar disponibilidade de agenda")
    public ResponseEntity<Map<String, Object>> verificarDisponibilidade(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate data,
            @RequestParam String turno) {

        long agendados = repository.countByDataVisitaAndTurnoAndStatusNot(data, turno, "cancelada");
        boolean disponivel = agendados < 3;

        return ResponseEntity.ok(Map.of(
                "data", data,
                "turno", turno,
                "disponivel", disponivel,
                "agendamentos_atuais", agendados));
    }

    // -------------------------------------------------------------------------
    // Observações
    // -------------------------------------------------------------------------

    @PostMapping("/{id}/observacoes")
    @Operation(summary = "Registrar observação ao finalizar a visita")
    public ResponseEntity<?> registrarObservacao(@PathVariable UUID id,
                                                  @RequestBody Map<String, String> body,
                                                  Authentication authentication) {
        String conteudo = body.get("conteudo");
        if (conteudo == null || conteudo.trim().length() < 10) {
            return ResponseEntity.badRequest().body("Observação deve ter no mínimo 10 caracteres.");
        }

        VisitaTecnica visita = repository.findById(id).orElse(null);
        if (visita == null) return ResponseEntity.notFound().build();

        Usuario tecnico = (Usuario) authentication.getPrincipal();

        ObservacaoVisita obs = ObservacaoVisita.builder()
                .visita(visita)
                .usuario(tecnico)
                .conteudo(conteudo.trim())
                .build();

        return ResponseEntity.ok(observacaoRepository.save(obs));
    }

    @GetMapping("/{id}/observacoes")
    @Operation(summary = "Listar observações de uma visita")
    public ResponseEntity<List<ObservacaoVisita>> listarObservacoes(@PathVariable UUID id) {
        if (!repository.existsById(id)) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(observacaoRepository.findByVisitaIdOrderByCriadoEmDesc(id));
    }

    // -------------------------------------------------------------------------
    // Fotos
    // -------------------------------------------------------------------------

    @PostMapping("/{id}/fotos")
    @Operation(summary = "Fazer upload de foto da visita")
    public ResponseEntity<?> uploadFoto(@PathVariable UUID id,
                                         @RequestParam("foto") MultipartFile arquivo,
                                         Authentication authentication) throws IOException {

        if (arquivo.isEmpty()) return ResponseEntity.badRequest().body("Arquivo vazio.");

        String mimeType = arquivo.getContentType();
        if (mimeType == null || !mimeType.startsWith("image/")) {
            return ResponseEntity.badRequest().body("Apenas imagens são permitidas.");
        }

        VisitaTecnica visita = repository.findById(id).orElse(null);
        if (visita == null) return ResponseEntity.notFound().build();

        // Salva o arquivo no diretório de uploads
        String extensao = mimeType.contains("png") ? ".png" : ".jpg";
        String nomeArquivo = UUID.randomUUID() + extensao;
        Path destino = Paths.get(uploadDir, "visitas", nomeArquivo);
        Files.copy(arquivo.getInputStream(), destino);

        String urlPublica = baseUrl + "/uploads/visitas/" + nomeArquivo;
        int tamanhoKb = (int) (arquivo.getSize() / 1024);

        Usuario tecnico = (Usuario) authentication.getPrincipal();

        FotoVisita foto = FotoVisita.builder()
                .visita(visita)
                .usuario(tecnico)
                .url(urlPublica)
                .mimeType(mimeType)
                .tamanhoKb(tamanhoKb)
                .build();

        return ResponseEntity.ok(fotoRepository.save(foto));
    }

    @GetMapping("/{id}/fotos")
    @Operation(summary = "Listar fotos de uma visita")
    public ResponseEntity<List<FotoVisita>> listarFotos(@PathVariable UUID id) {
        if (!repository.existsById(id)) return ResponseEntity.notFound().build();
        return ResponseEntity.ok(fotoRepository.findByVisitaIdOrderByCriadoEmDesc(id));
    }
}
