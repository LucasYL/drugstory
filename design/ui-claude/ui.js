/* 新药物语 · 一屏研究所：界面层。
 * 时间、面板、决定卡片和底栏都在这里。场景只读数据、只发事件，规则一律交给驱动（这里是 sim.js）。 */
(() => {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const esc = (v) =>
    String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const money = (v) => `¥${Math.round(v).toLocaleString("zh-CN")} 万`;
  const signed = (v) => `${v >= 0 ? "+" : "−"}¥${Math.abs(Math.round(v)).toLocaleString("zh-CN")} 万`;
  const SECONDS_PER_WEEK = 0.8;
  const KIND = { make: "做", test: "测" };

  const sim = window.DrugstoryDemo.create(7);
  let view = sim.view();
  let speed = 1;
  let acc = 0;
  let selection = null;
  let modalId = null;
  const ticker = [];

  const canvas = $("#canvas");
  const labels = $("#labels");
  const modal = $("#modal");
  const panel = $("#panel");
  const scene = window.DrugstoryScene.create(canvas, {
    onSelect: (hit) => select(hit),
    onLayout: () => placeOverlays(),
    onFrame: (dt) => frame(dt),
  });

  /* ---------- 时间 ---------- */
  function frame(dt) {
    if (speed > 0 && !view.blocking && !touring && $("#gallery").hidden) {
      acc += dt;
      const spw = SECONDS_PER_WEEK / speed;
      if (acc >= spw) {
        acc -= spw;
        refresh(sim.tick());
      }
    } else {
      acc = 0;
    }
  }
  function setSpeed(k) {
    speed = k;
    scene.setSpeed(k || 1);
    for (const b of document.querySelectorAll("[data-speed]")) b.setAttribute("aria-pressed", String(Number(b.dataset.speed) === k));
    renderClock();
  }

  /* ---------- 刷新 ---------- */
  function refresh(events = []) {
    view = sim.view();
    scene.setWorld(view);
    for (const e of events) {
      scene.event(e);
      if (e.type !== "cash_changed") ticker.unshift(e);
      if (e.type === "work_completed") goal("make");
      if (e.type === "product_launched") goal("launch");
      if (e.type === "milestone_reached") toast(`公司大事记 · ${e.data.title}`);
      if (e.type === "patent_granted") toast(`专利授权 · ${e.data.name}`);
      if (e.type === "product_launched") toast(`上市 · ${e.data.name}`);
    }
    ticker.length = Math.min(ticker.length, 40);
    renderTop();
    renderDock();
    renderTicker();
    renderPanel();
    renderOverlays();
    renderGuide();
    if (!touring) maybeOpenModal();
  }

  function renderTop() {
    $("#date").textContent = view.date;
    $("#cash").textContent = money(view.cash);
    const flow = $("#flow");
    flow.textContent = `${signed(view.flow)}/周`;
    flow.dataset.sign = view.flow >= 0 ? "up" : "down";
    const pending = view.decisions.length;
    const badge = $("#pending");
    badge.hidden = pending === 0;
    badge.textContent = `${pending} 件事待决定`;
    renderClock();
  }
  function renderClock() {
    const label = $("#clock-state");
    if (view.blocking) {
      label.textContent = "等你决定";
      label.dataset.state = "blocked";
    } else if (speed === 0) {
      label.textContent = "已暂停";
      label.dataset.state = "paused";
    } else {
      label.textContent = `${speed}× 运行中`;
      label.dataset.state = "running";
    }
  }

  /* ---------- 底栏：伙伴、项目、最近发生的事 ---------- */
  let dockBuilt = false;
  function renderDock() {
    const people = $("#people");
    if (!dockBuilt) {
      people.innerHTML = view.heroes
        .map(
          (h) => `<button class="person" type="button" data-hero="${h.id}">
            <canvas class="portrait" aria-hidden="true"></canvas>
            <span class="person-text"><b>${esc(h.name)}</b><small>${esc(h.rankName)} · ${esc(h.short)}</small>
            <span class="task"><i class="pip"></i><span class="task-text"></span></span></span></button>`,
        )
        .join("");
      for (const btn of people.querySelectorAll(".person")) {
        btn.addEventListener("click", () => select({ type: "hero", id: btn.dataset.hero }));
      }
      dockBuilt = true;
      drawPortraits();
    }
    for (const h of view.heroes) {
      const btn = people.querySelector(`[data-hero="${h.id}"]`);
      btn.querySelector(".pip").dataset.mode = h.mode;
      btn.querySelector(".task-text").textContent = h.task;
      btn.setAttribute("aria-pressed", String(selection?.type === "hero" && selection.id === h.id));
    }
    const box = $("#projects");
    if (box.children.length !== view.projects.length) {
      box.innerHTML = view.projects
        .map(
          (p) => `<button class="project-chip" type="button" data-project="${p.id}">
            <span class="chip-top"><b>${esc(p.name)}</b><span class="kind" hidden></span></span>
            <small></small><span class="bar" aria-hidden="true"><i></i></span></button>`,
        )
        .join("");
      for (const btn of box.querySelectorAll(".project-chip")) {
        btn.addEventListener("click", () => select({ type: "project", id: btn.dataset.project }));
      }
    }
    for (const p of view.projects) {
      const btn = box.querySelector(`[data-project="${p.id}"]`);
      const st = p.stage;
      const pct = st ? Math.round((st.elapsed / st.weeks) * 100) : p.status === "approved" ? 100 : 0;
      const kind = btn.querySelector(".kind");
      kind.hidden = !st;
      if (st) {
        kind.dataset.kind = st.kind;
        kind.textContent = KIND[st.kind];
      }
      btn.querySelector("small").textContent = st ? `${st.name} · ${st.elapsed}/${st.weeks} 周` : p.statusText;
      const bar = btn.querySelector(".bar i");
      bar.style.width = `${pct}%`;
      bar.dataset.kind = st?.kind || "none";
      btn.setAttribute("aria-pressed", String(selection?.type === "project" && selection.id === p.id));
    }
  }
  function drawPortraits() {
    for (const h of view.heroes) {
      const c = document.querySelector(`.person[data-hero="${h.id}"] canvas`);
      if (c) scene.drawPortrait(c, h.look);
    }
    for (const c of panel.querySelectorAll("canvas[data-hero]")) {
      const h = view.heroes.find((q) => q.id === c.dataset.hero);
      if (h) scene.drawPortrait(c, h.look);
    }
  }
  function tickerKind(e) {
    if (e.type === "work_completed") return "make";
    if (e.type === "evidence_received") return "test";
    if (e.type === "service_completed" || e.type === "product_launched") return "money";
    return "info";
  }
  function renderTicker() {
    const list = $("#ticker");
    const items = ticker.slice(0, 3);
    const html = items.length
      ? items
          .map(
            (e) =>
              `<li data-kind="${tickerKind(e)}"><span class="wk">第 ${(e.week % 48) + 1} 周</span><span>${esc(e.text)}</span></li>`,
          )
          .join("")
      : `<li data-kind="info"><span class="wk">提示</span><span>先在下方卡片里选一个候选处方，时间就会开始走。</span></li>`;
    if (list.innerHTML !== html) list.innerHTML = html;
  }

  /* ---------- 场景上的标签和提醒 ---------- */
  // 标签和提醒原地更新文字，不整块重建：加速时点下去的按钮不会突然被换掉
  function renderOverlays() {
    for (const r of scene.rooms) {
      const info = view.rooms[r.id];
      let el = labels.querySelector(`[data-room="${r.id}"]`);
      if (!el) {
        el = document.createElement("button");
        el.type = "button";
        el.dataset.room = r.id;
        el.innerHTML = "<b></b><small></small>";
        el.addEventListener("click", () => select({ type: "room", id: r.id }));
        labels.appendChild(el);
      }
      const lot = r.id === "bio" && !info.built;
      const status = lot
        ? info.building
          ? `施工中 ${info.building.total - info.building.left}/${info.building.total} 周`
          : "空地 · 可以扩建"
        : roomStatus(r.id);
      el.className = lot ? "room-tag lot" : "room-tag";
      el.setAttribute("aria-pressed", String(selection?.type === "room" && selection.id === r.id));
      setText(el.querySelector("b"), lot ? "+ 生物实验室" : r.name);
      setText(el.querySelector("small"), status);
    }
    const live = new Set(view.decisions.map((d) => d.id));
    for (const el of labels.querySelectorAll("[data-decision]")) if (!live.has(el.dataset.decision)) el.remove();
    for (const d of view.decisions) {
      let el = labels.querySelector(`[data-decision="${d.id}"]`);
      if (!el) {
        el = document.createElement("button");
        el.type = "button";
        el.dataset.decision = d.id;
        el.innerHTML = '<span aria-hidden="true">!</span><em></em>';
        el.addEventListener("click", () => {
          const q = view.decisions.find((x) => x.id === d.id);
          if (q?.deferred) refresh(sim.act("resume", { decision: d.id }));
          openModal(d.id);
        });
        labels.appendChild(el);
      }
      const short = { choose: "选候选", next: "安排下一步", interim: "期中决定", failed: "没过，怎么办", launch: "上市命名", license: "III 期还是授权" }[d.kind];
      el.className = d.deferred ? "bubble deferred" : "bubble";
      el.dataset.anchor = d.room;
      setText(el.querySelector("em"), `${d.projectName} · ${short}`);
    }
    placeOverlays();
  }
  function setText(el, text) {
    if (el.textContent !== text) el.textContent = text;
  }
  function placeOverlays() {
    if (!labels) return;
    const stack = {};
    for (const el of labels.children) {
      const room = el.dataset.room || el.dataset.anchor;
      const kind = el.dataset.room ? "room" : "bubble";
      const p = scene.anchor("room", room);
      if (!p) continue;
      let y = p.y;
      if (kind === "bubble") {
        stack[room] = (stack[room] || 0) + 1;
        y = p.y + 30 + (stack[room] - 1) * 30;
      }
      el.style.transform = `translate(${Math.round(p.x)}px, ${Math.round(y)}px) translate(-50%, -100%)`;
    }
  }
  function roomStatus(roomId) {
    const parts = [];
    for (const p of view.projects) {
      const st = p.stage;
      if (!st) continue;
      const room = window.DrugstoryDemo.STAGES[st.key].room;
      if (room !== roomId) continue;
      parts.push(`${p.name} · ${st.name.replace("上市审评与质量核查", "审评")} ${st.batches}/${st.batchCount} 批`);
    }
    for (const v of view.services) if (v.room === roomId) parts.push(`${v.name} · 剩 ${v.left} 周`);
    return parts[0] || "空闲";
  }

  /* ---------- 选择与面板 ---------- */
  function select(hit) {
    selection = hit;
    if (hit?.type === "hero") goal("hero");
    scene.select(hit && (hit.type === "hero" || hit.type === "room") ? hit : null);
    renderPanel(true);
    renderDock();
    renderOverlays();
  }

  let lastPanel = "";
  let pointerInPanel = false;
  panel.addEventListener("pointerenter", () => {
    pointerInPanel = true;
  });
  panel.addEventListener("pointerleave", () => {
    pointerInPanel = false;
    renderPanel();
  });
  function renderPanel(force = false) {
    if (pointerInPanel && !force) return;
    let html;
    if (!selection) html = overviewPanel();
    else if (selection.type === "hero") html = heroPanel(view.heroes.find((h) => h.id === selection.id));
    else if (selection.type === "room") html = roomPanel(selection.id);
    else if (selection.type === "project") html = projectPanel(view.projects.find((p) => p.id === selection.id));
    if (html === lastPanel) return;
    lastPanel = html;
    panel.innerHTML = html;
    for (const b of panel.querySelectorAll("[data-select]")) {
      b.addEventListener("click", () => {
        const [type, id] = b.dataset.select.split(":");
        select(type === "overview" ? null : { type, id });
      });
    }
    for (const b of panel.querySelectorAll("[data-act]")) {
      b.addEventListener("click", () => {
        try {
          if (b.dataset.act === "build" || b.dataset.act === "upgrade") goal("build");
          refresh(sim.act(b.dataset.act, JSON.parse(b.dataset.args || "{}")));
          renderPanel(true);
        } catch (err) {
          notice(err.message);
        }
      });
    }
    for (const b of panel.querySelectorAll("[data-open]")) b.addEventListener("click", () => {
      const d = view.decisions.find((q) => q.id === b.dataset.open);
      if (d?.deferred) refresh(sim.act("resume", { decision: d.id }));
      openModal(b.dataset.open);
    });
    drawPortraits();
  }

  function back() {
    return `<button class="back" type="button" data-select="overview:">← 研究所概况</button>`;
  }

  function overviewPanel() {
    return `<div class="panel-body">
      <p class="eyebrow">场景原型 · 示例数据</p>
      <h2>星火研究社</h2>
      <p class="lede">整个公司放在一屏里。时间自己走，遇到要你拿主意的事就停。点房间、点人、点项目都能看详情。</p>
      <ul class="legend-list">
        <li><span class="kind" data-kind="make">做</span>团队把药做好：人头上冒橙色数字，证据条上的点往右移。</li>
        <li><span class="kind" data-kind="test">测</span>数据揭晓真相：白板上多一个蓝点，证据范围收窄。</li>
        <li><span class="pip" data-mode="service"></span>技术服务：交付后收钱。</li>
        <li><span class="pip" data-mode="idle"></span>空闲：会去走廊和茶水间转转。</li>
      </ul>
      <h3>房间</h3>
      <div class="link-list">${scene.rooms
        .map((r) => `<button type="button" data-select="room:${r.id}"><b>${esc(r.name)}</b><small>${esc(view.rooms[r.id].built ? roomStatus(r.id) : "未建 · 可以扩建")}</small></button>`)
        .join("")}</div>
      <h3>项目</h3>
      <div class="link-list">${view.projects
        .map((p) => `<button type="button" data-select="project:${p.id}"><b>${esc(p.name)}</b><small>${esc(p.kindName)} · ${esc(p.stage ? p.stage.name : p.statusText)}</small></button>`)
        .join("")}</div>
      <h3>快捷键</h3>
      <p class="small">空格暂停或继续；1、2、3 切换 1×、2×、4×。</p>
    </div>`;
  }

  function heroPanel(h) {
    const recent = ticker.filter((e) => e.actors?.includes(h.id) && e.type === "work_completed").slice(0, 4);
    return `<div class="panel-body">${back()}
      <header class="hero-head">
        <canvas class="portrait big" data-hero="${h.id}" aria-hidden="true"></canvas>
        <div><p class="eyebrow">${esc(h.rankName)} · ${esc(h.professionName)}</p><h2>${esc(h.name)}</h2><p class="nick">「${esc(h.nickname)}」</p></div>
      </header>
      <p class="lede">${esc(h.story)}</p>
      <p class="small">${esc(h.bio)}</p>
      <dl class="facts">
        <div><dt>专业能力</dt><dd><span class="meter"><i style="width:${h.ability}%"></i></span><span class="num">${h.ability}</span></dd></div>
        <div><dt>团队成员</dt><dd>${h.members} 人（开发时站在旁边帮忙，越多越快）</dd></div>
        <div><dt>正在做</dt><dd><i class="pip" data-mode="${h.mode}"></i>${esc(h.task)}</dd></div>
        <div><dt>招牌能力</dt><dd><b>${esc(h.signature.name)}</b>：${esc(h.signature.text)}</dd></div>
        <div><dt>个人课题</dt><dd>「${esc(h.quest)}」</dd></div>
      </dl>
      <h3>最近的开发贡献</h3>
      ${recent.length ? `<ul class="plain">${recent.map((e) => `<li><span class="num">第 ${(e.week % 48) + 1} 周</span> ${esc(e.data.detail)}</li>`).join("")}</ul>` : `<p class="small">还没有。安排进“做”的阶段后，每批开发都会记在这里。</p>`}
    </div>`;
  }

  function roomPanel(id) {
    const r = scene.rooms.find((q) => q.id === id);
    const info = view.rooms[id];
    const does = {
      lab: "做：处方与工艺、工艺补正、分子优化",
      qc: "做：质量与稳定性；测：上市审评与质量核查",
      clinic: "测：生物等效性、I–III 期临床（白板上是实时读数）",
      bio: "做：创新药的分子优化与转化验证",
    }[id];
    if (id === "bio" && !info.built) {
      const building = info.building;
      return `<div class="panel-body">${back()}
        <p class="eyebrow">空地</p><h2>生物实验室</h2>
        <p class="lede">${esc(does)}。扩建是看得见的花钱去处：施工、落成，然后有人在里面干活。</p>
        <dl class="facts"><div><dt>费用</dt><dd>¥700 万</dd></div><div><dt>工期</dt><dd>6 周</dd></div>
        <div><dt>扣除已承诺后的现金</dt><dd>${money(view.available)}</dd></div></dl>
        ${building ? `<p class="small">施工中：还要 ${building.left} 周。</p>` : `<button class="primary" type="button" data-act="build" ${view.available < 700 ? "disabled" : ""}>扩建生物实验室 · ¥700 万</button>`}
      </div>`;
    }
    const here = view.heroes.filter((h) => view.assignments[h.id]?.room === id);
    const cost = sim.rooms.upgradeCost(info.level);
    const upgrade =
      info.level < 3
        ? `<button class="primary" type="button" data-act="upgrade" data-args='{"room":"${id}"}' ${view.available < cost ? "disabled" : ""}>升级到 ${info.level + 1} 级 · ${money(cost)}</button>`
        : `<p class="small">已经是最高级。</p>`;
    const board = view.boards[id] || [];
    return `<div class="panel-body">${back()}
      <p class="eyebrow">房间</p><h2>${esc(r.name)}</h2>
      <p class="lede">${esc(does)}</p>
      <dl class="facts">
        <div><dt>现在</dt><dd>${esc(roomStatus(id))}</dd></div>
        <div><dt>在这里的人</dt><dd>${here.length ? here.map((h) => `<button class="link" type="button" data-select="hero:${h.id}">${esc(h.name)}</button>`).join("、") : "没有人"}</dd></div>
        <div><dt>设备</dt><dd>${info.level} 级 · 每升一级，本专业每次开发量 +2，房间里会多一台仪器</dd></div>
        ${board.length ? `<div><dt>白板</dt><dd>${board.map((b) => `${esc(b.title)}：${b.readings.join("、") || "等第一批"}（门槛 ${b.limit}）`).join("<br>")}</dd></div>` : ""}
      </dl>
      ${upgrade}
    </div>`;
  }

  function projectPanel(p) {
    const st = p.stage;
    const steps = p.path
      .map((s) => `<li data-state="${s.state}"><span class="kind" data-kind="${s.kind}">${KIND[s.kind]}</span>${esc(s.name)}</li>`)
      .join("");
    let stage = "";
    if (st) {
      const pct = Math.round((st.elapsed / st.weeks) * 100);
      const detail =
        st.kind === "make"
          ? `<p class="small">每批开发会把药的真实性质推高一点（橙点右移）。计划总量：${p.work
              .map((w) => Object.entries(w.amounts).map(([k, v]) => `${esc(p.statNames[k])} +${v}`).join("、"))
              .join("；")}</p>`
          : `${chart(p)}<p class="small">四批读数的平均值和门槛比较。读数本身有误差，单批高低不算数。</p>`;
      stage = `<section class="stage-box" data-kind="${st.kind}">
        <div class="stage-title"><span class="kind" data-kind="${st.kind}">${KIND[st.kind]}</span><b>${esc(st.name)}</b><span class="num">${st.elapsed}/${st.weeks} 周</span></div>
        <span class="bar"><i style="width:${pct}%" data-kind="${st.kind}"></i></span>
        <p class="small">${esc(st.team.join("、") || "外包 CRO")}${st.mode === "cro" ? " · 外包 CRO" : ""} · 第 ${st.batches}/${st.batchCount} 批</p>
        ${detail}
      </section>`;
    }
    const pending = view.decisions.find((d) => d.project === p.id);
    return `<div class="panel-body">${back()}
      <p class="eyebrow">${esc(p.kindName)} · ${esc(p.combo)}</p><h2>${esc(p.name)}</h2>
      <p class="status-line">${esc(p.statusText)}${p.chosen ? ` · 候选：${esc(p.chosen)}` : ""}</p>
      ${pending ? `<button class="primary" type="button" data-open="${pending.id}">处理：${esc(pending.title)}</button>` : ""}
      <ol class="path">${steps}</ol>
      ${stage}
      ${p.evidence.length ? `<h3>现在知道的</h3>${evidenceBars(p.evidence)}<p class="small">灰带是 90% 可能的范围，竖线是当前估计，红线是本阶段门槛。</p>` : ""}
    </div>`;
  }

  function evidenceBars(list) {
    const pos = (v) => Math.max(0, Math.min(100, ((v - 400) / 600) * 100));
    return `<div class="ev-list">${list
      .map((e) => {
        const lo = pos(e.low);
        const hi = pos(e.high);
        return `<div class="ev">
          <div class="ev-label"><span>${esc(e.name)}</span><span class="num">${Math.round(e.low)}–${Math.round(e.high)}</span></div>
          <div class="ev-track">
            <i class="ev-band" style="left:${lo}%;width:${Math.max(1, hi - lo)}%"></i>
            <i class="ev-mean" style="left:${pos(e.mean)}%"></i>
            ${e.limit != null ? `<i class="ev-limit" style="left:${pos(e.limit)}%" title="门槛 ${e.limit}"></i>` : ""}
          </div></div>`;
      })
      .join("")}</div>`;
  }

  function chart(p) {
    const st = p.stage;
    const key = st.key;
    const limits = st.limits;
    const stat = Object.keys(limits)[0];
    const limit = limits[stat];
    const values = p.readings.filter((r) => r.stage === key).map((r) => r.values[stat]);
    const lo = limit - 240;
    const hi = limit + 240;
    const y = (v) => 80 - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * 64;
    const x = (i) => 40 + i * 50;
    const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
    return `<svg class="chart" viewBox="0 0 240 92" role="img" aria-label="${esc(p.statNames[stat])}读数，门槛 ${limit}">
      <line x1="30" x2="232" y1="${y(limit)}" y2="${y(limit)}" class="limit"></line>
      <text x="0" y="${y(limit) + 4}" class="axis">${limit}</text>
      ${[0, 1, 2, 3].map((i) => `<text x="${x(i) - 8}" y="91" class="axis">第${i + 1}批</text>`).join("")}
      ${mean != null && values.length > 1 ? `<line x1="30" x2="232" y1="${y(mean)}" y2="${y(mean)}" class="mean"></line>` : ""}
      ${values.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="4.5" class="dot"></circle><text x="${x(i) + 7}" y="${y(v) - 6}" class="val">${v}</text>`).join("")}
    </svg>`;
  }

  /* ---------- 决定卡片 ---------- */
  function maybeOpenModal() {
    if (modalId && view.decisions.some((d) => d.id === modalId && !d.deferred)) {
      return;
    }
    modalId = null;
    modal.hidden = true;
    const next = view.decisions.find((d) => !d.deferred);
    if (next) openModal(next.id);
  }
  function openModal(id) {
    const d = view.decisions.find((q) => q.id === id);
    if (!d) return;
    modalId = id;
    modal.hidden = false;
    let body = "";
    if (d.kind === "choose") {
      body = `<div class="cands">${d.candidates
        .map(
          (c) => `<article class="cand"><h4>${esc(c.label)}</h4>${evidenceBars(c.evidence)}
            <button class="primary" type="button" data-choose="${c.index}">选这个</button></article>`,
        )
        .join("")}</div><p class="small">${esc(d.next)}</p>`;
    } else {
      body = `${d.facts ? `<dl class="facts">${d.facts.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl>` : ""}
        ${d.input ? `<label class="field" for="${d.input.id}"><span>${esc(d.input.label)}</span><input id="${d.input.id}" value="${esc(d.input.value)}" maxlength="20"></label>` : ""}
        <div class="actions">${d.actions
          .map(
            (a, i) => `<button type="button" class="${a.primary ? "primary" : "ghost"}" data-action="${i}" ${a.disabled ? "disabled" : ""}>${esc(a.label)}</button>`,
          )
          .join("")}</div>`;
    }
    modal.innerHTML = `<div class="card" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <p class="eyebrow">${view.blocking ? "时间已暂停" : "待决定"} · ${esc(d.projectName)}</p>
      <h3 id="modal-title">${esc(d.title)}</h3>
      <p class="lede">${esc(d.text)}</p>${body}</div>`;
    for (const b of modal.querySelectorAll("[data-choose]")) {
      b.addEventListener("click", () => act("choose", { decision: d.id, candidate: Number(b.dataset.choose) }));
    }
    for (const b of modal.querySelectorAll("[data-action]")) {
      b.addEventListener("click", () => {
        const a = d.actions[Number(b.dataset.action)];
        const args = { decision: d.id, ...(a.args || {}) };
        if (d.input) args.name = $(`#${d.input.id}`, modal).value.trim();
        act(a.name, args);
      });
    }
    modal.querySelector("button:not([disabled]), input")?.focus({ preventScroll: true });
  }
  function act(name, args) {
    if (name === "choose") goal("choose");
    if (name === "interim") goal("interim");
    if (name === "build" || name === "upgrade") goal("build");
    try {
      modal.hidden = true;
      modalId = null;
      refresh(sim.act(name, args));
    } catch (err) {
      notice(err.message);
    }
  }
  function notice(text) {
    const n = $("#notice");
    n.textContent = text;
    n.hidden = false;
    clearTimeout(notice.t);
    notice.t = setTimeout(() => {
      n.hidden = true;
    }, 2600);
  }


  /* ---------- 目标条：一直告诉玩家下一步做什么 ---------- */
  const GOALS = [
    { key: "choose", title: "选一个候选处方", hint: "在下方卡片里比较三个处方，点「选这个」。红线是后面要过的门槛。" },
    { key: "make", title: "看一次“做”", hint: "时间在走。等陈一鸣、苏小禾在实验室里干完一批，头上会冒出橙色数字。" },
    { key: "interim", title: "做一次期中决定", hint: "临床办公室的白板会多一个蓝点，时间停下后，选继续收集或提前止损。" },
    { key: "hero", title: "认识一位伙伴", hint: "点底部任意一张人物卡，或直接点场景里的人，看看他的背景和招牌能力。" },
    { key: "build", title: "花一笔钱扩建", hint: "点右下角虚线空地扩建生物实验室，或点一个房间升级设备。" },
    { key: "launch", title: "让稳压片上市", hint: "按卡片一步步安排下一阶段：质量 → 生物等效性 → 审评 → 上市。可以按 ▶▶▶ 加速。" },
    { key: "gallery", title: "翻一翻伙伴图鉴", hint: "右上角「伙伴图鉴」里有全部 20 位伙伴的样子和故事。" },
  ];
  const goals = new Set();
  function goal(key) {
    if (goals.has(key)) return;
    goals.add(key);
    renderGuide();
  }
  function renderGuide() {
    const box = $("#guide");
    if (!box) return;
    const next = GOALS.find((g) => !goals.has(g.key));
    const done = GOALS.filter((g) => goals.has(g.key)).length;
    let line;
    if (view.blocking) line = "时间停了：先在下方卡片里做决定。";
    else if (view.decisions.some((d) => d.deferred)) line = "有事被暂缓了：点场景里的橙色气泡继续处理。";
    else line = next ? next.hint : "全部完成。可以自由玩下去，或者看看图鉴里还没加入的伙伴。";
    const html = `<button class="guide-toggle" type="button" aria-expanded="${guideOpen}">
        <span class="guide-count">${done}/${GOALS.length}</span>
        <span class="guide-text"><b>${next ? esc(next.title) : "新手目标完成"}</b><small>${esc(line)}</small></span>
      </button>
      ${guideOpen ? `<ol class="guide-list">${GOALS.map((g) => `<li data-done="${goals.has(g.key)}">${esc(g.title)}</li>`).join("")}</ol>` : ""}`;
    if (box.innerHTML !== html) {
      box.innerHTML = html;
      box.querySelector(".guide-toggle").addEventListener("click", () => {
        guideOpen = !guideOpen;
        renderGuide();
      });
    }
  }
  let guideOpen = false;

  /* ---------- 大事记横幅 ---------- */
  const toasts = [];
  function toast(text) {
    toasts.push(text);
    if (toasts.length === 1) showToast();
  }
  function showToast() {
    const el = $("#toast");
    if (!toasts.length) {
      el.hidden = true;
      return;
    }
    el.textContent = toasts[0];
    el.hidden = false;
    setTimeout(() => {
      toasts.shift();
      showToast();
    }, 2600);
  }

  /* ---------- 第一次打开：四步引导 ---------- */
  const TOUR = [
    { target: ".scene", title: "这是你的研究所", text: "整个公司在这一屏里。伙伴会自己走到房间干活：头上冒橙色数字，是在把药做好；白板上多一个蓝点，是数据回来了。" },
    { target: ".clock", title: "时间自己走", text: "这里暂停或加速，空格键也能暂停。遇到要你拿主意的事，时间会自动停下。" },
    { target: "#guide", title: "不知道做什么，就看这里", text: "这条目标会一直告诉你下一步。做完一项打一个勾，点开能看全部目标。" },
    { target: ".panel", title: "点什么，这里就讲什么", text: "点房间、点人、点底部的卡片，右边会显示详情和能做的事，比如升级设备、看证据。" },
  ];
  let touring = false;
  let tourStep = 0;
  function startTour() {
    touring = true;
    tourStep = 0;
    modal.hidden = true;
    $("#tour").hidden = false;
    showTourStep();
  }
  function showTourStep() {
    const step = TOUR[tourStep];
    const target = document.querySelector(step.target);
    const tour = $("#tour");
    const hole = tour.querySelector(".tour-hole");
    const card = tour.querySelector(".tour-card");
    const r = target.getBoundingClientRect();
    const pad = 6;
    Object.assign(hole.style, {
      left: `${r.left - pad}px`, top: `${r.top - pad}px`, width: `${r.width + pad * 2}px`, height: `${r.height + pad * 2}px`,
    });
    card.innerHTML = `<p class="eyebrow">第 ${tourStep + 1} / ${TOUR.length} 步</p><h3>${esc(step.title)}</h3><p>${esc(step.text)}</p>
      <div class="actions"><button class="primary" type="button" data-tour="next">${tourStep === TOUR.length - 1 ? "开始玩" : "下一步"}</button>
      <button class="ghost" type="button" data-tour="skip">跳过引导</button></div>`;
    const cw = Math.min(340, window.innerWidth - 32);
    let left = r.left + r.width / 2 - cw / 2;
    left = Math.max(16, Math.min(window.innerWidth - cw - 16, left));
    let top = r.bottom + 14;
    if (top + 200 > window.innerHeight) top = Math.max(16, r.top - 214);
    if (r.height > window.innerHeight * 0.6) top = Math.max(16, r.top + 24);
    Object.assign(card.style, { left: `${left}px`, top: `${top}px`, width: `${cw}px` });
    card.querySelector('[data-tour="next"]').addEventListener("click", () => {
      tourStep += 1;
      if (tourStep >= TOUR.length) endTour();
      else showTourStep();
    });
    card.querySelector('[data-tour="skip"]').addEventListener("click", endTour);
    card.querySelector('[data-tour="next"]').focus({ preventScroll: true });
  }
  function endTour() {
    touring = false;
    $("#tour").hidden = true;
    try {
      localStorage.setItem("drugstory-tour-done", "1");
    } catch (err) {
      void err;
    }
    maybeOpenModal();
  }
  window.addEventListener("resize", () => {
    if (touring) showTourStep();
  });

  /* ---------- 伙伴图鉴 ---------- */
  function openGallery() {
    goal("gallery");
    const cast = window.DrugstoryCast || [];
    const employed = new Set(view.heroes.map((h) => h.id));
    const groups = ["bio", "chem", "tox", "proc", "clinical"];
    const box = $("#gallery");
    box.innerHTML = `<div class="gallery-card" role="dialog" aria-modal="true" aria-labelledby="gallery-title">
      <div class="gallery-head"><div><p class="eyebrow">20 位伙伴 · 见习 → 精英 → 大师 → 传奇</p><h2 id="gallery-title">伙伴图鉴</h2></div>
      <button class="ghost" type="button" data-close>关闭</button></div>
      ${groups
        .map((g) => {
          const people = cast.filter((c) => c.profession === g);
          return `<section><h3>${esc(people[0]?.profession_name || g)}</h3><div class="gallery-grid">${people
            .map(
              (c) => `<button class="mate" type="button" data-mate="${c.id}" aria-expanded="false">
                <canvas class="portrait xl" data-cast="${c.id}" aria-hidden="true"></canvas>
                <span class="mate-text"><b>${esc(c.name)}</b><small>「${esc(c.nickname)}」 · ${esc(c.tier_name)}${employed.has(c.id) ? " · 在研究社" : ""}</small>
                <span class="mate-line">${esc(c.story)}</span>
                <span class="mate-more"><span>${esc(c.bio)}</span><span><b>${esc(c.signature.name)}</b>：${esc(c.signature.text)}</span><span>个人课题「${esc(c.quest)}」</span></span></span>
              </button>`,
            )
            .join("")}</div></section>`;
        })
        .join("")}
    </div>`;
    box.hidden = false;
    for (const c of box.querySelectorAll("canvas[data-cast]")) {
      const person = cast.find((q) => q.id === c.dataset.cast);
      scene.drawPortrait(c, person.look);
    }
    for (const b of box.querySelectorAll("[data-mate]")) {
      b.addEventListener("click", () => b.setAttribute("aria-expanded", String(b.getAttribute("aria-expanded") !== "true")));
    }
    box.querySelector("[data-close]").addEventListener("click", closeGallery);
    box.querySelector("[data-close]").focus({ preventScroll: true });
  }
  function closeGallery() {
    $("#gallery").hidden = true;
  }

  /* ---------- 控件 ---------- */
  for (const b of document.querySelectorAll("[data-speed]")) b.addEventListener("click", () => setSpeed(Number(b.dataset.speed)));
  for (const b of document.querySelectorAll("[data-style]")) {
    b.addEventListener("click", () => {
      scene.setStyle(b.dataset.style);
      for (const q of document.querySelectorAll("[data-style]")) q.setAttribute("aria-pressed", String(q === b));
      document.documentElement.dataset.sceneStyle = b.dataset.style;
      drawPortraits();
    });
  }
  $("#pending").addEventListener("click", () => {
    const d = view.decisions[0];
    if (!d) return;
    if (d.deferred) refresh(sim.act("resume", { decision: d.id }));
    openModal(d.id);
  });
  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea") || touring || !$("#gallery").hidden) return;
    if (e.key === "Escape" && modalId) {
      const d = view.decisions.find((q) => q.id === modalId);
      if (d?.deferrable) act("defer", { decision: d.id });
    }
    if (modalId) return;
    if (e.code === "Space") {
      e.preventDefault();
      setSpeed(speed === 0 ? 1 : 0);
    }
    if (e.key === "1") setSpeed(1);
    if (e.key === "2") setSpeed(2);
    if (e.key === "3") setSpeed(4);
  });
  window.addEventListener("resize", () => placeOverlays());

  $("#help").addEventListener("click", startTour);
  $("#open-gallery").addEventListener("click", openGallery);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("#gallery").hidden) closeGallery();
  });
  setSpeed(1);
  let seen = false;
  try {
    seen = localStorage.getItem("drugstory-tour-done") === "1";
  } catch (err) {
    void err;
  }
  touring = !seen;
  refresh([]);
  if (!seen) startTour();
})();
