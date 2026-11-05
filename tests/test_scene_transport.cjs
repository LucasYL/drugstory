const { test } = require("node:test");
const assert = require("node:assert/strict");
const Driver = require("../src/drugstory/career/web/api-driver.js");
const World = require("../src/drugstory/career/web/scene/world.js");
const response = (data, status = 200) => ({
  ok: status === 200,
  status,
  json: async () => data,
});
const initial = { revision: 0, token: "test", week: 0 };
function connected(fetcher) {
  const d = new Driver(fetcher, () => "stable-id");
  d.current = { ...initial };
  return d;
}
test("lost successful response is retried with same command identity and never committed optimistically", async () => {
  let attempts = 0;
  const sent = [];
  const d = connected(async (_, options) => {
    sent.push(options);
    assert.equal(d.view().week, 0);
    if (!attempts++) throw Error("lost response");
    return response({ ...initial, revision: 1, week: 1 });
  });
  const next = await d.tick();
  assert.equal(next.week, 1);
  assert.deepEqual(sent[0], sent[1]);
  assert.equal(JSON.parse(sent[0].body).request_id, "stable-id");
});
test("concurrent clocks cannot submit two weeks", async () => {
  let release;
  const d = connected(() => new Promise((r) => (release = r)));
  const first = d.tick();
  await assert.rejects(d.tick(), /上一项/);
  release(response({ ...initial, week: 1 }));
  await first;
  assert.equal(d.busy, false);
});
test("unconfirmed operation locks mutations until explicit reconnect", async () => {
  const d = connected(async () => {
    throw Error("offline");
  });
  await assert.rejects(d.tick(), /可能已保存/);
  assert.equal(d.view().week, 0);
  await assert.rejects(d.act("train"), /尚未确认/);
  d.fetcher = async (path) =>
    response(
      path === "/api/content"
        ? { api_version: 2 }
        : { ...initial, week: 1, revision: 1 },
    );
  await d.connect();
  assert.equal(d.view().week, 1);
  assert.equal(d.uncertain, false);
});
test("revision conflict loads authoritative state but does not replay stale choice", async () => {
  let calls = 0;
  const d = connected(async () => {
    calls++;
    return response(
      { error: "已变化", state: { ...initial, week: 9, revision: 9 } },
      409,
    );
  });
  await assert.rejects(d.act("choose_candidate", { candidate: 1 }), /已变化/);
  assert.equal(calls, 1);
  assert.equal(d.view().week, 9);
});
test("disk failure keeps confirmed state and can be retried deliberately", async () => {
  const d = connected(async () => response({ error: "存档失败" }, 500));
  await assert.rejects(d.tick(), /存档失败/);
  assert.equal(d.view().week, 0);
  assert.equal(d.uncertain, false);
});
const h = (id, room, activity) => ({
  id,
  room,
  activity,
  members: 4,
  profession: "bio",
  look: { hair: "short" },
});
const p = (extra = {}) => ({
  id: "1",
  name: "公开项目",
  team: [],
  status: "running",
  mode: "cro",
  key: "II",
  chosen: 1,
  readings: [
    { stage: "II", candidate: 0, values: { effect: 999 } },
    { stage: "II", candidate: 1, values: { effect: 712 } },
  ],
  scene: { room: "room_clinical", executor: "cro", limits: { effect: 700 } },
  ...extra,
});
const s = () => ({
  facility: { level: 0 },
  equipment: [],
  heroes: [h("a", "room_bio", "make"), h("b", "room_academy", "study")],
  projects: [p()],
  pending: 0,
  game_over: false,
});
test("shared rooms before expansion, dedicated rooms after it; no scene gates added", () => {
  const snapshot = s(),
    copy = structuredClone(snapshot);
  const early = World.world(snapshot, {});
  assert.equal(early.assignments.a.room, "lab");
  assert.equal(early.assignments.b.room, "clinic");
  assert.equal(early.cro, true);
  assert.deepEqual(snapshot, copy);
  snapshot.facility.level = 2;
  const later = World.world(snapshot, {});
  assert.equal(later.assignments.a.room, "bio");
  assert.equal(later.assignments.b.room, "academy");
  assert.equal(later.rooms.hall.built, false);
});
test("boards use only current candidate readings and public thresholds; CRO cannot persist into review", () => {
  const snapshot = s();
  const mapped = World.world(snapshot, {});
  assert.deepEqual(mapped.boards.clinic[0].readings, [712]);
  assert.equal(mapped.boards.clinic[0].limit, 700);
  snapshot.projects = [
    p({
      key: "review",
      scene: { room: "room_clinical", executor: "internal", limits: {} },
      readings: [],
    }),
  ];
  assert.equal(World.world(snapshot, {}).cro, false);
});
test("pending decisions and bankruptcy block automatic time", () => {
  assert.equal(World.blocked(s()), false);
  assert.equal(World.blocked({ ...s(), pending: 1 }), true);
  assert.equal(World.blocked({ ...s(), game_over: true }), true);
});
