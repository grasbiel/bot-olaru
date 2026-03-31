import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = `${environment.apiUrl}/auth`;

  constructor(private http: HttpClient) {}

  login(credentials: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/login`, credentials).pipe(
      tap((res: any) => {
        if (res && res.token) {
          sessionStorage.setItem('olaru_token', res.token);
          // Decodificar token para pegar o perfil se necessário
          // Por enquanto apenas guardamos
        }
      })
    );
  }

  logout(): void {
    sessionStorage.removeItem('olaru_token');
  }

  getToken(): string | null {
    return sessionStorage.getItem('olaru_token');
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }
}
