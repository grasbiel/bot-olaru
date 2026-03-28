# Stage 1: Build the Angular app
FROM node:22-alpine AS build
WORKDIR /app

# Instalar dependências primeiro para cache do Docker
COPY package*.json ./
RUN npm install

# Copiar código e rodar build
COPY . .
RUN npm run build

# Stage 2: Serve the app with Nginx
FROM nginx:alpine
# Copiar o build para a pasta padrão do Nginx
# NOTA: Ajuste o caminho 'dist/olaru-web' se o nome do projeto no build for diferente
COPY --from=build /app/dist/olaru-web/browser /usr/share/nginx/html

# Copiar configuração customizada do Nginx para suportar roteamento do Angular (SPA)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
