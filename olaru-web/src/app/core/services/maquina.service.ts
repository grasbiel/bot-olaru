import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class MaquinaService {
  private apiUrl = `${environment.apiUrl}/maquinas`;

  constructor(private http: HttpClient) {}

  listar(): Observable<any[]> {
    return this.http.get<any[]>(this.apiUrl);
  }

  salvar(maquina: any): Observable<any> {
    return this.http.post<any>(this.apiUrl, maquina);
  }

  atualizar(id: string, maquina: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/${id}`, maquina);
  }

  excluir(id: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/${id}`);
  }

  consultarEstoque(nome: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/estoque/${nome}`);
  }
}
