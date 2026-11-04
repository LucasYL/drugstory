/* v0.6 panels share commands with CLI and simulations. No rules run here. */
function personalCard(h) {
  const q = h.personal_project;
  return `<div class="hint"><b>个人课题 · ${esc(q.title)}</b><p>${esc(q.story)}</p>${q.done ? `<span class="good">已完成：${esc(q.choices[q.done.choice].name)} · 可抵一项晋阶履历要求</span><p>${esc(q.choices[q.done.choice].text)} 搭档专业：${esc(q.partner_name)}。</p>` : q.running ? `<span>与伙伴研究中 · 剩余 ${q.running.left} 周</span>` : `${modalButton(q.unlocked ? "升级招牌能力" : "查看课题与解锁条件", "personal", h.id)}`}</div>`;
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
  return `<p class="muted">${state.challenge.mode === "competition" ? "产业竞逐：更强对手、有限市场容量；研发门槛不随财富增加。" : "舒展经营：新开局可选择产业竞逐。"}</p>`;
}
function equipmentPanel() {
 return `<h3>实验室设备</h3><div class="card-grid">${state.equipment.map(r=>`<article class="project-card"><h4>${esc(r.name)} · ${r.level} 级</h4><p>${esc(r.text)}</p>${r.cost ? button("升级 · "+money(r.cost),"upgrade_equipment",{profession:r.profession},"",!r.available):"已达最高级"}</article>`).join("")}</div>`;
}
function workList(work) {
 return (work||[]).length ? `<p><b>本阶段预计开发贡献（总量，有上限）</b></p>${work.map(w=>`<p>${esc(state.heroes.find(h=>h.id===w.actor)?.name||w.actor)} · ${w.members} 位成员：${Object.entries(w.amounts).map(([k,v])=>esc(state.stats[k])+" "+(v>=0?"+":"")+v).join(" / ")}</p>`).join("")}` : "";
}
function workPanel(p) {
 return `<details ${p.status==="running"||p.status==="checkpoint"?"open":""}><summary>阶段工作与分批证据</summary>${workList(p.work)}${p.interim_chance?`<p>结合已回数据，本阶段预计 ${esc(p.interim_chance)}；尚非最终结果。</p>`:""}${p.readings.slice(-4).map(r=>`<p>第 ${r.week} 周 · 候选 ${r.candidate+1} · ${esc(r.stage_name)} 第 ${r.index}/4 批：${Object.entries(r.values).map(([k,v])=>esc(state.stats[k])+" "+v).join(" / ")}</p>`).join("")||(p.work.length ? "<p>开发工作分三批完成，开发量在候选可实现的上限内生效，结束时检验；不是反复刷分。</p>" : "<p>分批收集观察，最终按预先确定的四批均值判定；单批波动可能很大。</p>")}</details>`;
}
function catalogPicker() {
 const targets=[...new Set(state.catalog.filter(c=>c.target_id).map(c=>c.target))];
 return `<label>路线<select name="route"><option value="generic">仿制药</option><option value="improved">改良药</option><option value="innovative">创新组合</option></select></label><label>靶点筛选<select name="target_filter"><option value="">全部靶点</option>${targets.map(t=>`<option>${esc(t)}</option>`).join("")}</select></label><label>研究组合<select name="catalog"></select></label><p>创新组合手记：${Object.keys(state.notebook).length} / 288。每个组合有不同的适配与解锁要求；不是 288 条独立剧情。</p>`;
}
function filterCatalog() {
 const form=document.querySelector('form[data-form="project"]'); if(!form)return;
 const route=form.elements.route.value;
 if(route==="innovative" && !form.elements.target_filter.value) form.elements.target_filter.selectedIndex=1;
 const target=form.elements.target_filter.value;
 form.elements.target_filter.disabled=route!=="innovative";
 const items=state.catalog.filter(c=>c.kind===route && (route!=="innovative"||!target||c.target===target));
 form.elements.catalog.innerHTML=items.map(c=>`<option value="${c.key}">${esc(c.name)}${c.occupied?"（在研/在售）":!c.unlocked?"（待解锁）":""}</option>`).join("");
 updateNotes();
}
document.addEventListener("change",event=>{if(["route","target_filter"].includes(event.target.name))filterCatalog();});
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
            `<label class="opening-choice"><input type="radio" name="choice" value="${key}" ${key === "practice" ? "checked" : ""}><span><b>${esc(c.name)} · ${c.weeks} 周 / ${money(c.cost)}</b><small>${esc(c.text)}</small></span></label>`,
        )
        .join(
          "",
        )}</div><p>课题同时占用两位伙伴。完成后升级本人的招牌能力，并抵一项晋阶履历；不会伪造项目结项。</p>`,
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
