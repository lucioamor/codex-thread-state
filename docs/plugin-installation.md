# Instalação do plugin Thread State

Thread State 1.2.0 inclui `plugin.json`, `hooks/hooks.json`, o runtime
`thread_state/`, `thread_state.py` e `skills/thread-state/`. Os sete eventos
continuam chamando o mesmo runtime; não há chamadas a modelos nem dependências pip.

## Requisitos

- Python 3.11+ disponível como `python` no PATH do processo do Codex.
- Codex com suporte a plugins e hooks, e executável nativo com App Server.
- Ambiente local com acesso aos dados do Codex. Instalar na web não instala os scripts na máquina.

No Windows, confirme que `python --version` funciona em um terminal novo e
reinicie o Codex após alterar o PATH. O plugin usa `${PLUGIN_ROOT}`; não exige
o caminho do computador do autor. No macOS/Linux, o comando `python` também
precisa apontar para Python 3.11+.

## Instalação a partir do GitHub

Revise o código antes de instalar. Em versões da CLI que oferecem os comandos
abaixo (`codex plugin --help`), registre o repositório e instale:

```sh
codex plugin marketplace add lucioamor/codex-thread-state --ref main
codex plugin add thread-state@codex-thread-state
```

Para reprodução, prefira uma tag ou commit contendo
o plugin em vez de `main`.

Para instalar localmente, gere o ZIP com `python scripts/build_plugin.py`,
extraia-o fora do checkout e execute na pasta `thread-state/` extraída:

```sh
codex plugin marketplace add .
codex plugin add thread-state@codex-thread-state
```

Também é possível selecionar a fonte cadastrada no diretório de plugins do
Desktop e instalar por lá. Reinicie/recarregue o Codex e revise os sete hooks
no gerenciador de hooks do host (`/hooks` na CLI). Confie nas definições atuais;
a instalação do plugin não faz isso automaticamente.

A instalação local pela CLI copia a pasta da fonte, inclusive arquivos ignorados
pelo Git. Use o ZIP sanitizado como fonte local; não cadastre um checkout que
contenha backups privados. O ZIP inclui seu próprio catálogo de marketplace.

Não execute `python thread_state.py install` para uma instalação por plugin.

## Migração de hooks manuais

1. Preserve uma cópia exata de `$CODEX_HOME/hooks.json` fora do Git público.
2. Instale o plugin, mantendo seus hooks desabilitados ou sem confiança durante a preparação.
3. No checkout antigo, execute `python thread_state.py uninstall`. Esse comando
   cria snapshot/backup e remove handlers com `statusMessage: Thread State`,
   preservando outros handlers. Ele não desinstala o plugin nem apaga seus dados.
4. Revise e habilite/confie nos hooks do plugin. Não deixe as duas fontes ativas:
   Codex soma os hooks de todas as fontes.
5. Em um chat novo, verifique início do turno, uso de ferramentas, término,
   interrupção e solicitação de entrada/permissão quando ocorrerem naturalmente.
   Confirme os títulos e os eventos locais; testes sintéticos não provam entrega no Desktop.

O runtime mantém `$CODEX_HOME/thread-state/` como diretório de dados para
preservar preferências, registros e rollback entre instalações. Não copia esses
dados para o pacote e não os migra para `PLUGIN_DATA`. A desinstalação preserva
esses arquivos e os títulos já existentes.

Para voltar ao modo manual, desabilite/remova o plugin primeiro e execute
`python thread_state.py install` no checkout antigo; revise novamente a confiança.
Para remover apenas o plugin, use a interface ou
`codex plugin remove thread-state@codex-thread-state` conforme a ajuda da CLI instalada.

## Preservação dos hooks anteriores

`docs/history/manual-hooks-2026-10-09.json` preserva os sete registros observados,
incluindo timeouts e execução assíncrona. Somente o comando foi sanitizado para
remover caminhos pessoais. A cópia byte a byte e seu SHA-256 foram salvos em
`work/private/manual-hooks-2026-10-09/`, ignorado pelo Git e excluído do ZIP.
Esse backup local não será incluído em clones públicos.

## Gerar pacote público

```sh
python -m unittest discover -s tests -v
python scripts/build_plugin.py
```

O ZIP em `dist/thread-state-1.2.0.zip` contém uma pasta `thread-state/` com
os arquivos necessários. O gerador usa uma lista explícita: exclui `.git`,
backups privados, logs, dados locais, build anterior e bytecode. Para instalar
um ZIP extraído, cadastre uma fonte local apontando para a pasta do plugin;
não basta deixar a pasta em um checkout para ativar hooks.

## Distribuição e limites

Pode ser disponibilizado publicamente no GitHub sob Apache-2.0, mantendo LICENSE,
NOTICE e autoria. Segundo a documentação consultada em 09/10/2026, plugins com
hooks podem ser instalados manualmente no Desktop, mas não são elegíveis para
o diretório público oficial. Publicação no GitHub não significa aprovação da OpenAI.

O empacotamento não altera a classificação de estados nem elimina a exigência
de Python/App Server. Compatibilidade macOS/Linux e entrega real dos hooks da
instalação por plugin precisam de validação nos respectivos hosts.

Fontes: [empacotamento e instalação](https://developers.openai.com/plugins/build/plugins),
[hooks e confiança](https://learn.chatgpt.com/docs/hooks).
