/* 只点界面的自动玩家：像一个只认最显眼按钮的新手那样玩场景页，记下每一步看到的决定。
 *
 * 用来验收「只点推荐也能走下去」：决定卡的主按钮、候选「稳妥」、空研究台的「开始下一个项目」、
 * 新项目页的「开始筛选」，其余时间按「下一件事」。--guide 时，没有决定也会点左上角引导里
 * 带命令的按钮（v0.12 起引导按钮会直接执行建议的操作）。
 *
 * 只操作浏览器，不读存档、不读隐藏数值。请对独立端口、独立存档的新局使用，不要对玩家的存档跑。
 *
 *   uv run drugstory-web --port 8931 --seed 7 --save-path .artifacts/autoplay/s7.json &
 *   node scripts/ui-autoplay.cjs --port 8931 --weeks 480 --out .artifacts/autoplay --guide
 *
 * 输出：每种新出现的画面打印一行（带 * 的是第一次出现），最后一行是 JSON 汇总。
 */
const { chromium } = require("playwright");

function options(argv) {
  const o = { port: 8931, weeks: 480, steps: 2000, out: "", guide: false, width: 1440, height: 900 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i].replace(/^--/, "");
    if (k === "guide") o.guide = true;
    else if (k in o) o[k] = typeof o[k] === "number" ? Number(argv[++i]) : argv[++i];
  }
  return o;
}

(async () => {
  const o = options(process.argv.slice(2));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: o.width, height: o.height }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(`http://127.0.0.1:${o.port}/scene`);
  await page.waitForTimeout(1500);
  const seen = new Set();
  const counts = { quick: 0, pick: 0, start: 0, guide: 0, next: 0, modal: 0 };
  let shots = 0,
    week = 0,
    stuck = 0,
    lastWeek = -1;
  const shoot = async (tag) => {
    if (o.out && shots < 60) await page.screenshot({ path: `${o.out}/autoplay-${String(shots++).padStart(2, "0")}-w${week}-${tag}.png` });
  };
  const log = (kind, text) => {
    const key = kind + ":" + text.replace(/[\d,.–%-]+/g, "#").slice(0, 60);
    const fresh = !seen.has(key);
    seen.add(key);
    console.log(`[w${week}] ${kind}${fresh ? " *" : ""}: ${text.slice(0, fresh ? 400 : 100)}`);
    return fresh;
  };
  for (let i = 0; i < o.steps; i++) {
    const st = await page.evaluate(() => {
      const vis = (el) => el && el.offsetParent !== null;
      const modal = document.querySelector("#modal");
      const card = document.querySelector("aside.side .card.decide, aside.side article.card");
      const text = (el) => (el ? el.innerText.replace(/\s+/g, " ") : "");
      return {
        top: text(document.querySelector("#scene-metrics")),
        modal: modal?.open ? text(modal).slice(0, 600) : "",
        card: text(card).slice(0, 400),
        quick: [...document.querySelectorAll("aside.side button.quick:not([disabled])")].filter(vis).length,
        pick: [...document.querySelectorAll("aside.side button")].filter((b) => vis(b) && b.textContent.trim() === "选这个").length,
        empty: vis(document.querySelector("aside.side .empty button[data-np-open]")),
        guide: vis(document.querySelector("#scene-goal button[data-command]")) ? text(document.querySelector("#scene-goal")) : "",
        over: /停业/.test(text(document.querySelector("#scene-goal"))),
      };
    });
    week = Number((st.top.match(/第 (\d+) 周/) || [])[1] || 0);
    if (week >= o.weeks || st.over) break;
    stuck = week === lastWeek ? stuck + 1 : 0;
    lastWeek = week;
    if (stuck > 40) {
      log("STUCK", st.card || st.top);
      await shoot("stuck");
      break;
    }
    if (st.modal) {
      if (log("MODAL", st.modal)) await shoot("modal");
      const close = page.locator("#modal [data-close]").first();
      if (await close.count()) await close.click();
      else await page.keyboard.press("Escape");
      counts.modal++;
    } else if (st.quick) {
      if (log("QUICK", st.card)) await shoot("quick");
      await page.locator("aside.side button.quick:not([disabled])").first().click();
      counts.quick++;
    } else if (st.pick) {
      if (log("PICK", st.card)) await shoot("pick");
      const primary = page.locator('aside.side button.primary:has-text("选这个")');
      await ((await primary.count()) ? primary.first() : page.locator('aside.side button:has-text("选这个")').first()).click();
      counts.pick++;
    } else if (st.empty) {
      log("EMPTY", "研究台空着 → 开始下一个项目");
      await page.locator("aside.side .empty button[data-np-open]").click();
      counts.start++;
    } else if (o.guide && st.guide) {
      log("GUIDE", st.guide);
      await page.locator("#scene-goal button[data-command]").first().click();
      counts.guide++;
    } else {
      await page.getByRole("button", { name: "下一件事" }).first().click();
      counts.next++;
      await page.waitForTimeout(700);
    }
    await page.waitForTimeout(250);
  }
  const final = await page.evaluate(() => ({
    top: document.querySelector("#scene-metrics")?.innerText.replace(/\s+/g, " "),
    guide: document.querySelector("#scene-goal")?.innerText.replace(/\s+/g, " "),
    heroes: [...document.querySelectorAll("#scene-people [data-scene-hero] b")].map((b) => b.textContent),
  }));
  await shoot("final");
  console.log(JSON.stringify({ week, clicks: counts, ...final, errors }));
  await browser.close();
})();
