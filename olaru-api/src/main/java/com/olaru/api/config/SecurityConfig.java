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
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                .requestMatchers("/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html", "/api-docs/**").permitAll()
                .requestMatchers("/error").permitAll()
                
                // Endpoints usados pelo Bot
                .requestMatchers(HttpMethod.GET, "/api/v1/clientes/telefone/**").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/v1/clientes").permitAll()
                .requestMatchers(HttpMethod.PATCH, "/api/v1/clientes/telefone/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/visitas/disponibilidade").permitAll()
                .requestMatchers(HttpMethod.POST, "/api/v1/visitas").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/v1/maquinas/estoque/**").permitAll()

                // Endpoints Administrativos
                .requestMatchers("/api/v1/dashboard/**").hasAnyRole("admin", "gerente")
                .requestMatchers("/api/v1/clientes").hasAnyRole("admin", "gerente")
                .requestMatchers("/api/v1/maquinas/**").hasAnyRole("admin", "gerente")
                .requestMatchers("/api/v1/equipes/**").hasAnyRole("admin", "gerente")
                .requestMatchers("/api/v1/usuarios/**").hasRole("admin")
                
                // Visitas
                .requestMatchers(HttpMethod.GET, "/api/v1/visitas").hasAnyRole("admin", "gerente")
                .requestMatchers("/api/v1/visitas/minhas").hasRole("tecnico")
                .requestMatchers(HttpMethod.PATCH, "/api/v1/visitas/*/status").hasAnyRole("admin", "gerente", "tecnico")
                .requestMatchers(HttpMethod.POST, "/api/v1/visitas/*/observacoes").hasRole("tecnico")
                .requestMatchers(HttpMethod.POST, "/api/v1/visitas/*/fotos").hasRole("tecnico")
                
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
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(Arrays.asList(
            "https://olaru.grasbiel.cloud", 
            "http://olaru.grasbiel.cloud",
            "http://localhost:4200"
        ));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("Authorization", "Content-Type", "Origin", "Accept", "X-Requested-With"));
        configuration.setAllowCredentials(true);
        configuration.setMaxAge(3600L);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
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
