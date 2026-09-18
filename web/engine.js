// Talks to the engine in its Web Worker. Every call gets a promise and a time
// limit; a call that runs over it stops the worker and starts a fresh one.

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
  async call(kind, payload = {}) {
    try {
      await this.ready;
    } catch (error) {
      return { ok: false, error: "The math engine could not start: " + error.message };
    }
    return new Promise((resolve) => {
      const id = this.nextId++;
      const timer = setTimeout(() => {
        this.stop(
          "This took longer than 20 seconds, so it was stopped. Try writing it more simply."
        );
      }, TIME_LIMIT_MS);
      this.pending.set(id, { resolve, timer });
      this.worker.postMessage({ id, kind, payload });
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
