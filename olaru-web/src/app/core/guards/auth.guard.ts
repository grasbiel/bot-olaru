import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Protege rotas que exigem autenticação.
 *
 * Se o usuário não estiver logado, redireciona para /login.
 * Se estiver logado mas o token expirou e há refresh token,
 * o interceptor HTTP tentará renovar automaticamente.
 */
export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isLoggedIn()) {
    return true;
  }

  // Redireciona para login preservando a URL que o usuário tentou acessar
  router.navigate(['/login'], {
    queryParams: { returnUrl: router.getCurrentNavigation()?.extractedUrl.toString() }
  });
  return false;
};
