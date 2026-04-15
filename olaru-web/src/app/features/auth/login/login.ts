import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
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
  private route = inject(ActivatedRoute);

  email = '';
  senha = '';
  loading = false;
  errorMsg = '';

  login() {
    if (!this.email || !this.senha) return;
    
    this.loading = true;
    this.errorMsg = '';

    this.authService.login({ email: this.email.trim(), senha: this.senha }).subscribe({
      next: () => {
        // Redireciona para a URL original ou rota padrão do perfil
        const returnUrl = this.route.snapshot.queryParams['returnUrl'];
        if (returnUrl) {
          this.router.navigateByUrl(returnUrl);
        } else {
          this.router.navigate([this.authService.getDefaultRoute()]);
        }
      },
      error: () => {
        this.errorMsg = 'E-mail ou senha incorretos. Tente novamente.';
        this.loading = false;
      }
    });
  }
}
