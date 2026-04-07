package com.olaru.api.config;

import com.olaru.api.entity.Perfil;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class PerfilConverter implements AttributeConverter<Perfil, String> {

    @Override
    public String convertToDatabaseColumn(Perfil perfil) {
        if (perfil == null) return null;
        return perfil.name().toLowerCase(); // Salva como 'admin' no banco
    }

    @Override
    public Perfil convertToEntityAttribute(String dbData) {
        if (dbData == null) return null;
        try {
            return Perfil.valueOf(dbData.toUpperCase()); // Converte 'admin' para ADMIN no Java
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
