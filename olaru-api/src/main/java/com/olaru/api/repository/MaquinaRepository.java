package com.olaru.api.repository;

import com.olaru.api.entity.Maquina;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.Optional;
import java.util.UUID;

public interface MaquinaRepository extends JpaRepository<Maquina, UUID> {
    Optional<Maquina> findByNomeContainingIgnoreCase(String nome);

    @Query("SELECT SUM(m.quantidadeDisponivel) FROM Maquina m WHERE m.ativo = true")
    Long sumQuantidadeDisponivel();
}
