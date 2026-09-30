# Thread State

**Saiba exatamente em que estado cada conversa do Codex está.**

Thread State v1.0 prefixa títulos com uma projeção determinística e reversível do estado estruturado:

```text
▶ 🏆 [jevify] Implement auth migration
✋ 🏆 [jevify] Implement auth migration
🚩 🏆 📦 [cue] Generate investor report
✓ 📦 [cue] Generate investor report
```

Não é um componente oficial da OpenAI. O runtime usa apenas a biblioteca padrão do Python, não chama modelos, não classifica prosa, não faz polling e não cria serviço em segundo plano. A origem do estado presente são os eventos; leituras de outro App Server só confirmam estados terminais persistidos.

## Instalação e uso

Requisitos: Python 3.11+ e um executável nativo do Codex com App Server.

```sh
python -m unittest discover -s tests -v
python thread_state.py preview
python thread_state.py inspect THREAD_UUID
python thread_state.py install
```

`install` tira snapshot, mescla handlers marcados `Thread State` em `$CODEX_HOME/hooks.json` e preserva handlers alheios. Revise e aprove as definições no caminho de confiança do host; não contorne essa etapa. Uma instalação editável é opcional: `python -m pip install -e .`.

## Taxonomia

O título segue `STATE [MODIFICADORES] [TELEMETRIA] [tag] título`.

| Estado | Hybrid | Evidência |
| --- | --- | --- |
| `usage_limited` | 🚩 | falha estruturada de cota ou goal |
| `failed` / `blocked` | 🔴 | turno falho ou goal bloqueado |
| `waiting_on_user` | ✋ | `PermissionRequest` ou `request_user_input` |
| `running` | ▶ | `UserPromptSubmit` / `PostToolUse` |
| `interrupted` / `paused` | ‖ | `Interrupt` ou goal pausado |
| `budget_limited` | ⏳ | orçamento formal do goal |
| `pending` | 🟡 | goal ativo sem turno rodando |
| `completed` | ✓ | terminal persistido após `Stop` |
| `unknown` | ? | substituição de estado obsoleto |

Modificadores: 🏆 goal, 📦 entregável criado na allowlist e 🔁 recorrência experimental. Telemetria: `◕` a partir de 75%, `●` a partir de 90% de pressão de contexto e `⏱` experimental. O estado nunca é descartado; o padrão limita o total a três badges.

## Configuração

O arquivo é `$CODEX_HOME/thread-state/config.json`. Valores omitidos recebem os defaults abaixo:

```json
{
  "enabled": true,
  "style": "hybrid",
  "max_badges": 3,
  "maxTitleChars": 60,
  "states": {"completed_marker": "✓", "unknown_marker": "?", "waiting_on_user": true},
  "modifiers": {"goal": true, "artifacts": {"enabled": true, "extensions": ["pdf", "pptx", "docx", "xlsx", "zip", "png", "jpg", "svg", "html", "csv", "mp4"]}, "recurring": false},
  "telemetry": {"context": {"enabled": true, "warn": 0.75, "critical": 0.90}, "long_running": {"enabled": false, "minutes": 15}},
  "motion": "off",
  "icons": {},
  "projectRoots": {},
  "projects": {"cwd_basename": true},
  "reconcile_after_seconds": 120,
  "stale_after_minutes": 60
}
```

Temas: `emoji`, `hybrid` e `symbols`. Perfis: `minimal`, `default`, `full` e `lab`; arquivos em `profiles/<nome>.json` podem sobrescrever perfis locais.

A tag `[slug]` é resolvida nesta ordem: tag editorial já existente,
`projectRoots`, slug do remote Git e nome da pasta do checkout. Defina
`projects.cwd_basename` como `false` para não usar o último fallback.

## Comandos

```text
thread-state preview
thread-state status | doctor
thread-state inspect UUID [--apply]
thread-state snapshot create RÓTULO
thread-state profile use minimal|default|full|lab
thread-state render --all
thread-state clean --all
thread-state on
thread-state off [--clean]
thread-state toggle
thread-state rollback --op ID | --batch ID | --since ISO | --thread UUID
thread-state rollback --to-snapshot RÓTULO | --original [--force]
thread-state capture [PAYLOAD.json|-]
thread-state migrate --from-legacy
thread-state install | uninstall
```

Para um clique local, crie um atalho para `scripts/thread-state-toggle.cmd` (ou
copie o atalho, não o arquivo, para a área de trabalho, pois ele resolve o
checkout relativamente à própria localização).

Toda escrita normal e rollback registra `intent` antes da mutação e `applied` depois do readback. Rollback sem `--force` preserva renomeações concorrentes. Uma edição editorial detectada é adotada como novo `baseTitle`.

## Arquitetura e dados

`thread_state/reducer.py` e `thread_state/render/` são puros. `sources/` coleta evidência sem decidir estado. `writer.py` é o único módulo que chama `thread/name/set`. O estado local vive em:

```text
$CODEX_HOME/thread-state/
  config.json
  profiles/*.json
  threads/<uuid>.json
  journal.jsonl
  events.jsonl
  snapshots/*.json
  captures/*.json
```

`Stop` tenta a leitura terminal até três vezes com 200 ms. No próximo evento de qualquer thread, estados `running`/`waiting` antigos são reconciliados; após o limite stale viram `?`. `interrupted` persistido só é confiável quando há um evento `Interrupt` correlacionado.

A arquitetura realmente instalada antes da migração está documentada em
[docs/architecture-v0.1.md](docs/architecture-v0.1.md), com os fontes históricos
sanitariamente separados em `legacy/v0.1/skill/`. Ledgers, logs, configuração
local e IDs reais não fazem parte do repositório.

## Limites de validação

Testes usam RPC falso e diretórios temporários. Uma instalação local adicional
validou migração, confiança e escrita sintética, mas ainda não prova entrega real
após reload, falha de cota, latência visual nem compatibilidade macOS/Linux. O
adaptador live por daemon, recorrência e motion são experimentais. Veja
[VALIDATION.md](VALIDATION.md),
[docs/migration-v0.1-to-v0.2.md](docs/migration-v0.1-to-v0.2.md) e
[docs/upstream-proposal.md](docs/upstream-proposal.md).

## Authorship and maintenance

This project was created by [Lucio Amorim](https://linkedin.com/in/lucioamorim).

When reusing, redistributing, or citing this work, keep the attribution credits and include a link to this repository.

Licença [Creative Commons Atribuição-NãoComercial 4.0 Internacional](https://creativecommons.org/licenses/by-nc/4.0/).
Permite compartilhar e adaptar com atribuição, para fins não comerciais.
Aplica-se à versão 1.0.0 e às versões seguintes; os commits históricos preservam
as licenças sob as quais foram disponibilizados.
