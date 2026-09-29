# Thread State v0.2 — taxonomia consolidada e plano de melhoria

Status: proposta · 2026-09-28
Base: análise do Claude (código do `openai/codex` no commit `e07e58c`, ledger local da instalação antiga) + duas análises do ChatGPT sobre taxonomia e telemetria.

---

## 1. Princípios

1. **Saliência proporcional à intervenção necessária.** Cor e emoji ficam para exceções; o normal é discreto.
2. **O primeiro símbolo responde "preciso fazer algo?"**; os seguintes respondem "que tipo de trabalho é este?".
3. **O evento é a fonte de verdade do presente; a leitura persistida só vale para o que já terminou.**
4. **O título é uma renderização, não o banco de dados.** O estado vive num store local; o título é derivado e sempre reconstruível.
5. **Toda escrita é reversível** e o texto editorial do usuário nunca é perdido.
6. **Cada dimensão é desligável** por configuração, sem alterar código nem `hooks.json` (que exigiria nova confiança).
7. **Zero inferência e zero polling no motor.** Qualquer coisa temporal (animação) é plugin experimental, fora do default.

---

## 2. Comparação e decisão consolidada

| Tema | Claude | ChatGPT | Decisão | Motivo |
|---|---|---|---|---|
| Causa do ⏸️ em threads rodando | O hook abre outro App Server; para ele a thread está `notLoaded`, e `normalize_thread_turns_status` converte `InProgress` em `Interrupted` | "Corrigir na fonte" usando `active` e as flags `waitingOnApproval`/`waitingOnUserInput` | **Evento autoritativo + store local.** Leitura nativa de `active` só num adaptador "live" futuro | `active` e suas flags só existem no processo dono da thread (`resolve_thread_status` usa o turno *vivo daquele processo*). Nesta máquina não existe o socket do daemon compartilhado (`~/.codex/app-server-control/`), então o hook não tem como consultar o processo do desktop |
| Executando | ⏳ | ▶️ ou `▶` | **`▶` em texto** (U+25B6 + U+FE0E) | Semântica direta. Como texto não vira o quadrado azul, que se confundiria com ⏸️ |
| Concluída | Sem prefixo | `✓` | **`✓` por padrão**; vazio como opção | `✓` diferencia "processada e ok" de "nunca processada" |
| Desconhecido | Não escrever | `?` | **Nunca introduzir; `?` só para substituir um estado obsoleto** (ex.: `▶` órfão) | Evita ruído sem deixar um estado falso |
| Pausada | ⏸️ | ⏸️ | ⏸️ (emoji) / `‖` (texto) | Pausa é iniciada pelo usuário: atenção baixa |
| **Aguardando você** | — | Via flags do App Server | **✋ via hook `PermissionRequest` e ferramenta `request_user_input`** | É o estado de maior valor e faltava nas duas propostas. É detectável por evento, sem depender do processo do desktop |
| Goal ativo e parado | Fundir no badge de goal | 🟡 | **🟡** | Estado separado de modificador fica mais claro |
| Orçamento do goal esgotado | 🪫 | ⏳ | **⏳** (🪫 como override) | ⏳ fica livre, porque executando passa a ser `▶` |
| Goal | 🏁 ativo / 🏆 concluído | 🏆 como modificador; estado vai no slot principal | **🏆 como modificador** | 🏁 significa "fim de corrida" e colide com goal em andamento. O estado do goal aparece no slot principal (🟡, ⏳, `✓`) |
| Recorrente | Manter 🔁; hoje não há detecção | Modificador; distinguir "último ciclo" de "thread" | **Modificador 🔁**, desligado até existir sinal estruturado | Pista a verificar: `~/.codex/automations/`. `✓ 🔁` significa "último ciclo ok" |
| Artefatos | 📦 para qualquer arquivo novo | 📦 só para entregáveis | **📦 por allowlist de extensões + `ImageGeneration`; fixo na thread** | Arquivo alterado não é artefato |
| Contexto | Glifo via `token_count` do rollout | Glifo só acima de limiar, via `thread/tokenUsage/updated` | **Glifo `◕`/`●`; fonte = rollout; mesma fórmula do Codex** | A notificação só chega ao processo dono da thread. O rollout traz `model_context_window` do próprio modelo, então nada fica hardcoded |
| Execução longa | Avaliar a cada evento de ferramenta | `⏱` relativo, com limiar | **`⏱` experimental, avaliado nos eventos** | Sem timer, `⏱` não aparece se o agente travar num único comando longo. Limitação documentada |
| Estilo visual | Modo texto opcional | `symbols` como padrão, exceções em emoji | **`hybrid` como padrão** | Calmos em texto, alarmes em emoji: a hierarquia sai de graça |
| Animação | Um quadro por evento de ferramenta | Modo experimental menos agressivo | **`motion: off`**; `events` experimental; nunca timer | Cada renomeação faz append em `session_index.jsonl` |
| Tokens no título | Não; ir para um relatório | Não; "radar vs painel de instrumentos" | **`thread-state status`** | Número absoluto não leva a ação no título |
| Quantidade de símbolos | Limite de 60 caracteres | ≤ 3 normalmente | **`max_badges = 3`, com ordem de descarte** | Cada badge a mais reduz quantas threads cabem no limite |
| Ligar e desligar | Flag no config, sem nova confiança | Toggle nativo do plugin + config própria | **Os dois** | Níveis diferentes: instalação vs exibição |
| Ordem no título | — | Pressão de contexto antes do estado | **Estado sempre primeiro** | A proposta do ChatGPT contradizia a própria regra "o primeiro símbolo diz o que está acontecendo" |

---

## 3. Taxonomia v0.2

Gramática do título:

```text
STATE [MODIFICADORES] [TELEMETRIA] [tag] título
```

### 3.1 State — exatamente 1

| Estado | Atenção | emoji | hybrid (padrão) | symbols | Evidência |
|---|---|---|---|---|---|
| `usage_limited` | ação | 🚩 | 🚩 | ⚑ | Turno `failed` persistido com marcador estruturado de cota, ou goal `usage_limited` |
| `failed` / `blocked` | ação | 🔴 | 🔴 | ✗ | Turno `failed` persistido, ou goal `blocked` |
| `waiting_on_user` | ação | ✋ | ✋ | ! | Hook `PermissionRequest`, ou `PreToolUse` com `request_user_input` |
| `running` | nenhuma | ▶️ | ▶ | ▶ | Hook `UserPromptSubmit` / `PostToolUse` |
| `interrupted` / `paused` | observar | ⏸️ | ‖ | ‖ | Hook `Interrupt`, ou goal `paused` |
| `budget_limited` | observar | ⏳ | ⏳ | ⌛ | Goal `budget_limited` |
| `pending` | observar | 🟡 | 🟡 | … | Goal `active` sem turno em execução |
| `completed` | nenhuma | ✅ | ✓ | ✓ | Turno `completed` persistido após `Stop` |
| `unknown` | nenhuma | ⚪ | ? | ? | Só ao substituir um estado obsoleto |

### 3.2 Modificadores — 0 ou mais, estáveis

| Modificador | emoji / hybrid | symbols | Evidência | Padrão |
|---|---|---|---|---|
| `goal` | 🏆 | ★ | `thread/goal/get` retorna um goal | ligado |
| `artifacts` | 📦 | ◆ | Arquivo criado com extensão da allowlist, ou item `ImageGeneration` | ligado |
| `recurring` | 🔁 | ↻ | A definir (verificar `~/.codex/automations/`) | desligado |

### 3.3 Telemetria — transitória, só acima de limiar

| Sinal | Glifo | Regra | Padrão |
|---|---|---|---|
| Pressão de contexto | `◕` ≥ 75% · `●` ≥ 90% | Último `token_count` do rollout com a fórmula `percent_of_context_window_remaining` (base de 12 mil tokens) | ligado |
| Execução longa | `⏱` | `agora − início do turno > N min`, avaliado em eventos | desligado |

### 3.4 Orçamento de caracteres

- O estado nunca é descartado.
- Com mais de `max_badges`, descartar nesta ordem: `⏱` → `recurring` → `artifacts` → contexto → `goal`.
- Se ainda passar de `maxTitleChars`, pular a escrita (sem truncar), como hoje.

Exemplos (hybrid):

```text
▶ 🏆 [jevify] Implement auth migration
✋ 🏆 [jevify] Implement auth migration
🚩 🏆 📦 [cue] Generate investor report
✓ 📦 [cue] Generate investor report
🟡 🏆 ◕ [ppu] Implementar índice interno do DOU
```

---

## 4. Motor de estado (reducer)

O reducer é uma função pura:

```text
(visão anterior, evento, evidências) → nova visão
```

A visão fica no store local. Por isso a leitura feita por outro processo deixa de ser a única fonte de verdade.

| Evento | Efeito |
|---|---|
| `SessionStart` | Reconciliação de threads órfãs |
| `UserPromptSubmit` | `running`, **sem ler o turno**; guarda `turn_id` e o horário de início |
| `PermissionRequest` | `waiting_on_user` |
| `PreToolUse` (`request_user_input`) | `waiting_on_user` |
| `PostToolUse` | `running` (sai de `waiting`); atualiza artefatos e telemetria; avança o quadro de animação, se ligada |
| `Stop` | Lê o persistido com até 3 tentativas de 200 ms. `completed` vira `completed`, ou o estado derivado do goal. Se continuar ambíguo, mantém `running` e marca para reconciliação |
| `Interrupt` | `interrupted` |
| Qualquer evento | Reconciliação tardia (abaixo) |

**Confiabilidade de uma leitura feita por outro processo:**

- `failed` e `completed`: confiáveis (estado terminal gravado).
- `interrupted`: ambíguo. Só é aceito se houver um evento `Interrupt` registrado para aquele `turn_id`.
- `inProgress`: nunca aparece fora do processo dono. Não usar.

**Reconciliação tardia** — cobre o fato de o Codex não emitir `Stop` quando o turno falha:

- Threads em `running`/`waiting` no store, sem evento há mais de `reconcile_after_seconds`, são relidas no próximo evento de qualquer thread.
- `failed` vira 🚩/🔴 e `completed` vira `✓`.
- Se continuar ambíguo, mantém o estado até `stale_after_minutes` e depois troca para `?`.

---

## 5. Estado salvo e rollback

### 5.1 Layout em `$CODEX_HOME/thread-state/`

```text
config.json
profiles/<nome>.json
threads/<thread-id>.json   # visão + títulos
journal.jsonl              # toda escrita (intenção/aplicada)
snapshots/<ts>-<rótulo>.json
events.jsonl               # eventos recebidos e resultado
```

`threads/<id>.json` guarda:

- `originalTitle`: o título antes de o Thread State tocá-lo.
- `baseTitle`: o texto editorial atual, sem prefixos.
- `view`: estado, modificadores e telemetria.
- `lastRendered`: o último título escrito.
- `lastEvent`: nome, `turnId` e horário.
- `configHash`: a configuração usada na renderização.

### 5.2 Regras

1. **Adoção de edição do usuário.** Se o título atual, sem prefixos reconhecidos, difere de `baseTitle` e de `lastRendered`, o usuário renomeou. O novo texto vira `baseTitle` e o journal registra `adopt`. O texto do usuário nunca é sobrescrito.
2. **Journal antes e depois.** Cada escrita registra `intent` e depois `applied` com `actualTitle` lido de volta. Toda escrita pertence a um `batch`: evento, comando ou rollback.
3. **Rollback granular:**

   ```text
   thread-state rollback --op ID
   thread-state rollback --batch ID
   thread-state rollback --since 2026-09-28T18:00
   thread-state rollback --thread UUID
   thread-state rollback --to-snapshot NOME
   thread-state rollback --original        # volta ao título pré-Thread State
   ```

4. **Conflito.** Restaura só se o título atual for igual a `lastRendered`. Caso contrário, lista o conflito. `--force` é explícito.
5. **Rollback é um batch journaled** — portanto também pode ser desfeito.
6. **`clean`** renderiza só `baseTitle` (remove todos os prefixos) e é reversível.
7. **Snapshot automático** antes de `install`, `migrate`, `render --all` e troca de perfil.
8. **Quadros de animação** não entram no journal, um a um. Continuam recuperáveis, porque `baseTitle` é conhecido.

### 5.3 Migração do protótipo

`thread-state migrate --from-legacy`:

1. Importa `~/.codex/thread-status/changes.jsonl`.
2. Reconstrói `originalTitle` das 28 threads do lote inicial.
3. Tira um snapshot.
4. Só então desativa os hooks antigos.

---

## 6. Configuração e experimentação de UX

```json
{
  "enabled": true,
  "style": "hybrid",
  "max_badges": 3,
  "maxTitleChars": 60,
  "states": {
    "completed_marker": "✓",
    "unknown_marker": "?",
    "waiting_on_user": true
  },
  "modifiers": {
    "goal": true,
    "artifacts": {
      "enabled": true,
      "extensions": ["pdf", "pptx", "docx", "xlsx", "zip", "png", "jpg", "svg", "html", "csv", "mp4"]
    },
    "recurring": false
  },
  "telemetry": {
    "context": { "enabled": true, "warn": 0.75, "critical": 0.90 },
    "long_running": { "enabled": false, "minutes": 15 }
  },
  "motion": "off",
  "icons": {},
  "reconcile_after_seconds": 120,
  "stale_after_minutes": 60
}
```

- `icons` sobrescreve qualquer símbolo sem mexer no código (ex.: `{"recurring": "♻️", "running": "⏳"}`).
- Perfis prontos:

| Perfil | Conteúdo |
|---|---|
| `minimal` | Só o estado |
| `default` | O config acima |
| `full` | Tudo ligado, exceto animação |
| `lab` | `full` + `long_running` + `motion: events` |

- **Loop de teste de UX:**

  ```text
  thread-state preview                    # galeria de todos os estados; nada é escrito
  thread-state snapshot create antes-lab
  thread-state profile use lab            # snapshot automático
  thread-state render --all               # journaled
  # ...observar a barra lateral...
  thread-state rollback --to-snapshot antes-lab
  ```

- **Liga e desliga:**
  - `thread-state off` / `on` alternam `enabled`. O `hooks.json` não muda, então não há nova confiança.
  - `off --clean` também remove os prefixos de forma reversível.
  - Um `.cmd` na área de trabalho dá o clique único.
  - Para desligar tudo, o toggle nativo de hooks/plugin do Codex.

---

## 7. Arquitetura modular

```text
thread_state/
  events.py        # payload do hook → Event normalizado
  model.py         # ThreadView, State, Modifier, Telemetry, Attention (dataclasses)
  reducer.py       # (view, event, evidence) → view      [puro]
  sources/         # coletores de evidência; cada um desligável
    app_server.py  # turno persistido e goal (regras de confiabilidade)
    rollout.py     # token_count → contexto; ContextCompaction
    artifacts.py   # allowlist + ImageGeneration
    automations.py # recorrência (experimental)
  render/
    themes.py      # emoji | hybrid | symbols + overrides
    compose.py     # view → prefixo; max_badges; limite de caracteres  [puro]
  store.py         # threads/*.json, snapshots, locks
  journal.py       # intent/applied, batches, consulta
  writer.py        # ÚNICO módulo que chama thread/name/set; dry-run; readback
  rollback.py      # planeja e aplica restaurações, detecta conflitos
  motion.py        # experimental; desligado por padrão
  cli.py           # install, on/off, status, preview, render, snapshot,
                   # rollback, clean, migrate, profile, doctor, capture
```

Regras de fronteira:

- `reducer` e `render` são puros e não fazem I/O.
- Só `writer` escreve títulos.
- `sources` não decidem estado: fornecem evidência.
- O hook sai em menos de 50 ms quando `enabled=false`, antes de abrir o App Server.
- **Hooks:** todos os eventos são registrados uma vez (uma única aprovação). A ativação de cada recurso acontece no config.
  - Trade-off: `PostToolUse` roda Python a cada ferramenta.
  - Mitigação: sair cedo se nenhum recurso que dependa dele estiver ligado, e medir.

---

## 8. Plano por fases

| Fase | Entrega | Critério de aceite |
|---|---|---|
| **0. Higiene** | Mover dados privados e o protótipo para `work/`. Trazer `rollback_plan.py` para `rollback.py`. Adicionar `docs/upstream-proposal.md` e `agents/openai.yaml` | Repositório sem dados pessoais; `git status` limpo |
| **1. Fundação** | `model`, `store`, `journal`, `writer`, `snapshot`, `rollback`, `clean`, `capture` (grava payloads reais de hooks, sanitizados, como fixtures) | Rollback de op, batch, snapshot e original testados com fake RPC; nenhuma mudança visível ainda |
| **2. Motor correto** | Reducer orientado a eventos, confiabilidade de leitura, retry do `Stop`, reconciliação tardia, `waiting_on_user`, `migrate --from-legacy` | Replay de fixtures reais: thread rodando nunca vira ⏸️; falha de cota aparece em até 1 evento posterior; legado desativado com snapshot |
| **3. Renderer configurável** | Temas, `icons`, `max_badges`, perfis, `preview`, `render --all`, `on/off` | Troca de perfil e rollback em ida e volta sem perda de título |
| **4. Sinais** | Pressão de contexto (rollout), 📦 artefatos, estados derivados do goal | Percentual confere com o que o Codex mostra (±1 p.p.); 📦 não dispara em edição de código |
| **5. Experimental** | `recurring`, `⏱`, `motion: events`, adaptador "live" via daemon, issue upstream (evento terminal em falha; status estruturado) | Cada item atrás de flag; métricas de custo por evento registradas |

---

## 9. Riscos e questões abertas

- **O Codex não emite `Stop` quando o turno falha.** A reconciliação tardia atenua, mas não dá tempo real. Correção de verdade: issue upstream.
- **Latência da barra lateral** para renomeações feitas por outro processo: desconhecida. Afeta sobretudo a animação.
- **Contagem do limite de 60** em Unicode (emoji com seletor de variação) pode divergir. A leitura de volta detecta a diferença.
- **`thread/turns/list` é experimental.**
- **Custo de `PostToolUse`** em sessões com muitas ferramentas: medir antes de ligar recursos que dependam dele.
- **Detecção de recorrência** depende de verificar `~/.codex/automations/`.
- **Contexto logo após uma compactação** cai de forma abrupta. O indicador deve refletir isso sem marcação permanente.
