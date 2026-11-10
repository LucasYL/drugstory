/* 场景页右侧面板。常用操作压到一两次点击：
 * 决定卡上的主按钮直接执行引擎验证过的默认方案（快照里的 quick），技术服务默认派能力最低的合格伙伴。
 * 这里只读快照、发送已有命令，不推进时间、不做任何规则计算。 */
(() => {
  const RANK_CAP = [0, 48, 66, 83, 99];
  const DECIDE = ["selecting", "ready", "result", "problem", "checkpoint"];
  const heroOf = (id) => state.heroes.find((h) => h.id === id);
  const nameOf = (id) => heroOf(id)?.name || id;
  const args = (value) => esc(JSON.stringify(value));
  const cmd = (text, name, a, cls = "", disabled = false, title = "") =>
    `<button class="${cls}" data-command="${name}" data-args="${args(a)}" ${disabled ? "disabled" : ""} ${title ? `title="${esc(title)}"` : ""}>${text}</button>`;
  // 等玩家决定的项目；交给团队自动推进的不算
  const waiting = () =>
    state.projects.filter((p) => p.active && DECIDE.includes(p.status) && !p.autopilot);
  const PACE = { standard: "标准", rush: "加急", craft: "精工" };
  const tone = (p) =>
    ({
      selecting: "wait",
      ready: "wait",
      result: "good",
      problem: "bad",
      checkpoint: "wait",
      failed: "bad",
      screening: "run",
      running: "run",
      approved: "good",
      licensed: "good",
      terminated: "mute",
    })[p.status] || "mute";
  const statusPill = (p) =>
    `<span class="pill ${tone(p)}">${esc(p.status_name)}${p.deferred ? " · 暂缓" : ""}</span>`;

  /* ---------- 小部件 ---------- */
  // 「显示数字」：默认只显示词，数字放在悬停提示里；打开后词后面跟上数字
  function numbersOn() {
    try {
      return localStorage.getItem("drugstory.numbers") === "1";
    } catch {
      return false;
    }
  }
  function toggleNumbers() {
    try {
      localStorage.setItem("drugstory.numbers", numbersOn() ? "0" : "1");
    } catch {
      /* 存不了就只在这一页生效 */
    }
  }
  const WORD_TONE = { 很可能过: "ok", 大概率过: "ok", 可能过: "mid", 悬: "mid", 很难过: "no", 后面不考: "mute" };
  function evidenceWord(e) {
    const nums = `${e.low}–${e.high}${e.gate != null ? ` · 门槛 ${e.gate}（${e.gate_stage}）` : ""}`;
    return `<small class="word ${WORD_TONE[e.verdict] || ""}" title="${esc(nums)}">${esc(e.verdict)}${numbersOn() ? ` · ${e.low}–${e.high}` : ""}</small>`;
  }
  function phaseTrack(p) {
    if (p.status === "licensed") return "";
    return `<ol class="track">${p.path
      .map(
        (name, i) =>
          `<li class="${i < p.index || (i === p.index && ["result", "approved"].includes(p.status)) ? "done" : i === p.index ? "now" : ""}" title="${esc(name)}"><span>${esc(name)}</span></li>`,
      )
      .join("")}</ol>`;
  }
  // 区间条：灰底是可能范围，竖线是本阶段门槛
  function rangeBar(low, high, limit, lo, hi) {
    const x = (v) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
    const ok = limit == null ? "" : low >= limit ? "ok" : high < limit ? "no" : "mid";
    return `<span class="range ${ok}"><i style="left:${x(low)}%;width:${Math.max(2, x(high) - x(low))}%"></i>${limit == null ? "" : `<b style="left:${x(limit)}%"></b>`}</span>`;
  }
  function scaleOf(values) {
    const lo = Math.min(...values),
      hi = Math.max(...values);
    const pad = Math.max(40, (hi - lo) * 0.12);
    return [Math.floor((lo - pad) / 50) * 50, Math.ceil((hi + pad) / 50) * 50];
  }
  function resultBars(r) {
    if (!r) return "";
    const keys = Object.keys(r.values);
    const [lo, hi] = scaleOf(keys.flatMap((k) => [r.values[k], r.limits[k]]));
    return `<div class="result ${r.passed ? "pass" : "fail"}"><b>${r.passed ? "达到本阶段要求" : "未达到本阶段要求"}</b>${keys
      .map((k) => {
        const v = r.values[k],
          lim = r.limits[k];
        const x = (n) => Math.max(0, Math.min(100, ((n - lo) / (hi - lo)) * 100));
        const word = r.words?.[k] || "";
        return `<div class="bar-row"><span>${esc(state.stats[k])}</span><span class="bar ${v >= lim ? "ok" : "no"}" title="${num(v)} / 门槛 ${num(lim)}"><i style="width:${x(v)}%"></i><b style="left:${x(lim)}%"></b></span><small class="word ${v >= lim ? "ok" : "no"}" title="${num(v)} / 门槛 ${num(lim)}">${esc(word)}${numbersOn() ? ` · ${num(v)} / ${num(lim)}` : ""}</small></div>`;
      })
      .join("")}</div>`;
  }
  function candidateTags(p) {
    const score = p.candidates.map((c) => ({
      id: c.id,
      floor: Math.min(...c.evidence.map((e) => e.low)),
      ceiling: c.evidence.reduce((a, e) => a + e.high, 0),
    }));
    const steady = score.reduce((a, b) => (b.floor > a.floor ? b : a)).id;
    const upside = score.reduce((a, b) => (b.ceiling > a.ceiling ? b : a)).id;
    return (id) =>
      [id === steady ? "稳妥" : "", id === upside ? "潜力" : ""].filter(
        Boolean,
      );
  }
  function candidateTable(p) {
    const tags = candidateTags(p);
    const stats = p.candidates[0]?.evidence.map((e) => e.key) || [];
    const limits = p.scene?.limits || {};
    const [lo, hi] = scaleOf(
      p.candidates.flatMap((c) =>
        c.evidence.flatMap((e) => [e.low, e.high, ...(e.gate != null ? [e.gate] : [])]),
      ),
    );
    return `<div class="cands" style="--n:${p.candidates.length}"><div class="cands-head"><span></span>${p.candidates
      .map(
        (c) =>
          `<span><b>候选 ${c.id + 1}</b><small>${esc(c.label)}</small>${tags(c.id)
            .map((t) => `<em class="tag ${t === "稳妥" ? "steady" : "upside"}">${t}</em>`)
            .join("")}</span>`,
      )
      .join("")}</div>${stats
      .map(
        (k) =>
          `<div class="cands-row"><span class="stat">${esc(p.candidates[0].evidence.find((e) => e.key === k).name)}</span>${p.candidates
            .map((c) => {
              const e = c.evidence.find((x) => x.key === k);
              return `<span>${rangeBar(e.low, e.high, e.gate ?? limits[k], lo, hi)}${evidenceWord(e)}</span>`;
            })
            .join("")}</div>`,
      )
      .join(
        "",
      )}<div class="cands-foot"><span></span>${p.candidates
      .map((c) =>
        cmd(
          "选这个",
          "choose_candidate",
          { project: p.id, candidate: c.id },
          tags(c.id).includes("稳妥") ? "primary small" : "small",
        ),
      )
      .join("")}</div></div><p class="hint-line">灰条是可能的范围，竖线是门槛。范围越宽越不确定。</p>`;
  }
  // 某人还要忙几周：服务、培养看 jobs，项目看 left
  function busyFor(h) {
    const job = state.jobs.find((j) => j.heroes.includes(h.id));
    if (job) return job.left;
    const p = state.projects.find(
      (p) => p.team.includes(h.id) && ["screening", "running", "checkpoint"].includes(p.status),
    );
    return p ? p.left : null;
  }
  function busyNote(q) {
    const people = state.heroes.filter(
      (h) => h.busy && (q.roles || []).includes(h.profession),
    );
    if (!people.length) return q.error;
    return (
      "需要的人在忙：" +
      people
        .map((h) => {
          const left = busyFor(h);
          return `${h.name}（${h.busy}${left ? `，还剩 ${left} 周` : ""}）`;
        })
        .join("、")
    );
  }
  function cashNote(q) {
    if (!q.cost || q.command === "launch") return "";
    const after = state.available_cash - q.cost;
    const burn =
      state.costs_per_week + q.cost / Math.max(1, q.weeks || 1) - state.weekly_profit - state.weekly_royalty;
    if (after >= 300 && (burn <= 0 || after / burn >= 12)) return "";
    const weeks = burn > 0 ? Math.max(0, Math.floor(after / burn)) : null;
    return `<small class="warn cash">开工后可用现金 ${money(after)}${weeks != null ? `，按现在的开销约撑 ${weeks} 周` : ""}。可以先接服务或暂缓。</small>`;
  }
  function quickButton(p) {
    const q = p.quick;
    if (!q) return "";
    if (q.command === "launch") {
      return `<div class="launch"><label>药品名<input data-launch-name="${p.id}" value="${esc(p.name)}" maxlength="30"></label><button class="quick" data-launch="${p.id}" ${q.ok ? "" : "disabled"}><b>上市</b><small>准备费 ${money(q.cost)}</small></button>${q.ok ? "" : `<small class="warn">${esc(q.error)}</small>`}</div>`;
    }
    const team = q.args.heroes?.length
      ? q.args.heroes.map(nameOf).join("、")
      : q.args.mode === "cro"
        ? "外包 CRO"
        : "";
    const meta = [
      q.weeks ? `${q.weeks} 周` : "",
      q.cost != null ? money(q.cost) : "",
      q.level ? `成功机会${q.level}（${q.chance.replace("约 ", "")}）` : q.chance ? `成功率${q.chance}` : "",
      q.args.mode === "cro" && q.args.heroes?.length ? "CRO 执行" : "",
    ]
      .filter(Boolean)
      .join(" · ");
    if (!q.ok)
      return `<div class="quick blocked"><b>${esc(q.label)}</b><small>${esc(busyNote(q))}</small></div>`;
    const used = q.talents?.length ? `<small class="who talents">用上：${esc(q.talents.join("、"))}</small>` : "";
    return `<button class="quick" data-command="${q.command}" data-args="${args(q.args)}"><b>${esc(q.label)}</b><small>${esc(meta)}</small>${team ? `<small class="who">${esc(team)}</small>` : ""}${used}</button>${cashNote(q)}`;
  }
  // 难病的搭档关（阿尔茨海默是最后的难题），谁能过一目了然
  function gateBlock(list) {
    if (!list) return "";
    const label = { full: "已解决", partial: "部分解决", none: "缺人" };
    const nums = ["", "一", "两", "三", "四", "五"];
    return `<div class="gates"><b>${esc(list[0].title)} · ${nums[list.length] || list.length}道关</b>${list
      .map(
        (g) =>
          `<div class="gate ${g.state}"><span class="pill">${label[g.state]}</span><span><b>${esc(g.name)}</b> ${esc(g.problem)}<small>${g.state === "full" ? "" : `缺了：${esc(g.missing)}。`}${g.people.length ? `研究所里：${g.people.map(esc).join("、")}` : `完全解决：${esc(g.full)}；部分：${esc(g.partial)}`}</small></span></div>`,
      )
      .join("")}</div>`;
  }
  // 研究顾问：只在关键时刻出现，按钮直接安排对应的专项研究
  function advisor(p) {
    if (!p.advice?.length) return "";
    return p.advice
      .map(
        (t) =>
          `<div class="advisor ${t.kind}"><b>研究顾问</b><p>${esc(t.text)}</p>${t.command ? cmd(esc(t.label || "安排"), t.command, t.args, t.kind === "refine" ? "primary small" : "small", !t.ok, t.ok ? "" : t.error || "") : ""}${t.command && !t.ok && t.error ? `<small class="warn">${esc(t.error)}</small>` : ""}</div>`,
      )
      .join("");
  }
  // 传奇：退休倒计时和一次传承
  function legacyBlock(h) {
    if (h.tier !== 4) return "";
    const years = Math.ceil((h.retire_in || 0) / 48);
    const pupils = h.inherit_to.map((id) => state.heroes.find((x) => x.id === id)).filter(Boolean);
    return `<p class="hint-line">${h.retire_in > 0 ? `约 ${years} 年后退休。` : "这个月做完手上的事就退休。"}退休前可以把专长传给一位弟子（12 周、¥200 万）。</p>${pupils.length ? `<div class="act-row">${pupils.map((u) => cmd(`传承给${esc(u.name)}`, "inherit", { teacher: h.id, pupil: u.id }, "small", !!h.busy || !!u.busy)).join("")}</div>` : ""}`;
  }
  // 主动技能：能直接用在这个项目上的，列成次按钮
  function skillRow(p) {
    if (!p.skills?.length) return "";
    return `<div class="skill-row"><small>可用专长：</small>${p.skills
      .map((k) =>
        cmd(
          `${esc(k.hero_name)}·${esc(k.name)}${k.cost ? ` · ${money(k.cost)}` : ""}`,
          "use_skill",
          k.args,
          "small skill",
          false,
          k.text,
        ),
      )
      .join("")}</div>`;
  }
  function talentLine(p) {
    return p.talents_used?.length ? `<p class="hint-line talents">这一阶段用上的专长：${esc(p.talents_used.join("、"))}</p>` : "";
  }
  function deferButton(p) {
    return cmd(
      p.deferred ? "恢复提醒" : "暂缓",
      "defer",
      { project: p.id, waiting: p.deferred ? 0 : 1 },
      "ghost small",
      false,
      p.deferred ? "" : "先去做别的，时间可以继续走；未开工阶段不收费",
    );
  }

  /* ---------- 决定区：按项目状态给出主按钮和少量次要按钮 ---------- */
  function decision(p) {
    const result = p.results.at(-1);
    if (p.deferred) {
      if (p.quick?.ok && p.status !== "selecting")
        return `<p class="lead">${p.quick.command === "launch" ? "随时可以上市。" : "人和钱都够了，可以开工。"}</p>${quickButton(p)}<div class="act-row">${cmd("恢复提醒", "defer", { project: p.id, waiting: 0 }, "ghost small")}${modalButton("终止研究", "terminate", p.id, "ghost small danger")}</div>`;
      return `${p.quick && !p.quick.ok ? `<p class="hint-line">${esc(busyNote(p.quick))}</p>` : ""}<div class="act-row">${cmd("恢复，现在决定", "defer", { project: p.id, waiting: 0 }, "small")}${modalButton("终止研究", "terminate", p.id, "ghost small danger")}</div>`;
    }
    if (p.status === "selecting")
      return `${candidateTable(p)}<div class="act-row">${deferButton(p)}${modalButton("终止", "terminate", p.id, "ghost small danger")}</div>`;
    if (p.status === "checkpoint") {
      const v = p.trial_decision;
      // 只在已公开的期中估计很明确时提示一边；中间地带由玩家自己判断
      const lean =
        v.chance == null ? null : v.chance >= 35 ? "keep" : v.chance <= 15 ? "stop" : null;
      return `<div class="interim"><b>${esc(v.title)}</b><p>${esc(v.text)}</p>${p.interim_chance ? `<p class="hint-line">按已回数据，本阶段预计 ${esc(p.interim_chance)}${lean ? (lean === "keep" ? "，形势不错" : "，希望不大") : "，难说"}</p>` : ""}<div class="choice-grid">${v.choices
        .map((c) =>
          cmd(
            `<b>${esc(c.name)}</b><small>${esc(c.text)}</small>`,
            "trial_decision",
            { project: p.id, choice: c.key },
            c.key === lean ? "choice primary" : "choice",
          ),
        )
        .join("")}</div></div>`;
    }
    if (p.status === "ready")
      return `${gateBlock(p.gates)}${advisor(p)}${quickButton(p)}<div class="act-row">${p.quick && !p.quick.ok ? cmd("暂缓，等人空出来", "defer", { project: p.id, waiting: 1 }, "primary small") : ""}${modalButton("调整方案", "phase", p.id, "small")}${modalButton("专项研究", "experiment", p.id, "small")}${p.index < 2 ? modalButton("换候选", "switch", p.id, "small") : ""}${deferButton(p)}</div>`;
    if (p.status === "result") {
      const review = p.key === "review";
      return `${resultBars(result)}${talentLine(p)}${quickButton(p)}<div class="act-row">${review ? "" : modalButton("调整方案", "phase", p.id, "small")}${p.quotes.length ? modalButton(`授权报价 · ${p.quotes.length}`, "license", p.id, "small accent") : ""}${review ? "" : cmd("先放着", "continue_project", { project: p.id }, "ghost small", false, "进入下一阶段的准备状态，稍后再开工")}${deferButton(p)}</div>${p.kind === "innovative" && ["preclinical", "II"].includes(p.key) && !p.quotes.length ? '<p class="hint-line">证据还不够形成授权报价。</p>' : ""}`;
    }
    if (p.status === "problem" && p.incident)
      return `${incidentCard(p)}${resultBars(result)}${talentLine(p)}`;
    if (p.status === "problem")
      return `${resultBars(result)}${talentLine(p)}${quickButton(p)}<div class="act-row">${p.index < 2 ? modalButton("换候选重做", "switch", p.id, "small") : ""}${modalButton("止损", "terminate", p.id, "ghost small danger")}</div>`;
    if (p.status === "failed")
      return `${incidentCard(p)}${resultBars(result)}<p class="hint-line">研究记录和伙伴经验都保留。可以从新项目再出发。</p>`;
    return "";
  }

  // 失败事件卡：出了什么事、谁最懂、能怎么办
  function incidentCard(p) {
    const i = p.incident;
    if (!i) return "";
    const first = i.options.find((o) => o.ok && ["talent", "expert", "rework"].includes(o.kind));
    const option = (o) => {
      const meta = [o.weeks ? `${o.weeks} 周` : "", o.cost ? money(o.cost) : "", o.people.join("、")]
        .filter(Boolean)
        .join(" · ");
      const inner = `<b>${esc(o.label)}</b><small>${esc(meta)}</small><small class="who">${esc(o.note)}</small>`;
      // 推荐的那一项和其他决定卡的大按钮一样（.quick），回车执行的也是它
      const cls = `option ${o === first ? "primary quick" : ""} ${o.kind === "stop" ? "ghost danger" : ""}`;
      if (o.kind === "switch") return `<button class="${cls}" data-modal="switch" data-id="${p.id}" ${o.ok ? "" : "disabled"}>${inner}</button>`;
      if (o.kind === "stop") return `<button class="${cls}" data-modal="terminate" data-id="${p.id}">${inner}</button>`;
      return `<button class="${cls}" data-command="${o.command}" data-args="${args(o.args)}" ${o.ok ? "" : "disabled"}>${inner}</button>`;
    };
    const who = [`最懂的是${i.expert}`, i.talent ? `${i.talent}的专长对口` : ""].filter(Boolean).join("，");
    return `<div class="incident"><b class="incident-title">${esc(i.title)}</b><p>${esc(i.text)}</p><small>${esc(i.stat)}没过。${esc(who)}。</small>${i.options.length ? `<div class="incident-options">${i.options.map(option).join("")}</div>` : ""}</div>`;
  }

  function decisionCard(p) {
    return `<article class="card decide ${p.deferred ? "deferred" : ""}" data-project-card="${p.id}"><header><button class="title" data-scene-project="${p.id}"><b>${esc(p.name)}</b><small>${esc(p.kind_name)} · ${esc(p.phase)}</small></button>${statusPill(p)}</header>${p.deferred ? "" : `<p class="lead">${esc(leadText(p))}</p>`}${decision(p)}${p.deferred ? "" : skillRow(p)}</article>`;
  }
  function leadText(p) {
    return (
      {
        selecting: "候选资料到了。比较三张卡，选一个开始开发。",
        ready: p.question,
        result: p.key === "review" ? "审评通过。起个名字就能上市。" : "本阶段过关。下一步：" + (p.next_stage?.phase || "继续"),
        problem: p.incident ? "差一点。看看出了什么事，再决定怎么补。" : "差一点。可以补正一次再验证，不保证救回来。",
        checkpoint: "临床数据回来一半，决定后半程怎么走。",
      }[p.status] || p.feedback
    );
  }
  function runRow(p) {
    const total = p.scene.total || 1;
    const auto = p.autopilot ? `团队自主推进 · ${PACE[p.pace] || ""} · ` : "";
    const what = p.waiting || (p.running_experiment ? "专项研究" : p.status === "screening" ? "候选筛选" : p.phase);
    return `<button class="run-row ${p.waiting ? "waiting" : ""}" data-scene-project="${p.id}"><span class="dot ${p.scene.activity}"></span><span class="grow"><b>${esc(p.name)}</b><small>${esc(auto + what)}${p.scene.executor === "cro" ? " · CRO" : ""}</small><span class="progress"><i style="width:${Math.round((p.scene.elapsed / total) * 100)}%"></i></span></span><span class="left">${p.left} 周</span></button>`;
  }
  function pastRow(p) {
    return `<button class="past-row" data-scene-project="${p.id}"><b>${esc(p.name)}</b>${statusPill(p)}</button>`;
  }

  /* ---------- 研发：决定卡在最上面，然后是进行中的项目 ---------- */
  function desk() {
    const w = waiting(),
      running = state.projects.filter((p) => p.active && !w.includes(p)),
      past = state.projects.filter((p) => !p.active);
    const deals = state.deals.filter((d) => d.status === "developing");
    // 手机上第一张决定卡放在底部面板里，这里不再重复一次
    const shown = w.filter((p) => p.id !== sheet.id);
    return `${shown.map(decisionCard).join("")}<div class="sec-head"><h3>进行中</h3><button class="primary small" data-np-open>＋ 新项目</button></div>${
      running.map(runRow).join("") ||
      (w.length
        ? ""
        : `<div class="empty"><p>研究台空着。</p><button class="primary" data-np-open>${state.projects.length ? "开始下一个项目" : "开始第一个项目"}</button><small>${state.products.length ? "产品在卖，可以挑一条更难的路线，或者先培养伙伴。" : "也可以先接技术服务赚周转金。"}</small></div>`)
    }${nextSteps(running.length || w.length)}${deals.length ? `<div class="sec-head"><h3>合作方开发中</h3></div>${deals.map((d) => `<div class="run-row static"><span class="dot test"></span><span class="grow"><b>${esc(state.projects.find((p) => p.id === d.project)?.name || "")}</b><small>${esc(d.partner)} · 还需 ${d.left} 周</small></span></div>`).join("")}` : ""}${past.length ? `<details class="past"><summary>已结束 · ${past.length}</summary>${past.slice().reverse().map(pastRow).join("")}</details>` : ""}${money_line()}`;
  }
  // 接下来可以做：成长建议（晋阶、扩建、邀请、个人课题……），和左上角引导同源
  function nextSteps(busyDesk) {
    const items = (state.guide || []).filter((g) => busyDesk || g.kind !== "project");
    if (!items.length) return "";
    return `<div class="sec-head"><h3>接下来可以做</h3></div><div class="next-steps">${items
      .map((g) => window.DrugstorySceneUI.guideButton(g, `next-step ${g.chapter ? "chapter" : ""} ${g.ok ? "" : "blocked"}`))
      .join("")}</div>`;
  }
  const sheet = { id: null };
  function money_line() {
    const s = state;
    return `<div class="cashflow"><span>每周支出 <b>${money(s.costs_per_week)}</b></span><span>产品利润 <b>${money(s.weekly_profit)}</b></span>${s.weekly_royalty ? `<span>分成 <b>${money(s.weekly_royalty)}</b></span>` : ""}<span>${s.runway === null ? "收支为正" : `约可撑 <b>${s.runway}</b> 周`}</span></div>`;
  }

  /* ---------- 项目详情 ---------- */
  function project(p) {
    const current = p.candidates[p.chosen];
    const limits = p.scene?.limits || {};
    let evidenceBlock = "";
    if (current && p.active) {
      const ev = current.evidence;
      const [lo, hi] = scaleOf(
        ev.flatMap((e) => [e.low, e.high, ...(e.gate != null ? [e.gate] : limits[e.key] ? [limits[e.key]] : [])]),
      );
      evidenceBlock = `<section class="block"><h4>候选 ${current.id + 1} · ${esc(current.label)}<small>已优化 ${current.optimized}/2</small></h4>${ev
        .map(
          (e) =>
            `<div class="bar-row"><span>${esc(e.name)}</span>${rangeBar(e.low, e.high, e.gate ?? limits[e.key], lo, hi)}${evidenceWord(e)}</div>`,
        )
        .join(
          "",
        )}<p class="hint-line">竖线是门槛（当前阶段不考的，用后面最高的那个）。开发让灰条右移，验证让它变窄。</p></section>`;
    }
    const running = ["screening", "running"].includes(p.status);
    return `<button class="back" data-scene="overview">← 研发</button><article class="card detail"><header><div class="title"><b>${esc(p.name)}</b><small>${esc(p.kind_name)} · 已投入 ${money(p.spent)}</small></div>${statusPill(p)}</header>${phaseTrack(p)}${
      running
        ? `<div class="running-box"><span class="dot ${p.scene.activity}"></span><span class="grow"><b>${esc(p.running_experiment ? "专项研究" : p.status === "screening" ? "候选筛选" : p.phase)}</b><small>${p.team.map(nameOf).join("、") || "外包 CRO"} · 还需 ${p.left} 周</small><span class="progress"><i style="width:${Math.round((p.scene.elapsed / (p.scene.total || 1)) * 100)}%"></i></span></span></div>${p.interim_chance ? `<p class="hint-line">按已回数据，本阶段预计 ${esc(p.interim_chance)}</p>` : ""}`
        : ""
    }${DECIDE.includes(p.status) || p.status === "failed" ? decision(p) : ""}${
      p.status === "licensed"
        ? '<p class="hint-line">已授权给合作方，后续里程碑和分成在「产品」里看。</p>'
        : ""
    }${DECIDE.includes(p.status) ? "" : skillRow(p)}${autopilotBlock(p)}${evidenceBlock}${p.readings.length || p.work.length ? `<details class="block"><summary>分批数据与开发量</summary>${workList(p.work)}${p.readings
      .slice(-8)
      .reverse()
      .map(
        (r) =>
          `<p class="reading">第 ${r.week} 周 · ${esc(r.stage_name)} 第 ${r.index}/4 批：${Object.entries(
            r.values,
          )
            .map(([k, v]) => esc(state.stats[k]) + " " + v)
            .join(" / ")}</p>`,
      )
      .join("")}</details>` : ""}${productNote(p)}${p.active && !DECIDE.includes(p.status) ? "" : ""}${p.active ? `<div class="act-row end">${modalButton("终止研究", "terminate", p.id, "ghost small danger")}</div>` : ""}</article>`;
  }

  // 交给团队 / 接手
  function autopilotBlock(p) {
    if (!p.active || p.kind !== "generic") return "";
    if (p.autopilot)
      return `<div class="autopilot-box"><b>团队自主推进 · ${esc(PACE[p.pace] || "")}</b><small>${esc(p.waiting || "会自动选候选、开工、上市；遇到补正会停下来交给你。")}</small>${cmd("我来接手", "set_autopilot", { project: p.id, mode: "" }, "small")}</div>`;
    const ready = state.products.some((d) => d.kind === "generic" && !d.partner);
    if (!ready || !["ready", "result", "selecting", "screening", "running"].includes(p.status)) return "";
    return `<div class="act-row">${cmd("交给团队做完", "set_autopilot", { project: p.id, mode: p.pace || "standard" }, "small", false, "之后的选候选、开工、上市都由团队按推荐方案做")}</div>`;
  }
  function outlookLine(c) {
    const o = c.outlook;
    if (!o) return "";
    const coming = o.rivals_coming.map((r) => `${esc(r.name)}约第 ${r.eta_low}–${r.eta_high} 周上市`).join("、");
    return `<small class="outlook">每周利润约 ¥${Math.round(o.weekly_profit[0])}–${Math.round(o.weekly_profit[1])} 万 · 能卖约 ${o.years} 年</small>${o.rivals_selling || coming ? `<small class="outlook rival">${o.rivals_selling ? `对手在售 ${o.rivals_selling} 家` : ""}${o.rivals_selling && coming ? " · " : ""}${coming}</small>` : ""}`;
  }
  // 仿制药：选怎么做（标准 / 加急 / 精工），主按钮交给团队
  const handover = { mode: "standard" };
  function handoverBlock(c) {
    if (c.kind !== "generic") return "";
    if (!c.autopilot)
      return c.unlocked && !c.occupied && !state.products.some((d) => d.kind === "generic" && !d.partner)
        ? '<p class="hint-line">第一款仿制药亲手做一遍，之后可以交给团队做完。</p>'
        : "";
    const plan = c.autopilot[handover.mode];
    return `<fieldset class="seg pace" aria-label="怎么做">${Object.entries(PACE)
      .map(
        ([k, n]) =>
          `<label class="${handover.mode === k ? "on" : ""}"><input type="radio" name="autopilot" value="${k}" ${handover.mode === k ? "checked" : ""} data-pace="${k}"><b>${n}</b><small>约 ${c.autopilot[k].weeks} 周 · ${money(c.autopilot[k].cost)}</small></label>`,
      )
      .join("")}</fieldset><p class="hint-line">${esc(plan.note)}</p>`;
  }

  /* ---------- 新项目：选路线 → 点一张卡 → 开始 ---------- */
  const np = { route: "generic", target: "", pick: null, disease: null, custom: false };
  const ROUTE_NAMES = { generic: "仿制药", improved: "改良药", innovative: "创新药" };
  const openItems = (route) => state.catalog.filter((c) => c.kind === route && c.unlocked && !c.occupied);
  function firstRoute() {
    return ["generic", "improved", "innovative"].find((r) => openItems(r).length) || "generic";
  }
  // 当前路线没有能开始的项目时，说清楚为什么，并指向别的路线
  function routeNote(route, items) {
    if (openItems(route).length) return "";
    const taken = items.length && items.every((c) => c.occupied || !c.unlocked) && items.some((c) => c.occupied);
    const others = ["generic", "improved", "innovative"]
      .filter((r) => r !== route)
      .map((r) => {
        const n = openItems(r).length;
        if (n) return `<button class="small" data-np-route="${r}">去看${ROUTE_NAMES[r]} · ${n} 个可开始</button>`;
        const c = state.catalog.find((x) => x.kind === r && !x.occupied);
        const miss = c?.requirements.filter((q) => !q.ok).map((q) => q.text) || [];
        return miss.length ? `<small>${ROUTE_NAMES[r]}还差：${miss.map(esc).join("、")}</small>` : "";
      })
      .filter(Boolean)
      .join("");
    return `<div class="np-empty"><b>${ROUTE_NAMES[route]}${taken ? "都在研或在售了" : "还没有能开始的"}</b>${others}</div>`;
  }
  // 同领域对手：在售的抢走多少份额，在研的是谁
  function rivalLine(c) {
    const loss = Math.round((c.share_loss || 0) * 100);
    const selling = loss ? `同领域对手在售，份额约 −${loss}%` : "同领域对手：没有在售的";
    return selling + (c.announced_rivals.length ? ` · 在研：${c.announced_rivals.map(esc).join("、")}` : "");
  }
  function catalogStatus(c) {
    if (c.occupied) return ["在研或在售", "mute"];
    if (!c.unlocked) return ["待解锁", "mute"];
    return ["可开始", "good"];
  }
  function stars(tier) {
    return tier == null
      ? ""
      : `<em class="fit fit${tier}">${{ "-2": "不适配", "-1": "较差", 0: "一般", 1: "适配", 2: "很适配" }[tier]}</em>`;
  }
  // 疾病卡：领域分组，难度和市场用星，已攻克、委托中、还差什么
  function diseaseStatus(t) {
    const rows = t.routes.map((r) => state.catalog.find((c) => c.key === r.key)).filter(Boolean);
    const cured = state.chapters?.map?.some((m) => m.disease === t.disease && m.cured);
    const bounty = state.chapters?.bounties?.some((b) => b.disease === t.disease);
    if (rows.some((c) => c.unlocked && !c.occupied))
      return { cls: "good", text: cured ? "已攻克 ✓" : bounty ? "患者委托中 ✉" : "可开始", open: true };
    if (rows.length && rows.every((c) => c.occupied)) return { cls: "mute", text: "在研或在售" };
    const best = rows
      .map((c) => c.requirements.filter((q) => !q.ok).map((q) => q.text))
      .filter((m) => m.length)
      .sort((a, b) => a.length - b.length)[0];
    return { cls: "mute", text: best ? `还差：${best[0]}` : "待解锁" };
  }
  const star = (n) => "★".repeat(n) + "☆".repeat(Math.max(0, 5 - n));
  function diseaseGrid() {
    const groups = {};
    for (const t of state.targets || []) (groups[t.area] ||= []).push(t);
    return `${Object.entries(groups)
      .map(
        ([area, list]) =>
          `<h4 class="area">${esc(area)}</h4><div class="disease-cards">${list
            .map((t) => {
              const st = diseaseStatus(t);
              const hard = t.routes.some((r) => state.catalog.find((c) => c.key === r.key)?.gates);
              return `<button class="disease-card ${st.open ? "" : "locked"}" data-np-disease="${t.key}"><b>${esc(t.disease)}${hard ? ' <span class="pill wait">有搭档关</span>' : ""}</b><small>难度 ${star(t.difficulty_stars)} · 市场 ${star(t.market_stars)}</small><em>「${esc(t.quote)}」</em><span class="pill ${st.cls}">${esc(st.text)}</span></button>`;
            })
            .join("")}</div>`,
      )
      .join("")}<button class="ghost small custom-link" data-np-custom>自己设计组合（靶点 × 药物类型，${Object.keys(state.notebook).length} / 288 已记录）</button>`;
  }
  function routeList(t, items) {
    return `<button class="back" data-np-disease="">← 换一种病</button><div class="disease-head"><b>${esc(t.disease)}</b><small>${esc(t.name)} · ${esc(t.area)} · 难度 ${star(t.difficulty_stars)}</small><em>「${esc(t.quote)}」</em></div><p class="hint-line">研究界正在试的路线：</p><div class="cat-grid routes">${t.routes
      .map((r) => {
        const x = items.find((c) => c.key === r.key);
        if (!x) return "";
        const [label, cls] = catalogStatus(x);
        return `<button class="cat route ${x.key === np.pick ? "on" : ""}" data-np-pick="${x.key}"><b>${esc(r.name)}</b><small>约 ${r.years} 年 · ¥${num(r.cost)} 万起</small><span class="pill ${cls}">${label}</span>${stars(x.discovery?.tier)}</button>`;
      })
      .join("")}</div><button class="ghost small custom-link" data-np-custom>自己设计组合</button>`;
  }
  function picker(items, disease) {
    if (np.route === "innovative" && !np.custom) return disease ? routeList(disease, items) : diseaseGrid();
    const back = np.route === "innovative" ? '<button class="back" data-np-custom="0">← 按疾病选</button>' : "";
    return back + `${
      np.route === "innovative"
        ? `<label class="field">靶点<select data-np-target>${targets.map((t) => `<option ${t === np.target ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></label><p class="hint-line">组合手记 ${Object.keys(state.notebook).length} / 288 · 筛选后会记下这个组合是否适配。</p>`
        : ""
    }<div class="cat-grid">${items
      .map((x) => {
        const [label, cls] = catalogStatus(x);
        return `<button class="cat ${x.key === np.pick ? "on" : ""}" data-np-pick="${x.key}"><b>${esc(np.route === "innovative" ? x.modality : x.name)}</b><small>${esc(x.indication)}</small>${x.occupied ? "" : outlookLine(x)}<span class="pill ${cls}">${label}</span>${stars(x.discovery?.tier)}</button>`;
      })
      .join("")}</div>`;
  }
  function newProject() {
    const targets = [
      ...new Set(
        state.catalog.filter((c) => c.kind === "innovative").map((c) => c.target),
      ),
    ];
    if (np.route === "innovative" && !targets.includes(np.target))
      np.target =
        targets.find((t) =>
          state.catalog.some(
            (c) => c.target === t && c.unlocked && !c.occupied,
          ),
        ) || targets[0];
    // 创新药先选病，再从主流路线里选；288 格的自由组合收在「自己设计组合」里
    const diseaseMode = np.route === "innovative" && !np.custom;
    const disease = diseaseMode ? (state.targets || []).find((t) => t.key === np.disease) : null;
    const items = diseaseMode
      ? disease
        ? disease.routes.map((r) => state.catalog.find((c) => c.key === r.key)).filter(Boolean)
        : []
      : state.catalog.filter(
          (c) => c.kind === np.route && (np.route !== "innovative" || c.target === np.target),
        );
    if (!items.some((c) => c.key === np.pick))
      np.pick = (items.find((c) => c.unlocked && !c.occupied) || items[0])?.key;
    const c = state.catalog.find((x) => x.key === np.pick);
    const team = state.assist.screen[np.route] || [];
    const free = state.heroes.filter((h) => !h.busy);
    const canStart = c && c.unlocked && !c.occupied && team.length;
    return `<button class="back" data-scene="overview">← 研发</button><h2 class="panel-title">新项目</h2><div class="seg">${[
      ["generic", "仿制药", "稳，回本快"],
      ["improved", "改良药", "中等风险"],
      ["innovative", "创新药", "高风险高回报"],
    ]
      .map(
        ([k, n, sub]) =>
          `<button data-np-route="${k}" aria-pressed="${np.route === k}"><b>${n}</b><small>${sub}</small></button>`,
      )
      .join("")}</div>${routeNote(np.route, state.catalog.filter((c) => c.kind === np.route))}${picker(items, disease)}${
      c
        ? `<form class="card np" data-np-form><header><div class="title"><b>${esc(c.name)}</b><small>${esc(c.indication)} · ${esc(c.modality)}</small></div></header><p>${esc(c.description)}</p>${c.requirements.some((r) => !r.ok) ? `<div class="checks">${c.requirements.filter((r) => !r.ok).map((r) => `<span class="no">○ 还差：${esc(r.text)}</span>`).join("")}</div>` : ""}<p class="meta-line">${rivalLine(c)}${c.discovery?.reason ? " · " + esc(c.discovery.reason) : ""}${c.discovery?.mechanism != null ? ` · 叶清和看这条通路：机制偏移 ${c.discovery.mechanism > 0 ? "+" : ""}${c.discovery.mechanism}` : ""}</p>${gateBlock(c.gates)}<p class="meta-line">筛选团队：${team.map(nameOf).join("、") || esc(busyNote({ roles: np.route === "innovative" ? ["bio", "chem"] : ["chem", "proc"], error: "没有空闲的对应专业伙伴" }))}</p><details class="more"><summary>更多设置</summary><label class="field">开发侧重<select name="work_focus">${Object.entries(
            state.work_focuses,
          )
            .map(
              ([k, v]) =>
                `<option value="${k}">${esc(v.name)} · ${esc(v.text)}</option>`,
            )
            .join(
              "",
            )}</select></label>${c.product_profile ? `<label class="field">产品验证<select name="design"><option value="standard">标准开发</option><option value="validated">强化：${esc(c.product_profile.enhanced)}（关键阶段 +2 周、费用 +25%）</option></select></label><p class="hint-line">${esc(c.product_profile.title)}：${esc(c.product_profile.text)}</p>` : ""}<fieldset class="pick-team"><legend>筛选团队（最多 3 位）</legend>${free
            .map(
              (h) =>
                `<label><input type="checkbox" name="heroes" value="${h.id}" ${team.includes(h.id) ? "checked" : ""}><span>${esc(h.name)}<small>${esc(h.profession_name)} ${h.ability}</small></span></label>`,
            )
            .join(
              "",
            )}</fieldset></details>${handoverBlock(c)}${
              c.autopilot
                ? `<button class="quick" type="submit" ${canStart ? "" : "disabled"}><b>交给团队 · ${PACE[handover.mode]}</b><small>约 ${c.autopilot[handover.mode].weeks} 周 · ${money(c.autopilot[handover.mode].cost)} · 自动做到上市</small></button><button class="ghost small" type="submit" data-manual ${canStart ? "" : "disabled"}>我来一步步做</button>`
                : `<button class="quick" type="submit" ${canStart ? "" : "disabled"}><b>开始筛选</b><small>8 周 · ¥70 万 · 先找三个候选</small></button>`
            }</form>`
        : ""
    }`;
  }
  function newProjectArgs(form, submitter) {
    const data = new FormData(form);
    const c = state.catalog.find((x) => x.key === np.pick);
    const auto = c?.autopilot && !submitter?.hasAttribute("data-manual") ? data.get("autopilot") || "standard" : "";
    return {
      catalog: np.pick,
      heroes: data.getAll("heroes"),
      design: data.get("design") || "standard",
      work_focus: data.get("work_focus") || "balanced",
      ...(auto ? { autopilot: auto } : {}),
    };
  }

  /* ---------- 技术服务：每单一键，默认派能力最低的合格伙伴 ---------- */
  function services() {
    const picks = state.assist.services;
    const ready = state.orders.filter((o) => !o.taken && picks[o.id]?.hero);
    const quarterEnd = 12 - (state.week % 12);
    return `<div class="sec-head"><h3>技术服务</h3>${ready.length > 1 ? `<button class="primary small" data-services-all>全部接下 · ${ready.length} 单</button>` : ""}</div><p class="sub">本批订单还剩 ${quarterEnd} 周。默认派能力最低的合格伙伴，强的人留给研发；回款不看能力。</p>${state.orders
      .map((o) => orderCard(o, picks[o.id]))
      .join(
        "",
      )}<div class="sec-head"><h3>进行中的服务与培养</h3></div>${
      state.jobs.length
        ? state.jobs
            .map(
              (j) =>
                `<div class="run-row static"><span class="dot ${j.kind === "service" ? "service" : "study"}"></span><span class="grow"><b>${esc(j.name)}</b><small>${j.heroes.map(nameOf).join("、")}</small></span><span class="left">${j.left} 周</span></div>`,
            )
            .join("")
        : '<p class="sub">暂时没有。</p>'
    }`;
  }
  function orderCard(o, pick) {
    const head = `<div class="order-head"><b>${esc(o.name)}</b><span class="gain">+${money(o.reward)}</span></div><small class="meta-line">${o.weeks} 周 · 材料 ${money(o.cost)} · ${esc(state.professions[o.profession])}能力 ≥ ${o.requirement}</small>`;
    if (o.taken)
      return `<article class="order done">${head}<span class="pill good">已接单</span></article>`;
    const qualified = state.heroes
      .filter(
        (h) =>
          !h.busy &&
          h.profession === o.profession &&
          h.ability >= o.requirement,
      )
      .sort((a, b) => a.ability - b.ability);
    if (!qualified.length)
      return `<article class="order off">${head}<p class="note">${esc(pick?.note || "暂无合格的空闲伙伴")}</p></article>`;
    const note = pick?.hero
      ? pick.note
      : `${qualified.map((h) => h.name).join("、")}已推荐去接另一单；也可以改派到这单。`;
    return `<article class="order ${pick?.hero ? "" : "spare"}">${head}<div class="order-act"><select data-service-pick="${o.id}" aria-label="交付负责人">${qualified
      .map(
        (h) =>
          `<option value="${h.id}" ${h.id === pick?.hero ? "selected" : ""}>${esc(h.name)} · 能力 ${h.ability}</option>`,
      )
      .join(
        "",
      )}</select><button class="${pick?.hero ? "primary" : ""}" data-service-take="${o.id}">接单</button></div>${note ? `<small class="warn">${esc(note)}</small>` : ""}</article>`;
  }
  function serviceAssignments() {
    const picks = state.assist.services;
    return state.orders
      .filter((o) => !o.taken && picks[o.id]?.hero)
      .map((o) => ({ order: o.id, character: picks[o.id].hero }));
  }

  /* ---------- 伙伴 ---------- */
  function promotable(h) {
    return h.rank < 4 && h.promotion.every((c) => c.ok);
  }
  function activeBlock(h) {
    const a = h.active;
    if (!a) return "";
    const status = !a.unlocked ? a.note : a.ready_in ? `还要等 ${a.ready_in} 周` : a.choices.length ? "" : "现在没有能用的地方";
    return `<div class="active-skill"><b>主动 · ${esc(a.name)}</b><small>${esc(a.text)}${a.cost ? ` · ${money(a.cost)}` : ""} · 冷却 ${a.cooldown} 周</small>${status ? `<small class="hint-line">${esc(status)}</small>` : ""}${a.choices.length ? `<div class="act-row">${a.choices.map((c) => cmd(a.scope === "none" ? "使用" : `用在：${esc(c.label)}`, "use_skill", c.args, "small skill")).join("")}</div>` : ""}</div>`;
  }
  function trainButton(h, cls = "small") {
    const capped = h.ability >= Math.min(RANK_CAP[h.rank], h.potential);
    return cmd(
      `培训 · ${money(40 + h.rank * 20)}`,
      "train",
      { character: h.id },
      cls,
      !!h.busy || capped,
      capped ? "当前阶位能力已到上限，需要真实项目履历和晋阶" : "6 周，能力 +3",
    );
  }
  function team() {
    const f = state.facility;
    return `<div class="sec-head"><h3>伙伴 · ${state.heroes.length} 位</h3><button class="small" data-modal="roster">邀请新伙伴</button></div><p class="sub">团队 ${state.headcount}/${f.capacity} 人（含成员）。点头像看详情；能晋阶的人会亮起来。</p><div class="hero-list">${state.heroes
      .map(
        (h) =>
          `<article class="hero-row ${promotable(h) ? "glow" : ""}"><button class="who" data-scene-hero="${h.id}"><canvas data-portrait="${h.id}" aria-hidden="true"></canvas><span><b>${esc(h.name)}</b><small>${esc(h.rank_name)} · ${esc(h.profession_name)} ${h.ability}</small><small class="${h.busy ? "" : "free"}">${esc(h.busy || "空闲")}</small></span></button><span class="row-act">${promotable(h) ? cmd(`晋阶 · ${money(h.promotion_cost)}`, "promote", { character: h.id }, "primary small", !!h.busy) : ""}${h.busy ? "" : trainButton(h)}</span></article>`,
      )
      .join("")}</div>${facility()}`;
  }
  function facility() {
    const f = state.facility,
      n = state.next_facility;
    return `<div class="sec-head"><h3>研究所 · ${esc(f.name)}</h3></div><p class="sub">容纳 ${f.capacity} 人 · 自营临床席位 ${state.clinical_used}/${f.slots} · 租金 ${money(f.rent)}/周</p>${
      n
        ? `<div class="upgrade"><span><b>扩建为 ${esc(n.name)}</b><small>容纳 ${n.capacity} 人 · 租金 ${money(n.rent)}/周${n.upkeep ? ` · 平台维护 ${money(n.upkeep)}/周` : ""}</small></span>${cmd(`扩建 · ${money(n.cost)}`, "upgrade", {}, "primary small", state.available_cash < n.cost, state.available_cash < n.cost ? "可用现金不足" : "")}</div>`
        : '<p class="sub">已经是最高级的研究所。</p>'
    }<div class="equip">${state.equipment
      .map(
        (r) =>
          `<div class="upgrade"><span><b>${esc(r.name)} · ${r.level} 级</b><small>${esc(r.text)}</small></span>${r.cost ? cmd(`升级 · ${money(r.cost)}`, "upgrade_equipment", { profession: r.profession }, "small", !r.available || r.cost > state.available_cash) : '<span class="pill mute">满级</span>'}</div>`,
      )
      .join("")}</div>${investBlock()}`;
  }
  // 花钱的出口：青年学者计划、临床病房（产线和患者援助在产品卡上）
  function investBlock() {
    const v = state.investments;
    if (!v) return "";
    const f = v.fellowship,
      w = v.ward;
    return `<div class="sec-head"><h3>长远投入</h3></div><p class="sub">自有产线 ${v.lines.used}/${v.lines.total}（在产品卡上建）${v.upkeep ? ` · 运营 ${money(v.upkeep)}/周` : ""}</p><div class="upgrade"><span><b>青年学者计划 · ${f.done}/${f.max} 期</b><small>每期团队传承 +8 点；第 3 期起每期一位见习伙伴经验 +10${f.problem ? "。" + esc(f.problem) : ""}</small></span>${cmd(`办一期 · ${money(f.cost)}`, "fund_fellowship", {}, "small", !f.ok)}</div><div class="upgrade"><span><b>临床病房 · ${w.done}/${w.max}</b><small>自营临床席位 +1 · 运营 ${money(w.upkeep)}/周${w.problem ? "。" + esc(w.problem) : ""}</small></span>${cmd(`建一个 · ${money(w.cost)}`, "build_ward", {}, "small", !w.ok)}</div>`;
  }
  function hero(h) {
    const ready = promotable(h);
    const okCount = h.promotion.filter((c) => c.ok).length;
    return `<button class="back" data-scene="overview">← 伙伴</button><article class="card detail hero-card2"><header class="hero-head"><canvas data-portrait="${h.id}" class="big" aria-hidden="true"></canvas><div><h2>${esc(h.name)}<small>「${esc(h.nickname)}」</small></h2><p>${esc(h.rank_name)} · ${esc(h.profession_name)}</p><span class="meter"><i style="width:${Math.min(100, h.ability)}%"></i></span><small>能力 ${h.ability} / 阶位上限 ${Math.min(RANK_CAP[h.rank], h.potential)} · 潜力 ${h.potential} · 经验 ${h.xp} · 成员 ${h.members} · 履历 ${h.cases.length}</small></div></header><p class="status-line">${h.busy ? `<span class="dot make"></span>正在：${esc(h.busy)}` : '<span class="dot idle"></span>空闲，可以安排工作'} · 工资 ${money(h.weekly_salary)}/周</p><div class="act-row">${h.rank < 4 ? cmd(`晋阶${["", "", "精英", "大师", "传奇"][h.rank + 1]} · ${money(h.promotion_cost)}`, "promote", { character: h.id }, ready ? "primary small" : "small", !!h.busy || !ready) : ""}${trainButton(h)}${modalButton("团队成员", "team", h.id, "small")}${modalButton("带教", "mentor", h.id, "small")}</div><section class="block"><h4>专长 · ${esc(h.trait.name)}${h.awakened ? '<small class="good">已觉醒</small>' : ""}</h4><p>${esc(h.trait.description)}</p>${h.talent_uses?.total ? `<p class="hint-line">今年用上 ${h.talent_uses.year} 次 · 累计 ${h.talent_uses.total} 次</p>` : ""}${activeBlock(h)}<p class="${h.awakened ? "" : "hint-line"}">${h.awakened ? "觉醒" : "大师后完成个人课题即觉醒"}：${esc(h.trait.awaken)}</p>${h.inherited.map((t) => `<p><b>传承 · ${esc(t.name)}</b> ${esc(t.description)}</p>`).join("")}${legacyBlock(h)}</section>${personalCard(h)}${h.rank < 4 ? `<details class="block" ${ready ? "open" : ""}><summary>晋阶条件 ${okCount}/${h.promotion.length}</summary><p>${checks(h.promotion)}</p></details>` : '<p class="hint-line">已达传奇，可以带教后辈。</p>'}<details class="block"><summary>背景</summary><p>${esc(h.story)}</p><p>${esc(h.bio)}</p></details></article>`;
  }

  /* ---------- 房间 ---------- */
  function room(id, names, summary, built) {
    const equipment = state.equipment.filter(
      (r) => DrugstoryWorld.ROOMS[r.id] === id,
    );
    const people = state.heroes.filter(
      (h) => h.activity !== "idle" && h.room && DrugstoryWorld.ROOMS[h.room] === id,
    );
    return `<button class="back" data-scene="overview">← 返回</button><h2 class="panel-title">${esc(names[id])}</h2><p class="sub">${esc(summary)}</p>${!built ? '<p class="hint-line">扩建后开放专用空间。之前相关工作在共用工位进行，研发门槛不变。</p>' : ""}${people.map((h) => `<button class="run-row" data-scene-hero="${h.id}"><canvas data-portrait="${h.id}" class="mini" aria-hidden="true"></canvas><span class="grow"><b>${esc(h.name)}</b><small>${esc(h.busy || "")}</small></span></button>`).join("")}${equipment.map((r) => `<div class="upgrade"><span><b>${esc(r.name)} · ${r.level} 级</b><small>${esc(r.text)}</small></span>${r.cost ? cmd(`升级 · ${money(r.cost)}`, "upgrade_equipment", { profession: r.profession }, "primary small", !r.available || r.cost > state.available_cash) : '<span class="pill mute">满级</span>'}</div>`).join("")}${id === "academy" ? '<p class="hint-line">个人课题和带教在这里进行。去「伙伴」安排。</p>' : ""}${id === "hall" ? '<button class="small" data-tab="honors">年度大会与荣誉</button>' : ""}${facility()}`;
  }

  window.DrugstoryPanels = {
    desk,
    decisionCard,
    sheet,
    project,
    newProject,
    newProjectArgs,
    services,
    serviceAssignments,
    team,
    hero,
    room,
    np,
    handover,
    numbersOn,
    toggleNumbers,
    waiting,
    firstRoute,
  };
})();
