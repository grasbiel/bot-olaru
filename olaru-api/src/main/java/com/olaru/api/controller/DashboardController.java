package com.olaru.api.controller;

import com.olaru.api.repository.ClienteRepository;
import com.olaru.api.repository.MaquinaRepository;
import com.olaru.api.repository.VisitaTecnicaRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/dashboard")
@RequiredArgsConstructor
@Tag(name = "Dashboard", description = "Endpoints para indicadores e gráficos")
public class DashboardController {

    private final ClienteRepository clienteRepository;
    private final VisitaTecnicaRepository visitaRepository;
    private final MaquinaRepository maquinaRepository;

    @GetMapping("/indicadores")
    @Operation(summary = "Obter indicadores principais")
    public Map<String, Object> obterIndicadores() {
        Map<String, Object> stats = new HashMap<>();
        LocalDate hoje = LocalDate.now();
        
        long leadsHoje = clienteRepository.countByDataCriacao(hoje);
        long visitasHoje = visitaRepository.countByDataVisita(hoje);
        Long maquinasDisponiveis = maquinaRepository.sumQuantidadeDisponivel();
        long visitasPendentes = visitaRepository.countByStatus("pendente");
        
        stats.put("leadsHoje", leadsHoje);
        stats.put("visitasHoje", visitasHoje);
        stats.put("maquinasDisponiveis", maquinasDisponiveis != null ? maquinasDisponiveis : 0);
        stats.put("visitasPendentes", visitasPendentes);

        return stats;
    }

    @GetMapping("/evolucao")
    @Operation(summary = "Dados para o gráfico de evolução dos últimos 7 dias")
    public Map<String, Object> obterEvolucao() {
        Map<String, Object> data = new HashMap<>();
        String[] labels = new String[7];
        long[] leads = new long[7];
        long[] visitas = new long[7];

        LocalDate hoje = LocalDate.now();
        for (int i = 6; i >= 0; i--) {
            LocalDate dataRef = hoje.minusDays(i);
            int index = 6 - i;
            
            labels[index] = dataRef.getDayOfMonth() + "/" + dataRef.getMonthValue();
            leads[index] = clienteRepository.countByDataCriacao(dataRef);
            visitas[index] = visitaRepository.countByDataVisita(dataRef);
        }

        data.put("labels", labels);
        data.put("leads", leads);
        data.put("visitas", visitas);

        return data;
    }
}
