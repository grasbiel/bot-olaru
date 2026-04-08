import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class UsuarioService {
  private apiUrl = `${environment.apiUrl}/usuarios`;

  constructor(private http: HttpClient) {}

  listar(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  listarTecnicos(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/tecnicos`);
  }

  buscarPorId(id: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/${id}`);
  }

  criar(dados: any): Observable<any> {
    return this.http.post<any>(this.apiUrl, dados);
  }

  atualizar(id: string, dados: any): Observable<any> {
    return this.http.patch<any>(`${this.apiUrl}/${id}`, dados);
  }

  redefinirSenha(id: string, novaSenha: string): Observable<any> {
    return this.http.patch(`${this.apiUrl}/${id}/senha`, { novaSenha }, { responseType: 'text' });
  }

  desativar(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
