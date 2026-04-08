package com.olaru.api.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "fotos_visita")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FotoVisita {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "visita_id", nullable = false)
    private VisitaTecnica visita;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "usuario_id", nullable = false)
    private Usuario usuario;

    @Column(nullable = false)
    private String url;

    @Column(name = "mime_type", nullable = false, length = 50)
    private String mimeType;

    @Column(name = "tamanho_kb")
    private Integer tamanhoKb;

    @CreationTimestamp
    @Column(name = "criado_em", updatable = false)
    private LocalDateTime criadoEm;
}
