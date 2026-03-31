import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { AuthService } from '../../core/services/auth.service';
import { UsuarioService } from '../../core/services/usuario.service';

@Component({
  selector: 'app-configuracoes',
  standalone: true,
  imports: [CommonModule, FormsModule, SidebarComponent, HeaderComponent],
  templateUrl: './configuracoes.html',
  styleUrl: './configuracoes.css'
})
export class ConfiguracoesComponent implements OnInit {
  private authService = inject(AuthService);
  private usuarioService = inject(UsuarioService);

  usuario: any = {
    nome: '',
    email: '',
    login: '',
    perfil: ''
  };

  senhaAtual: string = '';
  novaSenha: string = '';
  confirmarSenha: string = '';

  ngOnInit() {
    this.carregarPerfil();
  }

  carregarPerfil() {
    // Aqui assumimos que o AuthService tem o usuário ou buscamos do backend
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    this.usuario = { ...user };
  }

  salvarPerfil() {
    alert('Funcionalidade de atualização de perfil em desenvolvimento.');
  }

  alterarSenha() {
    if (this.novaSenha !== this.confirmarSenha) {
      alert('As senhas não coincidem!');
      return;
    }
    alert('Funcionalidade de alteração de senha em desenvolvimento.');
  }
}
