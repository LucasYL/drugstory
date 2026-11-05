/* Scene shell. All decisions use app.js's existing forms and ApiDriver commands. */
(() => {
  let renderer,
    world,
    speed = 0,
    accumulator = 0,
    selected = null,
    cursor = null,
    lastRevision = null;
  let lastIdentity = null,
    lastPendingKey = null,
    toastTimer;
  const q = (s) => document.querySelector(s);
  const pending = (s) =>
    s.projects.filter(
      (p) =>
        p.active &&
        !p.deferred &&
        ["selecting", "ready", "result", "problem", "checkpoint"].includes(
          p.status,
        ),
    );
  const names = {
    lab: "化学与制剂实验室",
    qc: "质量与毒理室",
    clinic: "临床与数据办公室",
    bio: "生物实验室",
    academy: "共研教室",
    hall: "大会与荣誉室",
  };
  function pause() {
    speed = 0;
    accumulator = 0;
    clock();
  }
  function clock() {
    for (const el of document.querySelectorAll("[data-speed]"))
      el.setAttribute("aria-pressed", String(+el.dataset.speed === speed));
    q("#clock-status").textContent =
      typeof state === "undefined" || !state
        ? "连接中"
        : state.game_over
          ? "公司已停止经营"
          : state.pending
            ? "等你决定"
            : speed
              ? `${speed}× · 每周保存`
              : "已暂停";
  }
  function frame(dt) {
    if (
      !speed ||
      document.hidden ||
      !state ||
      requestBusy ||
      driver.busy ||
      driver.uncertain ||
      q("#modal").open ||
      DrugstoryWorld.blocked(state)
    ) {
      accumulator = 0;
      return;
    }
    accumulator += dt;
    if (accumulator >= 1.6 / speed) {
      accumulator = 0;
      send("advance", { weeks: 1 });
    }
  }
  function select(hit) {
    if (!hit) return;
    pause();
    selected = hit;
    renderer.select(hit);
    if (hit.type === "project") activeTab = "pipeline";
    if (hit.type === "hero") activeTab = "characters";
    renderPanel();
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
      selected = null;
      lastPendingKey = null;
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
    for (const ev of recent)
      renderer.event({ ...ev, data: { ...ev.data, labels: s.stats } });
    cursor = s.event_cursor;
    const matters = recent.filter((e) =>
      [
        "product_launched",
        "patent_granted",
        "patent_expired",
        "milestone_reached",
        "character_promoted",
        "personal_completed",
        "service_completed",
        "deal_signed",
        "award_won",
        "legacy_reached",
        "facility_upgraded",
      ].includes(e.type),
    );
    if (matters.length) {
      pause();
      q("#scene-toast").textContent = matters
        .slice(-3)
        .map((e) =>
          e.type === "milestone_reached"
            ? e.data.title
            : e.type === "patent_granted"
              ? `${e.data.name} · 专利授权`
              : e.type === "patent_expired"
                ? `${e.data.name} · 专利到期`
                : e.type === "service_completed"
                  ? `${e.data.service} · 回款 ${money(e.data.reward)}`
                  : `${{ product_launched: "上市", deal_signed: "授权签约", character_promoted: "晋阶", personal_completed: "课题完成", facility_upgraded: "扩建落成", award_won: "年度获奖", legacy_reached: "终局荣誉" }[e.type] || "新成果"} · ${e.data.name || ""}`,
        )
        .join("\n");
      q("#scene-toast").hidden = false;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => (q("#scene-toast").hidden = true), 8000);
    }
    const waiting = pending(s);
    const waitingKey = waiting
      .map((p) => `${p.id}:${p.key}:${p.status}`)
      .join("|");
    if (waiting.length) {
      pause();
      if (waitingKey !== lastPendingKey) {
        selected = { type: "project", id: waiting[0].id };
        activeTab = "pipeline";
      }
    }
    lastPendingKey = waitingKey;
    if (s.game_over) pause();
    q("#scene-metrics").innerHTML =
      `<span>${esc(s.date)}<b>第 ${s.week} 周</b></span><span>现金 / 已承诺<b>${money(s.cash)} / ${num(s.committed)}</b></span><span>团队 / 容量<b>${s.headcount} / ${s.facility.capacity}</b></span>`;
    q("#scene-goal").innerHTML = guide(s);
    q("#scene-journal").innerHTML = s.journal
      .slice(-12)
      .reverse()
      .map((e) => `<li>第 ${e.week} 周 · ${esc(e.text)}</li>`)
      .join("");
    renderPanel();
    lastRevision = s.revision;
    updateDock();
    labels();
    clock();
  }
  function guide(s) {
    const p = pending(s)[0];
    let title,
      text,
      action = "";
    if (s.game_over) {
      title = "研究所暂时停业";
      text = "经营记录已保存，可在经营复盘回看并备份重开。";
    } else if (p) {
      title = `${p.name} · ${p.status_name}`;
      text = {
        selecting:
          "比较候选的证据区间；区间宽表示尚不确定。选定后安排团队开发。",
        ready: "在右侧安排负责人、方案和执行方式，预览工期与费用后开工。",
        result:
          p.key === "review"
            ? "审评已通过，命名并安排上市。"
            : "本阶段已完成。看结果，再继续研发或比较可用的授权报价。",
        problem:
          "这一阶段未通过。可补正一次、早期换候选或止损；不保证能救回来。",
        checkpoint:
          "数据回来一半了。右侧有当前证据与剩余投入，决定继续还是提前止损。",
      }[p.status];
      action = `<button data-scene-project="${p.id}">查看这项决定${s.pending > 1 ? ` · 共 ${s.pending} 项` : ""}</button>`;
    } else if (
      s.projects.some((p) => ["running", "screening"].includes(p.status)) ||
      s.jobs.length ||
      s.deals.some((d) => d.status === "developing")
    ) {
      title = speed
        ? "研究进行中 · 留意橙色开发和蓝色数据"
        : "安排已就绪 · 可以推进时间";
      text =
        "点 1×、2×、4× 或下一件事。出现决定会停下；点人、打开操作窗口或切到后台也会暂停。";
    } else if (s.projects.some((p) => p.deferred)) {
      const deferred = s.projects.find((p) => p.deferred);
      title = "有暂缓的项目 · 随时可以继续";
      text =
        "项目保留了已取得的证据。点项目卡恢复安排，或先培养伙伴、承接服务。";
      action = `<button data-scene-project="${deferred.id}">查看 ${esc(deferred.name)}</button>`;
    } else if (!s.projects.length) {
      title = "第一步 · 建立自己的研究计划";
      text =
        "建议从稳压片开始。陈一鸣负责药化，苏小禾负责工艺；也可以先接技术服务。";
      action = modalButton("新建研究计划", "project", "", "primary");
    } else if (s.products.length) {
      title = "第一粒药之后 · 培养你的研究社";
      text =
        "用收入支持新项目和个人课题。图鉴能查看人才解锁条件，大会与荣誉里有长期目标。";
    } else {
      title = "下一步 · 安排工作或换条路线";
      text =
        "可以重新立项、接服务赚周转金，或培养伙伴后再出发。历史项目和证据仍可查看。";
    }
    return `<b>${esc(title)}</b><span>${esc(text)}</span>${action}`;
  }
  function roomSummary(id) {
    const team = state.heroes.filter(
      (h) => h.activity !== "idle" && world.locate(h.room) === id,
    );
    const remote =
      id === "clinic"
        ? state.projects.filter((p) => p.scene.executor === "cro")
        : [];
    if (!world.rooms[id]?.built) return "扩建后开放专用空间";
    return [
      team.length ? `${team.length} 位伙伴工作中` : "当前空闲",
      remote.length ? `${remote.length} 项外包 CRO` : "",
    ]
      .filter(Boolean)
      .join(" · ");
  }
  function labels() {
    if (!renderer || !world) return;
    const box = q("#room-labels"),
      live = new Set(renderer.rooms.map((r) => r.id));
    for (const el of box.children) if (!live.has(el.dataset.room)) el.remove();
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
      el.classList.toggle(
        "pending",
        pending(state).some((p) => world.locate(p.scene.room) === r.id),
      );
      const pt = renderer.anchor("room", r.id);
      if (!pt) continue;
      const rect = box.getBoundingClientRect(),
        w = el.offsetWidth,
        h = el.offsetHeight;
      el.style.left = `${Math.max(w / 2 + 6, Math.min(rect.width - w / 2 - 6, pt.x))}px`;
      el.style.top = `${Math.max(115 + h / 2, Math.min(rect.height - 60 - h / 2, pt.y))}px`;
    }
  }
  function updateDock() {
    const people = q("#scene-people");
    const ids = state.heroes.map((h) => h.id).join("|");
    if (people.dataset.ids !== ids) {
      people.dataset.ids = ids;
      people.innerHTML = state.heroes
        .map(
          (h) =>
            `<button class="scene-chip" data-scene-hero="${h.id}"><canvas class="scene-portrait" data-portrait="${h.id}" aria-hidden="true"></canvas><span><b></b><small class="hero-rank"></small><small class="hero-task"></small></span></button>`,
        )
        .join("");
    }
    for (const h of state.heroes) {
      const el = people.querySelector(`[data-scene-hero="${h.id}"]`);
      el.querySelector("b").textContent = h.name;
      el.querySelector(".hero-rank").textContent =
        `${h.rank_name} · ${h.members} 名成员`;
      el.querySelector(".hero-task").textContent =
        h.busy || "空闲 · 可安排工作";
      el.setAttribute(
        "aria-pressed",
        String(selected?.type === "hero" && selected.id === h.id),
      );
      renderer.drawPortrait(el.querySelector("canvas"), h.look);
    }
    const projects = q("#scene-projects");
    const active = state.projects.filter((p) => p.active);
    const keys = active.map((p) => p.id).join("|");
    if (projects.dataset.ids !== keys) {
      projects.dataset.ids = keys;
      projects.innerHTML = active
        .map(
          (p) =>
            `<button class="scene-chip scene-project" data-scene-project="${p.id}"><b></b><small></small><progress></progress></button>`,
        )
        .join("");
    }
    for (const p of active) {
      const el = projects.querySelector(`[data-scene-project="${p.id}"]`);
      el.querySelector("b").textContent = p.name;
      el.querySelector("small").textContent =
        `${p.status_name} · ${p.scene.total ? `剩 ${p.left} 周` : p.phase}${p.deferred ? " · 已暂缓" : ""}`;
      el.querySelector("progress").max = p.scene.total || 1;
      el.querySelector("progress").value = p.scene.elapsed;
    }
  }
  function heroPanel(h) {
    return `<button data-scene="overview">← 研究社总览</button><div class="hero-detail"><canvas data-portrait="${h.id}" aria-hidden="true"></canvas><div><h2>${esc(h.name)}「${esc(h.nickname)}」</h2><p>${esc(h.rank_name)} · ${esc(h.profession_name)}</p></div></div><p>${esc(h.bio)}</p><p><b>${esc(h.trait.name)}</b> · ${esc(h.trait.description)}</p><p>能力 ${h.ability} · 经验 ${h.xp} · 成员 ${h.members} · 履历 ${h.cases.length}</p><p>${esc(h.busy || "空闲")} · 工资 ${money(h.weekly_salary)}/周</p>${personalCard(h)}<div class="actions">${button("专业培训", "train", { character: h.id }, "", !!h.busy)}${modalButton("配置团队", "team", h.id)}${modalButton("导师课题", "mentor", h.id)}</div>${h.rank < 4 ? `<h3>下次晋阶</h3><p>${checks(h.promotion)}</p><p>费用 ${money(h.promotion_cost)}</p>${button("晋阶突破", "promote", { character: h.id }, "primary", !!h.busy || !h.promotion.every((c) => c.ok))}` : "<p>已达传奇，可带教后辈。</p>"}`;
  }
  function roomPanel(id) {
    const equipment = state.equipment.filter(
      (r) => DrugstoryWorld.ROOMS[r.id] === id,
    );
    return `<button data-scene="overview">← 研究所总览</button><h2>${esc(names[id])}</h2><p>${esc(roomSummary(id))}</p>${!world.rooms[id]?.built ? "<p>目前在共用工位开展相关工作；扩建增加专用空间，不额外提高已有研发门槛。</p>" : ""}${state.heroes
      .filter((h) => h.activity !== "idle" && world.locate(h.room) === id)
      .map(
        (h) =>
          `<p><button data-scene-hero="${h.id}">${esc(h.name)} · ${esc(h.busy || h.activity)}</button></p>`,
      )
      .join(
        "",
      )}${id === "academy" ? '<p>完成个人课题升级招牌能力；导师带教帮助新伙伴成长。</p><button data-tab="characters">安排培养与个人课题</button>' : ""}${id === "hall" || id === "clinic" ? '<button data-tab="honors">年度大会与终局荣誉</button>' : ""}${id === "clinic" ? '<button data-tab="market">查看授权与合作</button>' : ""}${equipment.map((r) => `<article class="project-card"><h3>${esc(r.name)} · ${r.level} 级</h3><p>${esc(r.text)}</p>${r.cost ? button("升级设备 · " + money(r.cost), "upgrade_equipment", { profession: r.profession }, "primary", !r.available || r.cost > state.available_cash) : "已达最高级"}</article>`).join("")}<h3>${esc(state.facility.name)}</h3><p>团队 ${state.headcount}/${state.facility.capacity} · 自营临床 ${state.clinical_used}/${state.facility.slots}</p>${state.next_facility ? `<p>下一站 ${esc(state.next_facility.name)} · ${money(state.next_facility.cost)}；租金 ${money(state.next_facility.rent)}/周。</p><p>专用生物室 → 共研教室 → 大会与荣誉室逐步开放。</p>${button("扩建研究场地", "upgrade", {}, "primary", state.available_cash < state.next_facility.cost)}` : "星火科学城已建成。"}`;
  }
  function renderPanel() {
    if (!state) return;
    let html;
    if (selected?.type === "hero") {
      const h = state.heroes.find((h) => h.id === selected.id);
      if (h) html = heroPanel(h);
    }
    if (selected?.type === "room") html = roomPanel(selected.id);
    if (selected?.type === "project") {
      const p = state.projects.find((p) => p.id === selected.id);
      if (p)
        html = `<button data-scene="overview">← 所有项目</button>${projectCard(p)}`;
    }
    if (!html)
      html = (
        {
          pipeline,
          characters,
          services,
          market,
          competition: competitionView,
          honors: honorsView,
          journal,
        }[activeTab] || pipeline
      )();
    q("#app").innerHTML =
      `${state.game_over ? '<p class="warning">公司已停止经营；可以查看记录或备份后重开。</p>' : ""}<div id="view">${html}</div>`;
    for (const el of q("#app").querySelectorAll("canvas[data-portrait]")) {
      const h = state.heroes.find((h) => h.id === el.dataset.portrait);
      if (h) renderer.drawPortrait(el, h.look);
    }
    for (const el of document.querySelectorAll(".scene-nav [data-tab]"))
      el.classList.toggle("active", el.dataset.tab === activeTab);
  }
  function gallery() {
    pause();
    q("#modal-body").innerHTML =
      `<h2 id="modal-title">伙伴图鉴 · 20 位研究者</h2><button data-close class="modal-close" aria-label="关闭弹窗">×</button><p>从见习到传奇。点人物查看背景、招牌能力和加入条件。</p><div class="gallery-grid">${staticContent.roster.map((h) => `<button data-cast="${h.key}"><canvas data-cast-portrait="${h.key}" aria-hidden="true"></canvas><b>${esc(h.name)}</b><span>「${esc(h.nickname)}」</span><small>${state.heroes.some((p) => p.id === h.key) ? "已加入研究社" : ["", "见习", "精英", "大师", "传奇"][h.tier]}</small></button>`).join("")}</div>`;
    if (!q("#modal").open) q("#modal").showModal();
    for (const el of document.querySelectorAll("[data-cast-portrait]"))
      renderer.drawPortrait(
        el,
        staticContent.roster.find((h) => h.key === el.dataset.castPortrait)
          .look,
      );
  }
  function cast(id) {
    const h = state.heroes.find((h) => h.id === id);
    if (h) {
      q("#modal").close();
      select({ type: "hero", id });
      return;
    }
    const spec = staticContent.roster.find((h) => h.key === id),
      recruit = state.roster.find((h) => h.key === id);
    q("#modal-body").innerHTML =
      `<h2 id="modal-title">${esc(spec.name)}「${esc(spec.nickname)}」</h2><button data-close class="modal-close" aria-label="关闭弹窗">×</button><p>${esc(spec.bio)}</p><p>${esc(recruit?.trait?.name)} · ${esc(recruit?.trait?.description)}</p>${recruit ? `<p>${checks(recruit.requirements)}</p><p>邀请费用 ${money(recruit.cost)}</p>${button("邀请加入", "hire", { character: id }, "primary", !recruit.unlocked || recruit.cost > state.available_cash)}${modalButton("合作建立联系", "collaborate", id)}` : ""}<p><button data-scene="gallery">← 全部伙伴</button></p>`;
  }
  function help() {
    pause();
    q("#modal-body").innerHTML =
      '<h2 id="modal-title">从两个人，到一家研究所</h2><button data-close class="modal-close" aria-label="关闭弹窗">×</button><ol><li><b>立项：</b>点「新建研究计划」，先用两位起步伙伴做一款仿制药。先看预算，再确认。</li><li><b>开时间：</b>1×、2×、4×会逐周推进并保存；遇到决定自动停。刷新、切到后台或打开操作窗口也会停。</li><li><b>看证据：</b>橙色数字是团队开发，蓝色读数是验证。选候选、安排阶段、期中止损都在右侧操作。</li><li><b>养成与经营：</b>点小人或底栏人物卡进行培养；点房间升级设备和扩建。下方菜单可接服务、谈授权、报名大会。</li></ol><p>文字手记与场景使用同一份存档。画面中的走动只是表现，不会改变研发结果。</p><button data-close class="primary">知道了，开始经营</button>';
    if (!q("#modal").open) q("#modal").showModal();
  }
  document.addEventListener("click", async (e) => {
    const b = e.target.closest("button");
    if (!b || (!state && b.dataset.scene !== "reconnect")) return;
    if (b.dataset.tab) {
      pause();
      selected = null;
      renderer.select(null);
    }
    if (b.dataset.speed !== undefined) {
      const k = +b.dataset.speed;
      if (k && (driver.uncertain || state.game_over)) {
        pause();
        notice(
          driver.uncertain
            ? "请先重新连接，确认上次操作的保存结果。"
            : "公司已停止经营，可在经营复盘查看记录。",
        );
        return;
      }
      if (k && state.pending) {
        notice("先处理右侧决定，或暂缓项目后再推进。");
        return;
      }
      speed = k;
      accumulator = 0;
      renderer.setSpeed(k || 1);
      clock();
    }
    if (b.dataset.style) {
      renderer.setStyle(b.dataset.style);
      for (const x of document.querySelectorAll("[data-style]"))
        x.setAttribute("aria-pressed", String(x === b));
    }
    if (b.dataset.sceneHero) select({ type: "hero", id: b.dataset.sceneHero });
    if (b.dataset.sceneProject)
      select({ type: "project", id: b.dataset.sceneProject });
    if (b.dataset.cast) cast(b.dataset.cast);
    if (b.dataset.scene === "overview") {
      selected = null;
      renderPanel();
    }
    if (b.dataset.scene === "gallery") gallery();
    if (b.dataset.scene === "help") help();
    if (b.dataset.scene === "step" || b.dataset.scene === "next") {
      pause();
      await send(
        b.dataset.scene === "step" ? "advance" : "next_event",
        b.dataset.scene === "step" ? { weeks: 1 } : {},
      );
    }
    if (b.dataset.scene === "reconnect") {
      pause();
      if (requestBusy) return;
      requestBusy = true;
      try {
        const data = await driver.connect();
        staticContent = driver.content;
        state = hydrate(data);
        cursor = state.event_cursor;
        lastRevision = null;
        selected = null;
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
  document.addEventListener(
    "pointerdown",
    (e) => {
      if (e.target.closest("#app, #scene-people, #scene-projects")) pause();
    },
    true,
  );
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
  });
  window.addEventListener("pagehide", pause);
  document.addEventListener("keydown", (e) => {
    if (
      !state ||
      e.target.closest("input,select,textarea,button") ||
      q("#modal").open
    )
      return;
    if (e.code === "Space") {
      e.preventDefault();
      if (speed) pause();
      else if (!state.pending) {
        speed = 1;
        clock();
      }
    }
  });
  window.DrugstorySceneUI = { render, pause };
})();
