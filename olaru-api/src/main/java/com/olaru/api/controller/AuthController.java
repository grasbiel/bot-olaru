package com.olaru.api.controller;

import com.olaru.api.dto.LoginDto;
import com.olaru.api.dto.TokenDto;
import com.olaru.api.entity.Usuario;
import com.olaru.api.security.TokenService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
@Tag(name = "Autenticação", description = "Endpoints para login e tokens")
public class AuthController {

    private final AuthenticationManager manager;
    private final TokenService tokenService;

    @PostMapping("/login")
    @Operation(summary = "Realizar login e obter token JWT")
    public ResponseEntity<?> login(@RequestBody @Valid LoginDto loginDto) {
        try {
            String email = loginDto.getEmail().trim().toLowerCase();
            UsernamePasswordAuthenticationToken authenticationToken = 
                    new UsernamePasswordAuthenticationToken(email, loginDto.getSenha());
            
            Authentication authentication = manager.authenticate(authenticationToken);
            Usuario usuario = (Usuario) authentication.getPrincipal();
            String tokenJWT = tokenService.gerarToken(usuario);

            TokenDto.UsuarioResumoDto usuarioResumo = new TokenDto.UsuarioResumoDto(
                    usuario.getNome(),
                    usuario.getEmail(),
                    usuario.getPerfil().name().toLowerCase()
            );
            return ResponseEntity.ok(new TokenDto(tokenJWT, "Bearer", usuarioResumo));
        } catch (Exception e) {
            System.err.println("FALHA NA AUTENTICAÇÃO: " + e.getMessage());
            return ResponseEntity.status(401).body("Credenciais inválidas ou erro interno");
        }
    }
}
