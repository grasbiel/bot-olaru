package com.olaru.api.controller;

import com.olaru.api.repository.ClienteRepository;
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

    @GetMapping("/indicadores")
    @Operation(summary = "Obter indicadores principais")
    public Map<String, Object> obterIndicadores() {
        Map<String, Object> stats = new HashMap<>();
        
        long totalLeads = clienteRepository.count();
        long visitasPendentes = visitaRepository.countByStatus("pendente");
        long visitasConcluidas = visitaRepository.countByStatus("concluida");
        
        stats.put("totalLeads", totalLeads);
        stats.put("visitasPendentes", visitasPendentes);
        stats.put("visitasConcluidas", visitasConcluidas);
        
        // Cálculo simples de conversão (Visitas Concluídas / Total Leads)
        double conversao = totalLeads > 0 ? (double) visitasConcluidas / totalLeads * 100 : 0;
        stats.put("taxaConversao", Math.round(conversao * 100.0) / 100.0);

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
            labels[6-i] = dataRef.getDayOfMonth() + "/" + dataRef.getMonthValue();
            // Aqui em produção usaríamos queries específicas por data, por hora mockamos com base no total
            leads[6-i] = (long) (Math.random() * 10);
            visitas[6-i] = (long) (Math.random() * 5);
        }

        data.put("labels", labels);
        data.put("leads", leads);
        data.put("visitas", visitas);

        return data;
    }
}
