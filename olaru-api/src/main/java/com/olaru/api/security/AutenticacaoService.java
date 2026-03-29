package com.olaru.api.security;

import com.olaru.api.repository.UsuarioRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AutenticacaoService implements UserDetailsService {

    private final UsuarioRepository repository;

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        System.out.println("Tentando carregar usuário: [" + username + "]");
        return repository.findByEmail(username.trim().toLowerCase())
                .map(u -> {
                    System.out.println("Usuário encontrado: [" + u.getEmail() + "]");
                    return u;
                })
                .orElseThrow(() -> {
                    System.out.println("Usuário NÃO encontrado: [" + username + "]");
                    return new UsernameNotFoundException("Usuário não encontrado: " + username);
                });
    }
}
