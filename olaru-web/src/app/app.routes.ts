import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login';
import { DashboardComponent } from './features/dashboard/dashboard';
import { KanbanComponent } from './features/visitas/kanban/kanban';
import { MinhasVisitasComponent } from './features/operacional/minhas-visitas/minhas-visitas';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'visitas', component: KanbanComponent },
  { path: 'tecnico', component: MinhasVisitasComponent },
  { path: '', redirectTo: 'login', pathMatch: 'full' }
];
