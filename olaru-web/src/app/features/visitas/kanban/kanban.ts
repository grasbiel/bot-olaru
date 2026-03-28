import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SidebarComponent } from '../../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../../shared/components/header/header';
import { VisitaService } from '../../../core/services/visita.service';

@Component({
  selector: 'app-kanban',
  standalone: true,
  imports: [CommonModule, SidebarComponent, HeaderComponent],
  templateUrl: './kanban.html',
  styleUrl: './kanban.css'
})
export class KanbanComponent implements OnInit {
  private visitaService = inject(VisitaService);

  colunas = [
    { title: 'Pendente', status: 'pendente', cards: [] as any[] },
    { title: 'Confirmada', status: 'confirmada', cards: [] as any[] },
    { title: 'Em Andamento', status: 'em_andamento', cards: [] as any[] },
    { title: 'Concluída', status: 'concluida', cards: [] as any[] }
  ];

  ngOnInit() {
    this.carregarVisitas();
  }

  carregarVisitas() {
    this.visitaService.listar().subscribe(data => {
      this.colunas.forEach(col => {
        col.cards = data.filter((v: any) => v.status === col.status);
      });
    });
  }

  mudarStatus(id: string, novoStatus: string) {
    this.visitaService.atualizarStatus(id, novoStatus).subscribe(() => {
      this.carregarVisitas();
    });
  }
}
