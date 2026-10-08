// Shared animation settings that honour the user's reduced-motion preference.
const query = matchMedia("(prefers-reduced-motion: reduce)");
let reduced = $state(query.matches);
query.addEventListener("change", (e) => (reduced = e.matches));

export const motion = {
  get reduced() { return reduced; },
  get move() { return reduced ? 0 : 650; },
  get fade() { return reduced ? 0 : 280; },
};
