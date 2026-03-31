import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { DashboardComponent } from './features/dashboard/dashboard';
import { KanbanComponent } from './features/visitas/kanban/kanban';
import { MinhasVisitasComponent } from './features/operacional/minhas-visitas/minhas-visitas';
import { MaquinaListComponent } from './features/maquinas/maquina-list';
import { ClienteListComponent } from './features/clientes/cliente-list';
import { ConfiguracoesComponent } from './features/config/configuracoes';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'visitas', component: KanbanComponent },
  { path: 'maquinas', component: MaquinaListComponent },
  { path: 'clientes', component: ClienteListComponent },
  { path: 'config', component: ConfiguracoesComponent },
  { path: 'tecnico', component: MinhasVisitasComponent },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
