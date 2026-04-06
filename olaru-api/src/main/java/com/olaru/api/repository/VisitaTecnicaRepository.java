package com.olaru.api.repository;

import com.olaru.api.entity.VisitaTecnica;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public interface VisitaTecnicaRepository extends JpaRepository<VisitaTecnica, UUID> {
    List<VisitaTecnica> findByDataVisitaAndTurno(LocalDate dataVisita, String turno);
    long countByDataVisitaAndTurnoAndStatusNot(LocalDate dataVisita, String turno, String status);
    List<VisitaTecnica> findByDataVisitaOrderByCriadoEmDesc(LocalDate dataVisita);
    List<VisitaTecnica> findAllByOrderByDataVisitaDescCriadoEmDesc();
    
    @Query("SELECT v FROM VisitaTecnica v JOIN v.tecnico t WHERE t.email = :email AND v.dataVisita = :data ORDER BY v.criadoEm DESC")
    List<VisitaTecnica> findByTecnicoEmailAndDataVisitaOrderByCriadoEmDesc(String email, LocalDate data);
    
    long countByStatus(String status);

    @Query("SELECT COUNT(v) FROM VisitaTecnica v WHERE v.dataVisita = :data")
    long countByDataVisita(LocalDate data);
}
