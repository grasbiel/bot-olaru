import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

const TOKEN_KEY = 'olaru_token';
const REFRESH_KEY = 'olaru_refresh_token';
const USER_KEY = 'olaru_user';

export type Perfil = 'admin' | 'gerente' | 'tecnico';

export interface UsuarioLogado {
  nome: string;
  email: string;
  perfil: Perfil;
}

interface TokenResponse {
  token: string;
  refreshToken: string;
  tipo: string;
  usuario: UsuarioLogado;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = `${environment.apiUrl}/auth`;

  /** Signal reativo com o usuário logado (ou null) */
  private _usuario = signal<UsuarioLogado | null>(this.loadUsuario());
  readonly usuario = this._usuario.asReadonly();
  readonly perfil = computed(() => this._usuario()?.perfil ?? null);
  readonly isLoggedIn = computed(() => !!this.getToken() && !!this._usuario());

  constructor(private http: HttpClient) {}

  login(credentials: { email: string; senha: string }): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, credentials).pipe(
      tap((res) => {
        if (res?.token) {
          sessionStorage.setItem(TOKEN_KEY, res.token);
          sessionStorage.setItem(REFRESH_KEY, res.refreshToken);
          this.saveUsuario(res.usuario);
        }
      })
    );
  }

  refresh(): Observable<TokenResponse> {
    const refreshToken = this.getRefreshToken();
    return this.http.post<TokenResponse>(`${this.apiUrl}/refresh`, { refreshToken }).pipe(
      tap((res) => {
        if (res?.token) {
          sessionStorage.setItem(TOKEN_KEY, res.token);
          sessionStorage.setItem(REFRESH_KEY, res.refreshToken);
          this.saveUsuario(res.usuario);
        }
      })
    );
  }

  logout(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    this._usuario.set(null);
  }

  getToken(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return sessionStorage.getItem(REFRESH_KEY);
  }

  /** Verifica se o perfil do usuário está na lista de perfis permitidos */
  hasRole(roles: Perfil[]): boolean {
    const p = this.perfil();
    return p !== null && roles.includes(p);
  }

  /** Retorna a rota padrão pós-login baseada no perfil */
  getDefaultRoute(): string {
    const p = this.perfil();
    if (p === 'tecnico') return '/tecnico';
    return '/dashboard';
  }

  private saveUsuario(usuario: UsuarioLogado): void {
    localStorage.setItem(USER_KEY, JSON.stringify(usuario));
    this._usuario.set(usuario);
  }

  private loadUsuario(): UsuarioLogado | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      // Valida que tem os campos necessários
      if (parsed?.nome && parsed?.email && parsed?.perfil) {
        return parsed as UsuarioLogado;
      }
      return null;
    } catch {
      return null;
    }
  }
}
