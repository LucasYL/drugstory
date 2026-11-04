const $ = (selector) => document.querySelector(selector);
let state,
  activeTab = "pipeline",
  previewSequence = 0,
  requestBusy = false;
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        ch
      ],
  );
const num = (v) => Math.round(v || 0).toLocaleString("zh-CN");
const money = (v) => `¥${num(v)} 万`;
const empty = (text) => `<div class="empty-state"><p>${esc(text)}</p></div>`;
const button = (text, name, args = {}, cls = "", disabled = false) =>
  `<button class="${cls}" data-command="${name}" data-args="${esc(JSON.stringify(args))}" ${disabled ? "disabled" : ""}>${esc(text)}</button>`;
const modalButton = (text, type, id = "", cls = "") =>
  `<button class="${cls}" data-modal="${type}" data-id="${esc(id)}">${esc(text)}</button>`;
const checks = (items) =>
  items
    .map(
      (c) =>
        `<span class="${c.ok ? "good" : "muted"}">${c.ok ? "✓" : "○"} ${esc(c.text)}</span>`,
    )
    .join("<br>");
const rankClass = (rank) => `rank-${rank}`;
function notice(text, bad = false) {
  const el = $("#notice");
  el.textContent = text;
  el.className = bad ? "error" : "";
  el.hidden = false;
  setTimeout(() => (el.hidden = true), 5500);
}
async function send(name, args = {}) {
  if (requestBusy) return;
  requestBusy = true;
  const priorFestivalYear = state?.honors?.festivals.at(-1)?.year || 0;
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
        render();
      }
      throw new Error(data.error);
    }
    state = data;
    $("#modal").close();
    render();
    $("#save-status").textContent = "✓ 进度已保存";
    if ((data.honors.festivals.at(-1)?.year || 0) > priorFestivalYear)
      showModal("ceremony");
  } catch (error) {
    notice(error.message, true);
  } finally {
    requestBusy = false;
  }
}
function evidence(c) {
  return `<div class="evidence-grid">${c.evidence.map((x) => `<div><span>${esc(x.name)}</span><strong>${x.low}–${x.high}</strong><small>${x.observations} 次观察 · 估计范围</small></div>`).join("")}</div>`;
}
function render() {
  const s = state,
    f = s.facility;
  $("#app").innerHTML = `<main class="shell">
    <section class="timebar"><div><div class="eyebrow">RESEARCH GUILD / 研究社养成</div><h1>${esc(s.date)} <small>第 ${s.week} 周</small></h1><p class="muted">${s.pending ? `${s.pending} 项等待决定；也可暂缓项目，经营其他业务。` : "时间由你推进。好研究，也包括及时识别不值得继续的候选。"}</p></div><div class="actions">${button("推进 1 周", "advance", { weeks: 1 }, "", !!s.pending || s.game_over)}${button("继续 4 周", "advance", { weeks: 4 }, "", !!s.pending || s.game_over)}${button("下一件事 →", "next_event", {}, "primary", !!s.pending || s.game_over)}</div></section>
    <section class="metrics" aria-label="公司概况">
      <div><span>现金</span><strong>${num(s.cash)} <small>万</small></strong><small>${s.runway === null ? "当前经营收支为正" : `按当前收支约 ${s.runway} 周`}</small></div>
      <div><span>已承诺支出</span><strong>${num(s.committed)} <small>万</small></strong><small>可安排 ${money(s.available_cash)} · 不含未来工资</small></div>
      <div><span>研究团队</span><strong>${s.heroes.length} <small>位角色</small></strong><small>${s.headcount} / ${f.capacity} 人 · ${esc(f.name)}</small></div>
      <div><span>研究成果</span><strong>${Object.values(s.report.approvals).reduce((a, b) => a + b, 0)} <small>款自主产品</small></strong><small>创新 ${s.report.approvals.innovative} 款 · 授权 ${s.deals.length} 项</small></div>
      <div><span>专业积累</span><strong>${num(Object.values(s.knowledge).reduce((a, b) => a + b, 0))}</strong><small>最高阶位：${["", "见习", "精英", "大师", "传奇"][s.report.highest_rank]}</small></div>
    </section>
    <div class="festival-strip"><span>第 ${s.honors.year} 届研究大会 · 距年末 ${s.honors.deadline - s.week} 周 · ${s.honors.entry ? "已报名 " + s.honors.categories.find((c) => c.key === s.honors.entry).name : "尚未报名"}</span><button data-tab="honors">荣誉与终局 →</button></div>
    <section class="goal-strip"><div><b>${esc(s.opening.name)} · ${s.objective_done ? "目标已达成" : "公司目标"}</b><p>${esc(s.opening.goal)}</p></div>${modalButton("选择开局路线", "new")}</section>
    ${s.game_over ? `<div class="warning"><b>公司已停止经营</b><p>连续三个月月底资金为负。研究履历仍可查看，新开局会先备份当前记录。</p>${modalButton("备份并开始新公司", "new")}</div>` : ""}
    ${s.career_done ? `<div class="hint">二十年回顾已开启 · 当前 ${s.report.score} 分。可以继续经营，或在「经营复盘」查看这段研究旅程。</div>` : ""}
    <div class="layout"><section><nav class="tabs" aria-label="经营菜单">${[
      ["pipeline", "研发手记"],
      ["characters", "研究社"],
      ["services", "技术服务"],
      ["market", "产品与授权"],
      ["competition", "产业动态"],
      ["honors", "荣誉与终局"],
      ["journal", "经营复盘"],
    ]
      .map(
        ([key, name]) =>
          `<button data-tab="${key}" class="${activeTab === key ? "active" : ""}">${name}</button>`,
      )
      .join(
        "",
      )}</nav><div id="view">${{ pipeline: pipeline, characters: characters, services: services, market: market, competition: competitionView, honors: honorsView, journal: journal }[activeTab]()}</div></section>
    <aside><section class="side-note"><h2>给社长的便签</h2><p>${hint()}</p><h3>现金流 / 每周</h3><p>工资 ${money(s.payroll)}<br>工资、租金与在研支出 ${money(s.costs_per_week)}<br>自有产品利润 ${money(s.weekly_profit)}<br>授权销售分成 ${money(s.weekly_royalty)}</p><small>当前现金流不包含未来新阶段、服务交付和条件里程碑。临床估计基于已有证据，不能保证后续成功。</small></section><h2>研究社日志</h2><ol class="journal-list">${s.journal
      .slice(-12)
      .reverse()
      .map(
        (j) => `<li><small>第 ${j.week} 周</small><p>${esc(j.text)}</p></li>`,
      )
      .join("")}</ol></aside></div></main>`;
}
function hint() {
  const s = state;
  if (s.game_over)
    return "这一局的项目、失败原因与人物成长都已保留，可以据此安排下一次尝试。";
  if (s.available_cash < 500)
    return "先守住周转金。暂缓下一阶段，接技术服务，或比较当前项目的授权报价。不要把合同总额当成已到账现金。";
  if (!s.projects.length)
    return "第一步可以做「稳压片」：烧杯仔和小药丸都能参与前期。等效性阶段可聘请刻度喵，或使用外部 CRO。";
  if (s.heroes.some((h) => h.rank < 4 && h.promotion.every((c) => c.ok)))
    return "有角色达到晋阶条件了。去研究社看看：经验、真实履历和平台一起决定突破。";
  return "普通角色能一路晋阶；高阶人才也有公开加入条件。角色越强，越擅长筛选、优化和判断，科学不确定性仍然存在。";
}
function pipeline() {
  const active = state.projects.filter((p) => p.active),
    past = state.projects.filter((p) => !p.active);
  return `<div class="section-head"><div><h2>从候选，到值得留下的药</h2><p class="muted">仿制、改良、创新有各自的证据路径。</p></div>${modalButton("＋ 新建研究计划", "project", "", "primary")}</div><div class="hint">自营临床 ${state.clinical_used} / ${state.facility.slots} · 阶段需要临床负责人或 CRO。等待资金时可以暂缓决策，未开工阶段不收费。</div>${active.length ? active.map(projectCard).join("") : empty("研究台暂时空着。先选一个适合当前团队的计划。")}<details ${past.length && !active.length ? "open" : ""}><summary>已结束的项目（${past.length}）</summary>${past.slice().reverse().map(projectCard).join("")}</details>`;
}
function projectCard(p) {
  const current = p.candidates[p.chosen],
    result = p.results.at(-1);
  let action = "";
  if (p.status === "selecting")
    action = `<p>选一张候选卡。区间较宽代表还不确定，并非潜力一定更高。</p><div class="candidate-grid">${p.candidates.map((c) => `<article class="candidate"><h3>候选 ${c.id + 1} · ${esc(c.label)}</h3>${evidence(c)}${button("选择候选 " + (c.id + 1), "choose_candidate", { project: p.id, candidate: c.id }, "primary")}</article>`).join("")}</div>`;
  if (p.status === "ready")
    action = `<p><b>下一步：${esc(p.phase)}</b> · ${esc(p.question)}</p><p class="muted">剩余路径估计：${esc(p.outlook)}。标准研究预算参考 ${money(p.future_base_cost)}，不含工资、实验和上市准备。</p><div class="actions">${modalButton("安排本阶段", "phase", p.id, "primary")}${modalButton("专项研究 / 定向优化", "experiment", p.id)}${p.index < 2 ? modalButton("比较其他候选", "switch", p.id) : ""}</div>`;
  if (p.status === "result")
    action = `${resultTable(result)}<div class="actions">${p.key === "review" ? modalButton("命名并安排上市", "launch", p.id, "primary") : modalButton("安排下一阶段 →", "phase", p.id, "primary") + button("先准备，稍后安排", "continue_project", { project: p.id }, "quiet")}${p.quotes.length ? modalButton("比较授权 / 共同开发", "license", p.id) : ""}</div>${p.kind === "innovative" && ["preclinical", "II"].includes(p.key) && !p.quotes.length ? '<p class="muted">当前证据还没有形成可接受的授权报价。</p>' : ""}`;
  if (p.status === "problem")
    action = `${resultTable(result)}<div class="actions">${modalButton("补正一次 · 8 周 / ¥100 万", "rework", p.id, "primary")}${p.index < 2 ? modalButton("更换候选重做", "switch", p.id) : ""}</div>`;
  if (p.status === "checkpoint") action = trialPanel(p);
  if (p.status === "failed") action = resultTable(result);
  if (["screening", "running"].includes(p.status))
    action = `<div class="running"><span>${p.running_experiment ? "专项研究" : p.status === "screening" ? "候选筛选" : esc(p.phase)}</span><strong>还需 ${p.left} 周</strong><small>负责人：${p.team.map((id) => esc(state.heroes.find((h) => h.id === id)?.name || id)).join("、") || "合作临床团队"}</small></div>`;
  return `<article class="project-card"><div class="card-title"><div><small>${esc(p.kind_name)} · 累计投入 ${money(p.spent)}</small><h3>${esc(p.name)}</h3></div><span class="badge ${p.status === "failed" ? "bad" : ""}">${esc(p.status_name)}${p.deferred ? " · 已暂缓" : ""}</span></div>${p.status === "licensed" ? '<p class="hint">后续开发由合作方推进。请在「产品与授权」查看里程碑、风险和分成。</p>' : `<div class="phase-track">${p.path.map((v, i) => `<span class="${i === p.index ? "current" : i < p.index ? "done" : ""}">${esc(v)}</span>`).join("")}</div>`}${current && p.active ? `<details><summary>查看候选 ${current.id + 1} 的证据 · 已优化 ${current.optimized}/2 次</summary>${evidence(current)}<small>范围随观察更新，追加验证也可能揭示不利证据。</small></details>` : ""}<p>${esc(p.feedback)}</p>${productNote(p)}${action}${p.active ? `<div class="card-footer">${["selecting", "ready", "result", "problem", "checkpoint"].includes(p.status) ? button(p.deferred ? "恢复提醒" : "暂缓决策，先经营其他业务", "defer", { project: p.id, waiting: p.deferred ? 0 : 1 }, "quiet") : ""}${modalButton("终止研究", "terminate", p.id, "danger quiet")}</div>` : ""}</article>`;
}
function resultTable(r) {
  if (!r) return "";
  return `<div class="result-box ${r.passed ? "" : "warning"}"><b>${r.passed ? "本阶段取得支持证据" : "本阶段证据未达要求"}</b><table><thead><tr><th>研究指标</th><th>本次观察</th><th>本阶段要求</th></tr></thead><tbody>${Object.entries(
    r.values,
  )
    .map(
      ([key, value]) =>
        `<tr><td>${esc(state.stats[key])}</td><td>${num(value)}</td><td>≥ ${r.limits[key]}</td></tr>`,
    )
    .join(
      "",
    )}</tbody></table><small>这些是游戏内研究指标，不是四项可以不断累加的成药分数。</small></div>`;
}
function characters() {
  return `<div class="section-head"><div><h2>普通角色，也有传奇之路</h2><p class="muted">见习 → 精英 → 大师 → 传奇。培养与新角色招募一起推进。</p></div>${modalButton("邀请新伙伴", "roster", "", "primary")}</div><div class="knowledge-grid">${Object.entries(
    state.professions,
  )
    .map(
      ([key, name]) =>
        `<div><span>${name}</span><strong>${state.knowledge[key]}</strong></div>`,
    )
    .join(
      "",
    )}</div><div class="hero-grid">${state.heroes.map((h) => `<article class="hero-card ${rankClass(h.rank)}"><span class="rank-tag">${esc(h.rank_name)}</span><h3>${esc(h.name)}</h3><p>${esc(h.profession_name)} · 能力 ${h.ability}</p><p class="muted">${esc(h.story)}</p><p><b>${esc(h.trait.name)}</b> · ${esc(h.trait.description)}</p><p>${h.focus_info ? `专长：<b>${esc(h.focus_info.name)}</b> · ${esc(h.focus_info.description)}` : h.rank >= 2 ? modalButton("选择长期专长", "focus", h.id) : "晋升精英后可选择深研或组织专长。"}</p><div class="hero-numbers"><span>经验 <b>${h.xp}</b></span><span>项目履历 <b>${h.cases.length}</b></span><span>成员 <b>${h.members}</b></span></div><p>${h.ability >= 55 ? "已具备" : "成长方向"}：<b>${esc(h.skill)}</b>；高阶能力需要对应研究与资源。</p><p>${h.busy ? `正在负责：${esc(h.busy)}` : "目前空闲"} · 工资 ${money(h.weekly_salary)} / 周</p>${h.rank < 4 ? `<details><summary>晋升${["", "", "精英", "大师", "传奇"][h.rank + 1]}的条件</summary><p>${checks(h.promotion)}</p><p>晋阶费用 ${money(h.promotion_cost)}</p></details>` : '<p class="good">已达传奇阶位，可通过带教培养新的研究力量。</p>'}${personalCard(h)}<div class="actions">${button("专业培训", "train", { character: h.id }, "", !!h.busy)}${h.rank < 4 ? button("晋阶突破", "promote", { character: h.id }, "primary", !!h.busy || !h.promotion.every((c) => c.ok)) : ""}${modalButton("配置团队", "team", h.id)}${modalButton("导师课题", "mentor", h.id)}</div></article>`).join("")}</div><section class="project-card"><h3>${esc(state.facility.name)}</h3><p>人数 ${state.headcount}/${state.facility.capacity} · 自营临床 ${state.clinical_used}/${state.facility.slots} · 生产线 ${state.lines_used}/${state.facility.lines}</p>${state.next_facility ? `<p>下一级 ${esc(state.next_facility.name)}：${money(state.next_facility.cost)}，租金 ${money(state.next_facility.rent)} / 周${state.next_facility.upkeep ? `，维护 ${money(state.next_facility.upkeep)} / 周` : ""}。</p>${button("扩建研究场地", "upgrade", {}, "primary")}` : "已建成星火科学城。"}</section>${challengePanel()}`;
}
function services() {
  return `<div class="section-head"><h2>让专业，也能支持现金流</h2>${modalButton("批量安排空闲伙伴", "batch")}</div><p class="muted">每 12 周更新有限的订单。服务会占用负责人，重复常规任务的成长逐渐减少。</p><div class="card-grid">${state.orders.map((o) => `<article class="project-card"><h3>${esc(o.name)}</h3><p>交付 ${o.weeks} 周 · 回款 ${money(o.reward)} · 材料 ${money(o.cost)}</p><p>需要 ${esc(state.professions[o.profession])} 能力 ${o.requirement}</p>${o.taken ? '<span class="badge">本期已接受</span>' : modalButton("安排交付", "service", o.id, "primary")}</article>`).join("")}</div><h3>正在进行的课题与订单</h3>${state.jobs.length ? state.jobs.map((j) => `<div class="job-line"><b>${esc(j.name)}</b><span>剩余 ${j.left} 周</span></div>`).join("") : empty("暂时没有进行中的订单或培训。")}`;
}
const categoryNames = {
  personal_projects: "个人课题",
  trial_operations: "临床执行调整",
  platform_maintenance: "平台维护",
  sales: "产品销售额",
  manufacturing: "生产与供货成本",
  upfront: "授权首付款",
  milestones: "条件里程碑",
  royalties: "销售分成",
  services: "技术服务回款",
  payroll: "工资",
  rent: "租金",
  research: "研究与试验",
  discovery: "候选筛选",
  launch: "上市准备",
  recruitment: "招募",
  training: "培养",
  promotion: "晋阶",
  facility: "场地",
  codevelopment: "共同开发",
  production_setup: "生产线准备",
  service_cost: "服务材料",
  collaboration: "合作课题",
  staffing: "团队调整",
  severance: "离职安排",
  awards: "年度奖金",
  specialization: "角色专长",
  independent_research: "独立复核与随访",
};
function market() {
  return `<h2>产品与合作</h2><p class="muted">成功带来长期回报。合同总额与未来销售都不等于今天的现金。</p><div class="business-totals"><div>首付款<strong>${money(state.income.upfront)}</strong></div><div>里程碑已到账<strong>${money(state.income.milestones)}</strong></div><div>累计销售分成<strong>${money(state.income.royalties)}</strong></div></div><h3>自主产品</h3>${
    state.products
      .filter((d) => !d.partner)
      .map(
        (d) =>
          `<article class="project-card"><div class="card-title"><h3>${esc(d.name)}</h3><span class="badge">${d.active ? "销售中" : "已退出市场"}</span></div>${productSalesNote(d)}<p>当前销售 ${money(d.last_revenue)} / 周 · 利润 ${money(d.last_profit)} / 周</p><p>累计销售 ${money(d.total_revenue)} · 累计产品利润 ${money(d.total_profit)}</p><p>生产方式：${{ contract: "委托生产", self: "自营生产", suspended: "暂停供货" }[d.production]} · ${d.kind === "innovative" ? 2 : 1} 条自营线需求</p>${d.active ? `<div class="actions">${button("委托生产", "set_production", { product: d.id, mode: "contract" }, "", d.production === "contract")}${button("自营生产 · ¥80 万准备费", "set_production", { product: d.id, mode: "self" }, "", d.production === "self")}${button("暂停供货", "set_production", { product: d.id, mode: "suspended" }, "", d.production === "suspended")}</div>` : ""}</article>`,
      )
      .join("") ||
    empty("第一款产品上市后，会在这里看到导入、现金回流与生命周期。")
  }<h3>授权与共同开发</h3>${state.deals.map((d) => `<article class="project-card"><div class="card-title"><h3>${esc(state.projects.find((p) => p.id === d.project)?.name)}</h3><span class="badge">${{ developing: "合作方开发中", approved: "已获批，按销售分成", failed: "开发未成功" }[d.status]}</span></div><p>${esc(d.partner)} · ${esc(d.name)} · 销售额分成 ${num(d.royalty * 100)}%</p><p>首付款 ${money(d.upfront)} 已到账 · 已收里程碑 ${money(d.received_milestones)}<br>累计分成 ${money(d.royalties)} · 当前 ${money(d.weekly_royalty)} / 周</p><p>我方后续费用比例 ${num(d.cost_share * 100)}% · 剩余承诺 ${money(d.remaining_cost * d.cost_share)} · 已付 ${money(d.owner_spent)}</p>${d.status === "developing" ? `<p>当前阶段还需 ${d.left} 周，获批前仍可能失败。</p>` : ""}</article>`).join("") || empty("创新项目通过临床前或 II 期后，可在阶段结果中比较合作报价。")}<p>产业动态会公布对手的方向、阶段、延迟与失败。</p><button data-tab="competition">查看产业动态 →</button>`;
}
function journal() {
  const r = state.report;
  return `<h2>这家研究社，留下了什么</h2><div class="business-totals"><div>经营分<strong>${r.score}</strong></div><div>有效项目结项<strong>${r.completed}</strong></div><div>未通过项目<strong>${r.failures}</strong></div></div><h3>${esc(state.opening.name)}目标</h3>${state.goals.map((g) => `<div class="goal-row"><span>${esc(g.name)}</span><b>${num(g.value)} / ${num(g.goal)}</b><progress value="${Math.min(g.value, g.goal)}" max="${g.goal}" aria-label="${esc(g.name)}"></progress></div>`).join("")}<p>当前现金${state.cash > 0 ? "为正" : "为负"}。${state.objective_done ? "曾经达成路线目标，可继续经营。" : ""}</p><h3>创新临床漏斗</h3><p>进入 I 期 ${r.clinical_entries} 项 · 自主获批 ${r.clinical_approved} · 自主失败 ${r.clinical_failed} · 已授权 ${r.clinical_licensed} · 主动终止 ${r.clinical_terminated} · 仍在开发 ${r.clinical_ongoing}</p><p class="muted">授权项目的后续成败另记：合作方获批 ${r.partner_approvals} 项、失败 ${r.partner_failures} 项。仍在研项目不算成功。</p><h3>成长时刻</h3><p>第一笔业务收入：${r.first_income === null ? "尚未发生" : `第 ${r.first_income} 周`}<br>第一位精英：${r.rank2 === null ? "尚未出现" : `第 ${r.rank2} 周`}<br>第一位大师：${r.rank3 === null ? "尚未出现" : `第 ${r.rank3} 周`}<br>第一位传奇：${r.rank4 === null ? "尚未出现" : `第 ${r.rank4} 周`}</p><div class="card-grid"><div><h3>累计现金收入</h3>${ledger(state.income)}</div><div><h3>累计现金支出</h3>${ledger(state.expense)}</div></div><p>最低现金 ${money(r.minimum_cash)} · 初始资本之外的累计净现金流 ${money(r.profit)}</p>${modalButton("备份当前记录，开始新公司", "new")}`;
}
function ledger(values) {
  return `<table><tbody>${Object.entries(values)
    .map(
      ([k, v]) =>
        `<tr><td>${esc(categoryNames[k] || k)}</td><td>${money(v)}</td></tr>`,
    )
    .join("")}</tbody></table>`;
}
function heroOptions(filter = () => true) {
  return state.heroes
    .filter((h) => !h.busy && filter(h))
    .map(
      (h) =>
        `<option value="${h.id}">${esc(h.title)} · ${esc(h.profession_name)} ${h.ability}</option>`,
    )
    .join("");
}
function teamPicker(ids = []) {
  return `<fieldset class="team-picker"><legend>安排负责人（最多 3 位）</legend>${state.heroes.map((h) => `<label class="team-choice ${h.busy ? "unavailable" : ""}"><input type="checkbox" name="heroes" value="${h.id}" ${ids.includes(h.id) ? "checked" : ""} ${h.busy ? "disabled" : ""}><span><b>${esc(h.title)}</b><small>${esc(h.profession_name)} ${h.ability} · ${h.members} 名成员 ${h.busy ? `· 忙于 ${esc(h.busy)}` : ""}</small></span></label>`).join("")}</fieldset>`;
}
function formFrame(type, title, body, id = "") {
  return `<h2 id="modal-title">${esc(title)}</h2><button class="modal-close" data-close aria-label="关闭弹窗">×</button><form data-form="${type}" data-id="${esc(id)}">${body}<div class="form-actions"><button type="button" data-close>返回</button><button class="primary" type="submit">确认</button></div><p class="form-error" role="alert"></p></form>`;
}
function showModal(type, id = "") {
  const originalProject = state.projects.find((p) => p.id === id);
  const p =
      originalProject?.next_stage && type === "phase"
        ? { ...originalProject, ...originalProject.next_stage }
        : originalProject,
    h = state.heroes.find((h) => h.id === id);
  let html = v06Modal(type, h, p, id) || extensionModal(type, h, id);
  if (type === "project")
    html = formFrame(
      type,
      "新建研究计划",
      `<label>研究方案<select name="catalog">${state.catalog.map((c) => `<option value="${c.key}" ${!c.unlocked || c.occupied ? "disabled" : ""}>${esc(c.kind_name)} · ${esc(c.name)} ${c.occupied ? "（已在研或在售）" : !c.unlocked ? "（尚未解锁）" : ""}</option>`).join("")}</select></label><div id="catalog-note"></div><label>产品验证路径<select name="design"><option value="standard">标准开发</option><option value="validated">强化产品特性验证</option></select></label><details><summary>查看待解锁的研究方向</summary>${
        state.catalog
          .filter((c) => !c.unlocked)
          .map((c) => `<h4>${esc(c.name)}</h4><p>${checks(c.requirements)}</p>`)
          .join("") || "当前方向均已解锁"
      }</details><p>先用 8 周筛选候选与整理资料，费用 ¥70 万。研发期间需安排对应专业负责人。</p>${teamPicker(
        state.heroes
          .filter((h) => !h.busy && ["proc", "chem"].includes(h.profession))
          .slice(0, 2)
          .map((h) => h.id),
      )}`,
    );
  if (type === "phase")
    html = formFrame(
      type,
      p.phase,
      `<p>${esc(p.question)}</p><label>研究方案<select name="plan">${p.plans.map((plan) => `<option value="${plan.plan}" ${p.population === "focused" && p.key === "III" && plan.plan === "focused" ? "selected" : ""}>${esc(plan.name)}</option>`).join("")}</select></label><label>执行方式<select name="mode"><option value="internal" ${p.recommended_mode === "internal" ? "selected" : ""}>${["I", "II", "III", "be", "bridge", "confirm"].includes(p.key) ? "自营临床 · 占用席位" : "本公司实验室 · 占用负责人"}</option>${["I", "II", "III", "be", "bridge", "confirm"].includes(p.key) ? `<option value="cro" ${p.recommended_mode === "cro" ? "selected" : ""}>外部 CRO · 临床能力 55，阶段费 +30%</option>` : ""}</select></label>${teamPicker(p.recommended)}<div id="phase-preview" class="hint">正在按当前团队核对费用与研究方案…</div>`,
      id,
    );
  if (type === "experiment")
    html = formFrame(
      type,
      "补证据，或定向优化",
      `<label>研究方法<select name="method">${Object.entries(state.experiments)
        .filter(
          ([k]) => p.kind !== "generic" || ["validate", "refine"].includes(k),
        )
        .map(
          ([k, v]) =>
            `<option value="${k}">${esc(v.name)} · ${v.weeks} 周 / ${money(v.cost)}</option>`,
        )
        .join(
          "",
        )}</select></label><div id="experiment-note"></div><label>关注指标<select name="stat">${Object.entries(
        state.stats,
      )
        .filter(([k]) => p.kind !== "generic" || k !== "effect")
        .map(([k, v]) => `<option value="${k}">${v}</option>`)
        .join("")}</select></label>${teamPicker(p.recommended)}`,
      id,
    );
  if (type === "switch")
    html = formFrame(
      type,
      "更换候选，需要重新验证",
      `<p>花费 ¥60 万返回第一阶段，原候选证据会留档；临床后不能直接换分子。</p><label>其他候选<select name="candidate">${p.candidates
        .filter((c) => c.id !== p.chosen)
        .map(
          (c) =>
            `<option value="${c.id}">候选 ${c.id + 1} · ${esc(c.label)}</option>`,
        )
        .join("")}</select></label>${p.candidates
        .filter((c) => c.id !== p.chosen)
        .map((c) => `<h3>候选 ${c.id + 1}</h3>${evidence(c)}`)
        .join("")}`,
      id,
    );
  if (type === "launch")
    html = formFrame(
      type,
      "让第一批产品走向市场",
      `<p>上市准备费 ${money(p.kind === "generic" ? 80 : 180)}。先采用委托生产，销售会逐渐形成；之后可以分配自营生产线。</p><label>药品名字<input name="name" maxlength="30" value="${esc(p.name)}"></label>`,
      id,
    );
  if (type === "terminate")
    html = formFrame(
      type,
      "终止这个研究计划",
      `<p>${esc(p.name)}已经投入 ${money(p.spent)}。终止后释放负责人和未支出的预算，保留已取得的证据；不能收回已经花掉的费用。</p>`,
      id,
    );
  if (type === "rework")
    html = formFrame(
      type,
      "补正实际工艺，再验证",
      `<p>8 周、¥100 万，改善本次发现的工艺或等效性短板。每个候选最多一次，随后仍需支付验证阶段的费用。</p>${teamPicker()}`,
      id,
    );
  if (type === "license")
    html = `<h2 id="modal-title">比较授权与共同开发</h2><button class="modal-close" data-close aria-label="关闭弹窗">×</button><p>后续失败时保留首付款，未达成的里程碑不会支付。分成按实际销售额计算。</p><div class="license-grid">${p.quotes.map((q) => `<article class="candidate"><h3>${esc(q.name)}</h3><p>首付款<strong>${money(q.upfront)}</strong></p><p>通过 I 期 ${money(q.human_milestone)}<br>通过 II 期 ${money(q.proof_milestone)}<br>获批 ${money(q.approval_milestone)}</p><p>销售分成 <b>${num(q.royalty * 100)}%</b><br>我方开发费 ${num(q.cost_share * 100)}%<br>剩余承诺 ${money(q.owner_commitment)}</p>${button("签约 · " + q.name, "license_project", { project: id, terms: q.kind }, "primary")}</article>`).join("")}</div><small>已完成的里程碑不会重新支付。报价依据现有证据、市场与剩余风险。</small>`;
  if (type === "team")
    html = formFrame(
      type,
      h.title + " · 配置团队",
      `<p>负责人决定专业和研究手段，成员改善执行速度。有效成员最多 ${2 + h.rank} 位；更多成员仍有工资。</p><label>成员人数<input name="members" type="number" min="0" max="6" value="${h.members}" required></label><p>每人每周 ¥0.42 万，增减每人一次性 ¥4 万。</p>${button("暂离公司 · 保留角色履历", "dismiss", { character: id }, "danger", !!h.busy)}`,
      id,
    );
  if (type === "mentor")
    html = formFrame(
      type,
      "安排同专业导师课题",
      `<label>导师<select name="teacher">${heroOptions((x) => x.rank >= 2 && state.heroes.some((y) => !y.busy && y.profession === x.profession && y.rank < x.rank && !y.mentored.includes(x.id)))}</select></label><label>学习者<select name="pupil"></select></label><p>需要同专业且导师阶位更高。两人占用 10 周，费用 ¥60 万；每对导师关系只能完成一次入门课题。</p>`,
    );
  if (type === "service") {
    const o = state.orders.find((o) => o.id === id);
    html = formFrame(
      type,
      o.name,
      `<p>交付 ${o.weeks} 周、回款 ${money(o.reward)}，前期材料 ${money(o.cost)}。</p><label>交付负责人<select name="character">${heroOptions((h) => h.profession === o.profession)}</select></label>`,
      id,
    );
  }
  if (type === "collaborate") {
    const c = state.roster.find((c) => c.key === id);
    html = formFrame(
      type,
      "与" + c.name + "开展联合课题",
      `<p>需要同专业能力 45 的负责人。10 周、¥120 万；完成后可支付 ${money(c.cost)} 正式邀请。</p><label>合作负责人<select name="researcher">${heroOptions((h) => h.profession === c.profession && h.ability >= 45)}</select></label>`,
      id,
    );
  }
  if (type === "roster")
    html = `<h2 id="modal-title">伙伴图鉴 · 从见习到传奇</h2><button class="modal-close" data-close aria-label="关闭弹窗">×</button><p>所有加入条件公开。专业成果会吸引更强的伙伴，普通角色也可通过晋阶走到传奇。</p><div class="roster-grid">${state.roster.map((c) => `<article class="hero-card ${rankClass(c.tier)}"><span class="rank-tag">${esc(c.rank_name)}</span><h3>${esc(c.name)}</h3><p>${esc(c.profession_name)} · 能力 ${c.ability}</p><p>${esc(c.story)}</p><p><b>${esc(c.trait.name)}</b> · ${esc(c.trait.description)}</p><p>${checks(c.requirements)}</p><p>签约 ${money(c.cost)}</p>${c.connecting ? '<span class="badge">联合课题进行中</span>' : c.tier >= 3 && !c.connected ? `<button data-modal="collaborate" data-id="${c.key}" ${!c.unlocked ? "disabled" : ""}>合作课题 · ¥120 万</button>` : button("邀请加入", "hire", { character: c.key }, "primary", !c.unlocked)}</article>`).join("")}</div>`;
  if (type === "new")
    html = formFrame(
      type,
      "开始一家新的研究社",
      `<div class="opening-options">${Object.entries(state.scenarios)
        .map(
          ([k, c]) =>
            `<label class="opening-choice"><input type="radio" name="scenario" value="${k}" ${k === state.scenario ? "checked" : ""}><span><b>${esc(c.name)} · ${money(c.cash)}</b><small>${esc(c.description)}</small><small>目标：${esc(c.goal)}</small></span></label>`,
        )
        .join(
          "",
        )}</div><label>经营模式<select name="difficulty">${Object.entries(
        state.challenge.modes,
      )
        .map(
          ([key, d]) =>
            `<option value="${key}">${esc(d.name)} · ${esc(d.text)}</option>`,
        )
        .join(
          "",
        )}</select></label><p>模式开局后固定。当前进度先备份到本地，新版使用独立存档。</p><label>随机种子<input name="seed" type="number" min="0" max="999999999" value="42" required></label>`,
    );
  if (type === "help")
    html = `<h2 id="modal-title">经营一间会成长的研究社</h2><button class="modal-close" data-close aria-label="关闭弹窗">×</button><ol><li>从普通仿制或技术服务建立现金流，也可以承担更高风险直接研究创新药。</li><li>候选资料是估计范围。复核可能揭露坏消息，扩大试验也不能保证成功。</li><li>负责人按专业配合。成员主要改善执行速度；人物晋阶还要真实项目履历。</li><li>缺钱或等人时，点击项目的「暂缓决策」，再推进其他业务。未开工阶段不收费。</li><li>创新项目在临床前或 II 期取得支持证据后，可以比较授权、分成和共同开发。</li><li>先看已承诺支出，再看账面现金。新阶段、工资和上市准备都要预留。</li><li>进入研究社的伙伴图鉴，可以提前看到精英、大师与传奇的解锁条件。</li></ol><p>当前版本的时间、指标和经济数值为游戏规则，流程参考研发逻辑。8880 荣誉版保留独立运行。本版在 8881 使用独立存档；2.5D 交互样稿另行展示。</p>`;
  $("#modal-body").innerHTML = html;
  if (!$("#modal").open) $("#modal").showModal();
  if (type === "phase") updatePreview();
  if (type === "mentor") {
    const teacher = $("select[name=teacher]");
    if ([...teacher.options].some((o) => o.value === id)) teacher.value = id;
    updateMentor();
  }
  if (type === "project" || type === "experiment") updateNotes();
}
function formArgs(form) {
  const data = new FormData(form),
    type = form.dataset.form,
    id = form.dataset.id;
  const heroes = data.getAll("heroes");
  const extra = v06Form(type, data, id);
  if (extra) return extra;
  const mapping = {
    study: ["independent_study", { product: id, heroes }],
    project: [
      "start_project",
      {
        catalog: data.get("catalog"),
        heroes,
        design: data.get("design") || "standard",
      },
    ],
    phase: [
      state.projects.find((p) => p.id === id)?.status === "result"
        ? "continue_and_run"
        : "run_phase",
      { project: id, heroes, plan: data.get("plan"), mode: data.get("mode") },
    ],
    experiment: [
      "experiment",
      {
        project: id,
        heroes,
        method: data.get("method"),
        stat: data.get("stat"),
      },
    ],
    switch: [
      "switch_candidate",
      { project: id, candidate: Number(data.get("candidate")) },
    ],
    launch: ["launch", { project: id, name: data.get("name") }],
    terminate: ["terminate", { project: id }],
    rework: ["rework", { project: id, heroes }],
    team: ["resize", { character: id, members: Number(data.get("members")) }],
    mentor: [
      "mentor",
      { teacher: data.get("teacher"), pupil: data.get("pupil") },
    ],
    service: ["take_service", { order: id, character: data.get("character") }],
    collaborate: [
      "collaborate",
      { character: id, researcher: data.get("researcher") },
    ],
    new: [
      "new_game",
      {
        scenario: data.get("scenario"),
        seed: Number(data.get("seed")),
        difficulty: data.get("difficulty"),
      },
    ],
  };
  return mapping[type];
}
async function updatePreview() {
  const form = $('form[data-form="phase"]');
  if (!form) return;
  const [, args] = formArgs(form),
    sequence = ++previewSequence;
  try {
    const response = await fetch("/api/preview", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Game-Token": state.token,
      },
      body: JSON.stringify({ args, revision: state.revision }),
    });
    const v = await response.json();
    if (sequence !== previewSequence || !$("#phase-preview")) return;
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = !response.ok;
    $("#phase-preview").innerHTML = response.ok
      ? `<b>${v.weeks} 周 · ${money(v.cost)} · 本阶段 ${esc(v.chance)}</b><p>安排后可用现金 ${money(v.reserve)}，仍需预留工资和后续阶段。</p><small>${esc(v.note)}</small>`
      : `<b>${esc(v.error)}</b>`;
  } catch (error) {
    if ($("#phase-preview"))
      $("#phase-preview").textContent = "暂时无法核对方案，请重新打开。";
  }
}
function updateMentor() {
  const form = $('form[data-form="mentor"]');
  if (!form) return;
  const teacher = state.heroes.find(
    (h) => h.id === form.elements.teacher.value,
  );
  const pupil = form.elements.pupil,
    previous = pupil.value;
  pupil.innerHTML = teacher
    ? heroOptions(
        (h) =>
          h.profession === teacher.profession &&
          h.rank < teacher.rank &&
          !h.mentored.includes(teacher.id),
      )
    : "";
  if ([...pupil.options].some((o) => o.value === previous))
    pupil.value = previous;
  form.querySelector('button[type="submit"]').disabled = !pupil.options.length;
  form.querySelector(".form-error").textContent = pupil.options.length
    ? ""
    : "目前没有可以带教的同专业组合；先邀请伙伴或提升导师阶位。";
}
function updateNotes() {
  const cf = $('form[data-form="project"]');
  if (cf) {
    const c = state.catalog.find(
      (c) => c.key === new FormData(cf).get("catalog"),
    );
    if (c) {
      const design = cf.elements.design;
      design.disabled = !c.product_profile;
      if (!c.product_profile) design.value = "standard";
      $("#catalog-note").innerHTML =
        `<p><b>${esc(c.indication)} · ${esc(c.target)} · ${esc(c.modality)}</b></p><p>${esc(c.description)}</p><p>当前同领域竞争压力 ${c.competition.toFixed(1)} / 3 · 公布在研的对手：${c.announced_rivals.map(esc).join("、") || "暂无"}。在研管线可能失败，不能当作已上市。</p><small>${c.kind === "generic" ? "虚构参比产品，当前可进入市场；先建立制剂与质量证据。" : c.kind === "improved" ? "具体改动需要桥接和价值确认。" : "临床会新增人体证据，早期估计不能保证获批。"}</small>${productNote(c)}`;
    }
  }
  const ef = $('form[data-form="experiment"]');
  if (ef) {
    const d = state.experiments[new FormData(ef).get("method")];
    $("#experiment-note").innerHTML = `<p>${esc(d.text)}</p>`;
  }
}
document.addEventListener("click", (event) => {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.close !== undefined) {
    $("#modal").close();
    return;
  }
  if (target.dataset.tab) {
    activeTab = target.dataset.tab;
    render();
    return;
  }
  if (target.dataset.modal) {
    event.preventDefault();
    showModal(target.dataset.modal, target.dataset.id || "");
    return;
  }
  if (target.dataset.command) {
    event.preventDefault();
    send(target.dataset.command, JSON.parse(target.dataset.args || "{}"));
  }
  if (target.dataset.action === "save") {
    event.preventDefault();
    send("save");
  }
});
document.addEventListener("submit", (event) => {
  const form = event.target.closest("form[data-form]");
  if (!form) return;
  event.preventDefault();
  const [name, args] = formArgs(form);
  send(name, args);
});
document.addEventListener("change", (event) => {
  if (event.target.closest('form[data-form="phase"]')) updatePreview();
  if (event.target.name === "teacher") updateMentor();
  updateNotes();
});
fetch("/api/state")
  .then((r) => r.json())
  .then((data) => {
    state = data;
    render();
    $("#save-status").textContent = "本地进度已载入";
  })
  .catch((error) => notice("无法连接本地服务：" + error.message, true));
