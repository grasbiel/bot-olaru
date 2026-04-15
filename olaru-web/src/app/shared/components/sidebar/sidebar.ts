import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService, Perfil } from '../../../core/services/auth.service';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  roles: Perfil[];
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css'
})
export class SidebarComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  readonly usuario = this.authService.usuario;

  /** Lista de itens de navegação com controle de acesso por perfil */
  private allNavItems: NavItem[] = [
    { label: 'Dashboard',        icon: '📊', route: '/dashboard', roles: ['admin', 'gerente'] },
    { label: 'Visitas Técnicas', icon: '📅', route: '/visitas',   roles: ['admin', 'gerente'] },
    { label: 'Máquinas',         icon: '🏗️', route: '/maquinas',  roles: ['admin', 'gerente'] },
    { label: 'Clientes',         icon: '👥', route: '/clientes',  roles: ['admin', 'gerente'] },
    { label: 'Equipes',          icon: '👷', route: '/equipes',   roles: ['admin', 'gerente'] },
    { label: 'Usuários',         icon: '🔐', route: '/usuarios',  roles: ['admin'] },
    { label: 'Configurações',    icon: '⚙️', route: '/config',    roles: ['admin'] },
  ];

  /** Itens filtrados pelo perfil do usuário logado */
  readonly navItems = computed(() => {
    const perfil = this.authService.perfil();
    if (!perfil) return [];
    return this.allNavItems.filter(item => item.roles.includes(perfil));
  });

  logout(event: Event) {
    event.preventDefault();
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
