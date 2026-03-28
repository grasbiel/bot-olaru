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
  error = '';

  onLogin(event: Event) {
    event.preventDefault();
    this.error = '';
    
    this.authService.login({ email: this.email, senha: this.senha }).subscribe({
      next: () => {
        console.log('Login efetuado com sucesso!');
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        console.error('Erro no login', err);
        this.error = 'Credenciais inválidas. Tente novamente.';
      }
    });
  }
}
