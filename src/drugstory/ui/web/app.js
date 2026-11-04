"use strict";

let state;
let activeView = "pipeline";
let busy = false;
let noticeTimer;
let selectedMilestone = null;
let selectedPlan = "boost";
const app = document.querySelector("#app");
const modal = document.querySelector("#modal");
const modalBody = document.querySelector("#modal-body");
const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const e = escapeHTML;
const number = (value, digits = 0) =>
  Number(value).toLocaleString("zh-CN", { maximumFractionDigits: digits });
const money = (value) => `¥${number(value, 1)} 万`;
const stats = ["efficacy", "druggability", "safety", "manufacturability"];
const attrs = ["bio", "chem", "tox", "proc"];
const stageNames = {
  research: "研发中",
  rd_review: "研发评估",
  clinical: "临床中",
  clinical_queue: "临床排队",
  phase_review: "阶段决策",
  naming: "等待上市",
  approved: "已获批",
  failed: "未通过",
  terminated: "已终止",
  cancelled: "已取消",
};
const nav = [
  ["pipeline", "研发管线"],
  ["teams", "团队"],
  ["contracts", "外包"],
  ["technology", "技术"],
  ["drugs", "药品"],
  ["company", "经营手记"],
];
const disabled = (condition) => (condition ? " disabled" : "");
const actionButton = (text, name, args = {}, opts = "") =>
  `<button data-action="${e(name)}" data-args="${e(JSON.stringify(args))}" ${opts}${disabled(state.game_over && !["new_game", "save"].includes(name))}>${text}</button>`;
const modalButton = (text, name, id = "", opts = "") =>
  `<button data-modal="${e(name)}" data-id="${e(id)}" ${opts}>${text}</button>`;
const badge = (text, tone = "") =>
  `<span class="badge ${tone}">${e(text)}</span>`;
const empty = (title, text, button = "", symbol = "↗") =>
  `<div class="empty"><div class="symbol">${symbol}</div><h3>${title}</h3><p>${text}</p>${button}</div>`;
const sectionHead = (title, subtitle, button = "") =>
  `<div class="section-head"><div><h1>${title}</h1><p>${subtitle}</p></div>${button}</div>`;
const statGrid = (values, keys = stats) =>
  `<div class="stat-grid">${keys.map((k) => `<div class="stat"><span>${e(state.names[keys === stats ? "stats" : "attrs"][k])}</span><strong>${number(values[k] || 0)}</strong></div>`).join("")}</div>`;
const projectById = (id) => state.projects.find((p) => p.id === Number(id));
const teamById = (id) => state.teams.find((t) => t.id === Number(id));
const activeProjects = () => state.projects.filter((p) => p.active);
const idleTeams = () => state.teams.filter((t) => !t.task);

function notify(text, error = false) {
  const box = document.querySelector("#notice");
  box.textContent = text;
  box.className = error ? "error" : "";
  box.hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(
    () => {
      box.hidden = true;
    },
    error ? 8000 : 3200,
  );
}

async function refresh() {
  try {
    const response = await fetch("/api/state");
    if (!response.ok)
      throw new Error("暂时无法连接游戏，请确认本地服务仍在运行。");
    state = await response.json();
    render();
  } catch (error) {
    notify(error.message, true);
    if (!state)
      app.innerHTML = empty(
        "暂时没有连上游戏",
        "请确认本地服务已启动，然后重新连接。",
        "<button data-refresh>重新连接</button>",
      );
  }
}

async function send(name, args = {}) {
  if (busy) return false;
  busy = true;
  document.querySelectorAll("button").forEach((b) => {
    b.dataset.wasDisabled = b.disabled ? "1" : "0";
    b.disabled = true;
  });
  try {
    const response = await fetch("/api/action", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Game-Token": state.token,
      },
      body: JSON.stringify({ name, args, revision: state.revision }),
    });
    const data = await response.json();
    if (!response.ok) {
      if (data.state) {
        state = data.state;
        modal.close();
        render();
      }
      throw new Error(data.error || "操作没有完成，请重试。");
    }
    state = data;
    modal.close();
    if (name === "start_project" || name === "new_game")
      activeView = "pipeline";
    if (name === "hire_candidate" && args.index >= 0) activeView = "teams";
    render();
    if (name === "save") notify("进度已保存");
    if (name === "new_game") notify("新公司成立。上一局已备份到本地存档目录。");
    if (name === "hire_candidate" && args.index >= 0)
      notify(
        args.members
          ? "负责人和成员已到位，可以安排研发。"
          : "负责人已加入。先给团队加人，再安排项目。",
      );
    if (state.pending.length && name === "advance")
      document
        .querySelector("#decision")
        ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    return true;
  } catch (error) {
    const text =
      error instanceof TypeError
        ? "连接中断。重新连接后请先核对进度，再继续操作。"
        : error.message;
    notify(text, true);
    const inline = modal.querySelector(".inline-error");
    if (inline) {
      inline.textContent = text;
      inline.hidden = false;
    }
    return false;
  } finally {
    busy = false;
    document.querySelectorAll("button[data-was-disabled]").forEach((b) => {
      b.disabled = b.dataset.wasDisabled === "1";
      delete b.dataset.wasDisabled;
    });
  }
}

function render() {
  const openDetails = new Set(
    [...app.querySelectorAll("details[open]")].map((d) => d.dataset.key),
  );
  const stopped = state.game_over || state.pending.length > 0;
  const mainViews = {
    pipeline: renderPipeline,
    teams: renderTeams,
    contracts: renderContracts,
    technology: renderTechnology,
    drugs: renderDrugs,
    company: renderCompany,
  };
  app.innerHTML = `<div class="shell">
    <div class="timebar"><div><span class="eyebrow">RESEARCH JOURNAL / 研发手记</span><div class="date">${e(state.date)}</div><div class="status-line"><span class="status-dot"></span>${state.game_over ? "公司已破产 · 可以查看这一局的记录" : state.pending.length ? `${state.pending.length} 件事等待你的决定` : "时间暂停中，准备好后再继续"}</div></div><div class="time-actions">
      ${actionButton("推进 1 周", "advance", { weeks: 1 }, disabled(stopped))}
      ${actionButton("继续 4 周", "advance", { weeks: 4 }, disabled(stopped))}
      ${actionButton("下一件事 →", "advance", { weeks: 48 }, `class="primary" title="最多推进一年，遇到决策即停下"${disabled(stopped)}`)}
    </div></div>
    <section class="metrics" aria-label="公司概况">
      ${metric("现金", `${number(state.cash)}<small> 万</small>`, state.cash_weeks === null ? "当前经营收支为正" : `按当前收支约 ${number(state.cash_weeks)} 周`, state.cash < 0 ? "negative" : "")}
      ${metric("项目已承诺", `${number(state.committed)}<small> 万</small>`, `扣除后余 ${number(state.uncommitted)} 万 · 不含工资租金`, state.uncommitted < 0 ? "negative" : "")}
      ${metric("研究数据", number(state.data), "解锁技术 / 培养负责人")}
      ${metric("公司口碑", `${number(state.reputation)}<small> / 100</small>`, `已获批 ${state.drugs.length} 个药物`)}
      ${metric("团队与场地", `${state.headcount}<small> / ${state.capacity} 人</small>`, e(state.facility.name))}
    </section>
    <div class="layout"><main class="main">
      ${state.game_over ? `<section class="decision"><span class="eyebrow">本次创业结束</span><h2>现金未能撑到下一次转机</h2><p class="small">获批 ${state.score.approvals} 个药 · 综合得分 ${state.score.score} · 累计利润 ${money(state.score.profit)}</p>${modalButton("开始一家新公司", "new-game", "", 'class="primary"')}</section>` : renderDecision()}
      <nav class="tabs" aria-label="经营菜单">${nav.map(([key, title]) => `<button data-view="${key}" class="${activeView === key ? "active" : ""}" aria-current="${activeView === key ? "page" : "false"}">${title}${key === "pipeline" && activeProjects().length ? `<span class="count">${activeProjects().length}</span>` : key === "teams" ? `<span class="count">${state.teams.length}</span>` : ""}</button>`).join("")}</nav>
      <section id="view">${mainViews[activeView]()}</section>
    </main><aside class="aside">${renderAside()}</aside></div>
  </div>`;
  app.querySelectorAll("details").forEach((d) => {
    if (openDetails.has(d.dataset.key)) d.open = true;
  });
  document.querySelector("#save-status").textContent = state.saved_at
    ? "✓ 进度已保存"
    : "本地进度已载入";
}

function metric(label, value, sub, tone = "") {
  return `<div class="metric"><span class="label">${label}</span><strong class="${tone}">${value}</strong><span class="sub">${sub}</span></div>`;
}

function renderAside() {
  let suggestion =
    "研发、临床和现金需要一起看。做下一项决定前，先留出工资和租金。";
  if (!state.projects.length)
    suggestion =
      "第一步，立一个 EGFR × 小分子项目。再招一位毒理负责人，补上安全性这块短板。";
  else if (!state.teams.some((t) => t.specialty === "tox"))
    suggestion =
      "目前还没有毒理组。尽早招聘毒理负责人，并把新团队安排进研发项目。";
  else if (idleTeams().length)
    suggestion = `${idleTeams().length} 个团队现在空闲。可以补进在研项目，或趁临床期间接一笔外包。`;
  if (state.uncommitted < 0)
    suggestion =
      "现有项目的后续花费已经超过现金。考虑外包回款，或在阶段决策时终止希望不大的项目。";
  return `<h2 class="aside-title">给创始人的便签</h2><div class="note"><strong>${state.drugs.length ? "下一次突破，从这里开始。" : "先让第一款药走出实验室。"}</strong><p>${suggestion}</p></div>
    <div class="note"><strong>现金流速览</strong><p>工资与租金 <b>${money(state.monthly_overhead)}/月</b><br>研发与临床 ${money(state.weekly_project_cost)}/周<br>在售药物利润 <span class="positive">${money(state.weekly_sales_profit)}/周</span></p><p class="small muted">现金可支撑周数按当前净开销粗估，不含未来临床升级、外包回款或销量变化。</p></div>
    <h2 class="aside-title">公司日志 <span class="muted small">最近 ${Math.min(state.messages.length, 18)} 条</span></h2><ol class="activity">${state.messages
      .slice(-18)
      .reverse()
      .map((m) => `<li><time>${e(m.date)}</time>${e(m.text)}</li>`)
      .join("")}</ol>`;
}

function routeNote(route) {
  return `<div class="hint ${route.tier < 0 ? "warn" : ""}"><b>路线适配：${e(route.name)} · 研发产出 ×${number(route.multiplier, 1)}</b><br>${e(route.reason)}${!route.allowed ? "<br>这条路线不开放新项目。已有项目可进入临床或终止。" : ""}</div>`;
}

function polishNote(p) {
  const x = p.polish;
  if (!x.remaining)
    return `<div class="hint warn">已打磨 ${x.used} 次（上限 ${x.limit} 次）。请根据上方预估进入临床，或终止并换路线、补齐专业团队后重新立项。</div>`;
  const next = x.forecasts.find((f) => f.key === "III");
  return `<div class="hint"><b>再打磨 ${state.extension_weeks} 周能得到什么？</b><br>${stats.map((k) => `${e(state.names.stats[k])}约 +${number(x.gains[k])}`).join(" / ")}<br>研发费＋全公司工资租金约 ${money(x.cash_cost)}（未计其他项目和收入）。${next ? `届时 III 期疗效预估 ${next.scores.efficacy} 分。` : ""}<br>已用 ${x.used} / ${x.limit} 次。各项超过 ${number(p.quality_knee)} 后增益逐渐放缓，优先补短板。增益按当前团队估算，未计升级、随机波动和隐患。</div>`;
}

function fundingNote(p) {
  return `<div class="hint ${p.cash_after_reserve < 0 ? "warn" : ""}">临床期间全公司工资租金另需约 ${money(p.operating_reserve)}。预留所有现有项目预算和这段工资租金后，现金余量约 <b>${money(p.cash_after_reserve)}</b>。${p.cash_after_reserve < 0 ? "建议先安排回款，再决定是否推进。" : ""}<br><span class="small muted">按当前团队估算，未计未来销售、外包回款或新项目。</span></div>`;
}

function outputNote(t) {
  return `<p class="small">每周基础产出：${stats.map((k) => `${e(state.names.stats[k])} ${number(t.weekly_output[k], 1)}`).join(" / ")}<br><span class="muted">各团队相加后，再乘路线与熟练度系数。成员提高研发产出和攻关收益，临床周期固定。</span></p>`;
}

function updateMembersEstimate() {
  const form = document.querySelector("#members-form");
  if (!form) return;
  const t = teamById(form.dataset.id);
  const count = Math.max(0, Number(new FormData(form).get("count")) || 0);
  const members = t.members + count;
  const r = state.team_rules;
  const factor =
    1 +
    r.member_weight *
      (Math.min(members, t.lead.leadership) +
        r.overflow_weight * Math.max(0, members - t.lead.leadership)) **
        r.member_exponent;
  document.querySelector("#members-estimate").textContent =
    `若增加 ${count} 人：团队产出 ×${number(t.size_factor, 2)} → ×${number(factor, 2)}（约 +${number((factor / t.size_factor - 1) * 100)}%），月薪 ${money(t.salary)} → ${money(t.salary + count * r.member_salary)}。增加人数的收益逐渐递减。`;
}

function forecastTable(p) {
  if (!p.forecasts.length) return "";
  return `<div class="table-scroll"><table><thead><tr><th>阶段</th>${stats.map((k) => `<th>${e(state.names.stats[k])}</th>`).join("")}<th>过关预估</th></tr></thead><tbody>${p.forecasts.map((f) => `<tr><td title="预计结束：${e(f.finish)}">${e(f.name)}</td>${stats.map((k) => `<td class="${f.scores[k] !== undefined && f.scores[k] < (f.requirements[k] || 0) ? "fail" : ""}">${f.scores[k] ?? "—"}${f.requirements[k] ? `<small class="muted"> / ≥${f.requirements[k]}</small>` : ""}</td>`).join("")}<td class="${f.passed ? "pass" : "fail"}">${f.passed ? (f.margin_ok ? "达标 · 有余量" : "达标 · 仍有风险") : "尚未达标"}${f.total_required ? `<small> · 合计 ≥${f.total_required}</small>` : ""}</td></tr>`).join("")}</tbody></table></div><p class="small muted">审批门槛不随年份上涨。分数按现有属性估算，未扣隐患；「有余量」表示各项随机 −1 仍能达标。${p.stage === "research" ? "研发期间属性还会增长。" : "达标不保证过关，临界分数仍有风险。"}</p>`;
}

function resultBlock(result) {
  return `<div class="scores">${Object.entries(result.scores)
    .map(
      ([k, v]) =>
        `<div class="score"><span>${e(state.names.stats[k])}专家</span><strong>${v}<small> / 10</small></strong></div>`,
    )
    .join(
      "",
    )}</div><p class="result-text">${e(result.text)}</p>${result.hazard_texts.map((t) => `<div class="hint warn">${e(t)}</div>`).join("")}`;
}

function renderDecision() {
  const d = state.pending[0];
  if (!d) return "";
  const p = projectById(d.project_id);
  const args = { decision_id: d.id };
  let title = "",
    subtitle = p?.label || "",
    body = "";
  if (d.kind === "milestone") {
    title = state.names.milestones[d.data.stat];
    if (selectedMilestone !== d.id) {
      selectedMilestone = d.id;
      selectedPlan = "boost";
    }
    const labels = {
      boost: "深挖性能",
      validate: "专项验证",
      fast: "尽快定型",
    };
    const descriptions = {
      boost: "提高本项属性，追加研发时间和专项费用。",
      validate: "排除已知隐患，放弃本次属性加成；对应专业需 ≥30。",
      fast: "缩短剩余研发时间，放弃本次属性加成，保留未解决风险。",
    };
    body = `<p>先选方案，再选负责人。负责人特长会改变时间、费用与效果。</p><div class="actions">${Object.entries(
      labels,
    )
      .map(
        ([key, label]) =>
          `<button data-milestone-plan="${key}" aria-pressed="${key === selectedPlan}" class="${key === selectedPlan ? "primary" : ""}">${label}</button>`,
      )
      .join(
        "",
      )}</div><p class="small muted">${descriptions[selectedPlan]}</p>${p.hazards.length ? `<div class="hint warn">待解决：${p.hazards.map((h) => `${e(h.text)}（${h.severity >= 2 ? "严重，需专项处理" : "轻微"}）`).join("、")}</div>` : ""}<div class="choice-grid">${d.options
      .map((o) => {
        const x = o.plans[selectedPlan];
        return `<div class="card"><h3>${e(o.name)} · ${e(o.type)}</h3><p class="small"><b>${e(o.trait.name)}</b>：${e(o.trait.description)}</p><p>${e(state.names.stats[d.data.stat])} +${number(x.bonus, 1)}<br>研发工期 ${x.weeks > 0 ? "+" : ""}${x.weeks} 周 · 专项费用 ${money(x.cost)}<br>排除 ${x.hazard_ids.length} 项隐患</p>${x.problem ? `<p class="small fail">${e(x.problem)}</p>` : ""}${actionButton(`由${e(o.name)}执行${labels[selectedPlan]}`, "choose_milestone_team", { ...args, team_id: o.team_id, plan: selectedPlan }, disabled(Boolean(x.problem) || (x.cost > 0 && state.cash < x.cost)))}</div>`;
      })
      .join(
        "",
      )}</div><p class="small muted">专项费用之外，增减工期也会改变研发费、工资和租金；例行药效验证与工艺节点会自动完成。</p>`;
  } else if (d.kind === "rd_end") {
    title = "研发结束，准备进入临床吗？";
    const total = p.forecasts.reduce((a, f) => a + f.cost, 0),
      weeks = p.forecasts.reduce((a, f) => a + f.weeks, 0);
    body = `${routeNote(p.route)}${statGrid(p.stats)}${p.hazards.length ? `<div class="hint warn">剩余隐患：${p.hazards.map((h) => `${e(h.text)}（${e(state.names.stats[h.stat])} −${h.severity}${h.severity >= 2 ? "，需专项排险" : ""}）`).join("、")}</div>` : '<div class="hint">目前没有未解决的隐患。</div>'}${forecastTable(p)}${polishNote(p)}${fundingNote(p)}<p class="small">后续临床与审评约 <b>${weeks} 周 / ${money(total)}</b>。自营临床空余 ${state.clinical_operations.available} 个席位；委托临床费用高 30%，无需等待且不提高通过分数。排队或进入临床后，研发团队全部空出来。</p><div class="actions">${actionButton(state.clinical_operations.available ? "进入自营临床 →" : "加入临床队列 →", "resolve_rd_end", { ...args, choice: "proceed" }, 'class="primary"')}${actionButton(`委托临床 · 全程约 ${money(p.contract_cost)}`, "resolve_rd_end", { ...args, choice: "contract" })}${p.validation.available ? actionButton(`专项排险 ${p.validation.weeks} 周 · ${money(p.validation.cost)}`, "resolve_rd_end", { ...args, choice: "validate" }, disabled(state.cash < p.validation.cost)) : ""}${actionButton(`再打磨 ${state.extension_weeks} 周（剩 ${p.polish.remaining} 次）`, "resolve_rd_end", { ...args, choice: "extend" }, disabled(!p.team_ids.length || !p.polish.remaining))}${actionButton("终止项目", "resolve_rd_end", { ...args, choice: "terminate" }, 'class="danger" data-confirm="终止后不再花钱，已花费用不会退回，熟练度照常增加。"')}</div>`;
  } else if (d.kind === "phase_result") {
    const result = p.results.findLast((r) => r.phase === d.data.phase);
    title = `${p.phase_name}结果 · ${d.data.passed ? "通过" : "未通过"}`;
    body = resultBlock(result);
    if (d.data.passed) {
      const next = p.forecasts[0];
      body += `<p class="small">下一步：<b>${e(next.name)}</b>，${next.weeks} 周 / ${money(next.cost)}。</p>${forecastTable(p)}<div class="actions">${actionButton(`继续${e(next.name)} →`, "resolve_phase", { ...args, choice: "continue" }, 'class="primary"')}${actionButton("到此为止", "resolve_phase", { ...args, choice: "terminate" }, 'class="danger" data-confirm="终止后无法恢复这个项目，熟练度照常增加。"')}</div>`;
    } else
      body += `<div class="hint warn">未过关原因：${d.failure_reasons.map(e).join("；")}。</div><div class="hint">这次尝试积累的研究数据和熟练度会留下来。可以查看项目记录，调整下一次的团队配置。</div><div class="actions">${actionButton("记下经验，继续", "resolve_phase", { ...args, choice: "ack" }, 'class="primary"')}</div>`;
  } else if (d.kind === "approval") {
    title = "新药获批，给它起个名字";
    body = `${resultBlock(p.results.at(-1))}<p class="positive">综合分 <b>${number(p.composite, 1)}</b> / 100</p><form id="name-form" class="name-form"><label class="field">药物名称<input name="name" maxlength="40" required value="${e(d.data.suggested)}"></label><button class="primary" type="submit">正式上市 →</button></form>`;
  } else if (d.kind === "candidates") {
    title = "候选人到了";
    subtitle = "签约时可配 3 位成员一起入职，也可以只签负责人。";
    body = `<div class="choice-grid">${d.candidates.map((lead, index) => `<div class="card"><h3>${e(lead.name)}</h3><p class="small muted">${e(lead.type)} · 带队 ${lead.leadership} 人</p><p class="small"><b>${e(lead.trait_info.name)}</b>：${e(lead.trait_info.description)}</p>${statGrid(lead, attrs)}<p class="small">月薪 ${money(lead.salary)}<br>签约费 ${money(lead.fee)}</p>${actionButton("签约＋3 位成员", "hire_candidate", { ...args, index, members: 3 }, `class="primary"${disabled(state.cash < lead.fee + 3 * state.team_rules.member_hire_fee || state.headcount + 4 > state.capacity)}`)}<p class="small muted">含成员签约 ${money(lead.fee + 3 * state.team_rules.member_hire_fee)} · 团队月薪 ${money(lead.salary + 3 * state.team_rules.member_salary)}</p>${actionButton("只签负责人", "hire_candidate", { ...args, index }, disabled(state.cash < lead.fee || state.headcount >= state.capacity))}</div>`).join("")}</div>${state.headcount >= state.capacity ? '<div class="hint warn">场地已满。可以先在「经营手记」升级场地，或在「团队」调整人数。</div>' : ""}<div class="actions">${actionButton("这次都不签", "hire_candidate", { ...args, index: -1 })}</div>`;
  } else if (d.kind === "cash_negative") {
    title = "现金告急";
    subtitle = `当前现金 ${money(state.cash)}`;
    body = `<div class="hint warn">连续 ${d.data.limit} 个月月底现金为负，公司会破产。可以接外包、减少开支，或在项目阶段结束时止损。</div><div class="actions">${actionButton("查看情况，继续经营", "acknowledge", args, 'class="primary"')}</div>`;
  } else if (d.kind === "year_end") {
    title = `第 ${d.data.year} 年 · 年度回顾`;
    subtitle = "把这一年的进展，记在手记里。";
    body = `<div class="two-column"><div class="card"><span class="small muted">药品销售收入</span><h3>${money(d.data.revenue)}</h3><p class="small">实际进账 ${money(d.data.income)}<br>全部支出 ${money(d.data.expense)}</p></div><div class="card"><span class="small muted">研发成果</span><h3>${d.data.approvals} 个药物获批</h3><p class="small">${d.data.failures} 个项目未通过<br>公司口碑 ${d.data.reputation}</p></div></div><div class="actions">${actionButton("开启新的一年 →", "acknowledge", args, 'class="primary"')}</div>`;
  } else if (d.kind === "game_end") {
    title = "二十年，从一间实验室到这里";
    subtitle = "这一局完成了。你也可以继续经营。";
    body = `<p>综合得分 <b>${d.data.score}</b> · ${d.data.approvals} 个药物获批 · ${d.data.hall_of_fame} 个名人堂药物</p><p>累计利润 ${money(d.data.profit)}</p><div class="actions">${actionButton("继续经营", "acknowledge", args, 'class="primary"')}${modalButton("开始新公司", "new-game")}</div>`;
  }
  return `<section class="decision" id="decision" aria-label="待处理事件"><span class="eyebrow">等待决定${state.pending.length > 1 ? ` / 还有 ${state.pending.length - 1} 件` : ""}</span><h2>${title}</h2><p class="small muted">${e(subtitle)}</p>${body}</section>`;
}

function projectCard(p) {
  const rd = ["research", "rd_review"].includes(p.stage);
  const stages = ["研发", "I 期", "II 期", "III 期", "审评", "上市"];
  const stage = rd
    ? 0
    : p.stage === "approved" || p.stage === "naming"
      ? 5
      : ["I", "II", "III", "NDA"].indexOf(p.phase) + 1;
  const done = rd ? p.rd_done : p.phase_weeks - p.phase_weeks_left;
  const total = rd ? p.rd_weeks : p.phase_weeks;
  const waiting = state.pending.some((d) => d.project_id === p.id);
  return `<article class="card"><div class="card-head"><div><span class="eyebrow">项目 ${String(p.id).padStart(3, "0")}</span><h3>${e(p.label)}</h3><span class="small muted">${e(state.targets.find((t) => t.key === p.target)?.disease)} · ${e(p.known_tier)}</span></div>${badge(stageNames[p.stage], p.stage === "failed" ? "red" : waiting ? "amber" : "green")}</div>
    <div class="project-stages">${stages.map((s, i) => `${i ? '<span aria-hidden="true">›</span>' : ""}<span class="${i === stage ? "current" : i < stage ? "done" : ""}">${s}</span>`).join("")}</div>
    ${p.stage === "clinical_queue" ? `<div class="hint">临床排队第 ${p.queue_position} 位 · 不收临床费，不占用研发团队。席位空出后自动开始；等待期间属性不下降。</div><div class="actions">${actionButton(`转委托临床 · 全程约 ${money(p.contract_cost)}`, "outsource_clinical", { project_id: p.id })}${actionButton("取消排队项目", "cancel_project", { project_id: p.id }, 'class="danger" data-confirm="取消后无法恢复，已投入费用不退还。"')}</div>` : ""}
    ${p.active && !["naming", "clinical_queue"].includes(p.stage) ? `<progress value="${done}" max="${total || 1}" aria-label="${e(p.label)}进度"></progress><div class="progress-caption"><span>${rd ? "研发" : e(p.phase_name)} ${done} / ${total} 周${rd && !p.team_ids.length ? " · 未配团队，已暂停" : ""}</span><span>累计花费 ${money(p.spent)}</span></div>` : ""}
    ${rd ? statGrid(p.stats) : ""}
    ${p.hazards.length ? `<p class="small muted">${p.hazards.length} 个研发遗留隐患 · ${p.hazards.map((h) => e(h.text)).join("、")}</p>` : ""}
    <details data-key="project-${p.id}"><summary>查看${p.active ? "分数预估与" : ""}项目记录</summary>${forecastTable(p)}${p.results
      .map(
        (r) =>
          `<p class="small"><b>${e(r.phase)} · ${r.passed ? "通过" : "未通过"}</b>　${Object.entries(
            r.scores,
          )
            .map(([k, v]) => `${e(state.names.stats[k])} ${v}`)
            .join(
              " / ",
            )}<br>${e(r.text)}${r.hazard_texts.length ? `<br>${r.hazard_texts.map(e).join("<br>")}` : ""}</p>`,
      )
      .join("")}</details>
    <div class="card-bottom"><span class="small muted">${rd ? p.team_ids.map((id) => e(teamById(id)?.lead.name)).join(" / ") || "尚未配备团队" : p.active ? (p.clinical_mode === "contract" ? "委托临床 · 费用 +30% · 不占自营席位" : p.stage === "clinical_queue" ? "等待自营席位 · 研发团队已释放" : "自营临床 · 不占用研发团队") : `已投入 ${money(p.spent)}`}</span><div class="compact-actions">${p.stage === "research" ? `${modalButton("调整团队", "project-teams", p.id, disabled(waiting || state.game_over))}${actionButton("取消", "cancel_project", { project_id: p.id }, 'class="quiet" data-confirm="取消研发项目后，已花费用不会退回，也不会增加熟练度。"')}` : ""}</div></div></article>`;
}

function renderPipeline() {
  const projects = activeProjects(),
    ended = state.projects.filter((p) => !p.active);
  return (
    sectionHead(
      "研发管线",
      "从一个好想法，到第一张批文。",
      modalButton(
        "＋ 新建项目",
        "project",
        "",
        'class="primary"' + disabled(!idleTeams().length || state.game_over),
      ),
    ) +
    `<div class="hint">自营临床 ${state.clinical_operations.used} / ${state.clinical_operations.capacity} 个席位 · 排队 ${state.clinical_operations.queue.length} 项。升级场地可增加席位，委托临床可立即启动。</div>` +
    (state.week > 48 && !state.drugs.length && state.cash < 0
      ? `<div class="hint warn">旧版的临床门槛问题已修复，已有属性和记录均保留。这家公司现金已透支 ${money(-state.cash)}；可备份这局后重新开始。 ${modalButton("备份旧局，开始新公司", "new-game", "", 'class="primary"')}</div>`
      : "") +
    (!projects.length
      ? empty(
          state.projects.length ? "准备下一次尝试" : "你的第一款药，从这里开始",
          "选择靶点与分子类型，再把团队安排进去。<br>开局可以试试 EGFR × 小分子。",
          modalButton(
            state.projects.length ? "新建下一个项目 →" : "立项：第一步 →",
            "project",
            "",
            'class="primary"' +
              disabled(!idleTeams().length || state.game_over),
          ),
          "Ⅰ",
        )
      : `<div class="stack">${projects.map(projectCard).join("")}</div>`) +
    (ended.length
      ? `<details data-key="ended"><summary>已结束的项目（${ended.length}）</summary><div class="stack">${ended.slice().reverse().map(projectCard).join("")}</div></details>`
      : "") +
    (!state.teams.some((t) => t.specialty === "tox")
      ? `<div class="hint">首款药建议：初始两组各补到 4 位成员，再通过学术会议招毒理负责人并配 3 位成员。研发结束尽量等各期「有余量」再进临床。 ${modalButton("招聘负责人", "recruit", "", 'class="quiet"' + disabled(Boolean(state.recruitment) || state.game_over))}</div>`
      : "")
  );
}

function renderTeams() {
  return (
    sectionHead(
      "团队",
      "研发结束后，团队就能接下一份工作。",
      modalButton(
        "＋ 招聘负责人",
        "recruit",
        "",
        'class="primary"' +
          disabled(Boolean(state.recruitment) || state.game_over),
      ),
    ) +
    (state.recruitment
      ? `<div class="hint">招聘进行中 · ${e(state.names.attrs[state.recruitment.specialty])}方向 · ${state.recruitment.candidates.length ? "候选人已到，请处理上方事件" : `还需 ${Math.max(0, state.recruitment.ready_week - state.week)} 周`}</div>`
      : "") +
    `<div class="two-column">${state.teams.map((t) => `<article class="card"><div class="card-head"><div class="person"><div class="team-avatar">${e(t.type.slice(0, 2))}</div><div><h3>${e(t.lead.name)}</h3><span class="small muted">${e(t.type)} · Lv.${t.lead.level}</span></div></div>${badge(t.task ? "忙碌" : "空闲", t.task ? "" : "green")}</div>${statGrid(t.lead, attrs)}<p class="small"><b>${e(t.trait.name)}</b>：${e(t.trait.description)}</p><p class="small">主修 ${e(state.names.attrs[t.specialty])} · 副修 ${e(state.names.attrs[t.lead.secondary])}<br>${t.members} 位成员 · 产出 ×${number(t.size_factor, 2)} · 带队 ${t.lead.leadership} 人<br><span class="muted">团队月薪 ${money(t.salary)} · ${e(t.task_label)}</span></p><progress value="${t.lead.exp}" max="${t.exp_next}" aria-label="${e(t.lead.name)}经验"></progress><div class="progress-caption"><span>经验 ${t.lead.exp} / ${t.exp_next}</span><span>${t.lead.level >= 10 ? "已满级" : "工作积累经验"}</span></div><div class="compact-actions">${modalButton("管理与培养", "team", t.id, disabled(state.game_over))}${!t.task && state.projects.some((p) => p.stage === "research" && p.team_ids.length < state.team_rules.max_per_project && !state.pending.some((d) => d.project_id === p.id)) ? modalButton("安排研发", "assign", t.id, 'class="primary"' + disabled(state.game_over)) : ""}</div></article>`).join("")}</div>`
  );
}

function renderContracts() {
  return (
    sectionHead("外包业务", "让空闲的团队赚回现金，也积累一些研究数据。") +
    (state.contracts.length
      ? `<div class="hint">进行中：${state.contracts.map((x) => `${e(x.name)} · ${e(teamById(x.team_id)?.lead.name)} · 还剩 ${x.weeks_left} 周 · 完成后 ${money(x.reward)}`).join("<br>")}</div>`
      : "") +
    `<div class="stack">${state.offers.map((o) => `<article class="card"><div class="card-head"><div><h3>${e(o.name)}</h3><span class="small muted">要求 ${e(o.attr_name)} ≥ ${o.requirement} · 研究数据 +${o.data}</span></div>${badge(`基础报酬 ${money(o.reward)}`, "green")}</div>${o.teams.length ? `<div class="actions">${o.teams.map((t) => actionButton(`派 ${e(t.name)} · ${t.weeks} 周 / ${money(t.reward)}`, "accept_contract", { offer_id: o.id, team_id: t.id })).join("")}</div>` : '<p class="small muted">没有符合要求的空闲团队。可以先调整项目配队，或等研发结束。</p>'}</article>`).join("")}</div><p class="small muted">每月初刷新外包单。报酬在完成时到账；接单会暂时占用这个团队。</p>`
  );
}

function renderTechnology() {
  const tile = (x, type) =>
    `<article class="card"><div class="card-head"><div><h3>${e(x.name)}</h3><span class="small muted">${e(x.disease || x.route)}</span></div>${x.unlocked ? badge(`已解锁 · 熟练 ${x.proficiency}`, "green") : badge(`${x.unlock} 数据`)}</div>${x.tags ? `<p class="muted">${e(x.tags)}</p>` : ""}${x.market ? `<p>市场 ${"★".repeat(x.market)} · 难度 ${x.difficulty}</p>` : ""}${!x.unlocked ? `<p class="muted">${x.problems.length ? e(x.problems.join("；")) : "条件已满足，可以解锁"}</p>${actionButton(`解锁${type === "target" ? "靶点" : "类型"}`, `unlock_${type}`, { key: x.key }, disabled(x.problems.length > 0))}` : ""}</article>`;
  return (
    sectionHead(
      "技术与探索",
      `可用研究数据 ${state.data} · 发现合适的靶点与分子类型组合。`,
    ) +
    `<h2 class="table-title">分子类型</h2><div class="unlock-grid">${state.modalities.map((x) => tile(x, "modality")).join("")}</div><h2 class="table-title">靶点</h2><div class="unlock-grid">${state.targets.map((x) => tile(x, "target")).join("")}</div>`
  );
}

function renderDrugs() {
  return (
    sectionHead("上市药品", "每一个名字，都是一次从实验室到市场的旅程。") +
    (state.drugs.length
      ? `<div class="stack">${state.drugs
          .slice()
          .reverse()
          .map(
            (d) =>
              `<article class="card"><div class="card-head"><div><h3>${e(d.name)} ${d.hall_of_fame ? "✦" : ""}</h3><span class="small muted">${e(d.label)}</span></div>${badge(d.active ? "销售中" : "已退市", d.active ? "green" : "")}</div><div class="two-column"><p>综合分 <b>${number(d.composite, 1)}</b><br><span class="small muted">上市 ${d.weeks_on_market} 周 · 利润率 ${number(d.margin * 100, 1)}%</span></p><p>每周销售 ${money(d.weekly_sales)}<br><span class="positive">每周利润 ${money(d.weekly_profit)}</span></p></div><p class="small muted">累计销售额 ${money(d.revenue_total)}${d.hall_of_fame ? " · 已进入名人堂" : ""}</p></article>`,
          )
          .join("")}</div>`
      : empty(
          "还没有药物上市",
          "把第一款药送过临床和审评，就能在这里看到它。",
          "",
          "✦",
        )) +
    `<h2 class="table-title">成就 ${state.achievements.filter((a) => a.earned).length} / ${state.achievements.length}</h2><div class="two-column">${state.achievements.map((a) => `<div class="achievement ${a.earned ? "earned" : ""}"><span class="seal">${a.earned ? "✦" : "◇"}</span><div><strong>${e(a.name)}</strong><p>${e(a.desc)}</p></div></div>`).join("")}</div>`
  );
}

function renderCompany() {
  const next = state.next_facility;
  return (
    sectionHead("经营手记", "公司的钱、空间，以及每次尝试留下的经验。") +
    `<div class="card"><div class="card-head"><div><h3>${e(state.facility.name)}</h3><span class="small muted">${state.headcount} / ${state.capacity} 人 · 临床 ${state.clinical_operations.used}/${state.clinical_operations.capacity} 席位 · 月租 ${money(state.facility.rent)}</span></div>${next ? actionButton("升级场地", "build_facility", {}, `class="primary" data-confirm="升级到${e(next.name)}，建造费 ${money(next.cost)}，新月租 ${money(next.rent)}。"${disabled(state.cash < next.cost)}`) : badge("最大场地", "green")}</div>${next ? `<p class="small">下一级 ${e(next.name)} · ${next.capacity} 人 · ${next.clinical_slots} 个临床席位 · 建造费 ${money(next.cost)} · 月租 ${money(next.rent)}</p>` : ""}<p class="small muted">当前工资与租金合计 ${money(state.monthly_overhead)}/月。</p></div>
    <h2 class="table-title">年度账本</h2><div class="table-scroll"><table><thead><tr><th>年份</th><th>药品销售额</th><th>实际进账</th><th>全部支出</th><th>净收支</th><th>获批 / 失败</th></tr></thead><tbody>${state.years
      .slice()
      .reverse()
      .map(
        (y) =>
          `<tr><td>第 ${y.year} 年${y.year === state.years.at(-1).year ? " · 进行中" : ""}</td><td>${money(y.revenue)}</td><td>${money(y.income)}</td><td>${money(y.expense)}</td><td class="${y.income - y.expense < 0 ? "fail" : "pass"}">${money(y.income - y.expense)}</td><td>${y.approvals} / ${y.failures}</td></tr>`,
      )
      .join(
        "",
      )}</tbody></table></div><p class="small muted">实际进账为药品销售利润与外包回款。项目预算不包含工资和租金。</p>
    <h2 class="table-title">组合笔记本</h2>${state.notebook.length ? `<div class="stack">${state.notebook.map((n) => `<div class="card"><div class="card-head"><h3>${e(n.label)}</h3>${badge(n.tier_name, n.tier >= 1 ? "green" : n.tier < 0 ? "amber" : "")}</div><p>${e(n.reason)}</p><p class="small muted">完成 ${n.times} 次${n.best_composite ? ` · 最佳综合分 ${number(n.best_composite, 1)}` : ""}</p></div>`).join("")}</div>` : '<div class="hint">研发完成后，这个组合的评价和原因会记在这里。</div>'}
    <div class="danger-zone"><p class="small muted">当前随机种子 ${state.seed}。每次操作自动保存，刷新页面会接着这一局。开始新公司时会备份旧进度。</p><div class="actions"><a class="button" href="/api/save" download>导出这局存档</a>${modalButton("开始新公司", "new-game")}</div></div>`
  );
}

function openModal(name, id) {
  let title = "",
    body = "";
  const err = '<div class="inline-error" role="alert" hidden></div>';
  const submit = (text) =>
    `<div class="modal-actions"><button type="button" data-close>返回</button><button class="primary" type="submit">${text}</button></div>`;
  const teamChecks = (teams, selected = []) =>
    `<div class="check-list">${teams.map((t) => `<label class="check-row"><input type="checkbox" name="team_ids" value="${t.id}"${selected.includes(t.id) ? " checked" : ""}><span>${e(t.lead.name)} · ${e(t.type)} · ${t.members} 位成员<small>生物 ${t.lead.bio} / 化学 ${t.lead.chem} / 毒理 ${t.lead.tox} / 工艺 ${t.lead.proc}</small></span></label>`).join("")}</div>`;
  if (name === "project") {
    const choices = Object.entries(state.estimates).filter(
      ([, x]) => x.route.allowed,
    );
    const activeTargets = new Set(activeProjects().map((p) => p.target));
    const rank = ([key, x]) =>
      x.route.tier * 100 -
      (activeTargets.has(key.split("|")[0]) ? 30 : 0) -
      Math.min(20, x.same_target_drugs.length * 10);
    choices.sort((a, b) => rank(b) - rank(a) || a[1].rd_cost - b[1].rd_cost);
    const [defaultTarget, defaultModality] = (
      choices[0]?.[0] || "egfr|small_molecule"
    ).split("|");
    title = "新建研发项目";
    body = `<form id="project-form"><div class="two-column"><label class="field">选择靶点<select name="target">${state.targets
      .filter((t) => t.unlocked)
      .map(
        (t) =>
          `<option value="${e(t.key)}"${t.key === defaultTarget ? " selected" : ""}>${e(t.name)} · ${e(t.disease)}</option>`,
      )
      .join(
        "",
      )}</select></label><label class="field">分子类型<select name="modality">${state.modalities
      .filter((m) => m.unlocked)
      .map(
        (m) =>
          `<option value="${e(m.key)}"${m.key === defaultModality ? " selected" : ""}>${e(m.name)}</option>`,
      )
      .join(
        "",
      )}</select></label></div><div id="project-estimate" class="estimate"></div><label class="field">配备团队 <small>至少 1 个，最多 ${state.team_rules.max_per_project} 个；临床开始后团队会释放。</small></label>${teamChecks(
      idleTeams(),
      idleTeams()
        .slice(0, state.team_rules.max_per_project)
        .map((t) => t.id),
    )}${err}${submit("确认立项 →")}</form>`;
  } else if (name === "project-teams") {
    const p = projectById(id);
    title = `调整团队 · ${p.label}`;
    body = `<form id="project-teams-form" data-id="${p.id}"><p class="small muted">最多 ${state.team_rules.max_per_project} 个团队。全部撤出时，研发暂停并停止研发费用。</p>${teamChecks(
      state.teams.filter((t) => !t.task || p.team_ids.includes(t.id)),
      p.team_ids,
    )}${err}${submit("保存配队")}</form>`;
  } else if (name === "recruit") {
    title = "招聘一位负责人";
    body = `<form id="recruit-form"><label class="field">专业方向<select name="specialty">${attrs.map((a) => `<option value="${a}"${a === "tox" ? " selected" : ""}>${e(state.names.attrs[a])}</option>`).join("")}</select></label><label class="field">招聘渠道<select name="channel">${state.channels.map((c) => `<option value="${e(c.key)}"${c.key === "conference" ? " selected" : ""}>${e(c.name)} · ${money(c.cost)}${c.key === "conference" ? "（开局推荐）" : ""}</option>`).join("")}</select></label><div class="estimate" id="recruit-estimate"></div><p class="small muted">2 周后会有 3 位候选人。签约需要另付 3 个月薪水；可同时配 3 位成员，产出约为负责人独自工作的 2.2 倍。</p>${err}${submit("发布招聘")}</form>`;
  } else if (name === "team") {
    const t = teamById(id);
    title = `${t.lead.name} · 管理与培养`;
    body = `${statGrid(t.lead, attrs)}<p><b>${e(t.trait.name)}</b>：${e(t.trait.description)}</p><div class="hint">主修 ${e(state.names.attrs[t.specialty])} 上限 100，副修 ${e(state.names.attrs[t.lead.secondary])} 上限 70，其他学科上限 45。需要不同专业合作补齐短板。</div>${outputNote(t)}<p class="small muted">${t.members} 位成员 / 带队能力 ${t.lead.leadership} 人。超过带队能力后，新增人数的效果减半。</p><form id="members-form" data-id="${t.id}"><label class="field">调整成员人数<input name="count" type="number" min="1" max="400" step="1" value="${Math.max(1, Math.min(3, state.capacity - state.headcount))}" required><small>招人 ${money(state.team_rules.member_hire_fee)}/人，新增月薪 ${money(state.team_rules.member_salary)}/人；减人遣散费 ${money(state.team_rules.member_severance)}/人。</small></label><div id="members-estimate" class="hint"></div><div class="actions"><button class="primary" type="submit" name="operation" value="add_members"${disabled(state.headcount >= state.capacity)}>招募成员</button><button type="submit" name="operation" value="remove_members"${disabled(!t.members)}>减少成员</button></div></form><h3 class="table-title">定向培养 · 每次 +${state.training_gain}</h3><div class="compact-actions">${attrs
      .map((a) => {
        const cost = t.training[a];
        return actionButton(
          `${e(state.names.attrs[a])} ${t.lead[a] >= t.training_caps[a] ? "已到上限" : `+${Math.min(state.training_gain, t.training_caps[a] - t.lead[a])}`}（上限 ${t.training_caps[a]}） · ${money(cost.cost)} / ${cost.data} 数据`,
          "train_lead",
          { team_id: t.id, attr: a },
          disabled(
            t.lead[a] >= t.training_caps[a] ||
              state.cash < cost.cost ||
              state.data < cost.data,
          ),
        );
      })
      .join(
        "",
      )}</div>${err}<div class="danger-zone">${actionButton("解散整个团队", "fire_lead", { team_id: t.id }, `class="danger" data-confirm="${e(t.lead.name)}会离开公司，整个团队解散，支付 ${money(t.severance)} 遣散费；当前外包会作废。"`)}</div>`;
  } else if (name === "assign") {
    const t = teamById(id);
    title = `安排研发 · ${t.lead.name}`;
    const ps = state.projects.filter(
      (p) =>
        p.stage === "research" &&
        p.team_ids.length < state.team_rules.max_per_project &&
        !state.pending.some((d) => d.project_id === p.id),
    );
    body = `<form id="assign-form" data-id="${t.id}"><label class="field">加入项目<select name="project_id">${ps.map((p) => `<option value="${p.id}">${e(p.label)} · ${p.team_ids.length} 个团队</option>`).join("")}</select></label>${t.members === 0 ? '<div class="hint warn">这个团队还没有成员。安排后可以在「管理与培养」里加人，提高每周产出。</div>' : ""}${err}${submit("加入研发")}</form>`;
  } else if (name === "new-game") {
    title = "开始一家新公司";
    body = `<form id="new-game-form"><p class="small">这一局的进度会先备份到本地存档目录，然后开始新的公司。</p><label class="field">随机种子<input type="number" name="seed" min="0" max="999999999" step="1" value="${Math.floor(Math.random() * 999999) + 1}" required><small>同一个种子与同样的操作，会得到同样的结果。</small></label>${err}${submit("备份旧局，开始新公司")}</form>`;
  } else if (name === "help") {
    title = "你的第一家制药公司";
    body = `<ol class="help-list"><li><b>立项。</b>先试 EGFR × 小分子，把生物组和化学组配进去。</li><li><b>补齐团队。</b>通过学术会议招聘毒理负责人，配 3 位成员；初始两组各补到 4 位成员，点击「安排研发」加入项目。</li><li><b>推进时间。</b>「继续 4 周」便于看进展；「下一件事」会在关键攻关、候选人或临床结果出现时停下。攻关可选性能、排险或速度。</li><li><b>研发结束，看够不够好。</b>尽量达到全部「有余量」，并清除隐患再进临床。最多打磨 6 次，每次显示收益和开销；严重隐患需要专项验证或研发末期排险。门槛不会随时间上涨。</li><li><b>研发要团队，临床不用。</b>自营临床占用场地席位；满员可排队、升级或加价委托。排队不阻止时间前进。研发团队可接新项目或外包。</li><li><b>留够现金。</b>「已承诺」是项目后续预算，工资和租金要另留。连续 3 个月月底现金为负会破产。</li></ol><div class="hint">每次操作都会自动保存，刷新或重新打开页面会继续这一局。游戏时间只会在你点击推进时流动。</div><p class="small muted">导出的 JSON 存档可以作为独立备份保留。平常继续游戏，只需重新打开页面。</p><div class="modal-actions"><button class="primary" data-close>开始经营</button></div>`;
  }
  modalBody.innerHTML = `<div class="modal-head"><h2 id="modal-title">${e(title)}</h2><button type="button" data-close aria-label="关闭弹窗">×</button></div>${body}`;
  if (!modal.open) modal.showModal();
  if (name === "project") updateProjectEstimate();
  if (name === "recruit") updateRecruitEstimate();
  if (name === "team") updateMembersEstimate();
}

function updateProjectEstimate() {
  const form = document.querySelector("#project-form");
  if (!form) return;
  const values = new FormData(form),
    target = state.targets.find((t) => t.key === values.get("target"));
  const estimate =
    state.estimates[`${values.get("target")}|${values.get("modality")}`];
  const remaining = estimate.cash_after_reserve;
  document.querySelector("#project-estimate").innerHTML =
    `${routeNote(estimate.route)}<p>${e(target.tags)}</p><div class="estimate-row"><span>研发阶段</span><strong>${estimate.rd_weeks} 周 · ${money(estimate.rd_cost)}</strong></div><div class="estimate-row"><span>临床与审评</span><strong>${estimate.clinical_weeks} 周 · ${money(estimate.clinical_cost)}</strong></div><div class="estimate-row"><span>同期全公司工资租金约</span><strong>${money(estimate.operating_reserve)}</strong></div><div class="estimate-row"><span>预留现有项目、本项目和工资租金后</span><strong class="${remaining < 0 ? "negative" : ""}">${money(remaining)}</strong></div>${remaining < 0 ? '<div class="hint warn">现金不足以覆盖全部预留。建议先接外包、等待药品回款或缩减计划，再开这条管线。</div>' : ""}${estimate.same_target_drugs.length ? `<div class="hint warn">同靶点已有 ${estimate.same_target_drugs.length} 款在售药：${estimate.same_target_drugs.map(e).join("、")}。若它们届时仍在售，新药会与它们平分市场，也可考虑不同靶点。</div>` : ""}<p class="muted small">预留未计未来销售或外包收入、额外打磨和扩员。组合记录：${e(estimate.known_tier)}</p>`;
  form.querySelector('button[type="submit"]').disabled =
    !estimate.route.allowed;
}

function updateRecruitEstimate() {
  const key = document.querySelector(
    '#recruit-form select[name="channel"]',
  ).value;
  const c = state.channels.find((x) => x.key === key);
  document.querySelector("#recruit-estimate").innerHTML =
    `<div class="estimate-row"><span>招聘费</span><strong>${money(c.cost)}</strong></div><div class="estimate-row"><span>基础专业属性</span><span>${c.specialty[0]}–${c.specialty[1]}</span></div><div class="estimate-row"><span>带队能力</span><span>${c.leadership[0]}–${c.leadership[1]} 人</span></div><span class="small muted">公司口碑还会提高候选人的专业属性。</span>`;
}

function confirmAction(button) {
  const name = button.dataset.action,
    args = JSON.parse(button.dataset.args || "{}");
  modalBody.innerHTML = `<div class="modal-head"><h2 id="modal-title">确认这项决定</h2><button data-close aria-label="关闭弹窗">×</button></div><p class="small">${e(button.dataset.confirm)}</p><div class="inline-error" role="alert" hidden></div><div class="modal-actions"><button data-close>返回</button>${actionButton("确认", "" + name, args, 'class="primary"')}</div>`;
  if (!modal.open) modal.showModal();
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button || button.disabled || busy) return;
  if (button.hasAttribute("data-close")) {
    modal.close();
    return;
  }
  if (button.hasAttribute("data-refresh")) {
    await refresh();
    return;
  }
  if (!state) return;
  if (button.dataset.view) {
    activeView = button.dataset.view;
    render();
    return;
  }
  if (button.dataset.milestonePlan) {
    selectedPlan = button.dataset.milestonePlan;
    render();
    return;
  }
  if (button.dataset.modal) {
    openModal(button.dataset.modal, button.dataset.id);
    return;
  }
  if (button.dataset.action) {
    if (button.dataset.confirm) {
      confirmAction(button);
      return;
    }
    await send(button.dataset.action, JSON.parse(button.dataset.args || "{}"));
  }
});
document.addEventListener("change", (event) => {
  if (event.target.closest("#project-form")) updateProjectEstimate();
  if (event.target.closest("#recruit-form")) updateRecruitEstimate();
});
document.addEventListener("input", (event) => {
  if (event.target.closest("#members-form")) updateMembersEstimate();
});
document.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  const form = event.target,
    values = new FormData(form),
    id = Number(form.dataset.id);
  if (form.id === "project-form" || form.id === "project-teams-form") {
    const team_ids = values.getAll("team_ids").map(Number);
    if (
      team_ids.length > state.team_rules.max_per_project ||
      (form.id === "project-form" && !team_ids.length)
    ) {
      notify(`请选择 1–${state.team_rules.max_per_project} 个团队`, true);
      return;
    }
    if (form.id === "project-form")
      await send("start_project", {
        target: values.get("target"),
        modality: values.get("modality"),
        team_ids,
      });
    else await send("set_project_teams", { project_id: id, team_ids });
  } else if (form.id === "recruit-form")
    await send("start_recruitment", {
      specialty: values.get("specialty"),
      channel: values.get("channel"),
    });
  else if (form.id === "members-form")
    await send(event.submitter?.value || "add_members", {
      team_id: id,
      count: Number(values.get("count")),
    });
  else if (form.id === "assign-form") {
    const p = projectById(values.get("project_id"));
    await send("set_project_teams", {
      project_id: p.id,
      team_ids: [...p.team_ids, id],
    });
  } else if (form.id === "name-form")
    await send("name_drug", {
      decision_id: state.pending[0].id,
      name: values.get("name"),
    });
  else if (form.id === "new-game-form")
    await send("new_game", { seed: Number(values.get("seed")) });
});
modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    const r = modal.getBoundingClientRect();
    if (
      event.clientX < r.left ||
      event.clientX > r.right ||
      event.clientY < r.top ||
      event.clientY > r.bottom
    )
      modal.close();
  }
});
window.addEventListener("focus", () => {
  if (state && !busy && !modal.open) refresh();
});
refresh();
