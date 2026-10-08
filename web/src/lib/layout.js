// Places 28 squares around a 9x9 grid, 7 per side, starting next to the bottom-right
// corner and running clockwise (bottom row right-to-left, up the left, along the top,
// down the right). Grid lines are 1-indexed.
export const SIDE_LENGTH = 7;
export const BOARD_SQUARES = SIDE_LENGTH * 4;

export function squarePosition(index) {
  const side = Math.floor(index / SIDE_LENGTH);
  const step = index % SIDE_LENGTH;
  switch (side) {
    case 0: return { side: "bottom", row: 9, col: 8 - step };
    case 1: return { side: "left", row: 8 - step, col: 1 };
    case 2: return { side: "top", row: 1, col: 2 + step };
    default: return { side: "right", row: 2 + step, col: 9 };
  }
}

export const CORNERS = [
  { id: "logon", row: 9, col: 9, title: "Log On", text: "Every visit starts here", icon: "arrow" },
  { id: "buffering", row: 9, col: 1, title: "Buffering…", text: "Sit tight, nearly loaded", icon: "spinner" },
  { id: "incognito", row: 1, col: 1, title: "Incognito", text: "Nobody saw you land here", icon: "mask" },
  { id: "notfound", row: 1, col: 9, title: "404", text: "Page not found. Back to Log On", icon: "broken" },
];

export function initials(brand) {
  const word = brand.replace(/[^\p{L}\p{N}\s]/gu, " ").trim().split(/\s+/)[0] ?? "?";
  return word.charAt(0).toUpperCase();
}
