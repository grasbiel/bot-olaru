package com.olaru.api.repository;

import com.olaru.api.entity.Cliente;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.time.LocalDate;
import java.util.Optional;
import java.util.UUID;

public interface ClienteRepository extends JpaRepository<Cliente, UUID> {
    Optional<Cliente> findByTelefone(String telefone);

    @Query("SELECT COUNT(c) FROM Cliente c WHERE CAST(c.criadoEm AS date) = :data")
    long countByDataCriacao(LocalDate data);
}
