# TCOTRUCK — Calculadora TCO de camiones pesados

Calculadora de Total Cost of Ownership (TCO) para flota pesada, comparando
gasóleo vs. eléctrico en mercado español/europeo. Audiencia: gestores de
flota, transportistas y consultores de transporte pesado.

Producción en https://tcotruck.com (Cloudflare Pages, deploy automático
en cada push a `main`).

## Ubicación del repo

- **Repo real**: `C:\proyectos\tcotruck\`
- **No está en OneDrive.** Si ves una carpeta `OneDrive\Desktop\Calculadora
  camión eléctrico\` con archivos parecidos, es un espejo histórico anterior
  al repo. Está marcado para archivar. Trabajar siempre en `C:\proyectos\tcotruck\`.

## Stack

- HTML5 + CSS3 (con variables custom) + JavaScript vanilla.
- Chart.js cargado vía CDN.
- **Sin frameworks. Sin build step. Sin npm.** No hay `package.json`
  y no debe haberlo.
- Un único `index.html` monolítico que contiene HTML, CSS y JS inline.
- Hosting: Cloudflare Pages, deploy automático al hacer push a `main`.

## Restricciones técnicas (importantes)

- **NO añadir frameworks** (React, Vue, Svelte, etc.) sin discutirlo antes.
- **NO añadir dependencias npm.** El proyecto es deliberadamente zero-deps.
- **NO romper el contrato con `prices.json`.** La estructura del JSON la
  consume el frontend y la produce el GitHub Action de MITECO; cambiar
  campos rompe ambos lados.
- **Mantener compatibilidad** con últimas 2 versiones de Chrome, Firefox,
  Safari y Edge.
- **Performance**: el archivo único debe cargar en menos de 1 segundo
  en 4G. Cuidado al añadir scripts o assets pesados.

## Diseño visual

- Paleta semántica con variables CSS en `:root`:
  - `--diesel` (#d97706, amber cálido) para gasóleo.
  - `--elec` (#0284c7, azul cielo) para eléctrico.
  - `--green` para ahorro, rojo para sobrecoste.
- Estilo editorial profesional, no SaaS típico.
- Layout responsive con tres breakpoints (1199 / 1023 / 640 px).
- En desktop: tres columnas con sidebar sticky.
- En tablet/mobile: una columna apilada, sidebar plegable con
  `<details class="sb-wrap">` y chevron animado.
- Tipografía fluida con `clamp()` en valores clave.
- Fix de scroll horizontal con `html, body { overflow-x: clip; }`.

## Datos

- **Precios de combustible**: actualizados diariamente por GitHub Action
  desde la API de MITECO. Ver `.github/workflows/update-prices.yml` y
  `.github/scripts/fetch_prices.py`. El cron está programado a las
  07:30 UTC (≈ 09:30 hora peninsular en verano).
- **Modelos de camión 2025-2026**: Mercedes Actros, Volvo FH, Scania R,
  MAN TGX, DAF XF, Renault T.
- **Degradación de batería**: basada en el estudio Geotab 2025.

## Idioma

- Versión actual: español.
- Versión inglesa para mercado europeo: planeada, todavía no implementada.
  Decisión pendiente: subdirectorio `/en/` vs. toggle ES/EN en runtime.

## Convenciones para Claude Code

- **Entorno**: Windows. Comandos en **PowerShell**, no bash. Siempre
  indicar antes en qué carpeta hay que estar.
- **Antes de modificar archivos críticos** (`index.html`, workflows,
  `prices.json`), mostrar `git diff` y esperar OK explícito antes
  de hacer `git add` / `commit` / `push`.
- **Mensajes de commit** en inglés, estilo Conventional Commits cuando
  aplique (`feat:`, `fix:`, `chore:`, `docs:`).
- **No tocar `prices.json` a mano**: lo gestiona el workflow.

## Pendientes priorizados

1. Aviso legal y footer mínimo (LSSI-CE, requerido antes de monetizar).
2. Configurar Cloudflare Email Routing (`info@tcotruck.com` → Gmail personal).
3. Página `/methodology` con fuentes y supuestos del modelo.
4. Versión inglesa (`/en/` o toggle en runtime).
5. Mejoras del modelo TCO inspiradas en ICCT TCO Calculator: tasa de
   descuento NPV, escalado anual de precios de combustible/electricidad,
   coste laboral del conductor + tiempo de carga, penalización por
   carga útil (peso de batería).
6. Blog en `tcotruck.com/blog` con generador estático (Astro u otro).
   **No usar WordPress** para este blog.
7. Actualizar `actions/checkout` y `actions/setup-python` cuando den
   deprecation warnings serios (versiones más nuevas estables).
8. Borrar repo viejo `javisalta/tco-truck-2026`.

## Estructura del repo

```
C:\proyectos\tcotruck\
├── .github/
│   ├── scripts/
│   │   └── fetch_prices.py        # script Python que consume API MITECO
│   └── workflows/
│       └── update-prices.yml      # cron diario que actualiza prices.json
├── CLAUDE.md                       # este archivo
├── README.md
├── index.html                      # único archivo HTML/CSS/JS
├── prices.json                     # generado por el workflow, no editar a mano
├── favicon.ico                     # set de favicons
├── favicon-*.png
├── apple-touch-icon.png
└── site.webmanifest
```
