import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { VisitaService } from '../../../core/services/visita.service';


@Component({
  selector: 'app-minhas-visitas',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './minhas-visitas.html',
  styleUrl: './minhas-visitas.css'
})
export class MinhasVisitasComponent implements OnInit {
  private visitaService = inject(VisitaService);

  isOnline = navigator.onLine;
  visitas: any[] = [];
  visitaAtiva: any = null;
  
  // Estado do Modal de Finalização
  mostrarModal = false;
  observacoes = '';
  fotoSelecionada: File | null = null;
  previewFoto: string | null = null;
  enviando = false;

  ngOnInit() {
    this.carregarVisitas();
    window.addEventListener('online', () => this.isOnline = true);
    window.addEventListener('offline', () => this.isOnline = false);
  }

  carregarVisitas() {
    this.visitaService.listarMinhasVisitas().subscribe({
      next: data => this.visitas = data,
      error: err => console.error('Erro ao carregar visitas:', err)
    });
  }

  chegueiNoLocal(visita: any) {
    if (!this.isOnline) return;
    this.visitaService.atualizarStatus(visita.id, 'em_andamento').subscribe(() => {
      this.carregarVisitas();
    });
  }

  abrirFinalizacao(visita: any) {
    this.visitaAtiva = visita;
    this.mostrarModal = true;
    this.observacoes = '';
    this.fotoSelecionada = null;
    this.previewFoto = null;
  }

  fecharModal() {
    this.mostrarModal = false;
    this.visitaAtiva = null;
  }

  onFotoSelecionada(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.fotoSelecionada = file;
      const reader = new FileReader();
      reader.onload = () => this.previewFoto = reader.result as string;
      reader.readAsDataURL(file);
    }
  }

  finalizarVisita() {
    if (this.observacoes.length < 10 || !this.isOnline) return;

    this.enviando = true;
    const id = this.visitaAtiva.id;

    // Sequência de salvamento: Observação -> Foto (se houver) -> Status
    this.visitaService.registrarObservacao(id, this.observacoes).subscribe({
      next: () => {
        if (this.fotoSelecionada) {
          this.visitaService.uploadFoto(id, this.fotoSelecionada).subscribe({
            next: () => this.concluirStatus(id),
            error: () => this.concluirStatus(id) // Continua mesmo se a foto falhar
          });
        } else {
          this.concluirStatus(id);
        }
      },
      error: () => {
        this.enviando = false;
        alert('Erro ao salvar observações. Tente novamente.');
      }
    });
  }

  private concluirStatus(id: string) {
    this.visitaService.atualizarStatus(id, 'concluida').subscribe(() => {
      this.enviando = false;
      this.fecharModal();
      this.carregarVisitas();
    });
  }

  abrirMapa(endereco: string) {
    const encoded = encodeURIComponent(endereco);
    window.open(`https://www.google.com/maps/search/?api=1&query=${encoded}`, '_blank');
  }
}
