import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../../shared/components/header/header';
import { VisitaService } from '../../../core/services/visita.service';
import { UsuarioService } from '../../../core/services/usuario.service';
import { Subscription } from 'rxjs';
import { 
  DragDropModule, 
  CdkDragDrop, 
  moveItemInArray, 
  transferArrayItem 
} from '@angular/cdk/drag-drop';

@Component({
  selector: 'app-kanban',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent, DragDropModule],
  templateUrl: './kanban.html',
  styleUrl: './kanban.css'
})
export class KanbanComponent implements OnInit, OnDestroy {
  private visitaService = inject(VisitaService);
  private usuarioService = inject(UsuarioService);
  private subNotificacoes?: Subscription;

  dataFiltro: string = new Date().toISOString().split('T')[0];
  tecnicos: any[] = [];

  colunas = [
    { id: 'pendente', title: 'Pendente', cards: [] as any[] },
    { id: 'confirmada', title: 'Confirmada', cards: [] as any[] },
    { id: 'em_andamento', title: 'Em Andamento', cards: [] as any[] },
    { id: 'concluida', title: 'Concluída', cards: [] as any[] },
    { id: 'cancelada', title: 'Cancelada', cards: [] as any[] }
  ];

  get colunasIds() {
    return this.colunas.map(c => c.id);
  }

  ngOnInit() {
    this.carregarVisitas();
    this.carregarTecnicos();
    this.ouvirNotificacoes();
  }

  ngOnDestroy() {
    this.subNotificacoes?.unsubscribe();
  }

  ouvirNotificacoes() {
    this.subNotificacoes = this.visitaService.notificacoes().subscribe({
      next: (data) => {
        console.log('Atualização em tempo real recebida:', data);
        this.carregarVisitas();
      },
      error: (err) => console.error('Erro SSE:', err)
    });
  }

  carregarTecnicos() {
    this.usuarioService.listarTecnicos().subscribe(data => {
      this.tecnicos = data;
    });
  }

  carregarVisitas() {
    this.visitaService.listar(this.dataFiltro).subscribe(data => {
      this.colunas.forEach(col => {
        col.cards = data.filter((v: any) => v.status === col.id);
      });
    });
  }

  drop(event: CdkDragDrop<any[]>) {
    if (event.previousContainer === event.container) {
      moveItemInArray(event.container.data, event.previousIndex, event.currentIndex);
    } else {
      const card = event.previousContainer.data[event.previousIndex];
      const novoStatus = event.container.id;

      // Validação básica de transições conforme §14.6.2
      if (this.podeMudarStatus(card.status, novoStatus)) {
        transferArrayItem(
          event.previousContainer.data,
          event.container.data,
          event.previousIndex,
          event.currentIndex,
        );
        this.mudarStatus(card.id, novoStatus);
      }
    }
  }

  podeMudarStatus(atual: string, novo: string): boolean {
    const transicoes: Record<string, string[]> = {
      'pendente': ['confirmada', 'cancelada'],
      'confirmada': ['em_andamento', 'cancelada'],
      'em_andamento': ['concluida', 'cancelada'],
      'concluida': [],
      'cancelada': []
    };
    return transicoes[atual]?.includes(novo) || false;
  }

  atribuirTecnico(visitaId: string, event: Event) {
    const tecnicoId = (event.target as HTMLSelectElement).value;
    if (tecnicoId) {
      this.visitaService.atribuirTecnico(visitaId, tecnicoId).subscribe(() => {
        console.log('Técnico atribuído com sucesso');
      });
    }
  }

  mudarStatus(id: string, novoStatus: string) {
    this.visitaService.atualizarStatus(id, novoStatus).subscribe({
      next: () => this.carregarVisitas(),
      error: () => this.carregarVisitas() // Rollback
    });
  }
}
