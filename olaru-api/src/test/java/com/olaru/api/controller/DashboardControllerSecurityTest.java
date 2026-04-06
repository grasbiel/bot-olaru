package com.olaru.api.controller;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
public class DashboardControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    @DisplayName("Não deve permitir acesso ao dashboard sem autenticação")
    void deveNegarAcessoSemToken() throws Exception {
        mockMvc.perform(get("/api/v1/dashboard/indicadores"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    @WithMockUser(roles = "TECNICO")
    @DisplayName("Deve negar acesso ao dashboard para o perfil Técnico (RBAC §6.1)")
    void deveNegarAcessoParaTecnico() throws Exception {
        mockMvc.perform(get("/api/v1/dashboard/indicadores"))
                .andExpect(status().isForbidden());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Deve permitir acesso ao dashboard para o perfil Admin")
    void devePermitirAcessoParaAdmin() throws Exception {
        mockMvc.perform(get("/api/v1/dashboard/indicadores"))
                .andExpect(status().isOk());
    }
}
