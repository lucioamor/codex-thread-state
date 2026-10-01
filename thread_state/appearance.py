"""Appearance preferences shared by the local panel and the title renderer."""
from __future__ import annotations

import hashlib
import json
import unicodedata
import uuid

from .config import load_config, merge
from .model import Modifier, State, ThreadView
from .render.compose import compose, icons
from .render.themes import THEMES, THEME_LABELS, THEME_NOTES
from .store import Store, lock, read_json, write_json

LABELS = {
    "running": "Em andamento", "completed": "Turno concluído", "waiting_on_user": "Aguardando você",
    "interrupted": "Interrompido", "paused": "Pausado", "pending": "Pendente",
    "failed": "Falha", "blocked": "Bloqueado", "usage_limited": "Limite de uso",
    "budget_limited": "Limite de orçamento", "unknown": "Sem confirmação",
    "goal": "Objetivo", "artifacts": "Entregável", "recurring": "Recorrência",
    "context_warn": "Contexto alto", "context_critical": "Contexto crítico", "long_running": "Turno longo",
}

# Curated, offline and searchable. Users can also paste any supported symbol.
PICKER = {
    "Símbolos": [(x, name) for x, name in [("▶︎", "play executar"), ("▷", "play contorno"),
        ("›", "avançar"), ("Ⅱ", "pausa"), ("‖", "pausa dupla"), ("✓", "verificado concluído"),
        ("✔", "check marcado"), ("✗", "falha"), ("×", "fechar falha"), ("⊘", "bloqueado"),
        ("…", "pendente"), ("·", "ponto"), ("○", "círculo vazio"), ("●", "círculo cheio"),
        ("◕", "contexto alto"), ("◷", "relógio tempo"), ("□", "quadrado"), ("■", "quadrado cheio"),
        ("◇", "losango vazio"), ("◆", "losango cheio"), ("★", "estrela"), ("☆", "estrela vazia"),
        ("⚑", "bandeira"), ("↻", "recorrência"), ("↗", "seta subir"), ("→", "seta direita"),
        ("↩", "retomar"), ("◴", "tempo")]],
    "Emojis": [(x, name) for x, name in [("🚀", "foguete executar"), ("▶️", "play"),
        ("✅", "check verde concluído"), ("🎉", "festa concluído"), ("🏁", "chegada bandeira"),
        ("✋", "mão aguardando"), ("👋", "olá mão"), ("🛑", "pare vermelho"), ("⏸️", "pausa"),
        ("💤", "sono pausado"), ("🌱", "semente pendente verde"), ("🔎", "buscar dúvida"),
        ("❓", "dúvida vermelho"), ("💥", "explosão falha"), ("🧱", "parede bloqueado"),
        ("🚧", "barreira limite amarelo"), ("🚩", "bandeira vermelho"), ("⏳", "tempo ampulheta"),
        ("🏆", "troféu objetivo"), ("🎯", "alvo objetivo"), ("📦", "caixa entregável"),
        ("🎁", "presente entregável"), ("🔁", "recorrente"), ("🔄", "atualizar"),
        ("💡", "ideia amarelo"), ("📌", "fixar vermelho"), ("🔴", "círculo vermelho"),
        ("🟢", "círculo verde"), ("🔵", "círculo azul"), ("🟡", "círculo amarelo"),
        ("🟣", "círculo roxo"), ("🟠", "círculo laranja"), ("⚪", "círculo branco"),
        ("⚫", "círculo preto"), ("🟥", "quadrado vermelho"), ("🟩", "quadrado verde"),
        ("🟦", "quadrado azul"), ("🟨", "quadrado amarelo"),
        ("🚗", "carro vermelho movimento"), ("❌", "falha vermelho"), ("⛔", "bloqueio vermelho"),
        ("🚫", "limite vermelho"), ("⏰", "alarme vermelho tempo"), ("💯", "cem conclusão vermelho"),
        ("🧰", "ferramentas entregável vermelho"), ("❗", "atenção vermelho"), ("‼️", "alerta vermelho"),
        ("🦠", "problema micróbio verde"), ("🌵", "obstáculo cacto verde"), ("🐢", "pausa tartaruga verde"),
        ("⛳", "objetivo golfe verde"), ("📗", "livro entregável verde"), ("♻️", "ciclo reciclagem verde"),
        ("🔋", "bateria verde"), ("🪫", "bateria esgotada"), ("❔", "dúvida branco"),
        ("🌊", "fluxo onda azul"), ("📬", "aguardando mensagem caixa correio azul"),
        ("🧊", "bloqueio gelo azul"), ("🥶", "interrompido congelado azul"), ("📨", "mensagem pendente"),
        ("🆗", "concluído OK azul"), ("🌀", "indefinido espiral azul"), ("🗺️", "objetivo mapa"),
        ("📘", "livro entregável azul"), ("⚡", "atividade energia amarelo"), ("😴", "pausa sono amarelo"),
        ("🐣", "pendente nascimento amarelo"), ("⚠️", "problema alerta amarelo"), ("🔒", "bloqueio cadeado amarelo"),
        ("🤔", "dúvida pensamento amarelo"), ("🌟", "concluído estrela amarelo"), ("📒", "entregável caderno amarelo"),
        ("🌗", "contexto meia lua amarelo"), ("🌕", "contexto lua cheia amarelo"), ("⏱️", "tempo relógio")]],
}


def revision(raw: dict) -> str:
    return hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_settings(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {"enabled", "style", "max_badges", "icons"}:
        raise ValueError("Preferências inválidas. Recarregue o painel.")
    if type(value["enabled"]) is not bool or value["style"] not in THEMES:
        raise ValueError("Escolha um estilo disponível.")
    if type(value["max_badges"]) is not int or not 1 <= value["max_badges"] <= 6:
        raise ValueError("Escolha entre 1 e 6 marcadores.")
    custom = value["icons"]
    if not isinstance(custom, dict) or not set(custom) <= set(LABELS):
        raise ValueError("Marcador desconhecido.")
    for key, marker in custom.items():
        if not isinstance(marker, str) or not 1 <= len(marker) <= 12:
            raise ValueError(f"{LABELS[key]}: use de 1 a 12 caracteres.")
        if marker.isalnum():
            raise ValueError(f"{LABELS[key]}: escolha um símbolo, não uma palavra ou número.")
        if any(c.isspace() or c in "[]" or unicodedata.category(c) in {"Cc", "Cs", "Zl", "Zp"}
               or (unicodedata.category(c) == "Cf" and c != "\u200d") for c in marker):
            raise ValueError(f"{LABELS[key]}: use símbolos sem espaços, colchetes ou códigos ANSI.")
    return json.loads(json.dumps(value))


def with_settings(config: dict, settings: dict) -> dict:
    result = merge(config, {key: val for key, val in settings.items() if key != "icons"})
    result["icons"] = dict(settings["icons"])
    # Explicit legacy overrides must not mask the selected theme or picker.
    result["states"] = {**result.get("states", {}), "completed_marker": None, "unknown_marker": None}
    return result


def project_settings(config: dict) -> dict:
    custom = dict(config.get("icons", {}))
    for state, old_key in (("completed", "completed_marker"), ("unknown", "unknown_marker")):
        if config.get("states", {}).get(old_key) is not None:
            custom[state] = config["states"][old_key]
    return {"enabled": config["enabled"], "style": config["style"],
            "max_badges": config["max_badges"], "icons": custom}


class Appearance:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()
        self.path = self.store.root / "config.json"

    def state(self) -> dict:
        raw = read_json(self.path, {})
        config = load_config(self.path, self.store.profiles)
        backups = sorted(self.store.snapshots.glob("*-appearance-*.json"), key=lambda p: p.stat().st_mtime_ns)
        undo = False
        if backups:
            last = read_json(backups[-1], {})
            undo = last.get("configAfterRevision") == revision(raw)
        return {"settings": project_settings(config), "revision": revision(raw), "canUndo": undo,
                "themes": [{"id": key, "name": name, "description": description, "icons": THEMES[key],
                            "note": THEME_NOTES.get(key, "")}
                           for key, (name, description) in THEME_LABELS.items()],
                "labels": LABELS, "picker": PICKER, "registeredThreads": len(self.store.all())}

    def preview(self, settings: dict) -> dict:
        config = with_settings(load_config(self.path, self.store.profiles), validate_settings(settings))
        rows = []
        for state in State:
            view = ThreadView(state, frozenset({Modifier.GOAL, Modifier.ARTIFACTS}))
            try:
                title = compose("Ajustar filas", view, config, "Ajustar filas", "sigma")
                rows.append({"state": state.value, "label": LABELS[state.value], "title": title})
            except ValueError as exc:
                rows.append({"state": state.value, "label": LABELS[state.value], "error": str(exc)})
        return {"rows": rows, "icons": icons(config), "enabled": config["enabled"]}

    def save(self, settings: dict, expected: str) -> dict:
        settings = validate_settings(settings)
        with lock("appearance-config"):
            raw = read_json(self.path, {})
            if expected != revision(raw):
                raise ValueError("As preferências mudaram em outra janela. Recarregue antes de salvar.")
            candidate = with_settings(raw, settings)
            history = set(raw.get("appearance_marker_history", []))
            history.update(icons(load_config(self.path, self.store.profiles)).values())
            history.update(settings["icons"].values())
            candidate["appearance_marker_history"] = sorted(history)
            if len(history) > 512:
                raise ValueError("O histórico de símbolos atingiu o limite de 512 entradas.")
            snapshot = self.store.snapshot("appearance-" + uuid.uuid4().hex[:8])
            backup = read_json(snapshot)
            backup.update(configBefore=raw, configExisted=self.path.exists(), configAfterRevision=revision(candidate))
            write_json(snapshot, backup)
            write_json(self.path, candidate)
        return {"saved": True, "state": self.state()}

    def undo(self, expected: str) -> dict:
        with lock("appearance-config"):
            raw = read_json(self.path, {})
            if expected != revision(raw):
                raise ValueError("As preferências mudaram. Recarregue antes de desfazer.")
            backups = sorted(self.store.snapshots.glob("*-appearance-*.json"), key=lambda p: p.stat().st_mtime_ns)
            if not backups:
                raise ValueError("Não há salvamento para desfazer.")
            backup = read_json(backups[-1])
            if backup.get("configAfterRevision") != revision(raw):
                raise ValueError("Há alterações posteriores; o salvamento anterior foi preservado.")
            before = backup["configBefore"]
            # Retain marker recognition so a saved style can safely be changed back.
            before["appearance_marker_history"] = sorted(set(before.get("appearance_marker_history", []))
                                                         | set(raw.get("appearance_marker_history", [])))
            write_json(self.path, before)
        return {"saved": True, "state": self.state()}
