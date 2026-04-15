import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { loginGuard } from './core/guards/login.guard';
import { roleGuard } from './core/guards/role.guard';
import { LayoutComponent } from './features/layout/layout';

export const routes: Routes = [
  // --- Rota pública ---
  {
    path: 'login',
    canActivate: [loginGuard],
    loadComponent: () =>
      import('./features/auth/login/login').then(m => m.LoginComponent)
  },

  // --- Rotas protegidas (dentro do layout com sidebar) ---
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      // Admin + Gerente
      {
        path: 'dashboard',
        canActivate: [roleGuard('admin', 'gerente')],
        loadComponent: () =>
          import('./features/dashboard/dashboard').then(m => m.DashboardComponent)
      },
      {
        path: 'visitas',
        canActivate: [roleGuard('admin', 'gerente')],
        loadComponent: () =>
          import('./features/visitas/kanban/kanban').then(m => m.KanbanComponent)
      },
      {
        path: 'maquinas',
        canActivate: [roleGuard('admin', 'gerente')],
        loadComponent: () =>
          import('./features/maquinas/maquina-list').then(m => m.MaquinaListComponent)
      },
      {
        path: 'clientes',
        canActivate: [roleGuard('admin', 'gerente')],
        loadComponent: () =>
          import('./features/clientes/cliente-list').then(m => m.ClienteListComponent)
      },
      {
        path: 'equipes',
        canActivate: [roleGuard('admin', 'gerente')],
        loadComponent: () =>
          import('./features/equipes/equipe-list').then(m => m.EquipeListComponent)
      },

      // Somente Admin
      {
        path: 'usuarios',
        canActivate: [roleGuard('admin')],
        loadComponent: () =>
          import('./features/usuarios/usuario-list').then(m => m.UsuarioListComponent)
      },
      {
        path: 'config',
        canActivate: [roleGuard('admin')],
        loadComponent: () =>
          import('./features/config/configuracoes').then(m => m.ConfiguracoesComponent)
      },

      // Somente Técnico
      {
        path: 'tecnico',
        canActivate: [roleGuard('tecnico')],
        loadComponent: () =>
          import('./features/operacional/minhas-visitas/minhas-visitas').then(m => m.MinhasVisitasComponent)
      },

      // Rota padrão — redireciona para dashboard (o guard cuidará de redirecionar técnicos)
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  },

  // Rota catch-all: redireciona para raiz (que após auth, vai para dashboard ou login)
  { path: '**', redirectTo: '' }
];
