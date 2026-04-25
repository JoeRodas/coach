// Minimal client-side PGN sniff. The server still does the real validation —
// this just catches obvious nonsense before we burn an analyze call on it.
//
// Heuristic: a PGN body must contain at least one move-number-and-SAN pair
// like "1. e4". Headers (the [...] tags) are optional from the user's
// perspective; many people paste move-list-only PGNs.

const MOVE_PATTERN = /\b\d+\.\s*[a-zA-Z][a-zA-Z0-9+#=\-]*/;

export type PgnValidation = { ok: true } | { ok: false; reason: string };

export function validatePgn(input: string): PgnValidation {
  const trimmed = input.trim();
  if (trimmed.length === 0) {
    return { ok: false, reason: "Paste a game in PGN format to analyze." };
  }
  if (trimmed.length < 5) {
    return { ok: false, reason: "That doesn't look like a complete game." };
  }
  if (!MOVE_PATTERN.test(trimmed)) {
    return { ok: false, reason: "Couldn't find any moves. Did you paste the full PGN?" };
  }
  return { ok: true };
}
