import { Component, OnInit, inject, AfterViewInit, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { DashboardService } from '../../core/services/dashboard.service';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, SidebarComponent, HeaderComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit, AfterViewInit {
  private dashboardService = inject(DashboardService);

  @ViewChild('evolucaoChart') evolucaoChart!: ElementRef;
  private chartInstance: any;

  indicadores: any = {
    totalLeads: 0,
    visitasPendentes: 0,
    visitasConcluidas: 0,
    taxaConversao: 0
  };

  ngOnInit() {
    this.carregarIndicadores();
  }

  ngAfterViewInit() {
    this.carregarEvolucao();
  }

  carregarIndicadores() {
    this.dashboardService.obterIndicadores().subscribe({
      next: data => this.indicadores = data,
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
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4
          },
          {
            label: 'Visitas Técnicas',
            data: data.visitas,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom' }
        },
        scales: {
          y: { beginAtZero: true, grid: { display: false } },
          x: { grid: { display: false } }
        }
      }
    });
  }
}
