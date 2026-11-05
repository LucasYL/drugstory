function competitionView() {
  return `<h2>有对手，也有机会</h2><p class="muted">三家研究机构有不同偏好。阶段可能延期或失败；相同种子可以复现，刷新不会改变结果。对手影响市场与年度评选，不会抬高你的审批门槛。</p>
  <div class="card-grid">${state.rivals.map((r) => `<article class="project-card"><span class="badge">${esc(r.style_name)}</span><h3>${esc(r.name)}</h3><p>${esc(r.description)}</p><h4>${esc(r.market_name)} · ${r.status === "rebuilding" ? "调整下一计划" : esc(r.phase)}</h4><p>${esc(r.last_update)}</p>${r.status === "developing" ? `<p>若顺利推进，预计第 ${r.eta_low}–${r.eta_high} 周进入市场；不是承诺。</p>` : "<p>下一条管线方向将重新公布。</p>"}<p>在售：${r.products.map((p) => `${esc(p.market)}（余 ${p.remaining} 周）`).join("、") || "暂无"}</p><details><summary>近期情报</summary>${r.history.map((e) => `<p>第 ${e.week} 周 · ${esc(e.text)}</p>`).join("") || "<p>等待首次数据公布。</p>"}</details></article>`).join("")}</div>
  <div class="hint">应对方式：转向竞争较少的领域；取得概念验证后授权；完善产品证据；保留仿制现金流，避免为了抢先而跳过证据。</div>`;
}
function honorsView() {
  const h = state.honors;
  return `<h2>让二十年，留下值得记住的事</h2><p class="muted">第一年只有观察与积累。第 2 年起每年选一个方向参评，第 46 周锁定报名，年末公布结果。早期认可、年度专业奖、终局荣誉逐层推进。</p>
  <h3>第 ${h.year} 届研究大会</h3><div class="card-grid">${h.categories.map((c) => `<article class="project-card"><h3>${esc(c.name)}</h3><p>${esc(c.description)}</p><p>本年成果分 <b>${c.score}</b> · 当前领先线 <b>${c.benchmark}</b></p><p class="muted">${esc(c.requirement)}</p><details><summary>本届对手</summary>${c.field.map((r) => `<p>${esc(r.name)} · ${r.score}</p>`).join("")}</details>${h.entry === c.key ? '<span class="badge">已报名这个方向</span>' : button("报名 " + c.name, "nominate", { category: c.key }, "primary", !c.eligible || state.week % 48 >= 46 || state.game_over)}</article>`).join("")}</div>
  <h3>终局挑战</h3><p>最高科学荣誉「星火生命科学大奖」是游戏中的诺贝尔级挑战，奖励经验证的突破与培养传承，不因一款药获批自动授予。</p>
  <div class="legacy-grid">${h.legacies.map((g) => `<article class="project-card ${g.won ? "legacy-won" : ""}"><span class="badge">${g.won ? "已达成" : "长线目标"}</span><h3>${esc(g.name)}</h3><progress max="${g.checks.length}" value="${g.checks.filter((x) => x.ok).length}" aria-label="${esc(g.name)}进度"></progress><p>${checks(g.checks)}</p><small>全部达成后，在年末大会授予。</small></article>`).join("")}</div>
  <h3>让突破经得起验证</h3><p class="muted">高难创新药上市后，凭公开 III 期结果解锁两轮独立研究。结果可能推翻早期判断，不能付费反复重抽。</p>
  ${
    h.studies
      .map(
        (t) =>
          `<article class="project-card"><h3>${esc(t.name)} · ${esc(t.title)}</h3><p>${t.weeks} 周 · ${money(t.cost)} · ${esc(t.roles)}</p><p>${checks(t.checks)}</p>${
            t.running
              ? `<p class="hint">研究进行中 · 还需 ${t.running.left} 周<br>负责人：${t.running.heroes.map((id) => esc(state.heroes.find((h) => h.id === id)?.name || id)).join("、")}</p>`
              : t.available
                ? modalButton("安排独立研究", "study", t.product)
                : "<button disabled>研究条件尚未满足</button>"
          }</article>`,
      )
      .join("") ||
    empty(
      "先留下高难度创新成果。可用自主或授权后获批的产品，研究贡献同样记在你的团队名下。",
    )
  }
  <div class="card-grid">${h.proofs.map((p) => `<article class="candidate"><h4>${esc(p.name)} · 第 ${p.step + 1} 轮</h4><p class="${p.passed ? "good" : "danger"}">${p.passed ? "取得独立支持" : "本轮证据未获支持"}</p><p>获益 ${p.values.effect} / ≥${p.limits.effect} · 安全 ${p.values.safety} / ≥${p.limits.safety}</p></article>`).join("")}</div>
  <h3>公司大事记</h3><div class="achievement-row">${h.achievements.map((a) => `<span class="badge">${esc(a.name)} · 第 ${a.week} 周</span>`).join("") || "还没有记录。第一粒药、第一项专利、搬进新场地、第一位精英都会记在这里。"}</div>
  <h3>奖杯室</h3>${h.awards.map((a) => `<p>第 ${a.year} 年 · <b>${esc(a.name)}</b> · 成果分 ${a.score}</p>`).join("") || '<p class="muted">现在还是空的。这里会记录你的第一次获奖，以及后来的每一次突破。</p>'}
  <h3>历届大会</h3>${h.festivals.length ? modalButton("回看最近一届颁奖", "ceremony") : ""}${
    h.festivals
      .slice()
      .reverse()
      .map(
        (f) =>
          `<details><summary>第 ${f.year} 年评选结果</summary><table><tbody>${f.results.map((r) => `<tr><td>${esc(r.name)}</td><td>${esc(r.winner)}</td><td>${esc(r.reason)}<br>我方 ${r.your_score} / 领先线 ${r.leading_score}</td></tr>`).join("")}</tbody></table></details>`,
      )
      .join("") || "<p>第一届大会尚未举行。</p>"
  }`;
}
function extensionModal(type, h, id) {
  if (type === "ceremony") return ceremonyView();
  if (type === "study") {
    const study = state.honors.studies.find((x) => x.product === id);
    return formFrame(
      type,
      study.title + " · " + study.name,
      `<p>${study.weeks} 周、${money(study.cost)}。需要 ${esc(study.roles)} 大师。失败结果保留，同一产品不能重复这一轮。</p>${teamPicker(study.recommended)}`,
      id,
    );
  }
  return "";
}

function ceremonyView() {
  const last = state.honors.festivals.at(-1);
  if (!last) return "";
  const won = last.results.filter((r) => r.won);
  const grand = state.honors.legacy_awards.filter((a) => a.year === last.year);
  const title = grand.length
    ? "这一年，留下了科学的名字"
    : won.length
      ? "轮到我们走上领奖台"
      : "把今年的积累，带到下一次舞台";
  const explanation =
    last.year === 1
      ? "街角实验室的第一年，还没有奖杯。明年起，可以选择一个专业方向参评。"
      : last.entry
        ? "本届尚未获奖。已有研究与培养成果会继续留在你的履历里。"
        : "今年没有报名。下一届可以比较四个方向，选择最能代表研究社的成果。";
  return `<div class="ceremony"><span class="award-emblem" aria-hidden="true">✦</span>
    <p>第 ${last.year} 届研究大会</p><h2 id="modal-title">${title}</h2>
    <button class="modal-close" data-close aria-label="关闭弹窗">×</button>
    ${grand
      .map(
        (a) => `<article class="legacy-won project-card"><h3>${esc(a.name)}</h3>
      <p>研究社的突破与传承获得终局荣誉。</p><p>${a.heroes.map(esc).join(" · ")}</p></article>`,
      )
      .join("")}
    ${
      won
        .map(
          (a) => `<h3 class="good">${esc(a.name)}</h3>
      <p>成果分 ${a.your_score} · 本届领先线 ${a.leading_score}</p>`,
        )
        .join("") ||
      `<p>${grand.length ? "终局荣誉已永久记入奖杯室。年度专业奖仍可在后续年份继续挑战。" : explanation}</p>`
    }
    <details><summary>完整评选与差距</summary>
    ${last.results
      .map(
        (r) => `<p><b>${esc(r.name)}</b> · ${esc(r.winner)}<br>
      ${esc(r.reason)} · 我方 ${r.your_score} / ${r.leading_score}</p>`,
      )
      .join("")}</details>
    <button class="primary" data-close>带着新的目标，继续研究 →</button></div>`;
}
