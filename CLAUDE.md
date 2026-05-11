# Proyecto TCOTRUCK

Calculadora TCO (Total Cost of Ownership) para camiones pesados en España y Europa. Compara escenarios diésel vs eléctrico con modelos reales del mercado, modalidades de financiación (compra/leasing/renting), y datos actualizados de combustible y degradación de batería.

## Producción
- URL: https://tcotruck.com
- Hosting: Cloudflare Pages
- Deploy: automático en cada push a main (en ~60 segundos)
- Dominio: gestionado en Cloudflare Registrar

## Arquitectura
- index.html: aplicación completa en un único archivo (HTML + CSS + JavaScript vanilla)
- prices.json: datos de precio del gasóleo (surtidor y profesional), actualizado automáticamente
- .github/workflows/: GitHub Action que actualiza prices.json diariamente desde la API del Ministerio de Transición Ecológica (MINETUR)
- README.md: documentación mínima

## Stack técnico
- HTML5, CSS3 (variables custom, sin frameworks)
- JavaScript vanilla (sin React, Vue, ni librerías de UI)
- Chart.js (vía CDN) para los gráficos
- Sin build step, sin transpilación
- Sin dependencias npm

## Lenguaje
- Interfaz actual: español (España)
- Planeada: versión inglesa para mercado europeo
- Audiencia: gestores de flota, transportistas, consultores del sector transporte pesado

## Diseño y estética
- Tipografía: serif para titulares y números grandes, sans-serif para datos y controles
- Paleta de colores: naranja para diésel, azul para eléctrico, verde para ahorro, rojo para sobrecoste
- Estilo editorial profesional, no SaaS típico. Inspirado en herramientas serias como ICCT, ACEA, IEA
- Tres columnas en desktop: panel diésel, resultados centrales, panel eléctrico

## Datos y fuentes
- Precio de gasóleo: API del Ministerio de Transición Ecológica (MINETUR), actualizado diariamente
- Modelos de camión: precios verificados de fabricantes (Mercedes, Volvo, Scania, MAN, DAF, Renault) para versiones 2025-2026
- Degradación de batería: estudio Geotab 2025 (22.700 vehículos analizados, ~2,3% al año)
- Mix eléctrico España: 0,21 kgCO2 por kWh
- Factor emisión diésel: 2,67 kgCO2 por litro

## Workflow Git
- Rama principal: main
- Estilo de commits: mensajes descriptivos en español, prefijo convencional (feat, fix, chore, style, docs)
- Push directo a main (proyecto de un solo desarrollador, sin PRs)
- Cloudflare Pages despliega automáticamente tras cada push

## Pendientes priorizados
1. CSS responsive: eliminar el scroll horizontal en pantallas medianas y pequeñas. Mantener diseño de tres columnas en desktop, colapsar a una columna en mobile
2. Versión inglesa (EN): toggle ES/EN integrado o subdirectorio /en/
3. Página /methodology: explicar fuentes, supuestos y metodología
4. Footer con aviso legal mínimo: requerido por LSSI-CE si se monetiza o capta leads
5. Mejoras inspiradas en ICCT TCO Calculator: tasa de descuento (NPV), escalado anual de precios, coste laboral del conductor, penalización por carga útil

## Restricciones importantes
- NO añadir frameworks (React, Vue, etc.) sin discutirlo antes. La simplicidad arquitectónica es deliberada
- NO añadir dependencias npm. El proyecto no tiene package.json ni node_modules
- NO romper el contrato con prices.json (estructura que espera el GitHub Action de MINETUR)
- Mantener compatibilidad con navegadores modernos (Chrome, Firefox, Safari, Edge, últimas 2 versiones)
- Performance: el archivo único debe seguir cargando en menos de 1 segundo en 4G

## Estilo de código
- Indentación: 2 espacios
- Comillas: dobles para HTML, simples para JavaScript
- Comentarios en español, breves y solo cuando aportan
- Nombres de variables y funciones en inglés (estándar JS), nombres de UI en español
