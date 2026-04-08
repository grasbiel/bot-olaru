package com.olaru.api.security;

import com.olaru.api.entity.Usuario;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.security.Key;
import java.util.Date;

@Service
public class TokenService {

    @Value("${api.security.token.secret}")
    private String secret;

    public String gerarToken(Usuario usuario) {
        Key key = Keys.hmacShaKeyFor(secret.getBytes());
        return Jwts.builder()
                .setIssuer("OLARU-API")
                .setSubject(usuario.getEmail())
                .claim("perfil", usuario.getPerfil().name())
                .claim("type", "access")
                .setExpiration(new Date(System.currentTimeMillis() + 3_600_000L)) // 1 hora
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    public String gerarRefreshToken(Usuario usuario) {
        Key key = Keys.hmacShaKeyFor(secret.getBytes());
        return Jwts.builder()
                .setIssuer("OLARU-API")
                .setSubject(usuario.getEmail())
                .claim("type", "refresh")
                .setExpiration(new Date(System.currentTimeMillis() + 604_800_000L)) // 7 dias
                .signWith(key, SignatureAlgorithm.HS256)
                .compact();
    }

    public String getSubject(String token) {
        try {
            Key key = Keys.hmacShaKeyFor(secret.getBytes());
            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(key)
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
            return claims.getSubject();
        } catch (Exception e) {
            return null;
        }
    }

    public String getSubjectFromRefreshToken(String token) {
        try {
            Key key = Keys.hmacShaKeyFor(secret.getBytes());
            Claims claims = Jwts.parserBuilder()
                    .setSigningKey(key)
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
            if (!"refresh".equals(claims.get("type", String.class))) return null;
            return claims.getSubject();
        } catch (Exception e) {
            return null;
        }
    }
}
