package com.olaru.api.repository;

import com.olaru.api.entity.FotoVisita;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface FotoVisitaRepository extends JpaRepository<FotoVisita, UUID> {
    List<FotoVisita> findByVisitaIdOrderByCriadoEmDesc(UUID visitaId);
}
