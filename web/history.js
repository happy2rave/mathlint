// What you solved, checked and worked out, kept on this device only.
//
// Entries are { id, tab, input, kind, answer, extra, time, starred }, newest
// first. The same input on the same tab moves to the top instead of repeating.
// Starred entries are favourites: they are never dropped, and "clear" leaves
// them. Without storage (a private window, blocked site data) the history is
// simply empty.

export const HISTORY_KEY = "mathlint:history";
export const MAX_UNSTARRED = 200;

export class History {
  constructor(storage = defaultStorage(), now = () => Date.now()) {
    this.storage = storage;
    this.now = now;
  }

  get available() {
    if (!this.storage) return false;
    try {
      const probe = HISTORY_KEY + ":probe";
      this.storage.setItem(probe, "1");
      this.storage.removeItem(probe);
      return true;
    } catch {
      return false;
    }
  }

  list({ starred = false } = {}) {
    const entries = this.#read();
    return starred ? entries.filter((entry) => entry.starred) : entries;
  }

  add({ tab, input, kind = "", answer = "", extra = null }) {
    const entries = this.#read();
    const index = entries.findIndex((entry) => entry.tab === tab && entry.input === input);
    const previous = index >= 0 ? entries.splice(index, 1)[0] : null;
    const entry = {
      id: previous ? previous.id : `${this.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
      tab,
      input,
      kind,
      answer,
      extra,
      time: this.now(),
      starred: previous ? previous.starred : false,
    };
    entries.unshift(entry);
    this.#write(trim(entries));
    return entry;
  }

  star(id, on) {
    this.#write(this.#read().map((entry) => (entry.id === id ? { ...entry, starred: on } : entry)));
  }

  remove(id) {
    this.#write(this.#read().filter((entry) => entry.id !== id));
  }

  clear() {
    this.#write(this.#read().filter((entry) => entry.starred));
  }

  #read() {
    try {
      const entries = JSON.parse(this.storage.getItem(HISTORY_KEY) || "[]");
      return Array.isArray(entries) ? entries.filter(isEntry) : [];
    } catch {
      return [];
    }
  }

  #write(entries) {
    try {
      this.storage.setItem(HISTORY_KEY, JSON.stringify(entries));
    } catch {
      /* full or blocked storage: the history just does not grow */
    }
  }
}

function isEntry(value) {
  return Boolean(value) && typeof value === "object" && typeof value.id === "string" &&
    typeof value.tab === "string" && typeof value.input === "string";
}

// Keep every starred entry and the newest unstarred ones.
function trim(entries) {
  let unstarred = 0;
  return entries.filter((entry) => entry.starred || ++unstarred <= MAX_UNSTARRED);
}

function defaultStorage() {
  try {
    return globalThis.localStorage || null;
  } catch {
    return null;
  }
}
