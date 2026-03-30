package com.olaru.api.repository;

import com.olaru.api.entity.VisitaTecnica;
import org.springframework.data.jpa.repository.JpaRepository;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public interface VisitaTecnicaRepository extends JpaRepository<VisitaTecnica, UUID> {
    List<VisitaTecnica> findByDataVisitaAndTurno(LocalDate dataVisita, String turno);
    long countByDataVisitaAndTurnoAndStatusNot(LocalDate dataVisita, String turno, String status);
    List<VisitaTecnica> findByDataVisitaOrderByCriadoEmDesc(LocalDate dataVisita);
    List<VisitaTecnica> findAllByOrderByDataVisitaDescCriadoEmDesc();
    List<VisitaTecnica> findByTecnicoEmailAndDataVisitaOrderByCriadoEmDesc(String email, LocalDate dataVisita);
    long countByStatus(String status);
}
