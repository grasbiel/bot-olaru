import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Impede que usuários já logados acessem a tela de login.
 *
 * Se o usuário já estiver autenticado, redireciona para sua
 * rota padrão (dashboard para admin/gerente, /tecnico para técnico).
 */
export const loginGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isLoggedIn()) {
    router.navigate([authService.getDefaultRoute()]);
    return false;
  }

  return true;
};
