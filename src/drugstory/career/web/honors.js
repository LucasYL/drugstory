function competitionView() {
  return `<h2>有对手，也有机会</h2><p class="muted">三家研究机构有不同偏好。阶段可能延期或失败；相同种子可以复现，刷新不会改变结果。对手影响市场与年度评选，不会抬高你的审批门槛。</p>
  <div class="card-grid">${state.rivals.map((r) => `<article class="project-card"><span class="badge">${esc(r.style_name)}</span><h3>${esc(r.name)}</h3><p>${esc(r.description)}</p><h4>${esc(r.market_name)} · ${r.status === "rebuilding" ? "调整下一计划" : esc(r.phase)}</h4><p>${esc(r.last_update)}</p>${r.status === "developing" ? `<p>若顺利推进，预计第 ${r.eta_low}–${r.eta_high} 周进入市场；不是承诺。</p>` : "<p>下一条管线方向将重新公布。</p>"}<p>在售：${r.products.map((p) => `${esc(p.market)}（余 ${p.remaining} 周）`).join("、") || "暂无"}</p><details><summary>近期情报</summary>${r.history.map((e) => `<p>第 ${e.week} 周 · ${esc(e.text)}</p>`).join("") || "<p>等待首次数据公布。</p>"}</details></article>`).join("")}</div>
  <div class="hint">应对方式：转向竞争较少的领域；取得概念验证后授权；完善产品证据；保留仿制现金流，避免为了抢先而跳过证据。</div>`;
}
function honorsView() {
  const h = state.honors;
  return `<h2>让二十年，留下值得记住的事</h2><p class="muted">第一年只有观察与积累。第 2 年起不用报名：年末自动评所有类别，每年最多颁一个大奖，其余胜出的类别记为提名。对手的领先线每年提高；同一类第二次获奖奖金减半。</p>
  <h3>章节与疾病地图</h3><p>${state.chapters.current ? `第 ${state.chapters.current.index} 章「${esc(state.chapters.current.name)}」 · 目标：${esc(state.chapters.current.goal)}` : "五章都完成了"} · 已攻克 ${state.chapters.cured} 种疾病 ${modalButton("查看章节与地图", "chapters")}</p>
  <h3>研究所评级</h3><p>${state.rating.final ? `任期评级 <b>${state.rating.final.grade}</b>「${esc(state.rating.final.title)}」，已定格。` : `按当前进度预计 <b>${state.rating.projected.grade}</b>「${esc(state.rating.projected.title)}」 · ${state.rating.term} 年任期还剩 ${Math.ceil(state.rating.weeks_left / 48)} 年 · 已帮助 ${num(Math.round(state.rating.patients / 10000))} 万人次`} ${modalButton("查看五项分数", "rating")}</p>
  <h3>第 ${h.year} 届研究大会</h3><div class="card-grid">${h.categories.map((c) => `<article class="project-card"><h3>${esc(c.name)}</h3><p>${esc(c.description)}</p><p>本年成果分 <b>${c.score}</b> · 当前领先线 <b>${c.benchmark}</b></p><p class="muted">${esc(c.requirement)}</p><details><summary>本届对手</summary>${c.field.map((r) => `<p>${esc(r.name)} · ${r.score}</p>`).join("")}</details>${awardStatus(c)}</article>`).join("")}</div>
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
  <h3>奖杯室</h3>${h.awards.map((a) => `<p>第 ${a.year} 年 · <b>${esc(a.name)}</b> · 成果分 ${a.score}</p>`).join("") || '<p class="muted">现在还是空的。这里会记录你的第一次获奖，以及后来的每一次突破。</p>'}${h.nominations.length ? `<p class="muted">提名：${h.nominations.map((n) => `第 ${n.year} 年${esc(n.name)}`).join("、")}</p>` : ""}
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
function awardStatus(c) {
  if (state.week < 48) return '<span class="badge">第 2 年起自动参评</span>';
  if (!c.eligible) return '<span class="badge">还没有可参评的成果</span>';
  if (c.score >= c.benchmark) return `<span class="badge good">目前领先${c.repeat ? " · 再次获奖奖金减半" : ""}</span>`;
  return `<span class="badge">还差 ${c.gap} 分</span>`;
}
function extensionModal(type, h, id) {
  if (type === "ceremony") return ceremonyView();
  if (type === "rating") return ratingView();
  if (type === "chapters") return chaptersView(id === "done");
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

function chaptersView(celebrate) {
  const c = state.chapters;
  const close = '<button class="modal-close" data-close aria-label="关闭弹窗">×</button>';
  const last = c.done.at(-1);
  const head =
    celebrate && last
      ? `<div class="chapter-done"><p>章节完成</p><h2 id="modal-title">「${esc(last.name)}」 ${"★".repeat(last.stars)}${"☆".repeat(3 - last.stars)}</h2></div>`
      : `<h2 id="modal-title">研究所的路</h2>`;
  const cur = c.current
    ? `<section class="chapter-now"><p class="sub">第 ${c.current.index} / ${c.total} 章 · ${esc(c.current.when)}</p><h3>${esc(c.current.name)}</h3><p>${esc(c.current.text)}</p><p><b>目标：${esc(c.current.goal)}</b>${c.current.reward ? ` · 完成奖励 ¥${c.current.reward} 万` : ""}</p><p>${c.current.stars.map((x) => `${x.ok ? "★" : "☆"} ${esc(x.text)}`).join("<br>")}</p></section>`
    : "<p>五章都完成了。剩下的时间，按你自己的想法经营。</p>";
  const tiers = ["common", "novel", "hard", "final"];
  const map = tiers
    .map((t) => {
      const rows = c.map.filter((r) => r.tier === t);
      return `<h4>${esc(c.tiers[t])} · ${rows.filter((r) => r.cured).length}/${rows.length}</h4><div class="disease-grid">${rows.map((r) => `<span class="disease ${r.cured ? "cured" : ""} ${t}" title="${esc(r.story || "")}">${esc(r.disease)}</span>`).join("")}</div>`;
    })
    .join("");
  const stories = c.map.filter((r) => r.cured && r.story);
  const bounties = c.bounties.length
    ? c.bounties.map((b) => `<p><b>${esc(b.disease)}</b> · 第 ${Math.floor(b.deadline / 48) + 1} 年前 · 奖励 ¥${b.reward} 万</p>`).join("")
    : '<p class="sub">暂时没有新的委托。大约每两年会有一封患者组织的来信。</p>';
  return `<div class="chapters-card">${close}${head}${cur}<h3>患者组织委托</h3>${bounties}<h3>疾病地图 · 已攻克 ${c.cured} 种</h3>${map}${stories.length ? `<details><summary>患者的话</summary>${stories.map((r) => `<p>「${esc(r.story)}」<small> · ${esc(r.disease)}</small></p>`).join("")}</details>` : ""}<button class="primary" data-close>继续</button></div>`;
}
function ratingBars(r) {
  return `<div class="rating-dims">${r.dimensions
    .map(
      (d) =>
        `<div class="rating-dim"><span>${esc(d.name)} <small>${d.weight}%</small></span><span class="track"><i style="width:${Math.max(0, Math.min(100, d.score))}%"></i></span><b>${Math.round(d.score)}</b></div>`,
    )
    .join("")}</div>`;
}
function ratingView() {
  const r = state.rating;
  const close = '<button class="modal-close" data-close aria-label="关闭弹窗">×</button>';
  if (r.final) {
    const f = r.final;
    const h = f.highlights;
    return `<div class="rating-card final">${close}<p>${f.early ? "提前停业" : `${r.term} 年任期结束`} · 第 ${f.week} 周</p>
      <div class="grade-big">${f.grade}</div><h2 id="modal-title">${esc(f.title)}</h2><p class="sub">总分 ${f.total}</p>
      <h3>结局：${esc(f.ending)}</h3><p>${esc(f.ending_text)}</p>${ratingBars(f)}
      <p>代表作：${h.product ? `<b>${esc(h.product)}</b>` : "还没有上市的药"} · 最得力的人：${h.hero ? `<b>${esc(h.hero)}</b>` : "—"}<br>上市 ${h.approved} 款（创新药 ${h.innovative} 款） · 累计帮助 ${num(Math.round(h.patients / 10000))} 万人次</p>
      <button class="primary" data-close>继续经营（评级已定格）</button></div>`;
  }
  const p = r.projected;
  return `<div class="rating-card">${close}<p>${r.term} 年任期 · 还剩 ${Math.ceil(r.weeks_left / 48)} 年</p>
    <div class="grade-big">${p.grade}</div><h2 id="modal-title">按当前进度预计：${esc(p.title)}</h2>
    <p class="sub">五项按已经过去的任期比例估计，任期结束那一周定格。现在的实际总分 ${r.current.total}（${r.current.grade}）。</p>
    ${ratingBars(p)}<p>已帮助 <b>${num(Math.round(r.patients / 10000))} 万</b>人次 · 如果现在结束，结局会是「${esc(p.ending)}」。</p>
    <details><summary>怎么算分</summary><p>惠及患者看产品覆盖的患者人次，难治疾病和创新药加权；科学突破看攻克的疾病难度和通过的独立复核；团队传承看自家培养的大师和传奇、带教和个人课题；经营稳健看现金增长、有没有出现负现金；行业声誉看大奖和提名。S ≥ 85，A ≥ 70，B ≥ 55，C ≥ 40。</p></details>
    <button class="primary" data-close>知道了</button></div>`;
}
function ceremonyView() {
  const last = state.honors.festivals.at(-1);
  if (!last) return "";
  const won = last.results.filter((r) => r.won);
  const nominated = last.results.filter((r) => r.nominated);
  const grand = state.honors.legacy_awards.filter((a) => a.year === last.year);
  const title = grand.length
    ? "这一年，留下了科学的名字"
    : won.length
      ? "轮到我们走上领奖台"
      : "把今年的积累，带到下一次舞台";
  const explanation =
    last.year === 1
      ? "街角实验室的第一年，还没有奖杯。明年起，所有成果都会自动参评。"
      : last.results.some((r) => r.category === "progress" && r.reason === "未满足年度成果要求")
        ? "今年没有通过新的研发阶段。推进一个阶段，就能参评研发进展奖。"
        : "本届尚未获奖。已有研究与培养成果会继续留在你的履历里。";
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
        .join("") +
        nominated.map((a) => `<p>提名：${esc(a.name)} · 成果分 ${a.your_score}（每年只颁一个大奖）</p>`).join("") ||
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
