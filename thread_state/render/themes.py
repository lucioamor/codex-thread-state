THEMES = {
    "emoji": {"usage_limited": "🚩", "failed": "🔴", "blocked": "🔴", "waiting_on_user": "✋",
              "running": "▶️", "interrupted": "⏸️", "paused": "⏸️", "budget_limited": "⏳",
              "pending": "🟡", "completed": "✅", "unknown": "⚪", "goal": "🏆",
              "artifacts": "📦", "recurring": "🔁"},
    "hybrid": {"usage_limited": "🚩", "failed": "🔴", "blocked": "🔴", "waiting_on_user": "✋",
               "running": "▶︎", "interrupted": "‖", "paused": "‖", "budget_limited": "⏳",
               "pending": "🟡", "completed": "✓", "unknown": "?", "goal": "🏆",
               "artifacts": "📦", "recurring": "🔁"},
    "symbols": {"usage_limited": "⚑", "failed": "✗", "blocked": "✗", "waiting_on_user": "!",
                "running": "▶", "interrupted": "‖", "paused": "‖", "budget_limited": "⌛",
                "pending": "…", "completed": "✓", "unknown": "?", "goal": "★",
                "artifacts": "◆", "recurring": "↻"},
}

# Every theme maps the same lifecycle vocabulary; colors never change meaning.
THEMES["symbols"]["budget_limited"] = "◴"
THEMES["symbols"]["running"] = "▶︎"
THEMES["minimal"] = dict(THEMES["symbols"])
THEMES["enterprise"] = {
    "usage_limited": "!", "failed": "×", "blocked": "⊘", "waiting_on_user": "?",
    "running": "›", "interrupted": "Ⅱ", "paused": "Ⅱ", "budget_limited": "◴",
    "pending": "·", "completed": "✓", "unknown": "◇", "goal": "◆",
    "artifacts": "□", "recurring": "↻",
}
THEMES["playful"] = {
    "usage_limited": "🚧", "failed": "💥", "blocked": "🧱", "waiting_on_user": "👋",
    "running": "🚀", "interrupted": "🛑", "paused": "💤", "budget_limited": "⌛",
    "pending": "🌱", "completed": "🎉", "unknown": "🔎", "goal": "🎯",
    "artifacts": "🎁", "recurring": "🔄",
}
THEMES["red"] = {
    "usage_limited": "🚫", "failed": "❌", "blocked": "⛔", "waiting_on_user": "❓",
    "running": "🚗", "interrupted": "🛑", "paused": "🛑", "budget_limited": "⏰",
    "pending": "🚩", "completed": "💯", "unknown": "❓", "goal": "🎯",
    "artifacts": "🧰", "recurring": "🔁",
}
THEMES["green"] = {
    "usage_limited": "🚧", "failed": "🦠", "blocked": "🌵", "waiting_on_user": "👋",
    "running": "🟢", "interrupted": "✋", "paused": "🐢", "budget_limited": "⏳",
    "pending": "🌱", "completed": "✅", "unknown": "❔", "goal": "⛳",
    "artifacts": "📗", "recurring": "♻️",
}
THEMES["blue"] = {
    "usage_limited": "🚧", "failed": "❌", "blocked": "🧊", "waiting_on_user": "📬",
    "running": "🌊", "interrupted": "🥶", "paused": "💤", "budget_limited": "⏳",
    "pending": "📨", "completed": "🆗", "unknown": "🌀", "goal": "🗺️",
    "artifacts": "📘", "recurring": "🔄",
}
THEMES["yellow"] = {
    "usage_limited": "🚧", "failed": "⚠️", "blocked": "🔒", "waiting_on_user": "👋",
    "running": "⚡", "interrupted": "✋", "paused": "😴", "budget_limited": "⏳",
    "pending": "🐣", "completed": "🌟", "unknown": "🤔", "goal": "🏆",
    "artifacts": "📒", "recurring": "🔁",
}

for name, theme in THEMES.items():
    theme.update(context_warn="◕", context_critical="●", long_running="⏱")
    if name in ("symbols", "minimal", "enterprise"):
        theme["long_running"] = "◷"

THEMES["red"].update(context_warn="❗", context_critical="‼️", long_running="⏰")
THEMES["green"].update(context_warn="🔋", context_critical="🪫", long_running="⏱️")
THEMES["blue"].update(context_warn="🌊", context_critical="🌀", long_running="⏱️")
THEMES["yellow"].update(context_warn="🌗", context_critical="🌕", long_running="⌛")

THEME_LABELS = {
    "hybrid": ("Híbrido", "O equilíbrio da versão 1.0"),
    "symbols": ("Monocromático", "Símbolos discretos, sem emojis coloridos"),
    "emoji": ("Colorido", "Um emoji para cada momento"),
    "minimal": ("Minimalista", "Somente o estado principal"),
    "enterprise": ("Enterprise", "Geometria sóbria e compacta"),
    "playful": ("Divertido", "Um pouco de personalidade"),
    "red": ("Vermelho", "Movimento, atenção e conquista"),
    "green": ("Verde", "Sinal aberto, crescimento e ciclos"),
    "blue": ("Azul", "Fluxo, espera e resfriamento"),
    "yellow": ("Amarelo", "Energia, gestos e conquistas"),
}

THEME_NOTES = {
    "red": "🚗 movimento · ❌ falha · ⛔ bloqueio · 💯 conclusão. A recorrência mantém 🔁, sem equivalente vermelho claro.",
    "green": "🟢 sinal aberto · 🌱 pendente · 🦠 problema · 🌵 obstáculo · ✅ conclusão. Mãos, limites, dúvida, relógio e bateria esgotada usam referências fora da paleta quando necessário.",
    "blue": "🌊 fluxo · 📬 aguardando resposta · 🧊 bloqueio · 💤 pausa · 🆗 conclusão. Falha, limites e relógio preservam os emojis de referência.",
    "yellow": "⚡ atividade · 👋 aguardando você · 🔒 bloqueio · 🌟 conclusão. A recorrência mantém 🔁, sem equivalente amarelo claro.",
}
