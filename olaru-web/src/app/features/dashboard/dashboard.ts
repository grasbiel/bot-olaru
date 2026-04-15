import { Component, OnInit, inject, AfterViewInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DashboardService } from '../../core/services/dashboard.service';
import { AuthService } from '../../core/services/auth.service';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit, AfterViewInit {
  private dashboardService = inject(DashboardService);
  private authService = inject(AuthService);

  @ViewChild('evolucaoChart') evolucaoChart!: ElementRef;
  private chartInstance: any;

  usuarioNome: string = 'Admin';
  saudacao: string = '';
  dataHoje: string = '';

  indicadores: any = {
    novosLeadsHoje: 0,
    visitasDoDia: 0,
    maquinasDisponiveis: 0,
    handoffsPendentes: 0
  };

  ngOnInit() {
    this.definirSaudacao();
    this.carregarIndicadores();
  }

  definirSaudacao() {
    const hora = new Date().getHours();
    if (hora < 12) this.saudacao = 'Bom dia';
    else if (hora < 18) this.saudacao = 'Boa tarde';
    else this.saudacao = 'Boa noite';

    this.dataHoje = new Intl.DateTimeFormat('pt-BR', { 
      weekday: 'long', 
      day: 'numeric', 
      month: 'long', 
      year: 'numeric' 
    }).format(new Date());

    // Pegar nome do usuário do AuthService
    const usuario = this.authService.usuario();
    if (usuario?.nome) this.usuarioNome = usuario.nome.split(' ')[0];
  }

  ngAfterViewInit() {
    this.carregarEvolucao();
  }

  carregarIndicadores() {
    this.dashboardService.obterIndicadores().subscribe({
      next: data => {
        // Mapeia do backend para os novos campos da UI conforme DashboardController.java
        this.indicadores = {
          novosLeadsHoje: data.leadsHoje || 0,
          visitasDoDia: data.visitasHoje || 0,
          maquinasDisponiveis: data.maquinasDisponiveis || 0,
          handoffsPendentes: data.visitasPendentes || 0 // Usando visitasPendentes como indicador de carga
        };
      },
      error: err => console.error('Erro ao carregar indicadores:', err)
    });
  }

  carregarEvolucao() {
    this.dashboardService.obterEvolucao().subscribe({
      next: data => {
        if (this.evolucaoChart) {
          this.renderizarGrafico(data);
        }
      },
      error: err => console.error('Erro ao carregar evolução:', err)
    });
  }

  renderizarGrafico(data: any) {
    if (this.chartInstance) {
      this.chartInstance.destroy();
    }

    this.chartInstance = new Chart(this.evolucaoChart.nativeElement, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Leads Qualificados',
            data: data.leads,
            borderColor: '#F0A500', // Âmbar da marca
            backgroundColor: 'rgba(240, 165, 0, 0.1)',
            fill: true,
            tension: 0.4
          },
          {
            label: 'Visitas Técnicas',
            data: data.visitas,
            borderColor: '#3b82f6', // Azul info
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { 
            position: 'bottom',
            labels: { color: '#E8EAF0' } // Cor do texto da legenda
          }
        },
        scales: {
          y: { 
            beginAtZero: true, 
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#9CA3AF' } 
          },
          x: { 
            grid: { display: false },
            ticks: { color: '#9CA3AF' }
          }
        }
      }
    });
  }
}
