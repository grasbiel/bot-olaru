package com.olaru.api.repository;

import com.olaru.api.entity.Cliente;
import com.olaru.api.entity.VisitaTecnica;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.test.context.ActiveProfiles;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@ActiveProfiles("test")
public class VisitaTecnicaRepositoryTest {

    @Autowired
    private VisitaTecnicaRepository visitaRepository;

    @Autowired
    private ClienteRepository clienteRepository;

    @Test
    @DisplayName("Deve contar corretamente as visitas de um turno específico")
    void deveContarVisitasPorTurno() {
        // Cenário
        Cliente cliente = Cliente.builder()
                .nome("Cliente Teste")
                .telefone("11999999999")
                .build();
        clienteRepository.save(cliente);

        VisitaTecnica visita = VisitaTecnica.builder()
                .cliente(cliente)
                .dataVisita(LocalDate.now())
                .turno("MANHA")
                .status("pendente")
                .descricaoServico("Teste")
                .endereco("Rua Teste")
                .build();
        visitaRepository.save(visita);

        // Ação
        long total = visitaRepository.countByDataVisitaAndTurnoAndStatusNot(LocalDate.now(), "MANHA", "cancelada");

        // Validação
        assertThat(total).isEqualTo(1);
    }
}
