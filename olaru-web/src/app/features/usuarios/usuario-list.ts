import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { UsuarioService } from '../../core/services/usuario.service';
import { EquipeService } from '../../core/services/equipe.service';

interface Usuario {
  id?: string;
  nome: string;
  email: string;
  senha?: string;
  perfil: string;
  equipeId?: string;
  equipe?: { id: string; nome: string };
  ativo?: boolean;
}

interface Equipe {
  id: string;
  nome: string;
}

@Component({
  selector: 'app-usuario-list',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent],
  templateUrl: './usuario-list.html',
  styleUrl: './usuario-list.css'
})
export class UsuarioListComponent implements OnInit {
  private usuarioService = inject(UsuarioService);
  private equipeService = inject(EquipeService);

  usuarios: Usuario[] = [];
  equipes: Equipe[] = [];
  exibirForm = false;
  exibirModalSenha = false;
  usuarioSelecionado: Usuario = this.resetUsuario();
  novaSenha = '';
  erroForm = '';

  ngOnInit() {
    this.carregar();
    this.equipeService.listar().subscribe((data: Equipe[]) => {
      this.equipes = data;
    });
  }

  carregar() {
    this.usuarioService.listar().subscribe((data: Usuario[]) => {
      this.usuarios = data;
    });
  }

  resetUsuario(): Usuario {
    return { nome: '', email: '', senha: '', perfil: 'tecnico' };
  }

  novoCadastro() {
    this.usuarioSelecionado = this.resetUsuario();
    this.erroForm = '';
    this.exibirForm = true;
  }

  editar(usuario: Usuario) {
    this.usuarioSelecionado = {
      ...usuario,
      equipeId: usuario.equipe?.id,
      senha: ''
    };
    this.erroForm = '';
    this.exibirForm = true;
  }

  abrirModalSenha(usuario: Usuario) {
    this.usuarioSelecionado = { ...usuario };
    this.novaSenha = '';
    this.exibirModalSenha = true;
  }

  desativar(id: string | undefined) {
    if (!id) return;
    if (confirm('Desativar este usuário?')) {
      this.usuarioService.desativar(id).subscribe(() => this.carregar());
    }
  }

  salvar() {
    this.erroForm = '';
    const payload: any = {
      nome: this.usuarioSelecionado.nome,
      email: this.usuarioSelecionado.email,
      perfil: this.usuarioSelecionado.perfil,
      equipeId: this.usuarioSelecionado.equipeId || null
    };

    if (this.usuarioSelecionado.id) {
      this.usuarioService.atualizar(this.usuarioSelecionado.id, payload).subscribe({
        next: () => { this.carregar(); this.exibirForm = false; },
        error: (err) => { this.erroForm = err.error || 'Erro ao salvar usuário.'; }
      });
    } else {
      payload.senha = this.usuarioSelecionado.senha;
      this.usuarioService.criar(payload).subscribe({
        next: () => { this.carregar(); this.exibirForm = false; },
        error: (err) => { this.erroForm = err.error || 'Erro ao criar usuário.'; }
      });
    }
  }

  salvarSenha() {
    if (!this.usuarioSelecionado.id) return;
    this.usuarioService.redefinirSenha(this.usuarioSelecionado.id, this.novaSenha).subscribe({
      next: () => { this.exibirModalSenha = false; this.novaSenha = ''; },
      error: (err) => { alert(err.error || 'Erro ao redefinir senha.'); }
    });
  }

  cancelar() {
    this.exibirForm = false;
    this.erroForm = '';
  }

  cancelarSenha() {
    this.exibirModalSenha = false;
    this.novaSenha = '';
  }

  perfilLabel(perfil: string): string {
    const labels: Record<string, string> = {
      admin: 'Administrador',
      gerente: 'Gerente',
      tecnico: 'Técnico'
    };
    return labels[perfil?.toLowerCase()] || perfil;
  }

  perfilClass(perfil: string): string {
    return perfil?.toLowerCase() || '';
  }
}
