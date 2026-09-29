# Arquitetura instalada antes da v0.2

Este documento registra a primeira implementação local observada em 2026-09-28,
antes da ativação do Thread State v0.2. É evidência histórica, não a arquitetura
recomendada nem uma cópia do estado privado da máquina.

## Topologia observada

```text
$CODEX_HOME/
  hooks.json
  skills/thread-status/
    SKILL.md
    agents/openai.yaml
    references/taxonomy.md
    scripts/
      hook.py
      daemon.py
      thread_status.py
      make_ledger.py
      rollback_plan.py
      install_daemon.ps1
      uninstall_daemon.ps1
      status_daemon.ps1
      test_thread_status.py
      test_daemon.py
  thread-status/
    config.json
    changes.jsonl
    daemon.log
    daemon.pid
    daemon.lock
```

Os fontes preservados estão em [`legacy/v0.1/skill`](../legacy/v0.1/skill).
O protótipo monolítico posterior do repositório permanece em
[`work/thread_state_v01.py`](../work/thread_state_v01.py), rastreado pelo Git
apesar de `work/` ser ignorado para novos arquivos.

## Fluxo

```text
UserPromptSubmit | Stop | Interrupt
  -> $CODEX_HOME/skills/thread-status/scripts/hook.py
  -> daemon.py --once --thread-id <session_id>
  -> App Server separado
  -> thread/read + thread/turns/list + thread/goal/get
  -> classificação determinística
  -> thread/name/set
  -> $CODEX_HOME/thread-status/changes.jsonl
```

Os três hooks eram assíncronos. Em Windows, `commandWindows` usava `pythonw.exe`.
O hook consultava um App Server novo; por isso uma thread viva podia ser lida como
`interrupted` e receber `⏸️`. A classificação também continha revisão semântica
pré-calculada, incluindo `explicit_completion_phrase`, que a v0.2 remove.

O daemon de polling existia como fallback, mas o PID encontrado não correspondia
a um processo vivo durante esta captura. A existência dos arquivos de PID/lock
não prova que o daemon estava ativo.

## Hooks instalados

Antes da migração, `$CODEX_HOME/hooks.json` continha apenas:

- `UserPromptSubmit` → `skills/thread-status/scripts/hook.py`;
- `Stop` → o mesmo hook;
- `Interrupt` → o mesmo hook.

As definições tinham hashes de confiança persistidos no `config.toml`. Esses
hashes não são reutilizáveis pela v0.2: confiança é vinculada à definição exata.

## Dados deliberadamente não copiados

- `thread-status/config.json`: caminhos locais, executável e mapeamentos privados;
- `changes.jsonl`: IDs e títulos reais de conversas;
- `daemon.log`, `daemon.pid` e `daemon.lock`;
- `__pycache__` e bytecode;
- backups de hooks, snapshots e capturas não sanitizadas.

O [`.gitignore`](../.gitignore) impede que esses nomes de runtime sejam adicionados
acidentalmente. A migração v0.2 lê o ledger no local original e preserva-o fora do
repositório.

## Limites da preservação

Esta cópia registra os bytes-fonte presentes na instalação local. Ela não afirma
que todos os caminhos do daemon foram exercitados, nem que o comportamento do
desktop foi validado em outras versões ou sistemas operacionais.
