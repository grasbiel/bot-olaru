package com.olaru.api.config;

import com.olaru.api.security.SecurityFilter;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final SecurityFilter securityFilter;

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .cors(AbstractHttpConfigurer::disable) // Agora gerenciado pela CorsConfig
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                .requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html", "/api-docs/**").permitAll()
                .requestMatchers("/error").permitAll()
                
                // Endpoints usados pelo Bot (Públicos por enquanto)
                .requestMatchers(HttpMethod.GET, "/api/v1/clientes/telefone/**").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/v1/clientes").permitAll()
                .requestMatchers(HttpMethod.PATCH, "/api/v1/clientes/telefone/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/visitas/disponibilidade").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/v1/visitas").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/maquinas/estoque/**").permitAll()

                // Endpoints Administrativos (RBAC §6.1)
                .requestMatchers("/api/v1/dashboard/**").hasAnyRole("ADMIN", "GERENTE")
                .requestMatchers("/api/v1/clientes").hasAnyRole("ADMIN", "GERENTE")
                .requestMatchers("/api/v1/maquinas/**").hasAnyRole("ADMIN", "GERENTE")
                .requestMatchers("/api/v1/equipes/**").hasAnyRole("ADMIN", "GERENTE")
                .requestMatchers("/api/v1/usuarios/**").hasRole("ADMIN")
                
                // Visitas
                .requestMatchers(HttpMethod.GET, "/api/v1/visitas").hasAnyRole("ADMIN", "GERENTE")
                .requestMatchers("/api/v1/visitas/minhas").hasRole("TECNICO")
                .requestMatchers(HttpMethod.PATCH, "/api/v1/visitas/*/status").hasAnyRole("ADMIN", "GERENTE", "TECNICO")
                .requestMatchers(HttpMethod.POST, "/api/v1/visitas/*/observacoes").hasRole("TECNICO")
                .requestMatchers(HttpMethod.POST, "/api/v1/visitas/*/fotos").hasRole("TECNICO")
                
                .anyRequest().authenticated()
            )
            .addFilterBefore(securityFilter, UsernamePasswordAuthenticationFilter.class)
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint((request, response, authException) -> {
                    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"error\": \"Não autorizado\", \"message\": \"" + authException.getMessage() + "\"}");
                })
            );
        
        return http.build();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
        return configuration.getAuthenticationManager();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }
}
