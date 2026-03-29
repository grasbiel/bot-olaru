import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class VisitaService {
  private apiUrl = `${environment.apiUrl}/visitas`;

  constructor(private http: HttpClient) {}

  listar(data?: string): Observable<any[]> {
    let params = {};
    if (data) {
      params = { data };
    }
    return this.http.get<any[]>(this.apiUrl, { params });
  }

  atualizarStatus(id: string, novoStatus: string): Observable<any> {
    return this.http.patch(`${this.apiUrl}/${id}/status`, { status: novoStatus });
  }

  verificarDisponibilidade(data: string, turno: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/disponibilidade`, { params: { data, turno } });
  }
}
