package com.olaru.api.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class PerfilConverter implements AttributeConverter<Perfil, String> {

    @Override
    public String convertToDatabaseColumn(Perfil attribute) {
        if (attribute == null) {
            return null;
        }
        // Converte o Perfil (ex: ADMIN) para a string suportada pelo banco (ex: "admin")
        return attribute.name().toLowerCase();
    }

    @Override
    public Perfil convertToEntityAttribute(String dbData) {
        if (dbData == null || dbData.trim().isEmpty()) {
            return null;
        }
        // Converte o valor do banco ("admin") de volta para o Enum Java (ADMIN)
        try {
            return Perfil.valueOf(dbData.toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
