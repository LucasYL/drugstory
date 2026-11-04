/* Deliberately separate demonstration state: no network requests or game saves. */
const people = {
  beaker: {
    name: "烧杯仔",
    role: "药物化学",
    level: "精英",
    ability: 52,
    story: "最后一管也要一样",
    wish: "“我想让新人也能复现自己的实验。”",
    status: "在质量室协助工艺验证",
    partner: "小药丸 · 制剂与工艺",
  },
  pill: {
    name: "小药丸",
    role: "制剂与工艺",
    level: "精英",
    ability: 54,
    story: "第一千粒药",
    wish: "“样品合格，还不等于一千粒都一样。”",
    status: "在质量室负责工艺验证",
    partner: "烧杯仔 · 药物化学",
  },
  sprout: {
    name: "豆芽博士",
    role: "生物与转化",
    level: "见习",
    ability: 43,
    story: "模型之外的病人",
    wish: "“培养皿里的发现，怎样才能回答患者的问题？”",
    status: "刚完成模型复核，可以参与共研",
    partner: "刻度喵 · 临床统计",
  },
  bubble: {
    name: "泡泡鼠",
    role: "安全与毒理",
    level: "见习",
    ability: 41,
    story: "没有被圈出的异常",
    wish: "“有一个小异常，没有被圈出来。”",
    status: "正在整理安全报告",
    partner: "刻度喵 · 临床统计",
  },
  ruler: {
    name: "刻度喵",
    role: "临床与统计",
    level: "见习",
    ability: 46,
    story: "曲线里的空白",
    wish: "“漂亮的曲线里，失访的人去了哪里？”",
    status: "临床执行已交给外部团队，可以开展个人课题",
    partner: "豆芽博士 · 生物与转化",
  },
};
let model,
  selected = { type: "room", id: "clinical" },
  choice = "verify";
const $ = (s) => document.querySelector(s);
function reset() {
  model = {
    week: 12,
    cash: 2860,
    trial: null,
    quest: null,
    remaining: 0,
    complete: false,
  };
  selected = { type: "room", id: "clinical" };
  choice = "verify";
  $("#scene-message").textContent = "临床团队等你做一个决定。";
  if ($("#celebration").open) $("#celebration").close();
  render();
}
function render() {
  $("#week").textContent = model.week;
  $("#cash").textContent = model.cash.toLocaleString("zh-CN");
  $("#ruler-status").textContent = model.complete
    ? "协作能力已解锁"
    : model.quest
      ? "共研中 · " + model.remaining + " 周"
      : "临床 · 有新心愿";
  $(".clinical span").textContent = model.trial ? "试验继续中" : "1 项待决定";
  $("#advance").disabled = !model.trial;
  $("#time-state").textContent = model.trial ? "已安排就绪" : "等你安排";
  document
    .querySelectorAll("[data-room],[data-person]")
    .forEach((b) =>
      b.classList.toggle(
        "selected",
        selected.type === "room"
          ? b.dataset.room === selected.id
          : b.dataset.person === selected.id,
      ),
    );
  $("#panel").innerHTML =
    selected.type === "person" ? person(selected.id) : room(selected.id);
}
function room(id) {
  if (id === "clinical")
    return `<p class="eyebrow">房间 / 临床办公室</p><h2>把后半程做扎实</h2><p class="intro">长效舒压 · 价值确认</p><span class="tag">试验进行到一半</span><span class="tag">外部团队执行</span><div class="card"><div class="metric"><span>原定剩余时间</span><b>12 周</b></div><div class="metric"><span>当前任务</span><b>完善患者使用记录</b></div><p>尚未查看最终疗效结果。可以维持计划，也可以投入随访，减少观察中的误差。</p></div>${model.trial ? `<div class="decision-note">已选择：${model.trial === "support" ? "补充患者随访 · +4 周 / ¥90 万" : "按原方案继续"}。继续经营，等待研究带回证据。</div><button class="choice" data-room="academy"><b>去看看伙伴的个人课题 →</b></button>` : `<button class="choice" data-trial="keep"><b>按原方案继续</b><small>保持当前成本、时长与观察精度。</small></button><button class="choice" data-trial="support"><b>补充患者随访</b><small>多 4 周、¥90 万，观察误差减少 18%。</small></button><p class="decision-note">更精确的证据可能支持，也可能否定候选。它不会增加药物本身的疗效。</p>`}<p class="small-note">设计意图：房间承载任务，右侧承载选择。只有需要决定时才打断推进。</p>`;
  if (id === "academy")
    return `<p class="eyebrow">房间 / 共研教室</p><h2>让经验传到别人手里</h2><p class="intro">普通伙伴，也有值得留下的方法。</p><div class="card"><span class="tag">新心愿</span><h3>刻度喵 · 曲线里的空白</h3><p>他想追踪失访数据的来处，邀请一位生物伙伴一起复核。</p><button data-person="ruler" class="primary">听听刻度喵怎么说 →</button></div><div class="card"><h3>导师与学徒</h3><p>以后在同一个房间里，能看见大师带教、伙伴讨论和课题完成留下的手记。</p></div><p class="small-note">设计意图：培养有可见的场所和成长纪念，不需要逐个点人物收经验。</p>`;
  if (id === "discovery")
    return `<p class="eyebrow">房间 / 发现实验室</p><h2>先问一个好问题</h2><p class="intro">靶点课题 · 模型复核已完成</p><div class="card"><h3>一条还不确定的线索</h3><p>这里查看候选、比较证据、安排专业伙伴。范围越宽，说明我们还知道得不够多。</p><div class="metric"><span>最新报告</span><b>已完成复核</b></div><div class="metric"><span>负责人</span><b>豆芽博士</b></div><button data-person="sprout">查看伙伴</button></div><p>人物会在工作台、共研教室和休息区之间活动。移动表现工作状态，不影响研发计时。</p><p class="small-note">当前画面与房间任务为设计示例；完整候选选择仍在玩法测试版。</p>`;
  return `<p class="eyebrow">房间 / 制剂与质量室</p><h2>从一管，到每一批</h2><p class="intro">稳压片 · 强化供货验证</p><span class="tag">烧杯仔 + 小药丸</span><div class="card"><h3>备选供应链</h3><p>多花时间验证第二来源。通过后免除周期性供货折减，成功的价值会留在产品上。</p><div class="metric"><span>研究进展</span><b>还需 6 周</b></div><progress value="6" max="12" aria-label="供货验证进度"></progress><button data-person="pill">查看小药丸</button></div><p>设备升级要有具体用途：容纳更多工作、解锁研究方法。装饰可以好看，不必样样增加分数。</p><p class="small-note">设计意图：药的差异能从工作内容看出来，而非只有四项数值不同。</p>`;
}
function person(id) {
  const h = people[id];
  return `<p class="eyebrow">伙伴 / ${h.role}</p><h2>${h.name}</h2><span class="tag">${h.level}</span><span class="tag">专业能力 ${h.ability}</span><p class="intro">${h.wish}</p><p>${h.status}</p><div class="card"><h3>个人课题 · ${h.story}</h3>${id === "ruler" ? questPanel() : `<p>需要的伙伴：${h.partner}</p><p>完成课题后，选择留下一种协作方法。每个角色有自己的问题和伙伴专业。</p><button data-person="ruler">体验刻度喵的完整课题 →</button>`}</div><p class="small-note">角色成长通过称号、徽章、动作与留下的手记表现；普通角色保持可辨认的外貌。</p>`;
}
function questPanel() {
  if (model.complete)
    return `<span class="tag">已完成 · 永久保留</span><p>${model.quest === "verify" ? "交叉复现：与生物伙伴合作临床研究，观察误差减少 8%。" : "联合交接：与生物伙伴共同承担相关阶段，阶段费用减少 5%。"}</p><p>这段经历也抵一项晋阶履历要求。</p>`;
  if (model.quest)
    return `<p>刻度喵与豆芽博士正在共同研究。</p><div class="metric"><span>剩余时间</span><b>${model.remaining} 周</b></div><progress value="${(model.quest === "verify" ? 12 : 8) - model.remaining}" max="${model.quest === "verify" ? 12 : 8}" aria-label="个人课题进度"></progress><p>推进时间后看看他们的收获。</p>`;
  return `<p>搭档：豆芽博士 · 生物与转化</p><button class="choice ${choice === "verify" ? "chosen" : ""}" data-choice="verify"><b>交叉复现</b><small>12 周 / ¥140 万 · 学会更准确地交叉核对。</small></button><button class="choice ${choice === "handoff" ? "chosen" : ""}" data-choice="handoff"><b>联合交接</b><small>8 周 / ¥80 万 · 让协作流程更省成本。</small></button><button class="primary" id="begin-quest">安排两位伙伴开始课题</button>`;
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.room) {
    selected = { type: "room", id: b.dataset.room };
    render();
  }
  if (b.dataset.person) {
    selected = { type: "person", id: b.dataset.person };
    render();
  }
  if (b.dataset.choice) {
    choice = b.dataset.choice;
    render();
  }
  if (b.dataset.trial) {
    model.trial = b.dataset.trial;
    if (model.trial === "support") model.cash -= 90;
    $("#scene-message").textContent =
      "研究安排已更新。现在可以看看伙伴，或推进时间。";
    render();
  }
  if (b.id === "begin-quest") {
    model.quest = choice;
    model.remaining = choice === "verify" ? 12 : 8;
    model.cash -= choice === "verify" ? 140 : 80;
    $("#scene-message").textContent = "刻度喵和豆芽博士开始了共研课题。";
    render();
  }
  if (b.id === "advance") {
    model.week += 4;
    if (model.quest && !model.complete) {
      model.remaining = Math.max(0, model.remaining - 4);
      if (!model.remaining) {
        model.complete = true;
        $("#award-detail").textContent =
          "完成个人课题「曲线里的空白」，永久解锁" +
          (model.quest === "verify" ? "交叉复现" : "联合交接") +
          "。伙伴配合时，方法才会发挥作用。";
        $("#celebration").showModal();
      }
    }
    $("#scene-message").textContent =
      "示例时间向前 4 周。点刻度喵，看看他的课题进展。";
    render();
  }
  if (b.id === "close-award") $("#celebration").close();
  if (b.id === "reset") reset();
});
reset();
