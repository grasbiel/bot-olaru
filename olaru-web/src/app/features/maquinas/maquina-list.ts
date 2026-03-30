import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../../shared/components/header/header';
import { MaquinaService } from '../../../core/services/maquina.service';

@Component({
  selector: 'app-maquina-list',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent],
  templateUrl: './maquina-list.html',
  styleUrl: './maquina-list.css'
})
export class MaquinaListComponent implements OnInit {
  private maquinaService = inject(MaquinaService);

  maquinas: any[] = [];
  exibirForm = false;
  maquinaSelecionada: any = this.resetMaquina();

  ngOnInit() {
    this.carregarMaquinas();
  }

  carregarMaquinas() {
    this.maquinaService.listar().subscribe(data => {
      this.maquinas = data;
    });
  }

  resetMaquina() {
    return {
      nome: '',
      descricao: '',
      quantidadeTotal: 0,
      quantidadeDisponivel: 0,
      valorDiaria: 0,
      ativo: true
    };
  }

  novoCadastro() {
    this.maquinaSelecionada = this.resetMaquina();
    this.exibirForm = true;
  }

  editar(maquina: any) {
    this.maquinaSelecionada = { ...maquina };
    this.exibirForm = true;
  }

  excluir(id: string) {
    if (confirm('Tem certeza que deseja excluir esta máquina?')) {
      this.maquinaService.excluir(id).subscribe(() => {
        this.carregarMaquinas();
      });
    }
  }

  salvar() {
    if (this.maquinaSelecionada.id) {
      this.maquinaService.atualizar(this.maquinaSelecionada.id, this.maquinaSelecionada).subscribe(() => {
        this.carregarMaquinas();
        this.exibirForm = false;
      });
    } else {
      this.maquinaService.salvar(this.maquinaSelecionada).subscribe(() => {
        this.carregarMaquinas();
        this.exibirForm = false;
      });
    }
  }

  cancelar() {
    this.exibirForm = false;
  }
}
