/* v0.6 panels share commands with CLI and simulations. No rules run here. */
function personalCard(h) {
  const q = h.personal_project;
  return `<div class="hint"><b>个人课题 · ${esc(q.title)}</b><p>${esc(q.story)}</p>${q.done ? `<span class="good">已完成：${esc(q.choices[q.done.choice].name)} · 可抵一项晋阶履历要求</span><p>${esc(q.choices[q.done.choice].text)} 搭档专业：${esc(q.partner_name)}。</p>` : q.running ? `<span>与伙伴研究中 · 剩余 ${q.running.left} 周</span>` : `${modalButton(q.unlocked ? "选择课题方向" : "查看课题与解锁条件", "personal", h.id)}`}</div>`;
}
function trialPanel(p) {
  const v = p.trial_decision;
  return `<div class="hint"><h3>${esc(v.title)}</h3><p>${esc(v.text)}</p><div class="card-grid">${v.choices.map((c) => `<article><h4>${esc(c.name)}</h4><p>${esc(c.text)}</p>${button("选择" + c.name, "trial_decision", { project: p.id, choice: c.key }, c.key === "keep" ? "" : "primary")}</article>`).join("")}</div></div>`;
}
function productNote(p) {
  const d = p.product_profile;
  return d
    ? `<details><summary>产品特性 · ${esc(d.title)}${p.design === "validated" ? " · 强化验证" : ""}</summary><p>${esc(d.text)}</p><p>关键指标：${esc(state.stats[d.stat])} ≥ ${d.limit}。选择「${esc(d.enhanced)}」后，关键阶段多 2 周、费用 +25%，观察误差减少 20%；通过才获得对应商业效果。</p></details>`
    : "";
}
function productSalesNote(d) {
  const names = {
    supply: "双来源供货",
    stability: "稳定性验证 · 生命周期 +48 周",
    adherence: "服用便利 · 更快导入",
    quality: "制造效率 · 利润率 +3 个百分点",
    tolerability: "耐受性支持 · 需求 +10%",
  };
  const capacity = state.market_capacity[d.market];
  return `<p class="muted">${d.design_reward ? esc(names[d.design_reward]) : "标准产品路径"}${d.catalog === "g_pressure" && d.design_reward !== "supply" ? " · 每第三季度供货折减 12%（当前" + (Math.floor(state.week / 12) % 3 === 2 ? "生效" : "未生效") + "）" : ""}${capacity?.capacity ? ` · 本领域容量 ${money(capacity.capacity)} / 周，当前容量分配 ${(capacity.factor * 100).toFixed(0)}%` : ""}</p>`;
}
function challengePanel() {
  const c = state.challenge;
  if (c.mode !== "competition")
    return `<p class="muted">当前模式：舒展经营。新开公司时可选「产业竞逐」。</p>`;
  return `<section class="project-card"><h3>产业竞逐 · 平台维护</h3><p>当前每周 ${money(c.upkeep)}；费用按场地级别固定，不随财富上涨。新策略从下周计费，新阶段采用新精度。</p><div class="card-grid">${Object.entries(
    c.policies,
  )
    .map(
      ([key, p]) =>
        `<div><b>${esc(p.name)}</b><p>${esc(p.text)}</p>${button(c.policy === key ? "正在采用" : "采用此策略", "platform_policy", { policy_name: key }, "", c.policy === key)}</div>`,
    )
    .join(
      "",
    )}</div><p>同领域总容量会限制需求分配。产品与合作页可查看当前影响；对手研发更快，临床过关要求保持相同。</p></section>`;
}
function v06Modal(type, h, p, id) {
  if (type === "personal") {
    const q = h.personal_project;
    if (!q.unlocked || h.busy || !q.partners.length)
      return `<h2 id="modal-title">${esc(q.title)}</h2><button class="modal-close" data-close aria-label="关闭弹窗">×</button><p>${esc(q.story)}</p><p>${checks(q.checks)}</p><p>需要一位空闲的${esc(q.partner_name)}伙伴。${h.busy ? "本人还在工作，请先完成当前安排。" : ""}</p>`;
    return formFrame(
      type,
      q.title,
      `<p>${esc(q.story)}</p><label>研究伙伴<select name="partner">${q.partners
        .map((id) => {
          const x = state.heroes.find((h) => h.id === id);
          return `<option value="${id}">${esc(x.name)} · ${esc(x.profession_name)}</option>`;
        })
        .join(
          "",
        )}</select></label><div class="opening-options">${Object.entries(
        q.choices,
      )
        .map(
          ([key, c]) =>
            `<label class="opening-choice"><input type="radio" name="choice" value="${key}" ${key === "verify" ? "checked" : ""}><span><b>${esc(c.name)} · ${c.weeks} 周 / ${money(c.cost)}</b><small>${esc(c.text)}</small></span></label>`,
        )
        .join(
          "",
        )}</div><p>课题同时占用两位伙伴。完成后永久保留一种协作能力，并抵一项晋阶履历；不会伪造项目结项。</p>`,
      id,
    );
  }
  if (type === "batch") {
    const orders = state.orders.filter((o) => !o.taken);
    return formFrame(
      type,
      "一次安排本期服务",
      `<p>可选 1–3 单，每位伙伴只能负责一单。先核对全部安排，再一起开工。</p>${orders.map((o) => `<label>${esc(o.name)} · ${money(o.cost)} 材料 / ${money(o.reward)} 回款<select name="order:${o.id}"><option value="">暂不安排</option>${heroOptions((h) => h.profession === o.profession && h.ability >= o.requirement)}</select></label>`).join("")}`,
    );
  }
  return "";
}
function v06Form(type, data, id) {
  if (type === "personal")
    return [
      "personal_project",
      {
        character: id,
        partner: data.get("partner"),
        choice: data.get("choice"),
      },
    ];
  if (type === "batch")
    return [
      "take_services",
      {
        assignments: [...data.entries()]
          .filter(([k, v]) => k.startsWith("order:") && v)
          .map(([k, v]) => ({ order: k.slice(6), character: v })),
      },
    ];
  return null;
}
