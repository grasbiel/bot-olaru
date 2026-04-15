import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from '../../shared/components/sidebar/sidebar';
import { HeaderComponent } from '../../shared/components/header/header';
import { AuthService } from '../../core/services/auth.service';

/**
 * Layout shell para rotas autenticadas.
 * Renderiza sidebar (desktop) ou bottom nav (mobile) + header + conteúdo.
 * Técnicos recebem layout simplificado sem sidebar completa.
 */
@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, SidebarComponent, HeaderComponent],
  template: `
    <div class="layout" [class.layout--tecnico]="isTecnico()">
      <app-sidebar *ngIf="!isTecnico()" />
      <div class="layout-main">
        <app-header />
        <main class="layout-content">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: [`
    .layout {
      display: flex;
      min-height: 100vh;
      background: var(--color-bg, #0D0F14);
    }

    .layout-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .layout-content {
      flex: 1;
      padding: var(--spacing-6, 24px);
      overflow-y: auto;
    }

    .layout--tecnico {
      flex-direction: column;
    }

    .layout--tecnico .layout-main {
      width: 100%;
    }

    @media (max-width: 767px) {
      .layout-content {
        padding: var(--spacing-4, 16px);
      }
    }
  `]
})
export class LayoutComponent {
  private authService = inject(AuthService);

  isTecnico = computed(() => this.authService.perfil() === 'tecnico');
}
