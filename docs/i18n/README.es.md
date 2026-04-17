# Architecture Compiler: un AI Harness a nivel de arquitectura

Nota: la documentación en inglés es la fuente de verdad canónica. Si esta traducción difiere de la versión en inglés, sigue la versión en inglés.

Idiomas: [English](../../README.md) | [简体中文](README.zh-CN.md) | Español

ArchCompiler compila restricciones y requisitos no funcionales (NFR) en decisiones arquitectónicas explícitas y revisables, con trade-offs claros y una visión concreta del impacto en costes.

Es un AI harness a nivel de arquitectura formado por tres partes:

- un compilador determinista
- un registro curado de patrones de diseño
- skills de flujo de trabajo para agents

Combinadas, estas tres piezas convierten requisitos en arquitectura compilada, redirigen el trabajo a través de aprobación y reaprobación cuando cambian las decisiones arquitectónicas, y guían la implementación contra un contrato arquitectónico explícito.

El compilador en sí está diseñado para ser simple a propósito: sin inferencia LLM, sin valores por defecto ocultos y sin lógica de selección opaca. La inteligencia arquitectónica vive en el registro de patrones y en la disciplina de flujo de trabajo que aportan estos tres skills:

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

[![CI - Test Suite](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml/badge.svg)](https://github.com/inetgas/arch-compiler/actions/workflows/main.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Registry](https://img.shields.io/badge/Registry-Curated-success)
![Skills](https://img.shields.io/badge/Skills-Workflow-orange)
![Core](https://img.shields.io/badge/Core-No--LLM%20Inference-black)

> **Etiquetas:** `architecture-as-code`, `architecture-harness`, `agent-harness`, `deterministic-compiler`, `pattern-registry`, `nfr-enforcement`, `ai-governance`

## Filosofía central

- **Los patrones son la base de conocimiento.** Toda la lógica arquitectónica vive en los archivos de `patterns/`. El compilador se mantiene deliberadamente simple.
- **Filtrado por inclusión.** Los patrones declaran qué condiciones del spec soportan mediante reglas `supports_constraints` y `supports_nfr`. Un patrón se selecciona cuando todas sus reglas coinciden con el spec.
- **Schema-first.** `schemas/canonical-schema.yaml` define el contrato del spec; `schemas/pattern-schema.yaml` define el contrato del patrón. Ambos son la fuente de verdad.

---

## Inicio rápido

Si tu sistema no dispone del comando `python`, sustituye `python` por `python3` en los comandos de abajo.

```bash
# Instala pipx si hace falta (recomendado para aplicaciones CLI en Python)
brew install pipx

# Instala la CLI desde el repo actual
pipx install .

# Compila un spec de ejemplo real (salida a stdout)
archcompiler tests/fixtures/no-advisory-success.yaml

# Compila y escribe artefactos en un directorio
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/

# Modo verbose — comentarios inline de patterns + archivo rejected-patterns
archcompiler tests/fixtures/no-advisory-success.yaml -v
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v

# Añade marca de tiempo UTC a los nombres de archivo de salida
archcompiler tests/fixtures/no-advisory-success.yaml -o compiled_output/ -v -t
```

### Entorno de desarrollo

```bash
# Crea y activa un entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instala dependencias de desarrollo local
python -m pip install -r tools/requirements.txt
python -m pip install -e .

# Ejecuta el compilador desde el árbol fuente
python tools/archcompiler.py tests/fixtures/no-advisory-success.yaml
```

Ejecuta los comandos de desarrollo desde la raíz del repo `arch-compiler/`. Algunas pruebas invocan `tools/archcompiler.py` con rutas relativas al directorio actual y fallarán si las ejecutas desde un directorio padre.

---

## Instalar los Agent Skills

Este repositorio también incluye agent skills instalables.

### Codex

Recomendado: usa el instalador bootstrap oficial de Codex. Instala los tres skills y clona o actualiza el repo completo de runtime en la ruta canónica de Codex.

```bash
# Instalación en una sola línea desde GitHub
bash <(curl -fsSL https://raw.githubusercontent.com/inetgas/arch-compiler/main/scripts/install_codex_skills.sh)
```

Si prefieres inspeccionar primero el repositorio:

```bash
git clone https://github.com/inetgas/arch-compiler.git
cd arch-compiler
./scripts/install_codex_skills.sh
```

Reinicia Codex después de instalar.

El instalador hace lo siguiente:

- instala `using-arch-compiler`, `compiling-architecture` y `implementing-architecture` en el directorio global compartido de agent skills `~/.agents/skills/`
- clona o actualiza el repo completo de runtime en `~/.codex/arch-compiler`
- verifica tanto los skills instalados como la estructura del runtime

Alternativa: instalación manual con la CLI abierta de `skills.sh` / Vercel skills.

```bash
# Lista los skills publicados por este repo
npx skills add inetgas/arch-compiler --list

# Instala los tres en el directorio global compartido (~/.agents/skills/)
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -g -y

# Clona el repo completo de runtime usado por los skills instalados
git clone https://github.com/inetgas/arch-compiler.git ~/.codex/arch-compiler

# Verifica que los tres skills se instalaron globalmente
ls ~/.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

Si omites `-g`, los skills se instalan dentro del proyecto actual en `./.agents/skills/` en lugar de tu directorio global de Codex.

```bash
# Instalación local al proyecto (compartida con el repo actual)
npx skills add inetgas/arch-compiler \
  --skill using-arch-compiler \
  --skill compiling-architecture \
  --skill implementing-architecture \
  -a codex -y

# Verifica la instalación local al proyecto
ls ./.agents/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

Importante: la CLI `skills` instala solo las carpetas de los skills. Los flujos de trabajo siguen necesitando el repo completo de Architecture Compiler en una ruta local estable como `~/.codex/arch-compiler` para que los agents puedan acceder al compilador, al registro de patrones, a los schemas, a la configuración y a los adaptadores.

Para desinstalar el layout global de `skills.sh`:

```bash
rm -rf ~/.agents/skills/using-arch-compiler
rm -rf ~/.agents/skills/compiling-architecture
rm -rf ~/.agents/skills/implementing-architecture
```

Para desinstalar el layout local al proyecto de `skills.sh`:

```bash
rm -rf ./.agents/skills/using-arch-compiler
rm -rf ./.agents/skills/compiling-architecture
rm -rf ./.agents/skills/implementing-architecture
```

Opcionalmente, elimina también el clon de runtime:

```bash
rm -rf ~/.codex/arch-compiler
```

Alternativa: usa las instrucciones nativas de onboarding para Codex incluidas en el repo.

Este fallback usa un layout en disco distinto al del bootstrap installer: una sola entrada de pack mediante symlink en `~/.agents/skills/arch-compiler`, en lugar de tres directorios copiados bajo `~/.agents/skills/`.

Dile a Codex:

```text
Fetch and follow instructions from https://raw.githubusercontent.com/inetgas/arch-compiler/refs/heads/main/.codex/INSTALL.md
```

O sigue directamente los pasos nativos de instalación:

```bash
mkdir -p ~/.agents/skills
ln -s ~/.codex/arch-compiler/skills ~/.agents/skills/arch-compiler
```

Verifica este layout con symlink:

```bash
ls -la ~/.agents/skills/arch-compiler
```

Desinstala este layout con symlink:

```bash
rm ~/.agents/skills/arch-compiler
```

Opcionalmente, elimina también el clon de runtime:

```bash
rm -rf ~/.codex/arch-compiler
```

Importante: los archivos de skill por sí solos no son suficientes. Los flujos de trabajo dependen de que el repo completo esté disponible en una ruta local estable para que los agents puedan acceder al compilador, al registro de patrones, a los schemas y a los adaptadores sin volver a clonar ni depender de `/tmp/`.

Fallback avanzado: instala los tres skills directamente desde el repo público:

Este fallback usa un tercer layout en disco: tres directorios de skill copiados bajo `~/.codex/skills/` y gestionados por el instalador GitHub integrado de Codex.

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo inetgas/arch-compiler \
  --path skills/using-arch-compiler skills/compiling-architecture skills/implementing-architecture
```

Nota del instalador de Codex: si instalas múltiples skills desde este repo, pasa todas las rutas de skill detrás de un único argumento `--path`. No repitas `--path`; en el instalador actual solo se conserva el último valor repetido.

Después de instalar, verifica que existan los tres directorios:

```bash
ls ~/.codex/skills | rg 'using-arch-compiler|compiling-architecture|implementing-architecture'
```

Para desinstalar este layout:

```bash
rm -rf ~/.codex/skills/using-arch-compiler
rm -rf ~/.codex/skills/compiling-architecture
rm -rf ~/.codex/skills/implementing-architecture
```

### Puntos de entrada de los skills

- `skills/using-arch-compiler` = elige el flujo correcto y redirige de vuelta a compilación si cambia la arquitectura
- `skills/compiling-architecture` = compila y finaliza la arquitectura
- `skills/implementing-architecture` = implementa una arquitectura aprobada

### Preflight del flujo de trabajo para agents

Antes de iniciar flujos de compilación o implementación de arquitectura sobre un repo de aplicación, ejecuta el helper de preflight compartido. Esto aplica independientemente de si el flujo está siendo conducido por Codex, Claude Code u otro wrapper de agent.

```bash
# Si instalaste el paquete como CLI:
archcompiler-preflight --app-repo /path/to/app-repo --mode compile

# O ejecuta directamente el helper desde una ruta local estable del repo:
python3 ~/.codex/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 ~/.claude/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
python3 ~/.hermes/arch-compiler/tools/archcompiler_preflight.py --app-repo /path/to/app-repo --mode compile
```

Usa `--mode implement` cuando el flujo vaya a escribir código a partir de una carpeta `docs/architecture/` ya aprobada.

### Claude Code

Claude Code no descubre skills de forma nativa como Codex, pero este repo incluye adaptadores de comando listos para copiar en `adapters/claude-code/commands/`, incluido un entrypoint de enrutamiento.

Comandos adaptadores disponibles:

- `using-arch-compiler.md`
- `compile-architecture.md`
- `implement-architecture.md`

### Hermes

Hermes puede descubrir estos skills desde `skills.sh` / instalaciones GitHub, o escaneando un directorio externo compartido de skills.

Si ya instalaste los skills para Codex, la forma más sencilla de configurar Hermes es reutilizar los mismos directorios:

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

Mantén también el repo completo de runtime en una ruta local estable como `~/.hermes/arch-compiler` para que los skills ejecutados por Hermes puedan encontrar el compilador, los patrones, los schemas, la configuración y los adaptadores sin volver a clonar.

```bash
git clone https://github.com/inetgas/arch-compiler.git ~/.hermes/arch-compiler
```

Si prefieres la instalación nativa de Hermes en lugar de reutilizar directorios externos, sigue el flujo habitual de Hermes con `skills.sh` o GitHub taps para descubrimiento e instalación, pero mantén el mismo clon estable de runtime en `~/.hermes/arch-compiler`.

---

## Formato del spec

El spec de entrada es un archivo YAML validado contra `schemas/canonical-schema.yaml`. Ejemplo:

```yaml
# ─── EXAMPLE SPEC ───
# This is a minimal spec showing the basic structure.
# You'll add fields progressively as your requirements become clearer.
# See test-specs/ for more complete examples and edge cases.
project:
  name: My Service
  domain: ecommerce
functional:
  summary: REST API for product catalogue
constraints:
  cloud: azure
  language: python
  platform: api
nfr:
  availability:
    target: 0.999
  latency:
    p95Milliseconds: 100
    p99Milliseconds: 200
  security:
    auth: jwt
```

Todos los campos no proporcionados se completan con `config/defaults.yaml` y se registran en la sección `assumptions` de la salida.

Para excluir explícitamente patrones que de otro modo serían seleccionados (por ejemplo, demasiado complejos para el alcance actual), añade una lista de nivel superior `disallowed-patterns`:

```yaml
disallowed-patterns:
  - ops-low-cost-observability
  - ops-slo-error-budgets
```

Los patrones excluidos aparecen en `rejected-patterns.yaml` con `phase: phase_2_5_disallowed_patterns`. Se emite una advertencia para cualquier ID no encontrado en el registro.

Consulta `test-specs/` para ver un conjunto amplio de specs de ejemplo que cubren casos límite, combinaciones de plataformas, requisitos de compliance y más.

---

## Salida del compilador

### stdout

El compilador siempre imprime el spec compilado a stdout: el spec fusionado con todos los defaults aplicados y, en modo verbose, comentarios inline de patterns. El código de salida es `0` en éxito y `1` en errores de validación.

### Archivos escritos con `-o`

| Archivo | Modo | Descripción |
|------|------|-------------|
| `compiled-spec.yaml` | siempre | Spec fusionado completo con assumptions; puede volver a usarse como entrada |
| `selected-patterns.yaml` | siempre | Patrones seleccionados con match scores y reglas honradas |
| `rejected-patterns.yaml` | solo `-v` | Patrones rechazados con motivo y fase de filtrado |
| `compiled-spec-<timestamp>.yaml` | `-t` | Mismos archivos anteriores, pero con sufijo UTC en el nombre |

### Comentarios inline en modo verbose

Con `-v`, el spec compilado anota cada campo con los patrones que lo activaron:

```yaml
constraints:
  platform: api  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
  cloud: aws     # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (13 more)
nfr:
  availability:
    target: 0.999  # arch-serverless--aws, db-managed-postgres, api-rest-resource-oriented, ... (14 more)
```

Esto hace visible de inmediato la relación entre los valores del spec y los patrones seleccionados.

---

## Cómo funciona la selección de patrones

| Fase | Qué ocurre |
|-------|-------------|
| **1. Parse & Validate** | Carga el spec, valida el schema y comprueba consistencia semántica |
| **2. Merge Defaults** | Rellena campos faltantes desde `config/defaults.yaml` y los registra en `assumptions` |
| **2.5 Disallowed filter** | Elimina cualquier patrón listado en `disallowed-patterns`; advierte sobre IDs desconocidos |
| **3.1 Constraint filter** | Conserva patrones cuyas reglas `supports_constraints` coinciden todas con el spec |
| **3.2 NFR filter** | Conserva patrones cuyas reglas `supports_nfr` coinciden todas con el spec |
| **3.3 Conflict resolution** | Elimina patrones en conflicto; gana el de mayor match score y luego menor coste según la intención activa |
| **3.4 Config merge** | Fusiona `defaultConfig` del patrón en `assumptions.patterns` |
| **3.5 Coding filter** | Descarta patrones de nivel coding salvo que se use `--include-coding-patterns` |
| **4. Cost feasibility** | Comprueba el coste total frente a `cost.ceilings`; emite advertencias advisory |
| **5. Output** | Emite el spec compilado a stdout y escribe artefactos si se especifica `-o` |

### Patrones de coding

Por defecto, los patrones de tipo `coding` (GoF, DI, estrategias de testing, workflows de desarrollo) se excluyen. En la era de los AI coding agents, estos se pueden manejar bajo demanda. Usa `--include-coding-patterns` para incluirlos.

---

## Refinamiento progresivo

El compilador está diseñado para usarse de manera iterativa e incremental. No necesitas un spec completo desde el principio: empieza con lo mínimo y añade restricciones conforme crezca tu comprensión.

### Un flujo de trabajo de ejemplo

```text
Start minimal → compile → review assumptions → add constraints → recompile → ...
```

**Paso 1: empieza con lo básico**

```yaml
constraints:
  cloud: aws
  language: javascript
  platform: api
nfr:
  availability:
    target: 0.999
```

Ejecuta el compilador. La sección `assumptions` de la salida muestra todos los defaults aplicados: son decisiones que el compilador tomó por ti. Revísalas para entender qué asumió el compilador.

**Paso 2: añade restricciones NFR a medida que las descubras**

```yaml
nfr:
  availability:
    target: 0.999
  latency:
    p95Milliseconds: 50
    p99Milliseconds: 100
```

Cada nueva restricción estrecha la selección de patrones. Algunos patrones serán rechazados y antes no lo eran. El compilador te dice por qué a través del archivo `rejected-patterns.yaml` (en modo `-v`).

En algunos casos, el propio spec puede ser rechazado: si un objetivo NFR duro (por ejemplo, latencia muy ajustada o alta disponibilidad) no puede satisfacerse con ningún patrón disponible, el compilador sale con código `1` y explica el fallo. Eso es una señal útil: significa que tus restricciones son contradictorias o que necesitas un patrón que aún no existe en el registro.

**Paso 3: activa capacidades de forma explícita**

```yaml
constraints:
  features:
    caching: true
```

Los feature flags viven en `constraints.features`, no en `nfr`. Representan capacidades opt-in, no objetivos de rendimiento.

Cuando un patrón coincide, el compilador puede emitir advisories `warn_nfr`: advertencias de que un patrón seleccionado está infrautilizado según tus valores NFR actuales. Por ejemplo, habilitar caching sin un NFR de throughput puede producir:

```text
⚠️  cache-aside: peak read QPS is 5 req/s (<10 req/s). Caching overhead
    (infrastructure, invalidation, serialization) may outweigh benefit at this scale.
```

Esto indica que el patrón fue seleccionado, pero probablemente no compense en esta escala. Es una invitación a proporcionar más datos NFR o a reconsiderar el feature flag.

**Paso 4: añade datos de throughput para resolver los advisories `warn_nfr`**

Si ves un advisory `warn_nfr` después de activar caching (u otros patrones sensibles al throughput), añade tu pico real de QPS:

```yaml
nfr:
  throughput:
    peak_query_per_second_read: 20
    peak_query_per_second_write: 10
```

Con cifras reales de throughput, el compilador puede decidir de forma definitiva: o desaparece el advisory (caching está justificado) o persiste con una explicación más específica. Cualquiera de los dos resultados es más útil que seleccionar un patrón a ciegas.

**Paso 5: especifica explícitamente `cost` y `operating_model` cuando te importen**

```yaml
cost:
  intent:
    priority: optimize-tco
  ceilings:
    monthly_operational_usd: 500
    one_time_setup_usd: 1000
operating_model:
  ops_team_size: 2
  single_resource_monthly_ops_usd: 10000
  on_call: true
  deploy_freq: daily
  amortization_months: 24
```

El compilador ejecuta un análisis completo de factibilidad de costes sobre tres cubos:

- **Pattern OpEx** — suma del coste mensual estimado de infraestructura de cada patrón seleccionado
- **Ops team cost** — `ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier`
- **CapEx (one-time)** — costes de adopción y puesta en marcha de los patrones seleccionados

Estos valores se comprueban contra tus ceilings declarados. Si se superan, el compilador emite advertencias `[high]` indicando la intención de coste activa. Sin un `operating_model`, el compilador asume `ops_team_size: 0`, lo que puede subestimar significativamente el TCO real.

### Por qué esto funciona

`compiled-spec.yaml` es un spec de entrada válido. Si vuelves a ejecutarlo por el compilador, obtendrás la misma salida: la sección `assumptions` se conserva y solo se rellenan los campos realmente ausentes. Esto significa:

- puedes editar un spec compilado y recompilarlo; tus cambios se respetan
- la salida siempre es un registro completo y autocontenido de todas las decisiones
- en cualquier etapa, la salida ya tiene valor; no necesitas un spec “completo” para obtener utilidad

### Qué cambia en cada etapa

La siguiente tabla sigue la misma progresión que el vídeo de demostración [[Architecture Compiler](https://www.youtube.com/watch?v=QPqNyozTArY)]:

| Paso | Qué añades | Qué hace el compilador |
|------|------------|------------------------|
| 1 | Spec mínimo (`cloud`, `language`, `platform`, `availability`) | Selecciona patrones base y rellena los campos faltantes en `assumptions` |
| 2 | Flag `-v` | Anota cada campo del spec con los patrones que lo activaron y escribe `rejected-patterns.yaml` |
| 3 | NFR de latencia (`p95`, `p99`) | Rechaza patrones que no pueden cumplir el objetivo; el spec completo puede rechazarse si ninguno encaja |
| 4 | `features.caching: true` | Activa cache-aside y patrones relacionados; emite `warn_nfr` si el QPS es demasiado bajo |
| 5 | NFR de throughput (`peak_query_per_second_read/write`) | Reevalúa advisories y patrones con datos reales de carga |
| 6 | Intención de coste (`optimize-tco`, `minimize-opex`, `minimize-capex`) | Activa la comprobación de factibilidad de costes y emite warnings `[high]` si se superan los ceilings |

---

## Estructura del proyecto

```text
.
├── README.md                   Documento principal en inglés
├── AGENTS.md                   Guía raíz canónica para workflows de agents
├── README-AGENTS.md            Guía del repo para AI agents
├── CLAUDE.md                   Puntero específico para Claude hacia AGENTS.md y los skills
├── LICENSE                     Licencia MIT
├── CHANGELOG.md                Registro de cambios del repo
├── CODE_OF_CONDUCT.md          Código de conducta
├── CONTRIBUTING.md             Guía de contribución
├── pyproject.toml              Metadatos del proyecto, dependencias y configuración de herramientas
├── .codex/                     Helpers nativos de instalación e integración para Codex
├── .github/                    Configuración de GitHub (workflows CI/CD)
├── adapters/                   Adaptadores de comandos entre agents
├── patterns/                   Archivos JSON de patrones curados: la base de conocimiento
├── schemas/                    Contratos de spec / patrón / capability
├── config/                     Configuración de valores por defecto
├── tools/                      Compilador y herramientas de auditoría
├── tests/                      Suite de pruebas pytest
├── test-specs/                 Specs integrados y reutilizables
├── docs/                       Documentación complementaria
├── reports/                    Salidas de auditoría (generadas localmente)
└── skills/                     Agent skills e instrucciones de instalación
```

Para un desglose más fino de subdirectorios y archivos, consulta la sección **Project Structure** de la versión en inglés de `README.md`.

---

## Ejecutar pruebas

```bash
# Ejecutar todas las pruebas
python -m pytest tests/ -q

# Salida verbose
python -m pytest tests/ -v

# Un archivo de prueba específico
python -m pytest tests/test_compiler_integration.py -v
```

Las pruebas cubren el pipeline del compilador de extremo a extremo, validación del schema de patrones, simetría de conflictos, lógica NFR/constraints, factibilidad de costes y más. Consulta `docs/test-inventory.md` para el inventario completo.

---

## Instalar los skills

Este repo también publica tres agent skills reutilizables:

- `using-arch-compiler`
- `compiling-architecture`
- `implementing-architecture`

Los usuarios de Codex pueden instalarlos directamente desde la ruta GitHub del repo:

```bash
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/using-arch-compiler
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/compiling-architecture
scripts/install-skill-from-github.py --repo inetgas/arch-compiler --path skills/implementing-architecture
```

Los usuarios de Claude Code pueden usar los adaptadores incluidos en `adapters/claude-code/commands/` copiándolos en `.claude/commands/`, incluido el comando router.

Consulta [skills/README.md](../../skills/README.md) para detalles de instalación y notas de uso entre distintos agents.

---

## Herramientas de auditoría

```bash
# Auditar calidad del metadata de patrones (descripciones, costes, reglas NFR)
python tools/audit_patterns.py

# Auditar rutas NFR/constraint (detectar referencias JSON pointer obsoletas)
python tools/audit_nfr_logic.py

# Auditar simetría de conflictos (si A entra en conflicto con B, B también debe declarar A)
python tools/audit_asymmetric_conflicts.py
```

Consulta [docs/tools.md](../tools.md) para la documentación completa de cada herramienta.

---

## Añadir o editar patrones

1. Actualiza `schemas/pattern-schema.yaml` si hace falta un campo nuevo
2. Actualiza `schemas/canonical-schema.yaml` si hace falta un nuevo campo del spec
3. Añade o edita archivos de patrón en `patterns/`
4. Ejecuta `python tools/audit_patterns.py` para comprobar calidad
5. Ejecuta `python -m pytest tests/ -q` para verificar que nada se rompe

Reglas clave:

- Los IDs de patrón deben coincidir con el nombre del archivo (por ejemplo, `cache-aside.json` → `id: "cache-aside"`)
- Las reglas `supports_constraints` y `supports_nfr` usan lógica AND: todas deben coincidir para que el patrón sea seleccionado
- Las declaraciones de conflicto deben ser **bidireccionales**: si A entra en conflicto con B, B también debe declarar A
- Los patrones hermanos de variantes (por ejemplo, `arch-serverless--aws`, `arch-serverless--azure`) deben entrar en conflicto entre sí
- Nunca uses coincidencia de strings de pattern ID dentro del compilador; toda la lógica debe codificarse en el metadata del patrón

---

## Siguientes pasos

Si quieres profundizar:

- instalación y uso de skills: revisa [skills/README.md](../../skills/README.md)
- documentación detallada de schemas: consulta [schemas/README.md](../../schemas/README.md) (inglés)
- detalles de las herramientas del compilador: consulta [docs/tools.md](../tools.md) (inglés)
- flujos de trabajo para agents: consulta [README-AGENTS.md](../../README-AGENTS.md) (inglés)

Si esta traducción todavía no cubre algún documento más específico que necesites, consulta primero la versión en inglés.
