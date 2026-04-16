import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit {
  private dashboardService = inject(DashboardService);
  private authService = inject(AuthService);

  usuarioNome: string = 'Admin';

  // Indicadores do topo (mantendo a carga do backend, mas com fallback p/ visual da imagem)
  indicadores: any = {
    novosLeadsHoje: 12,
    oportunidadesAbertas: 45,
    taxaConversao: '18.5%',
    maquinasAtivas: 68
  };

  // Dados Mockados baseados na imagem
  funil = [
    { label: 'Prospecting', value: 200, bgClass: 'funnel-blue-1', width: 95 },
    { label: 'Qualification', value: 90, bgClass: 'funnel-blue-2', width: 70 },
    { label: 'Proposal', value: 40, bgClass: 'funnel-blue-3', width: 45 },
    { label: 'Closed Won', value: 25, bgClass: 'funnel-blue-4', width: 30 }
  ];

  locaisMap = [
    { top: '30%', left: '60%' },
    { top: '55%', left: '30%' },
    { top: '80%', left: '45%' },
    { top: '45%', left: '75%' },
    { top: '75%', left: '80%' }
  ];

  atividades = [
    { titulo: 'Novo Lead: Carlos Santos', descricao: 'Construtora Alpha', tempo: '4 hours ago', cor: '#3b82f6' },
    { titulo: 'Escavadeira XYZ-456:', descricao: 'Manutenção Agendada', tempo: '3 hours ago', cor: '#60a5fa' },
    { titulo: 'Escavadeira XYZ-456:', descricao: 'Fim da Manutenção', tempo: '3 hours ago', cor: '#1e3a8a' },
    { titulo: 'Escavadeira XYZ-456:', descricao: 'Escola de Manutenção', tempo: '2 hours ago', cor: '#93c5fd' }
  ];

  ngOnInit() {
    // Pega o nome real do user
    const usuario = this.authService.usuario();
    if (usuario?.nome) this.usuarioNome = usuario.nome.split(' ')[0];

    // Carrega dados reais do backend e mescla no layout novo
    this.dashboardService.obterIndicadores().subscribe({
      next: data => {
        if(data) {
           this.indicadores.novosLeadsHoje = data.leadsHoje || 12;
           this.indicadores.maquinasAtivas = data.maquinasDisponiveis || 68;
        }
      },
      error: err => console.error('Erro ao carregar indicadores:', err)
    });
  }
}
