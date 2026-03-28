import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { VisitaService } from '../../../core/services/visita.service';

@Component({
  selector: 'app-minhas-visitas',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './minhas-visitas.html',
  styleUrl: './minhas-visitas.css'
})
export class MinhasVisitasComponent implements OnInit {
  private visitaService = inject(VisitaService);

  hoje = new Date().toISOString().split('T')[0];
  visitas: any[] = [];

  ngOnInit() {
    this.carregarVisitas();
  }

  carregarVisitas() {
    this.visitaService.listar().subscribe(data => {
      // No futuro, filtrar pelo ID do técnico logado
      this.visitas = data.filter((v: any) => v.dataVisita === this.hoje);
    });
  }

  mudarStatus(id: string, novoStatus: string) {
    this.visitaService.atualizarStatus(id, novoStatus).subscribe(() => {
      this.carregarVisitas();
    });
  }
}
