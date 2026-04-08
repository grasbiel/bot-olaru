package com.olaru.api.repository;

import com.olaru.api.entity.Perfil;
import com.olaru.api.entity.Usuario;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface UsuarioRepository extends JpaRepository<Usuario, UUID> {
    Optional<Usuario> findByEmail(String email);
    List<Usuario> findByAtivoTrue();
    List<Usuario> findByPerfilAndAtivoTrue(Perfil perfil);
}
