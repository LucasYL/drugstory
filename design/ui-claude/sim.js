/* 新药物语 · 一屏研究所：示例驱动。
 * 这是一个缩小版的规则模拟，数值和流程照着 v0.7 写（开发三批、验证四批、期中继续或止损）。
 * 它对外只做三件事：tick() 推进一周、act() 执行一个决定、view() 给出画面和面板要的数据。
 * 事件格式和 v0.7 的 /api/state 一样：{version, id, week, type, actors, project, room, data}。
 * 接真实引擎时，用一个调用 /api/action 的驱动替换这个文件，scene.js 和 ui.js 不用改。 */
(() => {
  "use strict";

  function mulberry32(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gauss(rnd) {
    let u = 0;
    while (u === 0) u = rnd();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rnd());
  }
  function normCdf(z) {
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const d = 0.3989423 * Math.exp((-z * z) / 2);
    const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
    return z > 0 ? 1 - p : p;
  }

  const PROFESSIONS = { bio: "生物与转化", chem: "药化与分子工程", tox: "药代与毒理", proc: "制剂与工艺", clinical: "临床与统计" };
  const SHORT = { bio: "生物", chem: "药化", tox: "毒理", proc: "工艺", clinical: "临床" };
  const RANKS = { 1: "见习", 2: "精英", 3: "大师", 4: "传奇" };
  const STAT_NAMES = {
    generic: { safety: "杂质与质量控制", exposure: "等效性支持", quality: "稳定性与放大" },
    innovative: { effect: "获益潜力", safety: "安全窗口", exposure: "暴露与等效", quality: "工艺稳定" },
  };
  const SHORT_STAT = { effect: "疗效", safety: "安全", exposure: "等效", quality: "工艺" };
  const SHORT_STAGE = { be: "BE", review: "审评", II: "II 期", III: "III 期" };
  // 场景房间：stage.room；事件里的 room 字段照 v0.7 的写法
  const STAGES = {
    formulation: {
      name: "处方与工艺", kind: "make", weeks: 9, cost: 60, roles: ["proc", "chem"], room: "lab",
      limits: { quality: 48 }, noise: 9, out: { proc: { quality: 0.65 }, chem: { exposure: 0.45 } },
    },
    quality: {
      name: "质量与稳定性", kind: "make", weeks: 7, cost: 40, roles: ["proc", "tox"], room: "qc",
      limits: { quality: 62, safety: 58 }, noise: 7, out: { proc: { quality: 0.35 }, tox: { safety: 0.35 } },
    },
    rework: {
      name: "工艺补正", kind: "make", weeks: 8, cost: 100, roles: ["proc", "chem"], room: "lab",
      limits: {}, noise: 0, out: { proc: { quality: 0.3 }, chem: { exposure: 0.6 } },
    },
    be: {
      name: "生物等效性验证", kind: "test", weeks: 10, cost: 90, roles: ["clinical", "tox"], room: "clinic",
      limits: { exposure: 64 }, noise: 6, clinical: true,
    },
    review: {
      name: "上市审评与质量核查", kind: "test", weeks: 8, cost: 60, roles: ["proc", "clinical"], room: "qc",
      limits: { quality: 65 }, noise: 4,
    },
    II: {
      name: "II 期概念验证", kind: "test", weeks: 28, cost: 650, roles: ["clinical", "bio"], room: "clinic",
      limits: { effect: 70, safety: 58 }, noise: 8, clinical: true, interim: true,
    },
    III: {
      name: "III 期确认获益", kind: "test", weeks: 44, cost: 1350, roles: ["clinical", "proc"], room: "clinic",
      limits: { effect: 75, safety: 66 }, noise: 6, clinical: true, interim: true,
    },
  };
  const SIGNATURE = {
    pill: { name: "首批守护", text: "处方与工艺阶段，工艺稳定额外 +3", stage: "formulation", stat: "quality", bonus: 3 },
    beaker: { name: "路线小试", text: "分子优化阶段，暴露与等效额外 +3", stage: "optimize", stat: "exposure", bonus: 3 },
    sprout: { name: "反例模型", text: "分子优化阶段，获益潜力额外 +3", stage: "optimize", stat: "effect", bonus: 3 },
    bubble: { name: "杂质清单", text: "质量与稳定性阶段，安全额外 +3", stage: "quality", stat: "safety", bonus: 3 },
    ruler: { name: "首期排程", text: "负责 I 期时，工期缩短 2 周", stage: "I", stat: "", bonus: 0 },
  };
  const LOOKS = {
    pill: { skin: "#f1c9a6", hair: "bun", hairColor: "#3b2a22", shirt: "#3f7fbf", accessory: "goggles", accent: "#6aa9d8" },
    beaker: { skin: "#e8b991", hair: "spiky", hairColor: "#1f1b19", shirt: "#e08a3c", glasses: true },
    sprout: { skin: "#f0caa8", hair: "short", hairColor: "#4a3326", shirt: "#4f9d69", glasses: true, accessory: "sprout" },
    bubble: { skin: "#f3d1b2", hair: "bob", hairColor: "#2a2220", shirt: "#7c6bb0", accessory: "clips", accent: "#f0a7c0" },
    ruler: {
      skin: "#edc29d", hair: "long", hairColor: "#2d211b", shirt: "#2a9d8f", coat: false, accessory: "catears",
      accent: "#2d211b", holds: "tablet",
    },
  };
  const TEMPLATES = {
    work_completed: (d) => `${d.name}完成一批${d.stage}：${d.detail}`,
    evidence_received: (d) => `${d.project}收到第 ${d.batch} 批${d.stage}数据：${d.detail}`,
    phase_started: (d) => `${d.project}开始${d.stage}，预计 ${d.weeks} 周`,
    phase_finished: (d) => `${d.project}完成${d.stage}：${d.outcome}`,
    service_completed: (d) => `${d.name}交付${d.service}，收入 ¥${d.reward} 万`,
    equipment_upgraded: (d) => `${d.name}升到 ${d.level} 级`,
    room_built: (d) => `${d.name}落成`,
    room_build_started: (d) => `开始扩建${d.name}，${d.weeks} 周`,
    product_launched: (d) => `${d.name}获批上市！`,
    decision_made: (d) => d.text,
    notice: (d) => d.text,
  };

  function create(seed = 7) {
    const rnd = mulberry32(seed);
    const s = {
      week: 101,
      cash: 2600,
      seq: 0,
      events: [],
      rooms: { lab: { built: true, level: 1 }, qc: { built: true, level: 1 }, clinic: { built: true, level: 1 }, bio: { built: false, level: 1, building: null } },
      heroes: [
        hero("pill", "小药丸", "proc", 2, 58, 2),
        hero("beaker", "烧杯仔", "chem", 2, 54, 2),
        hero("bubble", "泡泡鼠", "tox", 1, 41, 1),
        hero("ruler", "刻度喵", "clinical", 1, 46, 1),
        hero("sprout", "豆芽博士", "bio", 1, 44, 1),
      ],
      projects: [],
      services: [{ id: "svc1", name: "杂质谱检测服务", hero: "bubble", left: 4, total: 6, reward: 45, room: "qc" }],
      products: [],
      decisions: [],
      lastFlow: 0,
    };

    function hero(id, name, profession, rank, ability, members) {
      return { id, name, profession, rank, ability, members, look: LOOKS[id], signature: SIGNATURE[id] };
    }

    /* ----- 项目一：普通仿制药，刚完成筛选，等你选候选 ----- */
    const p1 = {
      id: "p1", name: "稳压片", kind: "generic", kindName: "普通仿制药", combo: "已知有效成分 · 口服片剂",
      path: ["formulation", "quality", "be", "review"], index: 0, status: "selecting", chosen: null,
      candidates: [
        cand("溶出优先处方", { safety: [82, 6], exposure: [73, 9], quality: [64, 9] }, { safety: 84, exposure: 71, quality: 63 }),
        cand("稳定优先处方", { safety: [83, 6], exposure: [69, 9], quality: [75, 9] }, { safety: 82, exposure: 66, quality: 78 }),
        cand("放大友好处方", { safety: [80, 6], exposure: [65, 9], quality: [82, 9] }, { safety: 79, exposure: 62, quality: 85 }),
      ],
      exec: null, results: [], repairs: 0, readings: [], work: [],
    };
    /* ----- 项目二：创新药，II 期已经做了 12 周，第 2 批数据快到了 ----- */
    const p2 = {
      id: "p2", name: "肺癌精准抑制", kind: "innovative", kindName: "创新药", combo: "EGFR × 小分子",
      path: ["optimize", "preclinical", "I", "II", "III", "review"], index: 3, status: "running", chosen: 0,
      candidates: [cand("活性线索", { effect: [74, 7], safety: [63, 6], exposure: [70, 6], quality: [72, 6] }, { effect: 74.5, safety: 62.4, exposure: 71, quality: 73 })],
      exec: null, results: [
        { key: "optimize", passed: true }, { key: "preclinical", passed: true }, { key: "I", passed: true },
      ], repairs: 0, readings: [], work: [],
      scripted: [{ effect: 69.4, safety: 64.6 }, { effect: 77.8, safety: 60.2 }, { effect: 74.1, safety: 61.8 }],
    };
    s.projects.push(p1, p2);
    startStage(p2, "II", ["ruler", "sprout"], "internal", true);
    p2.exec.elapsed = 12;
    p2.exec.batches.push({ index: 1, week: s.week - 5, values: { effect: 76.3, safety: 61.1 } });
    applyBelief(p2, { effect: 76.3, safety: 61.1 }, p2.exec.sigma);
    p2.readings.push({ stage: "II", index: 1, week: s.week - 5, values: { effect: 76.3, safety: 61.1 } });
    s.events = [];
    s.decisions.push({ id: "d-choose", kind: "choose", project: "p1" });

    function cand(label, belief, truth) {
      const b = {};
      for (const [k, [mean, sd]] of Object.entries(belief)) b[k] = { mean, variance: sd * sd, observations: 1 };
      return { label, belief: b, truth };
    }

    /* ----- 小工具 ----- */
    const findHero = (id) => s.heroes.find((h) => h.id === id);
    const findProject = (id) => s.projects.find((p) => p.id === id);
    const statNames = (p) => STAT_NAMES[p.kind === "generic" ? "generic" : "innovative"];
    function emit(type, { actors = [], project = null, room = null, data = {} } = {}) {
      const e = { version: 1, id: ++s.seq, week: s.week, type, actors, project, room, data };
      e.text = TEMPLATES[type] ? TEMPLATES[type](data) : data.text || type;
      s.events.push(e);
      return e;
    }
    function busy() {
      const out = {};
      for (const p of s.projects) if (p.exec && p.status === "running") for (const id of p.exec.team) out[id] = p.id;
      for (const v of s.services) out[v.hero] = v.id;
      return out;
    }
    function payroll() {
      return s.heroes.reduce((sum, h) => sum + 1.3 + h.rank * 0.65 + h.ability * 0.018 + h.members * 0.42, 0);
    }
    function committed() {
      let sum = 0;
      for (const p of s.projects) if (p.exec && p.status !== "result") sum += p.exec.costPerWeek * (p.exec.weeks - p.exec.elapsed);
      return sum;
    }
    function recommend(p, key) {
      const st = STAGES[key];
      const taken = busy();
      const team = [];
      for (const role of st.roles) {
        const options = s.heroes.filter((h) => h.profession === role && !taken[h.id] && !team.includes(h.id));
        options.sort((a, b) => b.ability - a.ability);
        if (options[0]) team.push(options[0].id);
      }
      const hasClinical = team.some((id) => findHero(id).profession === "clinical");
      const mode = st.clinical && !hasClinical ? "cro" : "internal";
      return { team, mode };
    }
    function workPlan(p, key, team) {
      const st = STAGES[key];
      if (st.kind !== "make") return [];
      const plan = [];
      for (const id of team) {
        const h = findHero(id);
        const weights = st.out[h.profession];
        if (!weights) continue;
        const members = Math.min(h.members, 2 + h.rank);
        const mastery = Math.max(0, (h.ability - 22) / 65) ** 1.25;
        const equipment = (s.rooms[roomOfProfession(h.profession)]?.level ?? 1) - 1;
        const base = (2 + 15 * mastery) * (1 + 0.16 * Math.sqrt(members)) + equipment * 2;
        const amounts = {};
        for (const [stat, w] of Object.entries(weights)) {
          const sig = h.signature && h.signature.stage === key && h.signature.stat === stat ? h.signature.bonus : 0;
          amounts[stat] = Math.min(24, base * w + sig);
        }
        plan.push({ actor: id, role: h.profession, members, amounts });
      }
      return plan;
    }
    function roomOfProfession(prof) {
      return { proc: "lab", chem: "lab", tox: "qc", clinical: "clinic", bio: "bio" }[prof];
    }
    function stageCost(key, mode) {
      return STAGES[key].cost * (mode === "cro" ? 1.3 : 1);
    }

    function startStage(p, key, team, mode, silent = false) {
      const st = STAGES[key];
      const cost = stageCost(key, mode);
      const weeks = st.weeks;
      p.exec = {
        key, team, mode, weeks, elapsed: 0, cost, costPerWeek: cost / weeks,
        batchCount: st.kind === "make" ? 3 : 4, batches: [], done: 0, plan: workPlan(p, key, team),
        sigma: st.noise * 2, interimDone: !st.interim, interimAt: weeks - Math.floor((weeks + 1) / 2),
      };
      p.status = "running";
      p.work = p.exec.plan;
      if (!silent) {
        emit("phase_started", {
          actors: team, project: p.id, room: st.clinical ? "room_clinical" : "room_lab",
          data: { project: p.name, stage: st.name, weeks, mode },
        });
      }
    }
    function applyBelief(p, values, sigma) {
      const c = p.candidates[p.chosen];
      for (const [stat, v] of Object.entries(values)) {
        const b = c.belief[stat];
        const precision = 1 / b.variance + 1 / (sigma * sigma);
        b.mean = (b.mean / b.variance + v / (sigma * sigma)) / precision;
        b.variance = 1 / precision;
        b.observations += 1;
      }
    }
    function forecast(p) {
      const e = p.exec;
      const st = STAGES[e.key];
      const c = p.candidates[p.chosen];
      const k = e.batchCount;
      const n = e.batches.length;
      const left = k - n;
      let prob = 1;
      for (const [stat, limit] of Object.entries(st.limits)) {
        const b = c.belief[stat];
        const past = e.batches.reduce((sum, x) => sum + x.values[stat], 0);
        const mean = (past + left * b.mean) / k;
        const variance = (left / k) ** 2 * b.variance + (left * (st.noise * st.noise)) / k;
        prob *= 1 - normCdf((limit - mean) / Math.sqrt(variance));
      }
      return prob;
    }
    function chanceNow(p, key) {
      const st = STAGES[key];
      const c = p.candidates[p.chosen];
      let prob = 1;
      for (const [stat, limit] of Object.entries(st.limits)) {
        const b = c.belief[stat];
        prob *= 1 - normCdf((limit - b.mean) / Math.sqrt(b.variance + st.noise * st.noise));
      }
      return prob;
    }

    /* ----- 推进一周 ----- */
    function tick() {
      s.events = [];
      if (blocking()) return [];
      s.week += 1;
      const before = s.cash;
      s.cash -= payroll() + 4;
      for (const v of [...s.services]) {
        v.left -= 1;
        if (v.left <= 0) {
          s.cash += v.reward;
          s.services = s.services.filter((q) => q !== v);
          emit("service_completed", { actors: [v.hero], room: "room_tox", data: { name: findHero(v.hero).name, service: v.name, reward: v.reward } });
        }
      }
      const bio = s.rooms.bio;
      if (bio.building) {
        bio.building.left -= 1;
        if (bio.building.left <= 0) {
          bio.building = null;
          bio.built = true;
          emit("room_built", { room: "room_bio", data: { name: "生物实验室" } });
        }
      }
      for (const p of s.projects) {
        if (p.status !== "running" || !p.exec) continue;
        const e = p.exec;
        const st = STAGES[e.key];
        s.cash -= e.costPerWeek;
        e.elapsed += 1;
        if (st.kind === "make") {
          const due = Math.min(3, Math.floor((e.elapsed * 4) / e.weeks));
          while (e.done < due) {
            e.done += 1;
            const c = p.candidates[p.chosen];
            for (const pkg of e.plan) {
              const detail = [];
              const amounts = {};
              for (const [stat, total] of Object.entries(pkg.amounts)) {
                const delta = total / 3;
                c.truth[stat] = Math.min(98, c.truth[stat] + delta);
                c.belief[stat].mean = Math.min(98, c.belief[stat].mean + delta);
                amounts[stat] = Math.round(delta * 10) / 10;
                detail.push(`${statNames(p)[stat]} +${delta.toFixed(1)}`);
              }
              emit("work_completed", {
                actors: [pkg.actor], project: p.id, room: `room_${pkg.role}`,
                data: {
                  name: findHero(pkg.actor).name, stage: st.name, detail: detail.join("、"), amounts,
                  labels: Object.fromEntries(Object.keys(amounts).map((k) => [k, SHORT_STAT[k]])), batch: e.done,
                },
              });
            }
          }
        } else {
          const due = Math.min(4, Math.floor((e.elapsed * 4) / e.weeks));
          while (e.batches.length < due) {
            const index = e.batches.length + 1;
            const c = p.candidates[p.chosen];
            let values;
            if (p.scripted && e.key === "II") values = p.scripted[index - 2];
            if (!values) {
              values = {};
              for (const stat of Object.keys(st.limits)) values[stat] = c.truth[stat] + gauss(rnd) * e.sigma;
            }
            e.batches.push({ index, week: s.week, values });
            p.readings.push({ stage: e.key, index, week: s.week, values });
            applyBelief(p, values, e.sigma);
            emit("evidence_received", {
              actors: e.team, project: p.id, room: st.clinical ? "room_clinical" : "room_tox",
              data: {
                project: p.name, stage: st.name, batch: index, final: index === 4,
                values: Object.fromEntries(Object.entries(values).map(([k, v]) => [k, Math.round(v * 10) / 10])),
                detail: Object.entries(values).map(([k, v]) => `${SHORT_STAT[k]} ${v.toFixed(1)}`).join("、"),
              },
            });
          }
          if (st.interim && !e.interimDone && e.elapsed >= e.interimAt && e.batches.length >= 2) {
            p.status = "checkpoint";
            s.decisions.push({ id: `d-interim-${p.id}-${e.key}`, kind: "interim", project: p.id });
            continue;
          }
        }
        if (e.elapsed >= e.weeks) finish(p);
      }
      for (const d of s.products) {
        d.age += 1;
        const revenue = d.peak * Math.min(1, d.age / 16);
        d.lastProfit = revenue * d.margin;
        s.cash += d.lastProfit;
        d.total += d.lastProfit;
      }
      s.lastFlow = s.cash - before;
      return s.events.slice();
    }

    function finish(p) {
      const e = p.exec;
      const st = STAGES[e.key];
      const c = p.candidates[p.chosen];
      const values = {};
      const failures = [];
      for (const [stat, limit] of Object.entries(st.limits)) {
        let v;
        if (st.kind === "make") v = c.truth[stat] + gauss(rnd) * st.noise;
        else v = e.batches.reduce((sum, b) => sum + b.values[stat], 0) / e.batches.length;
        values[stat] = Math.round(v * 10) / 10;
        if (v < limit) failures.push(stat);
      }
      if (st.kind === "make" && Object.keys(st.limits).length) applyBelief(p, values, st.noise);
      const passed = failures.length === 0;
      p.results.push({ key: e.key, passed, values, limits: st.limits, failures, week: s.week });
      emit("phase_finished", {
        actors: e.team, project: p.id, room: st.clinical ? "room_clinical" : "room_lab",
        data: {
          project: p.name, stage: st.name, passed,
          outcome: passed ? "取得支持证据" : `未达标（${failures.map((f) => statNames(p)[f]).join("、")}）`,
        },
      });
      const lastExec = e;
      p.lastExec = lastExec;
      p.exec = null;
      p.work = [];
      if (e.key === "rework") {
        p.index = p.path.indexOf("be");
        p.status = "ready";
        s.decisions.push({ id: `d-next-${p.id}-${s.week}`, kind: "next", project: p.id });
        return;
      }
      if (!passed) {
        p.status = "failed-pending";
        s.decisions.push({ id: `d-fail-${p.id}-${s.week}`, kind: "failed", project: p.id });
        return;
      }
      if (e.key === "review") {
        p.status = "approved-pending";
        s.decisions.push({ id: `d-launch-${p.id}`, kind: "launch", project: p.id });
        return;
      }
      p.index += 1;
      p.status = "ready";
      if (p.kind === "innovative" && p.path[p.index] === "III") {
        s.decisions.push({ id: `d-license-${p.id}`, kind: "license", project: p.id });
      } else {
        s.decisions.push({ id: `d-next-${p.id}-${s.week}`, kind: "next", project: p.id });
      }
    }

    /* ----- 玩家的决定 ----- */
    function blocking() {
      return s.decisions.some((d) => !d.deferred);
    }
    function close(id) {
      s.decisions = s.decisions.filter((d) => d.id !== id);
    }
    function available() {
      return s.cash - committed();
    }
    function act(name, args = {}) {
      s.events = [];
      const d = args.decision ? s.decisions.find((q) => q.id === args.decision) : null;
      const p = args.project ? findProject(args.project) : d ? findProject(d.project) : null;
      if (name === "choose") {
        p.chosen = args.candidate;
        close(d.id);
        const { team, mode } = recommend(p, "formulation");
        startStage(p, "formulation", team, mode);
        s.cash -= 0;
        emit("decision_made", { project: p.id, data: { text: `选择${p.candidates[p.chosen].label}，开始处方与工艺` } });
      } else if (name === "next") {
        const key = p.path[p.index];
        const { team, mode } = recommend(p, key);
        close(d.id);
        startStage(p, key, team, mode);
      } else if (name === "defer") {
        d.deferred = true;
      } else if (name === "resume") {
        d.deferred = false;
      } else if (name === "interim") {
        close(d.id);
        p.exec.interimDone = true;
        if (args.choice === "stop") {
          const saved = p.exec.costPerWeek * (p.exec.weeks - p.exec.elapsed);
          p.lastExec = p.exec;
          p.exec = null;
          p.status = "stopped";
          emit("decision_made", { project: p.id, data: { text: `${p.name}期中止损，省下约 ¥${Math.round(saved)} 万` } });
        } else {
          p.status = "running";
          emit("decision_made", { project: p.id, data: { text: `${p.name}继续收集${STAGES[p.exec.key].name}剩余数据` } });
        }
      } else if (name === "rework") {
        close(d.id);
        p.repairs += 1;
        const c = p.candidates[p.chosen];
        c.truth.exposure = Math.min(98, c.truth.exposure + 4);
        c.belief.exposure.mean += 4;
        const { team, mode } = recommend(p, "rework");
        startStage(p, "rework", team, mode);
      } else if (name === "terminate") {
        close(d.id);
        p.status = "stopped";
        p.exec = null;
        emit("decision_made", { project: p.id, data: { text: `终止${p.name}，证据留档，人员空出来` } });
      } else if (name === "launch") {
        close(d.id);
        const cost = 80;
        s.cash -= cost;
        p.status = "approved";
        const c = p.candidates[p.chosen];
        const drug = {
          id: `drug-${p.id}`, name: args.name || p.name, project: p.id, age: 0, peak: 27,
          margin: Math.min(0.82, 0.46 + (c.truth.quality - 60) / 300), lastProfit: 0, total: 0,
        };
        s.products.push(drug);
        emit("product_launched", { project: p.id, data: { name: drug.name } });
      } else if (name === "license") {
        close(d.id);
        s.cash += 520;
        p.status = "licensed";
        emit("decision_made", { project: p.id, data: { text: `${p.name}授权给合作方：首付款 ¥520 万到账，后续按里程碑` } });
      } else if (name === "start_III") {
        close(d.id);
        const { team, mode } = recommend(p, "III");
        startStage(p, "III", team, mode);
      } else if (name === "build") {
        const cost = 700;
        if (available() < cost) throw new Error("扣除已承诺支出后现金不够");
        s.cash -= cost;
        s.rooms.bio.building = { left: 6, total: 6 };
        emit("room_build_started", { room: "room_bio", data: { name: "生物实验室", weeks: 6 } });
      } else if (name === "upgrade") {
        const room = s.rooms[args.room];
        const cost = [0, 800, 3000, 9000][room.level];
        if (room.level >= 3) throw new Error("已经是最高级");
        if (available() < cost) throw new Error("扣除已承诺支出后现金不够");
        s.cash -= cost;
        room.level += 1;
        emit("equipment_upgraded", {
          room: { lab: "room_proc", qc: "room_tox", clinic: "room_clinical", bio: "room_bio" }[args.room],
          data: { name: roomName(args.room), level: room.level },
        });
      }
      return s.events.slice();
    }
    function roomName(id) {
      return { lab: "化学与制剂实验室", qc: "质量与毒理室", clinic: "临床与数据办公室", bio: "生物实验室" }[id];
    }

    /* ----- 给画面和面板的数据 ----- */
    function assignments() {
      const out = {};
      for (const p of s.projects) {
        if (!p.exec || !(p.status === "running" || p.status === "checkpoint")) continue;
        const st = STAGES[p.exec.key];
        for (const id of p.exec.team) {
          const h = findHero(id);
          out[id] = { mode: st.kind, room: st.room, role: h.profession, project: p.id, members: Math.min(h.members, 2) };
        }
      }
      for (const v of s.services) out[v.hero] = { mode: "service", room: v.room, role: findHero(v.hero).profession, project: v.id, members: 0 };
      return out;
    }
    function boards() {
      const out = { clinic: [], qc: [] };
      for (const p of s.projects) {
        const e = p.exec || (p.lastExec && ["ready", "stopped", "failed-pending", "approved-pending", "approved"].includes(p.status) ? p.lastExec : null);
        if (!e) continue;
        const st = STAGES[e.key];
        if (st.kind !== "test") continue;
        const stat = Object.keys(st.limits)[0];
        const list = out[st.room];
        if (!list) continue;
        list.push({
          title: `${p.name.slice(0, 2)} · ${SHORT_STAGE[e.key] || st.name} · ${SHORT_STAT[stat]}`,
          limit: st.limits[stat], readings: e.batches.map((b) => b.values[stat]), batches: 4, live: !!p.exec,
        });
      }
      for (const k of Object.keys(out)) {
        out[k].sort((a, b) => Number(b.live) - Number(a.live));
        out[k] = out[k].slice(0, 2);
      }
      return out;
    }
    function evidence(p) {
      const c = p.chosen == null ? null : p.candidates[p.chosen];
      const names = statNames(p);
      const key = p.exec?.key || p.path[p.index];
      const limits = STAGES[key]?.limits || {};
      return c
        ? Object.entries(names).filter(([k]) => c.belief[k]).map(([k, name]) => {
            const b = c.belief[k];
            const sd = Math.sqrt(b.variance);
            return { key: k, name, mean: b.mean, low: b.mean - 1.645 * sd, high: b.mean + 1.645 * sd, limit: limits[k] ?? null };
          })
        : [];
    }
    function candidateView(p, c) {
      const names = statNames(p);
      const strict = { safety: 58, exposure: 64, quality: 65 };
      return Object.entries(names).map(([k, name]) => {
        const b = c.belief[k];
        const sd = Math.sqrt(b.variance);
        return { key: k, name, mean: b.mean, low: b.mean - 1.645 * sd, high: b.mean + 1.645 * sd, limit: strict[k] };
      });
    }
    function decisionView(d) {
      const p = findProject(d.project);
      const base = { id: d.id, kind: d.kind, project: p.id, projectName: p.name, deferred: !!d.deferred };
      if (d.kind === "choose") {
        const { team } = recommend(p, "formulation");
        return {
          ...base, title: `${p.name}：选一个候选处方`, room: "lab",
          text: "三个处方各有短板。范围越窄，说明证据越多；红线是后面要过的门槛。开发能把药做好一点，验证只会揭晓真相。",
          candidates: p.candidates.map((c, i) => ({ index: i, label: c.label, evidence: candidateView(p, c) })),
          next: `选好后直接开始处方与工艺（做）· ${team.map((id) => findHero(id).name).join("、")} · ${STAGES.formulation.weeks} 周 · ¥${STAGES.formulation.cost} 万`,
          deferrable: false,
        };
      }
      if (d.kind === "next") {
        const key = p.path[p.index];
        const st = STAGES[key];
        const { team, mode } = recommend(p, key);
        const last = p.results[p.results.length - 1];
        const plan = workPlan(p, key, team);
        const gains = plan.flatMap((pkg) => Object.entries(pkg.amounts).map(([k, v]) => `${statNames(p)[k]} +${v.toFixed(1)}`));
        return {
          ...base, title: `${p.name}：${last ? STAGES[last.key].name + (last.passed ? "通过" : "完成") : "准备就绪"}`, room: st.room,
          text: `下一步是${st.name}（${st.kind === "make" ? "做" : "测"}）。`,
          facts: [
            ["团队", team.length ? team.map((id) => `${findHero(id).name}（${SHORT[findHero(id).profession]}）`).join("、") : "无人可用"],
            ["执行", mode === "cro" ? "临床负责人正忙，交给外包 CRO（费用 +30%）" : "本公司团队"],
            ["工期与费用", `${st.weeks} 周 · ¥${Math.round(stageCost(key, mode))} 万`],
            [st.kind === "make" ? "预计开发量" : "本阶段过关估计", st.kind === "make" ? gains.join("、") || "—" : `约 ${Math.round(chanceNow(p, key) * 100)}%`],
          ],
          actions: [{ name: "next", label: `开始${st.name}`, primary: true }, { name: "defer", label: "稍后再说" }],
          deferrable: true,
        };
      }
      if (d.kind === "interim") {
        const e = p.exec;
        const st = STAGES[e.key];
        const chance = Math.round(forecast(p) * 100);
        const stats = Object.keys(st.limits);
        const rule = stats.map((k) => `${SHORT_STAT[k]} ≥ ${st.limits[k]}`).join("、");
        const rows = e.batches.map((b) => `第 ${b.index} 批：${stats.map((k) => `${SHORT_STAT[k]} ${b.values[k].toFixed(1)}`).join("、")}`);
        const remaining = Math.round(e.costPerWeek * (e.weeks - e.elapsed));
        const team = e.team.map((id) => findHero(id).name).join("和");
        return {
          ...base, title: `${p.name}：${SHORT_STAGE[e.key] || st.name}期中数据到了`, room: st.room,
          text: `门槛：${rule}（看四批的平均）。${rows.join("；")}。`,
          chance,
          facts: [
            ["按现有数据，最终过关", `约 ${chance}%`],
            ["继续还要", `${e.weeks - e.elapsed} 周 · 约 ¥${remaining} 万`],
            ["止损能省", `约 ¥${remaining} 万${team ? `，${team}空出来` : ""}`],
          ],
          actions: [
            { name: "interim", args: { choice: "keep" }, label: "继续收集剩余两批", primary: true },
            { name: "interim", args: { choice: "stop" }, label: "提前止损" },
            { name: "defer", label: "稍后再说" },
          ],
          deferrable: true,
        };
      }
      if (d.kind === "failed") {
        const last = p.results[p.results.length - 1];
        const st = STAGES[last.key];
        const parts = last.failures.map((f) => `${statNames(p)[f]} ${last.values[f]} < ${last.limits[f]}`);
        const canRework = p.kind === "generic" && p.repairs < 1;
        return {
          ...base, title: `${p.name}：${st.name}没过`, room: st.room,
          text: `${parts.join("；")}。数据会留档，刷新也不会重抽。`,
          facts: canRework ? [["补正一次", "8 周 · ¥100 万 · 改进处方，再做一次 BE"]] : [],
          actions: [
            ...(canRework ? [{ name: "rework", label: "补正后重新验证", primary: true }] : []),
            { name: "terminate", label: "终止项目", primary: !canRework },
          ],
          deferrable: false,
        };
      }
      if (d.kind === "launch") {
        return {
          ...base, title: `${p.name}：审评通过`, room: "qc",
          text: "给它起个名字吧。上市费用 ¥80 万，采用委托生产，销售会在 16 周内慢慢爬升。",
          input: { id: "drug-name", label: "药品名", value: "稳稳小药丸" },
          actions: [{ name: "launch", label: "上市", primary: true }],
          deferrable: false,
        };
      }
      if (d.kind === "license") {
        const enough = available() >= STAGES.III.cost;
        const chanceIII = chanceNow(p, "III");
        const preferLicense = !enough || chanceIII < 0.4;
        return {
          ...base, title: `${p.name}：II 期取得支持证据`, room: "clinic",
          text: "III 期要 44 周、¥1,350 万。钱不够的话，可以把它授权出去，换首付款和以后的分成。",
          facts: [
            ["III 期过关估计", `约 ${Math.round(chanceIII * 100)}%（门槛更高：疗效 ≥ 75、安全 ≥ 66）`],
            ["扣除已承诺后的现金", `¥${Math.round(available()).toLocaleString("zh-CN")} 万`],
          ],
          actions: [
            { name: "license", label: "授权：首付款 ¥520 万", primary: preferLicense },
            { name: "start_III", label: enough ? "自己做 III 期" : "自己做 III 期（现金不够）", primary: !preferLicense, disabled: !enough },
            { name: "defer", label: "稍后再说" },
          ],
          deferrable: true,
        };
      }
      return base;
    }
    function heroView(h) {
      const job = assignments()[h.id];
      const p = job && findProject(job.project);
      const task = job
        ? job.mode === "service"
          ? `技术服务 · ${s.services.find((v) => v.hero === h.id)?.name}`
          : `${p.name} · ${STAGES[p.exec.key].name}（${STAGES[p.exec.key].kind === "make" ? "做" : "测"}）`
        : "空闲";
      return {
        ...h, professionName: PROFESSIONS[h.profession], short: SHORT[h.profession], rankName: RANKS[h.rank],
        task, mode: job?.mode || "idle",
      };
    }
    function projectView(p) {
      const e = p.exec;
      const st = e ? STAGES[e.key] : null;
      const statusText = {
        selecting: "等你选候选", running: "进行中", checkpoint: "期中决定", ready: "等安排下一阶段", stopped: "已止损",
        "failed-pending": "没通过", "approved-pending": "等上市", approved: "已上市", licensed: "已授权",
      }[p.status];
      return {
        id: p.id, name: p.name, kind: p.kind, kindName: p.kindName, combo: p.combo, status: p.status, statusText,
        path: p.path.map((k, i) => ({
          key: k, name: STAGES[k]?.name || { optimize: "分子优化", preclinical: "临床前与申报准备", I: "I 期安全与剂量" }[k], kind: STAGES[k]?.kind || (k === "optimize" ? "make" : "test"),
          state: i < p.index ? "done" : i === p.index ? (p.status === "approved" ? "done" : "current") : "todo",
        })),
        stage: st ? { key: e.key, name: st.name, kind: st.kind, weeks: e.weeks, elapsed: e.elapsed, mode: e.mode, team: e.team.map((id) => findHero(id).name), batches: st.kind === "make" ? e.done : e.batches.length, batchCount: e.batchCount } : null,
        evidence: evidence(p),
        readings: p.readings.slice(-8),
        work: e?.plan || [],
        chosen: p.chosen == null ? null : p.candidates[p.chosen].label,
        statNames: statNames(p),
      };
    }

    function view() {
      const product = s.products[0];
      return {
        week: s.week,
        date: `第 ${Math.floor(s.week / 48) + 1} 年 · 第 ${(s.week % 48) + 1} 周`,
        cash: s.cash,
        available: available(),
        flow: s.lastFlow,
        payroll: payroll() + 4,
        heroes: s.heroes.map(heroView),
        assignments: assignments(),
        rooms: JSON.parse(JSON.stringify(s.rooms)),
        boards: boards(),
        cro: s.projects.some((p) => p.exec && p.exec.mode === "cro" && (p.status === "running" || p.status === "checkpoint")),
        projects: s.projects.map(projectView),
        services: s.services.map((v) => ({ ...v, heroName: findHero(v.hero).name })),
        products: s.products.map((d) => ({ ...d })),
        decisions: s.decisions.map(decisionView),
        blocking: blocking(),
        product,
      };
    }

    return { tick, act, view, rooms: { upgradeCost: (lvl) => [0, 800, 3000, 9000][lvl] } };
  }

  window.DrugstoryDemo = { create, STAGES, PROFESSIONS };
})();
