import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../../shared/components/header/header';
import { VisitaService } from '../../../core/services/visita.service';
import { UsuarioService } from '../../../core/services/usuario.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-kanban',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent],
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
    { title: 'Pendente', status: 'pendente', cards: [] as any[] },
    { title: 'Confirmada', status: 'confirmada', cards: [] as any[] },
    { title: 'Em Andamento', status: 'em_andamento', cards: [] as any[] },
    { title: 'Concluída', status: 'concluida', cards: [] as any[] }
  ];

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
        col.cards = data.filter((v: any) => v.status === col.status);
      });
    });
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
    this.visitaService.atualizarStatus(id, novoStatus).subscribe(() => {
      this.carregarVisitas();
    });
  }
}
