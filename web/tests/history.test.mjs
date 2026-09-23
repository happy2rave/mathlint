import { test } from "node:test";
import assert from "node:assert/strict";

import { History, MAX_UNSTARRED } from "../history.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

let clock = 0;
const now = () => ++clock;

test("the newest entry comes first", () => {
  const history = new History(memoryStorage(), now);
  history.add({ tab: "solve", input: "x+1=2", kind: "Linear equation", answer: "x = 1" });
  history.add({ tab: "solve", input: "x^2=4", kind: "Quadratic equation", answer: "x = -2" });
  assert.deepEqual(history.list().map((entry) => entry.input), ["x^2=4", "x+1=2"]);
});

test("the same problem moves to the top instead of repeating, and keeps its star", () => {
  const history = new History(memoryStorage(), now);
  const first = history.add({ tab: "solve", input: "x+1=2" });
  history.add({ tab: "solve", input: "x^2=4" });
  history.star(first.id, true);
  history.add({ tab: "solve", input: "x+1=2", answer: "x = 1" });
  const entries = history.list();
  assert.equal(entries.length, 2);
  assert.equal(entries[0].input, "x+1=2");
  assert.equal(entries[0].answer, "x = 1");
  assert.equal(entries[0].starred, true);
  // the same text on another tab is another entry
  history.add({ tab: "check", input: "x+1=2" });
  assert.equal(history.list().length, 3);
});

test("starred entries can be listed on their own", () => {
  const history = new History(memoryStorage(), now);
  const kept = history.add({ tab: "solve", input: "a" });
  history.add({ tab: "solve", input: "b" });
  history.star(kept.id, true);
  assert.deepEqual(history.list({ starred: true }).map((entry) => entry.input), ["a"]);
  history.star(kept.id, false);
  assert.deepEqual(history.list({ starred: true }), []);
});

test(`at most ${MAX_UNSTARRED} unstarred entries are kept, and starred ones never go`, () => {
  const history = new History(memoryStorage(), now);
  const oldest = history.add({ tab: "solve", input: "keep me" });
  history.star(oldest.id, true);
  for (let index = 0; index < MAX_UNSTARRED + 20; index += 1) {
    history.add({ tab: "solve", input: `problem ${index}` });
  }
  const entries = history.list();
  assert.equal(entries.filter((entry) => !entry.starred).length, MAX_UNSTARRED);
  assert.ok(entries.some((entry) => entry.input === "keep me"));
  assert.equal(entries[0].input, `problem ${MAX_UNSTARRED + 19}`);
});

test("remove takes one entry out; clear keeps the starred ones", () => {
  const history = new History(memoryStorage(), now);
  const a = history.add({ tab: "solve", input: "a" });
  const b = history.add({ tab: "solve", input: "b" });
  history.add({ tab: "solve", input: "c" });
  history.star(b.id, true);
  history.remove(a.id);
  assert.deepEqual(history.list().map((entry) => entry.input), ["c", "b"]);
  history.clear();
  assert.deepEqual(history.list().map((entry) => entry.input), ["b"]);
});

test("a storage that throws gives an empty history and no errors", () => {
  const broken = {
    getItem() {
      throw new Error("denied");
    },
    setItem() {
      throw new Error("denied");
    },
    removeItem() {
      throw new Error("denied");
    },
  };
  const history = new History(broken, now);
  assert.equal(history.available, false);
  assert.deepEqual(history.list(), []);
  assert.doesNotThrow(() => history.add({ tab: "solve", input: "x" }));
  assert.doesNotThrow(() => history.clear());
});

test("damaged saved data is treated as empty", () => {
  const storage = memoryStorage();
  storage.setItem("mathlint:history", "{not json");
  const history = new History(storage, now);
  assert.deepEqual(history.list(), []);
  storage.setItem("mathlint:history", JSON.stringify([{ nonsense: true }, null, 3]));
  assert.deepEqual(history.list(), []);
});
