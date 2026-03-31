import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { ClienteService } from '../../core/services/cliente.service';

interface Cliente {
  id?: string;
  nome: string;
  email: string;
  telefone: string;
  cpfCnpj: string;
  endereco: string;
  ativo: boolean;
  statusLead?: string;
}

@Component({
  selector: 'app-cliente-list',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent],
  templateUrl: './cliente-list.html',
  styleUrl: './cliente-list.css'
})
export class ClienteListComponent implements OnInit {
  private clienteService = inject(ClienteService);

  clientes: Cliente[] = [];
  exibirForm = false;
  clienteSelecionado: Cliente = this.resetCliente();

  ngOnInit() {
    this.carregarClientes();
  }

  carregarClientes() {
    this.clienteService.listar().subscribe((data: Cliente[]) => {
      this.clientes = data;
    });
  }

  resetCliente(): Cliente {
    return {
      nome: '',
      email: '',
      telefone: '',
      cpfCnpj: '',
      endereco: '',
      ativo: true
    };
  }

  novoCadastro() {
    this.clienteSelecionado = this.resetCliente();
    this.exibirForm = true;
  }

  editar(cliente: Cliente) {
    this.clienteSelecionado = { ...cliente };
    this.exibirForm = true;
  }

  excluir(id: string | undefined) {
    if (!id) return;
    if (confirm('Tem certeza que deseja excluir este cliente?')) {
      this.clienteService.excluir(id).subscribe(() => {
        this.carregarClientes();
      });
    }
  }

  salvar() {
    if (this.clienteSelecionado.id) {
      this.clienteService.atualizar(this.clienteSelecionado.id!, this.clienteSelecionado).subscribe({
        next: () => {
          this.carregarClientes();
          this.exibirForm = false;
        }
      });
    } else {
      this.clienteService.salvar(this.clienteSelecionado).subscribe({
        next: () => {
          this.carregarClientes();
          this.exibirForm = false;
        }
      });
    }
  }

  cancelar() {
    this.exibirForm = false;
  }
}
