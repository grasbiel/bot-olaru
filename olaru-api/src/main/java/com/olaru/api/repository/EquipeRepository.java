package com.olaru.api.repository;

import com.olaru.api.entity.Equipe;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface EquipeRepository extends JpaRepository<Equipe, UUID> {
    List<Equipe> findByAtivoTrue();
}
