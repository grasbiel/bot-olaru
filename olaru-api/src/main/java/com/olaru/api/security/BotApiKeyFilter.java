package com.olaru.api.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
public class BotApiKeyFilter extends OncePerRequestFilter {

    private static final String API_KEY_HEADER = "X-Bot-Api-Key";

    @Value("${api.bot.api-key}")
    private String botApiKey;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        if (!isBotEndpoint(request)) {
            filterChain.doFilter(request, response);
            return;
        }

        String providedKey = request.getHeader(API_KEY_HEADER);
        if (botApiKey != null && botApiKey.equals(providedKey)) {
            UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                    "bot", null, List.of(new SimpleGrantedAuthority("ROLE_bot"))
            );
            SecurityContextHolder.getContext().setAuthentication(auth);
        }

        filterChain.doFilter(request, response);
    }

    private boolean isBotEndpoint(HttpServletRequest request) {
        String method = request.getMethod();
        String path = request.getRequestURI();

        return (HttpMethod.GET.name().equals(method) && path.startsWith("/api/v1/clientes/telefone/")) ||
               (HttpMethod.POST.name().equals(method) && "/api/v1/clientes".equals(path)) ||
               (HttpMethod.PATCH.name().equals(method) && path.startsWith("/api/v1/clientes/telefone/")) ||
               (HttpMethod.GET.name().equals(method) && "/api/v1/visitas/disponibilidade".equals(path)) ||
               (HttpMethod.POST.name().equals(method) && "/api/v1/visitas".equals(path)) ||
               (HttpMethod.GET.name().equals(method) && path.startsWith("/api/v1/maquinas/estoque/"));
    }
}
