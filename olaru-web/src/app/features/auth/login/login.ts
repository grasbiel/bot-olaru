import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  email = '';
  senha = '';
  loading = false;
  errorMsg = '';

  login() {
    if (!this.email || !this.senha) return;
    
    this.loading = true;
    this.errorMsg = '';

    this.authService.login({ email: this.email.trim(), senha: this.senha }).subscribe({
      next: (res: any) => {
        // Guardar usuário para saudação no dashboard
        localStorage.setItem('user', JSON.stringify(res.usuario || { nome: 'Admin' }));
        
        const perfil = res.usuario?.perfil || 'admin';
        if (perfil === 'tecnico') {
          this.router.navigate(['/tecnico']);
        } else {
          this.router.navigate(['/dashboard']);
        }
      },
      error: () => {
        this.errorMsg = 'E-mail ou senha incorretos. Tente novamente.';
        this.loading = false;
      }
    });
  }
}
