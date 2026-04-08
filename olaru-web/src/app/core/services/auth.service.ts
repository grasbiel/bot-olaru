import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

const TOKEN_KEY = 'olaru_token';
const REFRESH_KEY = 'olaru_refresh_token';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = `${environment.apiUrl}/auth`;

  constructor(private http: HttpClient) {}

  login(credentials: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/login`, credentials).pipe(
      tap((res: any) => {
        if (res?.token) {
          sessionStorage.setItem(TOKEN_KEY, res.token);
          sessionStorage.setItem(REFRESH_KEY, res.refreshToken);
        }
      })
    );
  }

  refresh(): Observable<any> {
    const refreshToken = this.getRefreshToken();
    return this.http.post<any>(`${this.apiUrl}/refresh`, { refreshToken }).pipe(
      tap((res: any) => {
        if (res?.token) {
          sessionStorage.setItem(TOKEN_KEY, res.token);
          sessionStorage.setItem(REFRESH_KEY, res.refreshToken);
        }
      })
    );
  }

  logout(): void {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  }

  getToken(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return sessionStorage.getItem(REFRESH_KEY);
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }
}
