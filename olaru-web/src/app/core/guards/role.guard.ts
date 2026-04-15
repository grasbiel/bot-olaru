import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService, Perfil } from '../services/auth.service';

/**
 * Factory que cria um guard de rota baseado em perfis permitidos.
 *
 * Uso nas rotas:
 *   canActivate: [roleGuard('admin', 'gerente')]
 *
 * Se o perfil do usuário não estiver na lista, redireciona para
 * a rota padrão do perfil dele (dashboard ou /tecnico).
 */
export function roleGuard(...allowedRoles: Perfil[]): CanActivateFn {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (authService.hasRole(allowedRoles)) {
      return true;
    }

    // Usuário autenticado mas sem permissão — redireciona para rota padrão do perfil
    const defaultRoute = authService.getDefaultRoute();
    router.navigate([defaultRoute]);
    return false;
  };
}
