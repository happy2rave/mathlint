// Talks to the engine in its Web Worker. Every call gets a promise and a time
// limit; a call that runs over it stops the worker and starts a fresh one.
// Every request carries the reader's language, so the steps come back in it.
import { language, t } from "./i18n.js";

export const TIME_LIMIT_MS = 20000;

export class Engine {
  #resolveReady = null;
  #rejectReady = null;

  constructor({ onStatus } = {}) {
    this.onStatus = onStatus || (() => {});
    this.pending = new Map();
    this.nextId = 1;
    this.#spawn();
  }

  #spawn() {
    this.ready = new Promise((resolve, reject) => {
      this.#resolveReady = resolve;
      this.#rejectReady = reject;
    });
    this.worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
    this.worker.onmessage = (event) => this.#receive(event.data);
    this.worker.onerror = (event) => this.#rejectReady(new Error(event.message || "worker failed"));
  }

  #receive(message) {
    if (message.type === "status") return this.onStatus(message.text);
    if (message.type === "ready") return this.#resolveReady(message.version);
    if (message.type === "failed") return this.#rejectReady(new Error(message.error));
    const job = this.pending.get(message.id);
    if (!job) return;
    this.pending.delete(message.id);
    clearTimeout(job.timer);
    job.resolve(message);
  }

  // Resolves to {ok: true, result} or {ok: false, error}; it never rejects.
  // A quiet call (the live answer) that runs over its limit is simply dropped:
  // restarting the engine for it would cost more than it is worth.
  async call(kind, payload = {}, { timeLimit = TIME_LIMIT_MS, quiet = false } = {}) {
    try {
      await this.ready;
    } catch (error) {
      return { ok: false, error: t("engine.couldNotStart", { error: error.message }) };
    }
    return new Promise((resolve) => {
      const id = this.nextId++;
      const timer = setTimeout(() => {
        if (quiet) {
          this.pending.delete(id);
          resolve({ ok: false, error: "too slow for a live answer" });
          return;
        }
        this.stop(t("engine.tooSlow"));
      }, timeLimit);
      this.pending.set(id, { resolve, timer });
      this.worker.postMessage({ id, kind, payload: { lang: language(), ...payload } });
    });
  }

  get busy() {
    return this.pending.size > 0;
  }

  // Abandon whatever is running and start a fresh engine.
  stop(reason = "Stopped.") {
    this.worker.terminate();
    for (const job of this.pending.values()) {
      clearTimeout(job.timer);
      job.resolve({ ok: false, error: reason });
    }
    this.pending.clear();
    this.#spawn();
  }
}
