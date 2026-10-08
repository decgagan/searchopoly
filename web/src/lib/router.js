// URL hash state: "#world", "#uk", "#world/google", "#uk/bbc". Empty hash = World board.
export const BOARDS = ["world", "uk"];

export function parseHash(hash) {
  const [board, site] = hash.replace(/^#\/?/, "").toLowerCase().split("/");
  return {
    board: BOARDS.includes(board) ? board : "world",
    site: site ? decodeURIComponent(site) : null,
  };
}

export function formatHash({ board, site }) {
  if (site) return `#${board}/${encodeURIComponent(site)}`;
  return board === "world" ? "" : `#${board}`;
}
