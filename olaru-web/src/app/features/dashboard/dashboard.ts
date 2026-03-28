import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { ClienteService } from '../../core/services/cliente.service';
import { VisitaService } from '../../core/services/visita.service';
import { MaquinaService } from '../../core/services/maquina.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, SidebarComponent, HeaderComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit {
  private clienteService = inject(ClienteService);
  private visitaService = inject(VisitaService);
  private maquinaService = inject(MaquinaService);

  leads: any[] = [];
  visitas: any[] = [];
  maquinas: any[] = [];

  stats = {
    novosLeads: 0,
    visitasHoje: 0,
    maquinasAlugadas: 0,
    disponibilidade: '0%'
  };

  ngOnInit() {
    this.carregarDados();
  }

  carregarDados() {
    this.clienteService.listar().subscribe(data => {
      this.leads = data;
      this.stats.novosLeads = data.length;
    });

    this.visitaService.listar().subscribe(data => {
      this.visitas = data;
      const hoje = new Date().toISOString().split('T')[0];
      this.stats.visitasHoje = data.filter((v: any) => v.dataVisita === hoje).length;
    });

    this.maquinaService.listar().subscribe(data => {
      this.maquinas = data;
      const total = data.reduce((acc, m) => acc + m.quantidadeTotal, 0);
      const disp = data.reduce((acc, m) => acc + m.quantidadeDisponivel, 0);
      this.stats.maquinasAlugadas = total - disp;
      this.stats.disponibilidade = total > 0 ? `${Math.round((disp / total) * 100)}%` : '0%';
    });
  }
}
