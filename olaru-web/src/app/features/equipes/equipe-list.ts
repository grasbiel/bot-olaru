import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { EquipeService } from '../../core/services/equipe.service';

interface Equipe {
  id?: string;
  nome: string;
  telefoneWhatsapp: string;
  especialidade: string;
  ativo: boolean;
}

@Component({
  selector: 'app-equipe-list',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent],
  templateUrl: './equipe-list.html',
  styleUrl: './equipe-list.css'
})
export class EquipeListComponent implements OnInit {
  private equipeService = inject(EquipeService);

  equipes: Equipe[] = [];
  exibirForm = false;
  equipeSelecionada: Equipe = this.resetEquipe();

  ngOnInit() {
    this.carregar();
  }

  carregar() {
    this.equipeService.listar().subscribe((data: Equipe[]) => {
      this.equipes = data;
    });
  }

  resetEquipe(): Equipe {
    return { nome: '', telefoneWhatsapp: '', especialidade: '', ativo: true };
  }

  novoCadastro() {
    this.equipeSelecionada = this.resetEquipe();
    this.exibirForm = true;
  }

  editar(equipe: Equipe) {
    this.equipeSelecionada = { ...equipe };
    this.exibirForm = true;
  }

  desativar(id: string | undefined) {
    if (!id) return;
    if (confirm('Desativar esta equipe?')) {
      this.equipeService.desativar(id).subscribe(() => this.carregar());
    }
  }

  salvar() {
    if (this.equipeSelecionada.id) {
      this.equipeService.atualizar(this.equipeSelecionada.id!, this.equipeSelecionada).subscribe({
        next: () => { this.carregar(); this.exibirForm = false; }
      });
    } else {
      this.equipeService.salvar(this.equipeSelecionada).subscribe({
        next: () => { this.carregar(); this.exibirForm = false; }
      });
    }
  }

  cancelar() {
    this.exibirForm = false;
  }
}
