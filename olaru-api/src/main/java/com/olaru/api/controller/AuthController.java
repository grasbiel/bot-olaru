package com.olaru.api.controller;

import com.olaru.api.dto.LoginDto;
import com.olaru.api.dto.TokenDto;
import com.olaru.api.entity.Usuario;
import com.olaru.api.repository.UsuarioRepository;
import com.olaru.api.security.TokenService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.Data;
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
    private final UsuarioRepository usuarioRepository;

    @PostMapping("/login")
    @Operation(summary = "Realizar login e obter tokens JWT")
    public ResponseEntity<?> login(@RequestBody @Valid LoginDto loginDto) {
        try {
            String email = loginDto.getEmail().trim().toLowerCase();
            UsernamePasswordAuthenticationToken authenticationToken =
                    new UsernamePasswordAuthenticationToken(email, loginDto.getSenha());

            Authentication authentication = manager.authenticate(authenticationToken);
            Usuario usuario = (Usuario) authentication.getPrincipal();

            return ResponseEntity.ok(buildTokenDto(usuario));
        } catch (Exception e) {
            System.err.println("FALHA NA AUTENTICAÇÃO: " + e.getMessage());
            return ResponseEntity.status(401).body("Credenciais inválidas ou erro interno");
        }
    }

    @PostMapping("/refresh")
    @Operation(summary = "Renovar access token usando refresh token")
    public ResponseEntity<?> refresh(@RequestBody @Valid RefreshRequest request) {
        String email = tokenService.getSubjectFromRefreshToken(request.getRefreshToken());
        if (email == null) {
            return ResponseEntity.status(401).body("Refresh token inválido ou expirado.");
        }

        return usuarioRepository.findByEmail(email)
                .filter(Usuario::isEnabled)
                .map(usuario -> ResponseEntity.ok(buildTokenDto(usuario)))
                .orElse(ResponseEntity.status(401).build());
    }

    private TokenDto buildTokenDto(Usuario usuario) {
        String accessToken = tokenService.gerarToken(usuario);
        String refreshToken = tokenService.gerarRefreshToken(usuario);
        TokenDto.UsuarioResumoDto usuarioResumo = new TokenDto.UsuarioResumoDto(
                usuario.getNome(),
                usuario.getEmail(),
                usuario.getPerfil().name().toLowerCase()
        );
        return new TokenDto(accessToken, refreshToken, "Bearer", usuarioResumo);
    }

    @Data
    public static class RefreshRequest {
        @jakarta.validation.constraints.NotBlank
        private String refreshToken;
    }
}
