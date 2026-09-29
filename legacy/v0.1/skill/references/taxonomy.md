# Title status taxonomy

| Prefix | State | Required evidence |
|---|---|---|
| 🔵 | Running | Current thread or latest turn is actively running |
| 🚩 | Usage limited | Latest turn failed with a structured usage/quota/credit-limit runtime error |
| ⏳ | Goal budget exhausted | Current goal is `budget_limited`; never use this for account quota |
| 🔴 | Failed or blocked | Latest runtime failure not caused by usage limit, or explicit current blocker |
| 🟡 | Pending | Required work, validation, or acceptance remains |
| ⏸️ | Paused/interrupted | Formal goal pause or runtime interruption without attributing cause |
| ✅ | Complete | Deliverable in the examined scope is explicitly complete |
| 🔁 | Monitoring | Recurring monitor is healthy and waiting for the next cycle |
| ⚪ | Unknown | Available evidence cannot distinguish completion from abandonment |
| 🏁 | Goal modifier | Formal goal record or explicit evidence that the work ran as a goal |

Priority: active runtime > latest runtime failure/interruption > current goal state > semantic review > unknown.

Do not treat these as completion evidence by themselves: `idle`, `notLoaded`, a `completed` turn, green tests, a commit, a final-answer phase, or words quoted from another source.

Project tags are editorial metadata, not status. Preserve an existing bracketed prefix exactly. Suggest a new one only when the repository/project association is directly observed and unambiguous.
