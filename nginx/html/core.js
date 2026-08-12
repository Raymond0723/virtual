export class CommandBudget {
  #remaining;

  constructor(limit = 5) {
    this.#remaining = { left: limit, right: limit };
  }

  use(side) {
    if (!(side in this.#remaining) || this.#remaining[side] === 0) return false;
    this.#remaining[side] -= 1;
    return true;
  }

  remaining(side) {
    return this.#remaining[side] ?? 0;
  }
}