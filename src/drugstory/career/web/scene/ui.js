/* 场景外壳：时间、面板路由、底部人物栏、提示。决定和表单都走 app.js 的命令与 ApiDriver。
 * 时间：玩家选的速度一直保留；遇到待决定、打开弹窗、切到后台时停住，处理完自动接着走。 */
(() => {
  let renderer,
    world,
    want = 0, // 玩家选的速度，0 是暂停
    accumulator = 0,
    route = { type: "tab" },
    cursor = null,
    lastRevision = null,
    lastIdentity = null,
    lastPendingKey = "",
    panelHtml = "",
    panelRoute = "",
    panelDeferred = false,
    forceNext = false,
    lastCash = null;
  const q = (s) => document.querySelector(s);
  const P = () => window.DrugstoryPanels;
  const names = {
    lab: "化学与制剂实验室",
    qc: "质量与毒理室",
    clinic: "临床与数据办公室",
    bio: "生物实验室",
    academy: "共研教室",
    hall: "大会与荣誉室",
  };
  const TABS = {
    pipeline: () => P().desk(),
    characters: () => P().team(),
    services: () => P().services(),
    market: () => market(),
    competition: () => competitionView(),
    honors: () => honorsView(),
    journal: () => journal(),
  };

  /* ---------- 时间 ---------- */
  function held() {
    return (
      !state ||
      document.hidden ||
      requestBusy ||
      driver.busy ||
      driver.uncertain ||
      q("#modal").open ||
      DrugstoryWorld.blocked(state)
    );
  }
  function setWant(k) {
    want = k;
    accumulator = 0;
    renderer?.setSpeed(k || 1);
    clock();
  }
  function pause() {
    setWant(0);
  }
  function clock() {
    for (const el of document.querySelectorAll("[data-speed]"))
      el.setAttribute("aria-pressed", String(+el.dataset.speed === want));
    const status = q("#clock-status");
    if (!status) return;
    let text = "已暂停",
      cls = "";
    if (!state) text = "连接中";
    else if (state.game_over) (text = "已停业"), (cls = "bad");
    else if (driver.uncertain) (text = "请重新连接"), (cls = "bad");
    else if (state.pending) (text = `等你决定 · ${state.pending}`), (cls = "wait");
    else if (want) (text = `${want}× 进行中`), (cls = "run");
    status.textContent = text;
    status.className = cls;
  }
  function frame(dt) {
    if (!want || held()) {
      accumulator = 0;
      return;
    }
    accumulator += dt;
    if (accumulator >= 1.6 / want) {
      accumulator = 0;
      send("advance", { weeks: 1 });
    }
  }

  /* ---------- 渲染 ---------- */
  function select(hit) {
    if (!hit) return;
    route = hit;
    renderer.select(hit.type === "tab" || hit.type === "new" ? null : hit);
    if (hit.type === "project") activeTab = "pipeline";
    if (hit.type === "hero") activeTab = "characters";
    renderPanel(true);
    updateDock();
  }
  function render(s) {
    if (!renderer)
      renderer = DrugstoryScene.create(q("#scene-canvas"), {
        onSelect: select,
        onLayout: labels,
        onFrame: frame,
      });
    const identity = `${s.token}:${s.scenario}`;
    if (
      identity !== lastIdentity ||
      (lastRevision !== null && s.revision < lastRevision) ||
      s.event_cursor < (cursor || 0)
    ) {
      cursor = s.event_cursor;
      route = { type: "tab" };
      lastPendingKey = "";
      pause();
      lastIdentity = identity;
    }
    const recent = [...s.events, ...s.transition_events].filter(
      (e, i, a) =>
        e.id > (cursor ?? s.event_cursor) &&
        a.findIndex((t) => t.id === e.id) === i,
    );
    world = DrugstoryWorld.world(s, staticContent);
    renderer.setWorld(world);
    for (const ev of merged(recent))
      renderer.event({ ...ev, data: { ...ev.data, labels: s.stats } });
    cursor = s.event_cursor;
    toasts(recent);
    // 新的待决定出现：面板切到研发，决定卡在最上面
    const waiting = P().waiting().filter((p) => !p.deferred);
    const waitingKey = waiting
      .map((p) => `${p.id}:${p.key}:${p.status}`)
      .join("|");
    let force = forceNext;
    if (waitingKey && waitingKey !== lastPendingKey) {
      const stillThere =
        route.type === "project" && waiting.some((p) => p.id === route.id);
      if (!stillThere) {
        route = { type: "tab" };
        activeTab = "pipeline";
        renderer.select(null);
      }
      force = true;
    }
    lastPendingKey = waitingKey;
    forceNext = false;
    // 第一次出现的成长机会：停一下，让玩家看到引导条上的按钮
    if (want && recent.some((e) => e.type === "growth_ready")) pause();
    // 现金转负时自动暂停，给玩家三个月的应对时间
    if (s.cash < 0 && lastCash !== null && lastCash >= 0 && want) {
      pause();
      notice("现金转负了，时间已暂停。连续三个月月底为负会停业。", true);
    }
    lastCash = s.cash;
    metrics(s);
    q("#scene-goal").innerHTML = guide(s);
    q("#scene-journal").innerHTML = s.journal
      .slice(-14)
      .reverse()
      .map(
        (e) =>
          `<li><small>第 ${e.week} 周</small><span>${esc(e.text)}</span></li>`,
      )
      .join("");
    updateSheet();
    renderPanel(force);
    lastRevision = s.revision;
    updateDock();
    labels();
    clock();
  }
  function metrics(s) {
    const flow = s.weekly_profit + s.weekly_royalty - s.costs_per_week;
    q("#scene-metrics").innerHTML =
      `<span class="m-date"><small>${esc(s.date)}</small><b>第 ${s.week} 周</b></span><span title="现金；「可用」是扣掉已安排的花费以后还能动用的"><small>现金</small><b>${money(s.cash)}</b>${s.committed > 0 ? `<em>可用 ${num(s.available_cash)}</em>` : ""}</span><span title="产品利润与分成减去工资、租金和在研费用"><small>每周</small><b class="${flow >= 0 ? "pos" : "neg"}">${flow >= 0 ? "+" : "−"}${num(Math.abs(flow))} 万</b></span><span title="含成员共 ${s.headcount} 人 · 研究所能容纳 ${s.facility.capacity} 人"><small>伙伴</small><b>${s.heroes.length}</b></span><button class="m-grade" data-scene="rating" title="研究所评级：点开看五项分数和怎么涨分"><small>${s.rating.final ? "任期评级" : s.rating.early ? "评级" : "预计评级"}</small><b class="grade-${s.rating.early ? "early" : (s.rating.final || s.rating.projected).grade}">${s.rating.early ? "起步" : (s.rating.final || s.rating.projected).grade}</b></button>`;
  }
  // 跳过几周时，同一个人的多批开发合成一条飘字，同一项目只显示最后一批数据
  function merged(events) {
    const out = [],
      work = new Map(),
      batch = new Map();
    for (const e of events) {
      if (e.type === "work_completed" && e.actors?.length === 1) {
        const prior = work.get(e.actors[0]);
        if (prior) {
          for (const [k, v] of Object.entries(e.data.amounts || {}))
            prior.data.amounts[k] = (prior.data.amounts[k] || 0) + v;
          continue;
        }
        const copy = { ...e, data: { ...e.data, amounts: { ...(e.data.amounts || {}) } } };
        work.set(e.actors[0], copy);
        out.push(copy);
        continue;
      }
      if (e.type === "evidence_received") {
        const key = e.project ?? e.room;
        if (batch.has(key)) out[batch.get(key)] = null;
        batch.set(key, out.length);
      }
      out.push(e);
    }
    return out.filter(Boolean);
  }
  const TOAST_TYPES = {
    product_launched: ["上市", "big"],
    patent_granted: ["专利授权", ""],
    patent_expired: ["专利到期", "warn"],
    milestone_reached: ["大事记", "big"],
    character_promoted: ["晋阶", ""],
    personal_completed: ["课题完成", ""],
    service_completed: ["服务回款", "money"],
    deal_signed: ["授权签约", "big"],
    award_won: ["年度获奖", "big"],
    legacy_reached: ["终局荣誉", "big"],
    chapter_completed: ["章节完成", "big"],
    bounty_offered: ["患者来信", ""],
    bounty_completed: ["委托完成", "big"],
    term_ended: ["任期结束", "big"],
    facility_upgraded: ["扩建落成", ""],
    phase_finished: ["阶段结果", ""],
    growth_ready: ["可以做了", "big"],
    goal_completed: ["年度目标完成", "big"],
  };
  function toasts(recent) {
    const box = q("#scene-toasts");
    for (const e of recent) {
      const kind = TOAST_TYPES[e.type];
      if (!kind) continue;
      let text = e.data.name || "";
      if (e.type === "milestone_reached") text = e.data.title;
      if (e.type === "service_completed")
        text = `${e.data.name} · +${money(e.data.reward)}`;
      if (e.type === "character_promoted")
        text = `${e.data.name} 晋升${e.data.rank}`;
      if (e.type === "growth_ready" || e.type === "goal_completed") text = e.data.title;
      if (e.type === "phase_finished")
        text = `${e.data.name} · ${e.data.stage}${e.data.passed ? "通过" : "未通过"}`;
      const el = document.createElement("div");
      el.className = `toast ${kind[1]} ${e.type === "phase_finished" && !e.data.passed ? "warn" : ""}`;
      el.innerHTML = `<small>${esc(kind[0])}</small><b>${esc(text)}</b>`;
      box.prepend(el);
      setTimeout(() => el.classList.add("out"), 4200);
      setTimeout(() => el.remove(), 4800);
    }
    while (box.children.length > 4) box.lastChild.remove();
  }
  function guide(s) {
    const w = P().waiting();
    const live = w.filter((p) => !p.deferred);
    if (s.game_over)
      return '<span class="g-bad">研究所停业了。记录都在「复盘」里，可以备份后重开。</span>';
    if (live.length)
      return `<button data-scene-project="${live[0].id}" class="g-wait"><b>${live.length > 1 ? `${live.length} 件事等你决定` : esc(live[0].name)}</b><span>${live.length > 1 ? "在右侧依次处理" : esc(live[0].status_name)}</span></button>`;
    if (s.cash < 0)
      return `<button data-tab="services" class="g-bad-btn"><b>现金为负${s.negative_months ? ` · 已 ${s.negative_months} 个月` : ""}</b><span>连续三个月月底为负会停业：接服务、止损花钱的项目、减少成员</span></button>`;
    if (s.runway !== null && s.runway < 16)
      return `<button data-tab="services" class="g-bad-btn"><b>现金只够撑 ${s.runway} 周</b><span>接技术服务、暂缓花钱的阶段，或减少团队成员</span></button>`;
    const resumable = w.find((p) => p.deferred && p.quick?.ok);
    if (resumable)
      return `<button data-scene-project="${resumable.id}" class="g-wait"><b>${esc(resumable.name)}</b><span>${resumable.quick.command === "launch" ? "可以上市了" : "人空出来了，可以开工"}</span></button>`;
    if (!s.projects.length)
      return '<button data-np-open data-np-route="generic" class="g-go"><b>第一步</b><span>点这里，开始第一个项目（推荐「稳压片」）</span></button>';
    // 年度目标：还没选就提醒去选；选了就显示进度
    const y = s.year_goal;
    if (y?.offers?.length)
      return `<button data-modal="goals" class="g-chapter"><b>选一个今年的目标</b><span>${y.offers.map((g) => esc(g.title)).join(" / ")}</span></button>`;
    // 成长建议：跟着章节走，按钮直接执行（晋阶、扩建、邀请……）
    const tip = (s.guide || []).find((g) => g.ok || g.chapter);
    if (tip && (tip.ok || !want)) return guideButton(tip, tip.chapter ? "g-chapter" : "g-tip");
    if (!want && !s.pending)
      return `<button data-speed="1" class="g-go"><b>▶ 开始</b><span>按 1× 让时间走起来；有决定会自动停</span></button>`;
    const goal = s.year_goal?.current;
    if (goal && !goal.done)
      return `<button data-modal="goals" class="g-tip"><b>今年目标：${esc(goal.title)}${goal.progress ? `（${Math.min(goal.progress[0], goal.progress[1])}/${goal.progress[1]}）` : ""}</b><span>${esc(goal.text)}</span></button>`;
    const ch = s.chapters.current;
    if (ch)
      return `<button data-scene="chapters" class="g-chapter"><b>第 ${ch.index} 章 · ${esc(ch.name)}</b><span>目标：${esc(ch.goal)}${ch.reward ? ` · 奖励 ¥${ch.reward} 万` : ""}</span></button>`;
    return "";
  }
  // 一条成长建议变成一个按钮：有命令就直接执行，否则打开对应的地方
  function guideButton(g, cls) {
    const attrs =
      g.command && g.ok
        ? `data-command="${esc(g.command)}" data-args="${esc(JSON.stringify(g.args))}"`
        : g.kind === "project"
          ? `data-np-open data-np-route="${esc(g.route || "")}"${g.catalog ? ` data-np-catalog="${esc(g.catalog)}"` : ""}`
          : g.hero
            ? `data-scene-hero="${esc(g.hero)}"`
            : g.tab
              ? `data-tab="${esc(g.tab)}"`
              : g.command === "upgrade"
                ? 'data-tab="characters"'
                : "";
    return `<button class="${cls}" ${attrs} title="${esc(g.ok ? "" : g.error || "")}"><b>${esc(g.title)}</b><span>${esc(g.text)}</span></button>`;
  }
  function roomSummary(id) {
    const team = state.heroes.filter(
      (h) => h.activity !== "idle" && world.locate(h.room) === id,
    );
    const remote =
      id === "clinic"
        ? state.projects.filter((p) => p.scene.executor === "cro")
        : [];
    if (!world.rooms[id]?.built) return "扩建后开放";
    return (
      [
        team.length ? `${team.length} 人在忙` : "",
        remote.length ? `CRO ${remote.length}` : "",
      ]
        .filter(Boolean)
        .join(" · ") || "空闲"
    );
  }
  function labels() {
    if (!renderer || !world) return;
    const box = q("#room-labels"),
      live = new Set(renderer.rooms.map((r) => r.id));
    for (const el of [...box.children])
      if (!live.has(el.dataset.room)) el.remove();
    const pendingRooms = new Set(
      P()
        .waiting()
        .filter((p) => !p.deferred)
        .map((p) => world.locate(p.scene.room)),
    );
    for (const r of renderer.rooms) {
      let el = box.querySelector(`[data-room="${r.id}"]`);
      if (!el) {
        el = document.createElement("button");
        el.dataset.room = r.id;
        el.className = "room-label";
        el.innerHTML = "<b></b><small></small>";
        el.addEventListener("click", () => select({ type: "room", id: r.id }));
        box.append(el);
      }
      el.querySelector("b").textContent = names[r.id];
      el.querySelector("small").textContent = roomSummary(r.id);
      el.classList.toggle("pending", pendingRooms.has(r.id));
      el.classList.toggle("locked", !world.rooms[r.id]?.built);
      const pt = renderer.anchor("room", r.id);
      if (!pt) continue;
      const rect = box.getBoundingClientRect(),
        w = el.offsetWidth,
        h = el.offsetHeight;
      el.style.left = `${Math.max(w / 2 + 6, Math.min(rect.width - w / 2 - 6, pt.x))}px`;
      el.style.top = `${Math.max(56 + h / 2, Math.min(rect.height - 96 - h / 2, pt.y))}px`;
    }
  }

  /* ---------- 底部人物栏与项目栏 ---------- */
  function updateDock() {
    const people = q("#scene-people");
    const ids = state.heroes.map((h) => h.id).join("|");
    if (people.dataset.ids !== ids) {
      people.dataset.ids = ids;
      people.innerHTML = state.heroes
        .map(
          (h) =>
            `<button class="chip" data-scene-hero="${h.id}"><canvas class="scene-portrait" data-portrait="${h.id}" aria-hidden="true"></canvas><span><b></b><small></small></span><i class="badge" hidden>可晋阶</i></button>`,
        )
        .join("");
      for (const h of state.heroes)
        renderer.drawPortrait(
          people.querySelector(`[data-portrait="${h.id}"]`),
          h.look,
        );
    }
    for (const h of state.heroes) {
      const el = people.querySelector(`[data-scene-hero="${h.id}"]`);
      el.querySelector("b").textContent = h.name;
      el.querySelector("small").textContent = h.busy
        ? h.busy
        : `空闲 · ${h.profession_name.slice(0, 2)} ${h.ability}`;
      el.classList.toggle("idle", !h.busy);
      el.classList.toggle("busy", !!h.busy);
      el.querySelector(".badge").hidden = !(
        h.rank < 4 && h.promotion.every((c) => c.ok)
      );
      el.setAttribute(
        "aria-pressed",
        String(route.type === "hero" && route.id === h.id),
      );
    }
    const projects = q("#scene-projects");
    const active = state.projects.filter((p) => p.active);
    const keys = active.map((p) => p.id).join("|");
    if (projects.dataset.ids !== keys) {
      projects.dataset.ids = keys;
      projects.innerHTML = active
        .map(
          (p) =>
            `<button class="chip proj" data-scene-project="${p.id}"><b></b><small></small><span class="progress"><i></i></span></button>`,
        )
        .join("");
    }
    // 场景按底部人物栏的实际高度留白，房间不被挡住
    renderer.setInsets(54, q(".dock").offsetHeight + 16);
    for (const p of active) {
      const el = projects.querySelector(`[data-scene-project="${p.id}"]`);
      const deciding =
        !p.autopilot && ["selecting", "ready", "result", "problem", "checkpoint"].includes(p.status);
      el.querySelector("b").textContent = p.name;
      el.querySelector("small").textContent = deciding
        ? p.deferred
          ? p.quick?.ok
            ? "可以开工"
            : "已暂缓"
          : "等你决定"
        : p.autopilot && p.waiting
          ? p.waiting
          : `${p.autopilot ? "自主 · " : ""}${p.status === "screening" ? "筛选" : p.phase} · 剩 ${p.left} 周`;
      el.classList.toggle("deciding", deciding && !p.deferred);
      el.querySelector(".progress i").style.width =
        `${Math.round((p.scene.elapsed / (p.scene.total || 1)) * 100)}%`;
      el.setAttribute(
        "aria-pressed",
        String(route.type === "project" && route.id === p.id),
      );
    }
  }

  /* ---------- 手机：等你决定的卡片压在场景上 ---------- */
  const phone = matchMedia("(max-width: 700px)");
  let sheetOpen = true,
    sheetKey = "";
  function updateSheet() {
    const box = q("#sheet");
    const live = P().waiting().filter((p) => !p.deferred);
    const p = phone.matches && !state.game_over ? live[0] : null;
    P().sheet.id = p ? p.id : null;
    document.body.classList.toggle("has-sheet", !!p);
    if (!p) {
      box.hidden = true;
      box.innerHTML = "";
      sheetKey = "";
      return;
    }
    const key = `${p.id}:${p.status}:${p.key}`;
    if (key !== sheetKey) sheetOpen = true; // 新的决定：展开
    sheetKey = key;
    box.hidden = false;
    box.classList.toggle("closed", !sheetOpen);
    const head = `<button class="sheet-handle" data-sheet-toggle><b>等你决定 · ${live.length}</b><span>${sheetOpen ? "收起" : `${esc(p.name)} · ${esc(p.status_name)} · 展开`}</span></button>`;
    box.innerHTML = head + (sheetOpen ? P().decisionCard(p) : "");
  }
  phone.addEventListener?.("change", () => state && (updateSheet(), renderPanel(true)));

  /* ---------- 右侧面板 ---------- */
  function content() {
    if (route.type === "project") {
      const p = state.projects.find((p) => p.id === route.id);
      if (p) return P().project(p);
    }
    if (route.type === "hero") {
      const h = state.heroes.find((h) => h.id === route.id);
      if (h) return P().hero(h);
    }
    if (route.type === "room")
      return P().room(
        route.id,
        names,
        roomSummary(route.id),
        !!world.rooms[route.id]?.built,
      );
    if (route.type === "new") return P().newProject();
    route = { type: "tab" };
    return (TABS[activeTab] || TABS.pipeline)();
  }
  function renderPanel(force = false) {
    if (!state) return;
    const box = q("#app");
    const html = `${state.game_over ? '<p class="banner bad">公司已停业。可以查看记录，或在「复盘」里备份后开新公司。</p>' : ""}${content()}`;
    const key = JSON.stringify(route) + activeTab;
    if (!force && html === panelHtml) return;
    // 玩家正在面板里操作（悬停、输入、下拉）时先不重画，离开后再补上
    const busyHere =
      box.matches(":hover") ||
      (box.contains(document.activeElement) &&
        document.activeElement.matches("input,select,textarea"));
    if (!force && busyHere && key === panelRoute) {
      panelDeferred = true;
      return;
    }
    const keepScroll = key === panelRoute ? box.scrollTop : 0;
    panelHtml = html;
    panelRoute = key;
    panelDeferred = false;
    box.innerHTML = html;
    box.scrollTop = keepScroll;
    for (const el of box.querySelectorAll("canvas[data-portrait]")) {
      const h = state.heroes.find((h) => h.id === el.dataset.portrait);
      if (h) renderer.drawPortrait(el, h.look);
    }
    for (const el of document.querySelectorAll(".tabs [data-tab]"))
      el.setAttribute(
        "aria-current",
        String(route.type === "tab" && el.dataset.tab === activeTab),
      );
    const counts = {
      pipeline: P()
        .waiting()
        .filter((p) => !p.deferred || p.quick?.ok).length,
      services: Object.values(state.assist.services).filter((v) => v.hero)
        .length,
      characters: state.heroes.filter(
        (h) => h.rank < 4 && h.promotion.every((c) => c.ok),
      ).length,
    };
    for (const [tab, n] of Object.entries(counts)) {
      const el = document.querySelector(`.tabs [data-tab="${tab}"] i`);
      if (el) {
        el.textContent = n || "";
        el.hidden = !n;
      }
    }
  }

  /* ---------- 弹窗：图鉴、帮助 ---------- */
  function gallery() {
    q("#modal-body").innerHTML =
      `<h2 id="modal-title">伙伴图鉴 · 21 位研究者</h2><button data-close class="modal-close" aria-label="关闭弹窗">×</button><p class="sub">从见习到传奇。点人物看背景、招牌能力和加入条件。</p><div class="gallery-grid">${staticContent.roster.map((h) => `<button data-cast="${h.key}"><canvas data-cast-portrait="${h.key}" aria-hidden="true"></canvas><b>${esc(h.name)}</b><span>「${esc(h.nickname)}」</span><small>${state.heroes.some((p) => p.id === h.key) ? "已加入" : ["", "见习", "精英", "大师", "传奇"][h.tier]}</small></button>`).join("")}</div>`;
    if (!q("#modal").open) q("#modal").showModal();
    for (const el of document.querySelectorAll("[data-cast-portrait]"))
      renderer.drawPortrait(
        el,
        staticContent.roster.find((h) => h.key === el.dataset.castPortrait)
          .look,
        true,
      );
  }
  function cast(id) {
    if (state.heroes.some((h) => h.id === id)) {
      q("#modal").close();
      select({ type: "hero", id });
      return;
    }
    const spec = staticContent.roster.find((h) => h.key === id),
      recruit = state.roster.find((h) => h.key === id);
    q("#modal-body").innerHTML =
      `<button data-close class="modal-close" aria-label="关闭弹窗">×</button><div class="cast-head"><canvas data-cast-portrait="${id}" aria-hidden="true"></canvas><div><h2 id="modal-title">${esc(spec.name)}<small>「${esc(spec.nickname)}」</small></h2><p class="sub">${esc(recruit?.rank_name || "")} · ${esc(recruit?.profession_name || "")} · 能力 ${recruit?.ability ?? ""}</p></div></div><p>${esc(spec.bio)}</p>${recruit ? `<p><b>${esc(recruit.trait.name)}</b> · ${esc(recruit.trait.description)}</p><p>${checks(recruit.requirements)}</p><p class="sub">加入后每周工资约 ${money(recruit.weekly_salary)}（含 2 名成员）。现在每周净${state.weekly_profit + state.weekly_royalty - state.costs_per_week >= 0 ? "收入" : "支出"} ${money(Math.abs(state.weekly_profit + state.weekly_royalty - state.costs_per_week))}。</p><div class="form-actions">${recruit.tier >= 3 && !recruit.connected ? `<button data-modal="collaborate" data-id="${id}" ${recruit.unlocked && !recruit.connecting ? "" : "disabled"}>${recruit.connecting ? "合作课题进行中" : "先做合作课题 · ¥120 万"}</button>` : button("邀请加入 · " + money(recruit.cost), "hire", { character: id }, "primary", !recruit.unlocked || recruit.cost > state.available_cash)}<button data-scene="gallery">← 全部伙伴</button></div>` : ""}`;
    renderer.drawPortrait(
      q(`[data-cast-portrait="${id}"]`),
      spec.look,
      true,
    );
  }
  function help() {
    q("#modal-body").innerHTML =
      '<h2 id="modal-title">怎么玩</h2><button data-close class="modal-close" aria-label="关闭弹窗">×</button><ol class="help"><li><b>开项目：</b>右侧「＋ 新项目」，选一张卡点「开始筛选」。新手推荐「稳压片」。</li><li><b>让时间走：</b>点 ▶ 1×、2×、4×。有决定会自动停，决定完自动继续。⏭ 直接跳到下一件需要你的事。</li><li><b>做决定：</b>决定卡上的大按钮就是推荐方案，周数、费用和成功率都写在上面，点一下就开工。想换人、换方案点「调整方案」。</li><li><b>看画面：</b>橙色数字是开发（让药变好），蓝色是验证（看清药有多好）。</li><li><b>赚周转金：</b>「服务」里每单一键接下，默认派能力最低的合格伙伴。</li><li><b>养人和扩建：</b>点人物晋阶、培训；点房间升级设备、扩建研究所。</li></ol><p class="sub">快捷键：空格 暂停/继续 · 1 2 3 切换速度 · N 下一件事 · 回车 执行推荐方案</p><button data-close class="primary">开始经营</button>';
    if (!q("#modal").open) q("#modal").showModal();
  }

  /* ---------- 输入 ---------- */
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b || (!state && b.dataset.scene !== "reconnect")) return;
    if (b.dataset.command) forceNext = true;
    if (b.dataset.tab) {
      route = { type: "tab" };
      renderer.select(null);
      forceNext = true;
      setTimeout(() => renderPanel(true));
    }
    if (b.dataset.speed !== undefined) {
      const k = +b.dataset.speed;
      if (k && (driver.uncertain || state.game_over)) {
        notice(
          driver.uncertain
            ? "请先重新连接，确认上次操作的保存结果。"
            : "公司已停业，可在复盘查看记录。",
        );
        return;
      }
      setWant(k);
      if (k && state.pending) notice("先处理右侧的决定，时间会自动继续。");
      q("#scene-goal").innerHTML = guide(state);
    }
    if (b.dataset.sceneHero) select({ type: "hero", id: b.dataset.sceneHero });
    if (b.dataset.sceneProject)
      select({ type: "project", id: b.dataset.sceneProject });
    if (b.dataset.cast) cast(b.dataset.cast);
    if (b.dataset.npOpen !== undefined) {
      // 重新打开时重挑第一个可开始的品种：上次选中的那个多半已经在研或在售，开始按钮会是灰的。
      // 没指定路线时，选第一条有可开始项目的路线（仿制 → 改良 → 创新）。
      P().np.pick = null;
      P().np.route = b.dataset.npRoute || P().firstRoute();
      if (b.dataset.npCatalog) {
        // 引导推荐了具体路线：直接打开那种病、选中那条路线
        const c = state.catalog.find((x) => x.key === b.dataset.npCatalog);
        Object.assign(P().np, { custom: false, disease: c?.target_id || null, pick: b.dataset.npCatalog });
      }
      select({ type: "new" });
    } else if (b.dataset.npRoute) {
      P().np.route = b.dataset.npRoute;
      renderPanel(true);
    }
    if (b.dataset.npDisease !== undefined) {
      P().np.disease = b.dataset.npDisease || null;
      P().np.pick = null;
      renderPanel(true);
    }
    if (b.dataset.npCustom !== undefined) {
      P().np.custom = b.dataset.npCustom !== "0";
      P().np.pick = null;
      renderPanel(true);
    }
    if (b.dataset.npPick) {
      P().np.pick = b.dataset.npPick;
      renderPanel(true);
    }
    if (b.dataset.serviceTake) {
      const pick = q(`[data-service-pick="${b.dataset.serviceTake}"]`);
      forceNext = true;
      await send("take_service", {
        order: b.dataset.serviceTake,
        character: pick.value,
      });
    }
    if (b.dataset.servicesAll !== undefined) {
      forceNext = true;
      await send("take_services", { assignments: P().serviceAssignments() });
    }
    if (b.dataset.launch) {
      const name = q(`[data-launch-name="${b.dataset.launch}"]`);
      forceNext = true;
      await send("launch", {
        project: b.dataset.launch,
        name: (name?.value || "").trim(),
      });
    }
    if (b.dataset.scene === "overview") {
      route = { type: "tab" };
      renderer.select(null);
      renderPanel(true);
      updateDock();
    }
    if (b.dataset.scene === "gallery") gallery();
    if (b.dataset.scene === "help") help();
    if (b.dataset.scene === "rating") showModal("rating");
    if (b.dataset.sheetToggle !== undefined) {
      sheetOpen = !sheetOpen;
      updateSheet();
    }
    if (b.dataset.scene === "numbers") {
      P().toggleNumbers();
      b.textContent = P().numbersOn() ? "隐藏数字" : "显示数字";
      renderPanel(true);
    }
    if (b.dataset.scene === "chapters") showModal("chapters");
    if (b.dataset.scene === "next") {
      forceNext = true;
      await send("next_event", { batches: 0 });
    }
    if (b.dataset.scene === "reconnect") {
      if (requestBusy) return;
      requestBusy = true;
      try {
        const data = await driver.connect();
        staticContent = driver.content;
        state = hydrate(data);
        cursor = state.event_cursor;
        lastRevision = null;
        route = { type: "tab" };
        q("#modal").close();
        render(state);
        notice("已重新载入存档，请确认进度后继续。");
      } catch (error) {
        notice(error.message, true);
      } finally {
        requestBusy = false;
      }
    }
  });
  document.addEventListener("change", (e) => {
    if (e.target.matches("[data-pace]")) {
      P().handover.mode = e.target.value;
      renderPanel(true);
    }
    if (e.target.matches("[data-np-target]")) {
      P().np.target = e.target.value;
      P().np.pick = null;
      renderPanel(true);
    }
  });
  document.addEventListener("submit", (e) => {
    const form = e.target.closest("form[data-np-form]");
    if (!form) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    forceNext = true;
    route = { type: "tab" };
    activeTab = "pipeline";
    send("start_project", P().newProjectArgs(form, e.submitter));
  }, true);
  q("#app").addEventListener("pointerleave", () => {
    if (panelDeferred) renderPanel();
  });
  document.addEventListener("focusout", () => {
    if (panelDeferred) setTimeout(() => renderPanel());
  });
  document.addEventListener("visibilitychange", clock);
  q("#modal").addEventListener("close", clock);
  document.addEventListener("keydown", (e) => {
    if (
      !state ||
      e.target.closest("input,select,textarea") ||
      q("#modal").open ||
      e.metaKey ||
      e.ctrlKey ||
      e.altKey
    )
      return;
    if (e.code === "Space") {
      e.preventDefault();
      setWant(want ? 0 : 1);
    } else if (["Digit1", "Digit2", "Digit3"].includes(e.code)) {
      setWant({ Digit1: 1, Digit2: 2, Digit3: 4 }[e.code]);
    } else if (e.code === "Enter" || e.code === "NumpadEnter") {
      // 回车：执行第一张决定卡上的推荐方案
      if (e.target.closest("button,a,summary")) return;
      const p = P().waiting().find((x) => !x.deferred);
      if (!p?.quick?.ok) return;
      e.preventDefault();
      forceNext = true;
      send(p.quick.command, p.quick.args);
    } else if (e.code === "KeyN" && !state.pending && !state.game_over) {
      forceNext = true;
      send("next_event", { batches: 0 });
    } else return;
    q("#scene-goal").innerHTML = guide(state);
  });
  window.DrugstorySceneUI = { render, pause, guideButton };
})();
