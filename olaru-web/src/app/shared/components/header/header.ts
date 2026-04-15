import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/services/auth.service';

const PERFIL_LABELS: Record<string, string> = {
  admin: 'Administrador',
  gerente: 'Gerente',
  tecnico: 'Técnico'
};

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './header.html',
  styleUrl: './header.css',
})
export class HeaderComponent {
  private authService = inject(AuthService);

  readonly usuario = this.authService.usuario;

  readonly iniciais = computed(() => {
    const nome = this.usuario()?.nome ?? '';
    const partes = nome.split(' ').filter(Boolean);
    if (partes.length === 0) return '??';
    if (partes.length === 1) return partes[0].substring(0, 2).toUpperCase();
    return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
  });

  readonly perfilLabel = computed(() => {
    const perfil = this.usuario()?.perfil;
    return perfil ? PERFIL_LABELS[perfil] ?? perfil : '';
  });
}
