# Migração local v0.1 → v0.2

Execução realizada em 2026-09-28, no Windows, após preservar a arquitetura v0.1
em [`architecture-v0.1.md`](architecture-v0.1.md).

## Sequência executada

1. Testes da v0.2: 21 aprovados.
2. Testes preservados da v0.1: 21 aprovados.
3. `thread-state migrate --from-legacy`:
   - snapshot anterior à migração criado;
   - 8 registros de thread reconstruídos a partir do ledger legado;
   - hooks `thread-status` removidos somente após importação;
   - ledger e logs antigos mantidos no local original.
4. `thread-state install`:
   - snapshot automático anterior à instalação criado;
   - backup de `hooks.json` criado;
   - sete handlers v0.2 instalados.
5. A definição absoluta foi revisada no navegador nativo de hooks do Codex.
   Todos os sete hashes foram confiados sem usar bypass.
6. A skill v0.2 foi copiada para `$CODEX_HOME/skills/thread-state/`.
7. A skill v0.1 foi movida de `skills/thread-status/` para o arquivo recuperável
   `$CODEX_HOME/skills-disabled/thread-status-v0.1/`.
8. Um evento `PostToolUse` sintético e explicitamente identificado validou:
   reducer, App Server, escrita, journal e readback.

## Handlers ativos

- `SessionStart`
- `UserPromptSubmit`
- `PermissionRequest`
- `PreToolUse`
- `PostToolUse`
- `Stop`
- `Interrupt`

Todos apontam para o entry point absoluto deste checkout e aparecem como ativos
na revisão do Codex. Hooks não gerenciados são confiados pelo hash exato; qualquer
alteração futura no comando exigirá nova revisão.

## Estado de continuação

- Configuração v0.2: habilitada, perfil `default`.
- Threads importadas: 8.
- Daemon v0.1: nenhum processo ou tarefa agendada ativa foi observado.
- Runtime privado permanece fora do Git em `$CODEX_HOME/thread-state/` e
  `$CODEX_HOME/thread-status/`.
- A sessão do desktop que realizou a instalação já tinha carregado a configuração
  anterior. É necessário recarregar/reabrir o Codex para observar automaticamente
  os novos hooks nessa sessão; a configuração e a confiança já estão persistidas.

O teste sintético prova o caminho técnico local. Ele não substitui a observação
de um `UserPromptSubmit` e `Stop` reais após o reload.
