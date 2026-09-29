# Proposta upstream: estado estruturado e eventos terminais confiáveis

## Problema

Clientes externos não conseguem distinguir com segurança uma thread ativa de uma
thread interrompida ao abrir outro processo App Server. Além disso, falhas podem
encerrar um turno sem entregar o evento `Stop` aos hooks.

## Proposta

1. Expor um estado estruturado persistente com `running`, `waiting_on_approval`,
   `waiting_on_user_input`, `completed`, `failed` e `interrupted`.
2. Emitir um evento terminal exatamente uma vez para todo turno, inclusive em
   falhas, cancelamento e encerramento inesperado.
3. Incluir `thread_id`, `turn_id`, estado terminal e erro estruturado no evento.
4. Documentar se o status é vivo, persistido ou uma projeção conservadora.

## Critérios de aceite

- Um cliente em outro processo não converte atividade viva em interrupção.
- Toda falha observável no App Server produz um evento terminal correlacionável.
- Clientes não precisam classificar prosa nem fazer polling.

Esta é uma proposta local. Nenhuma issue ou PR upstream foi publicada.
