// v0.11 人物画法：按角色表里的 look.art 生成 SVG。半身立绘（头像、图鉴）和 Q 版全身（场景）
// 共用同一个头。生成的图片按角色缓存；还没加载好时，figures.js 先用旧画法顶上。
// 原型与讨论稿见 design/v11/characters.html。
(function (global) {
  const PROF = {
    bio: { name: "生物与转化", short: "生物", color: "#3f9e66" },
    chem: { name: "药化与分子工程", short: "药化", color: "#e57b2e" },
    tox: { name: "药代与毒理", short: "毒理", color: "#8462c4" },
    proc: { name: "制剂与工艺", short: "工艺", color: "#3a78d0" },
    clinical: { name: "临床与统计", short: "临床", color: "#df5868" },
  };

  function hex(c) {
    const n = parseInt(c.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function mix(a, b, t) {
    const x = hex(a), y = hex(b);
    return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
  }
  const dark = (c, t = 0.35) => mix(c, "#2a1f2a", t);
  const light = (c, t = 0.3) => mix(c, "#ffffff", t);
  const f1 = (n) => n.toFixed(1);

  let uid = 0;

  // 沿椭圆弧生成一圈小卷（用于卷发、短卷发）
  function scallop(cx, cy, rx, ry, a0, a1, n, bulge) {
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const a = ((a0 + ((a1 - a0) * i) / n) * Math.PI) / 180;
      pts.push([cx + rx * Math.cos(a), cy + ry * Math.sin(a)]);
    }
    let d = `M${f1(pts[0][0])},${f1(pts[0][1])}`;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
      const r = Math.hypot(x1 - x0, y1 - y0) / 2 * bulge;
      d += ` A${f1(r)},${f1(r)} 0 0 1 ${f1(x1)},${f1(y1)}`;
    }
    return d;
  }

  // ---------- 头部 ----------
  const FACES = {
    round: "M56,88 C56,56 76,42 100,42 C124,42 144,56 144,88 C144,114 128,134 100,134 C72,134 56,114 56,88Z",
    long: "M58,86 C58,54 78,42 100,42 C122,42 142,54 142,86 C142,118 126,139 100,139 C74,139 58,118 58,86Z",
    square: "M56,86 C56,54 76,42 100,42 C124,42 144,54 144,86 C144,112 137,128 119,134 C110,137 90,137 81,134 C63,128 56,112 56,86Z",
    heart: "M56,86 C56,54 76,42 100,42 C124,42 144,54 144,86 C144,110 126,130 100,136 C74,130 56,110 56,86Z",
  };

  function hairBack(p) {
    const c = p.hair_color, o = dark(c, 0.45);
    const st = `fill="${c}" stroke="${o}" stroke-width="2.5" stroke-linejoin="round"`;
    switch (p.hair) {
      case "long":
        return `<path ${st} d="M50,86 C46,46 72,30 100,30 C128,30 154,46 150,86 L154,168 C140,176 124,172 118,160 L118,120 L82,120 L82,160 C76,172 60,176 46,168Z"/>`;
      case "bob_sleek":
        return `<path ${st} d="M50,90 C44,48 72,30 100,30 C128,30 156,48 150,90 L152,136 C140,144 126,142 122,134 L78,134 C74,142 60,144 48,136Z"/>`;
      case "bob_bangs":
        return `<path ${st} d="M50,90 C44,46 72,30 100,30 C128,30 156,46 150,90 C152,108 152,122 146,132 C136,138 126,136 122,128 L78,128 C74,136 64,138 54,132 C48,122 48,108 50,90Z"/>`;
      case "wavy":
        return `<path ${st} d="M50,88 C44,46 72,30 100,30 C128,30 156,46 150,88 C158,104 150,118 156,132 C150,146 136,146 128,138 L72,138 C64,146 50,146 44,132 C50,118 42,104 50,88Z"/>`;
      case "bun":
        return `<circle ${st} cx="100" cy="30" r="17"/><path fill="none" d="M92,22 C96,18 104,18 108,22" stroke="${light(c, 0.35)}" stroke-width="2" stroke-linecap="round"/>`;
      case "low_bun":
        return `<ellipse ${st} cx="142" cy="104" rx="15" ry="14"/><path d="M134,98 C140,96 146,98 150,102" fill="none" stroke="${light(c, 0.3)}" stroke-width="2" stroke-linecap="round"/>`;
      case "ponytail_high":
        return `<path ${st} d="M120,40 C150,30 170,52 166,84 C164,104 170,118 160,132 C156,112 150,98 146,84 C142,66 132,54 120,48Z"/><path ${st} d="M114,34 C120,28 130,30 132,38 C128,42 118,42 114,34Z"/>`;
      case "manbun":
        return `<ellipse ${st} cx="104" cy="30" rx="14" ry="11"/>`;
      case "updo":
        return `<ellipse ${st} cx="128" cy="40" rx="18" ry="15"/><path d="M118,36 C124,30 134,30 140,36 M120,44 C126,40 134,40 140,44" fill="none" stroke="${o}" stroke-width="1.6" opacity=".45"/>`;
      case "curly": {
        const d = scallop(100, 96, 66, 64, 125, 415, 20, 1.15);
        return `<path ${st} d="${d} L120,158 L80,158Z"/>` +
          `<path fill="${c}" d="M48,130 C40,150 56,164 72,156 L128,156 C144,164 160,150 152,130Z"/>`;
      }
      case "braid":
        return `<path ${st} d="M52,92 C48,50 74,34 100,34 C126,34 152,50 148,92 L146,112 L54,112Z"/>`;
      case "fluffy":
        return `<path ${st} d="M50,92 C44,50 72,32 100,32 C128,32 156,50 150,92 L152,116 C146,120 140,116 138,110 L62,110 C60,116 54,120 48,116Z"/>` +
          `<path d="M48,116 L50,106 L55,114Z M152,116 L150,106 L145,114Z" fill="${p.hair_inner || c}"/>`;
      default:
        return "";
    }
  }

  function hairFront(p) {
    const c = p.hair_color, o = dark(c, 0.45), hl = light(c, 0.28);
    const st = `fill="${c}" stroke="${o}" stroke-width="2.5" stroke-linejoin="round"`;
    const shine = (d) => `<path d="${d}" fill="none" stroke="${hl}" stroke-width="3" stroke-linecap="round" opacity=".8"/>`;
    const strand = (d, w = 1.6) => `<path d="${d}" fill="none" stroke="${o}" stroke-width="${w}" stroke-linecap="round" opacity=".45"/>`;
    switch (p.hair) {
      case "spiky":
        return `<path ${st} d="M52,92 C48,70 54,56 60,50 L54,34 L70,42 L72,22 L86,36 L96,16 L106,34 L120,20 L122,40 L138,32 L136,50 C146,58 150,74 148,92 C142,76 134,68 124,64 L118,74 L110,62 L100,72 L92,62 L84,74 L78,64 C66,68 56,78 52,92Z"/>${shine("M80,40 L86,36 M104,32 L108,30")}`;
      case "bun":
        return `<path ${st} d="M54,92 C50,58 72,42 100,42 C128,42 150,58 146,92 C140,74 130,66 118,64 C110,72 92,74 80,70 C70,72 60,80 54,92Z"/>${shine("M76,52 C84,47 94,46 102,47")}`;
      case "long":
        return `<path ${st} d="M54,96 C50,58 72,40 100,40 C128,40 150,58 146,96 C144,80 140,72 136,68 L136,76 L124,70 L120,78 L110,70 L100,80 L90,70 L80,78 L76,70 L64,76 L64,68 C60,74 56,84 54,96Z"/>${shine("M78,50 C88,45 100,44 110,46")}`;
      case "short_side":
        return `<path ${st} d="M54,88 C50,52 74,38 102,38 C130,38 150,54 146,88 C144,72 136,62 126,58 C112,64 90,62 76,54 C66,62 58,72 54,88Z"/>${strand("M76,54 C90,50 104,46 118,48", 2)}${shine("M86,44 C96,41 108,41 118,44")}`;
      case "wavy":
        return `<path ${st} d="M54,94 C48,56 72,38 100,38 C130,38 152,58 146,94 C142,80 136,70 128,66 C122,74 112,64 104,70 C96,62 86,70 78,64 C66,70 58,80 54,94Z"/>${shine("M80,48 C90,44 102,43 112,45")}`;
      case "bob_sleek":
        return `<path ${st} d="M52,98 C48,58 72,40 100,40 C128,40 152,58 148,98 C144,80 138,70 130,64 C116,66 100,60 92,54 C86,62 74,70 64,72 C58,80 54,88 52,98Z"/>${shine("M74,50 C86,44 100,43 112,46")}`;
      case "bob_bangs":
        return `<path ${st} d="M52,100 C48,56 72,38 100,38 C128,38 152,56 148,100 C146,88 144,80 142,76 L58,76 C56,80 54,88 52,100Z"/>${strand("M78,76 L80,60 M100,76 L100,58 M122,76 L120,60")}${shine("M76,50 C88,44 102,43 114,46")}`;
      case "pixie":
        return `<path ${st} d="M54,90 C50,54 74,38 102,38 C130,38 150,54 146,88 C142,74 138,66 132,62 L128,72 C120,64 112,60 104,60 C92,64 80,74 66,76 C60,80 56,84 54,90Z"/>${shine("M84,44 C94,41 106,41 116,44")}`;
      case "slick_back":
        return `<path ${st} d="M56,82 C54,52 76,38 100,38 C124,38 146,52 144,82 C138,66 130,58 120,56 C106,54 92,54 80,56 C68,60 60,70 56,82Z"/>${strand("M78,48 C94,44 110,44 124,48 M82,54 C96,50 110,50 122,53")}`;
      case "low_bun":
        return `<path ${st} d="M54,90 C50,54 74,38 100,38 C126,38 150,54 146,92 C142,74 134,64 124,60 C112,56 100,56 92,58 C80,60 70,64 64,70 C58,76 55,82 54,90Z"/>${strand("M72,62 C88,52 110,50 130,60")}${shine("M82,46 C92,42 104,42 114,45")}`;
      case "ponytail_high":
        return `<path ${st} d="M54,92 C50,56 74,38 100,38 C128,38 150,56 146,90 C140,74 130,64 118,60 C104,58 88,64 76,74 C68,80 60,86 54,92Z"/>${strand("M76,72 C88,60 104,54 120,56")}${shine("M80,48 C90,44 102,43 112,45")}`;
      case "buzz":
        return `<path fill="${c}" stroke="${o}" stroke-width="2.2" d="M58,84 C56,52 76,40 100,40 C124,40 144,52 142,84 C138,66 126,57 100,56 C74,57 62,66 58,84Z"/>` +
          `<g fill="${o}" opacity=".35">${[[76, 50], [88, 46], [100, 45], [112, 46], [124, 50], [82, 54], [118, 54], [94, 50], [106, 50]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.2"/>`).join("")}</g>`;
      case "manbun":
        return `<path ${st} d="M56,84 C54,52 76,38 100,38 C124,38 146,52 144,84 C140,68 132,60 120,58 C106,56 92,58 82,60 C68,64 60,72 56,84Z"/>${strand("M74,58 C90,48 110,46 128,52 M80,64 C94,56 110,54 124,58")}${p.hair_tuft ? `<path d="M76,60 C68,70 68,80 74,88" fill="none" stroke="${c}" stroke-width="4" stroke-linecap="round"/>` : ""}`;
      case "coily": {
        const cap = scallop(100, 86, 47, 46, 186, 354, 14, 1.25);
        return `<path ${st} d="${cap} C140,72 128,62 100,62 C72,62 60,72 54,81Z"/>` +
          `<g fill="none" stroke="${hl}" stroke-width="1.6" stroke-linecap="round" opacity=".6">${[[74, 52], [88, 46], [104, 44], [118, 48], [130, 56], [80, 60], [96, 54], [112, 56]].map(([x, y]) => `<path d="M${x - 3},${y} a3,3 0 1 1 4,2"/>`).join("")}</g>`;
      }
      case "wavy_short":
        return `<path ${st} d="M56,86 C52,52 74,36 102,36 C130,36 148,52 144,86 C142,74 138,66 132,62 C126,68 118,60 110,64 C102,58 92,64 84,60 C74,64 64,72 56,86Z"/>${strand("M74,52 C80,46 88,46 92,50 C98,44 108,44 112,48 C118,44 126,46 130,52")}${shine("M86,42 C96,39 108,39 118,42")}`;
      case "updo":
        return `<path ${st} d="M54,92 C50,54 72,38 100,38 C128,38 150,54 146,92 C144,74 136,62 124,58 C108,66 86,72 66,68 C60,76 56,84 54,92Z"/>${strand("M66,68 C86,70 110,62 126,56 M74,56 C92,52 110,48 128,50")}${shine("M80,46 C92,42 104,41 116,43")}` +
          `<path ${st} d="M58,82 C56,92 58,102 62,110 C64,100 64,92 66,84Z"/>`;
      case "curly": {
        const cap = scallop(100, 88, 50, 50, 184, 356, 13, 1.3);
        return `<path ${st} d="${cap} C142,76 132,64 118,64 C106,72 88,74 74,68 C64,72 58,78 50,85Z"/>` +
          `<g fill="none" stroke="${hl}" stroke-width="1.8" stroke-linecap="round" opacity=".55">${[[70, 52], [86, 44], [104, 42], [122, 46], [136, 56], [62, 66], [140, 70]].map(([x, y]) => `<path d="M${x - 4},${y + 1} a4,4 0 1 1 5,3"/>`).join("")}</g>`;
      }
      case "braid": {
        let b = `<path ${st} d="M54,92 C50,54 74,38 100,38 C126,38 150,54 146,92 C142,70 128,58 100,56 C72,58 58,70 54,92Z"/>`;
        b += `<path d="M100,40 L100,56" stroke="${o}" stroke-width="2" stroke-linecap="round" opacity=".6"/>`;
        b += shine("M80,48 C88,44 94,43 98,43 M104,43 C110,43 116,44 122,48");
        // 发辫从右耳后垂到胸前
        const segs = [[142, 112], [143, 126], [142, 140], [139, 154], [135, 168], [131, 182]];
        for (const [x, y] of segs) b += `<ellipse cx="${x}" cy="${y}" rx="9" ry="8.5" fill="${c}" stroke="${o}" stroke-width="2.2"/><path d="M${x - 6},${y - 2} C${x - 2},${y + 3} ${x + 2},${y + 3} ${x + 6},${y - 2}" fill="none" stroke="${o}" stroke-width="1.4" opacity=".5"/>`;
        b += `<path d="M131,190 L127,200 L135,200Z" fill="${c}" stroke="${o}" stroke-width="2" stroke-linejoin="round"/>`;
        b += `<rect x="124" y="186" width="14" height="6" rx="3" fill="${p.tie_color || "#f2c14e"}" stroke="${dark(p.tie_color || "#f2c14e")}" stroke-width="1.4"/>`;
        return b;
      }
      case "fluffy": {
        let f = `<path ${st} d="M52,98 C46,56 72,36 100,36 C130,36 156,56 148,98 C146,86 142,78 138,74 L140,88 C134,80 128,74 124,72 L122,84 C116,76 110,72 104,72 L98,86 C94,78 88,74 82,74 L76,86 C74,80 70,76 66,76 L60,90 C58,84 56,80 56,78 C54,84 52,90 52,98Z"/>`;
        // 挑染的发梢
        f += `<g fill="${p.hair_inner || c}">${[[140, 88], [122, 84], [98, 86], [76, 86], [60, 90]].map(([x, y]) => `<path d="M${x - 4},${y - 7} L${x + 3},${y - 8} L${x},${y}Z"/>`).join("")}</g>`;
        f += strand("M70,58 C82,50 96,48 108,50 M112,50 C122,52 132,58 138,66");
        f += shine("M78,46 C88,42 100,41 110,43");
        // 呆毛
        f += `<path d="M104,38 C102,24 112,16 120,20 C114,20 108,26 110,36" fill="${c}" stroke="${o}" stroke-width="2.2" stroke-linejoin="round"/>`;
        return f;
      }
      default:
        return "";
    }
  }

  function streak(p) {
    let s = "";
    if (p.streak) s += `<path d="M86,44 C80,52 74,60 66,70" fill="none" stroke="${p.streak}" stroke-width="5" stroke-linecap="round"/>`;
    if (p.temples) {
      s += `<path d="M58,70 C57,78 57,86 59,94 L64,94 C63,86 63,78 64,70Z" fill="${p.temples}" opacity=".95"/>`;
      s += `<path d="M142,70 C143,78 143,86 141,94 L136,94 C137,86 137,78 136,70Z" fill="${p.temples}" opacity=".95"/>`;
    }
    return s;
  }

  function eyes(p) {
    const iris = p.eye || "#3b2a2a";
    const y = 94;
    const ry = p.eye_shape === "almond" ? 7 : 8.4;
    const sparkle = p.eyes === "sparkle";
    const one = (x) =>
      `<ellipse cx="${x}" cy="${y}" rx="6.6" ry="${ry}" fill="#2a2030"/>` +
      `<ellipse cx="${x}" cy="${y + 1.6}" rx="4.6" ry="${ry - 2.8}" fill="${iris}"/>` +
      (sparkle
        ? `<path d="M${x - 2.4},${y - 6.2} l1.1,2.4 2.4,1.1 -2.4,1.1 -1.1,2.4 -1.1,-2.4 -2.4,-1.1 2.4,-1.1Z" fill="#fff"/><circle cx="${x + 2.6}" cy="${y + 3.4}" r="1.4" fill="#fff"/>`
        : `<circle cx="${x - 2.2}" cy="${y - 3}" r="2.6" fill="#fff"/><circle cx="${x + 2.4}" cy="${y + 3.4}" r="1.2" fill="#fff" opacity=".85"/>`) +
      (p.eye_shape === "almond" ? `<path d="M${x - 8},${y - 5} C${x - 4},${y - 9} ${x + 4},${y - 9} ${x + 8},${y - 5}" fill="none" stroke="#2a2030" stroke-width="2.4" stroke-linecap="round"/>` : "") +
      (p.lashes ? `<path d="M${x + 6},${y - 6} L${x + 9},${y - 8}" stroke="#2a2030" stroke-width="2" stroke-linecap="round"/>` : "");
    let lids = "";
    if (p.age === "senior") {
      lids = `<path d="M74,84 C78,82 84,82 88,84 M112,84 C116,82 122,82 126,84" fill="none" stroke="${dark(p.skin, 0.25)}" stroke-width="1.6" stroke-linecap="round"/>`;
    }
    if (p.eyes === "smile") {
      return `<path d="M74,96 C77,90 85,90 88,96 M112,96 C115,90 123,90 126,96" fill="none" stroke="#2a2030" stroke-width="3.2" stroke-linecap="round"/>` + lids;
    }
    if (p.eyes === "calm") {
      return `<path d="M74,93 C78,97 85,97 88,93 M112,93 C116,97 123,97 126,93" fill="none" stroke="#2a2030" stroke-width="3" stroke-linecap="round"/>` + lids;
    }
    return one(81) + one(119) + lids;
  }

  function brows(p) {
    const c = dark(p.brow || p.hair_color, 0.15);
    const shapes = {
      soft: "M73,80 C77,77 84,77 88,79 M112,79 C116,77 123,77 127,80",
      firm: "M72,79 L88,77 M112,77 L128,79",
      arch: "M72,81 C76,75 84,75 89,78 M111,78 C116,75 124,75 128,81",
      worried: "M73,77 C78,79 84,80 88,79 M112,79 C116,80 122,79 127,77",
      sharp: "M72,80 L89,76 M111,76 L128,80",
      raised: "M72,80 L88,78 M112,76 C117,73 123,73 128,76",
    };
    return `<path d="${shapes[p.brow_shape || "soft"]}" fill="none" stroke="${c}" stroke-width="${p.thick_brows ? 4.2 : 3}" stroke-linecap="round"/>`;
  }

  function mouth(p) {
    const lip = p.lip || "#9a4a4a";
    switch (p.mouth) {
      case "grin":
        return `<path d="M90,112 C94,120 106,120 110,112 Z" fill="#7a2f38" stroke="#5a2228" stroke-width="1.5" stroke-linejoin="round"/><path d="M93,113 L107,113" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>`;
      case "open":
        return `<ellipse cx="100" cy="115" rx="5" ry="4.5" fill="#7a2f38"/><path d="M96,117 C98,119 102,119 104,117" stroke="#e98a95" stroke-width="2" fill="none" stroke-linecap="round"/>`;
      case "flat":
        return `<path d="M93,115 L107,115" stroke="${lip}" stroke-width="2.6" stroke-linecap="round"/>`;
      case "smirk":
        return `<path d="M92,115 C98,118 104,116 109,111" fill="none" stroke="${lip}" stroke-width="2.6" stroke-linecap="round"/>`;
      case "full":
        return `<path d="M91,114 C95,111 98,112 100,113 C102,112 105,111 109,114 C106,120 94,120 91,114Z" fill="${lip}" stroke="${dark(lip, 0.3)}" stroke-width="1.4" stroke-linejoin="round"/><path d="M92,114.5 L108,114.5" stroke="${dark(lip, 0.35)}" stroke-width="1.2"/>`;
      default:
        return `<path d="M92,113 C96,118 104,118 108,113" fill="none" stroke="${lip}" stroke-width="2.6" stroke-linecap="round"/>`;
    }
  }

  function nose(p) {
    const c = dark(p.skin, 0.3);
    if (p.nose === "bridge") return `<path d="M101,90 C101,96 99,101 97,104 C99,107 102,107 104,105" fill="none" stroke="${c}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>`;
    if (p.nose === "broad") return `<path d="M95,104 C96,108 104,108 105,104" fill="none" stroke="${c}" stroke-width="1.8" stroke-linecap="round"/><path d="M100,97 C100,100 99,102 98,103" fill="none" stroke="${c}" stroke-width="1.5" stroke-linecap="round" opacity=".7"/>`;
    return `<path d="M99,101 C98,104 99,106 101,106" fill="none" stroke="${c}" stroke-width="1.6" stroke-linecap="round"/>`;
  }

  function faceDetails(p) {
    let s = "";
    const blush = p.age === "senior" ? 0.18 : p.blush ?? 0.32;
    s += `<ellipse cx="73" cy="107" rx="7" ry="4" fill="#f08a8a" opacity="${blush}"/>`;
    s += `<ellipse cx="127" cy="107" rx="7" ry="4" fill="#f08a8a" opacity="${blush}"/>`;
    s += nose(p);
    if (p.freckles) {
      s += `<g fill="${dark(p.skin, 0.32)}" opacity=".55">${[[68, 102], [73, 104], [70, 107], [132, 102], [127, 104], [130, 107]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.1"/>`).join("")}</g>`;
    }
    if (p.age === "senior") {
      s += `<path d="M68,100 C70,103 70,105 69,107 M132,100 C130,103 130,105 131,107" fill="none" stroke="${dark(p.skin, 0.2)}" stroke-width="1.4" stroke-linecap="round" opacity=".7"/>`;
    }
    if (p.age === "mid") {
      s += `<path d="M66,99 C67,102 67,104 66,106" fill="none" stroke="${dark(p.skin, 0.18)}" stroke-width="1.2" stroke-linecap="round" opacity=".55"/>`;
    }
    return s;
  }

  function beard(p) {
    const c = p.beard_color || p.hair_color, o = dark(c, 0.4);
    if (p.beard === "goatee") return `<path d="M92,121 C94,130 106,130 108,121 C104,124 96,124 92,121Z" fill="${c}" stroke="${o}" stroke-width="1.6"/><path d="M90,110 C94,108 106,108 110,110" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round"/>`;
    if (p.beard === "full")
      return `<path d="M60,98 C60,124 80,142 100,142 C120,142 140,124 140,98 C136,112 128,120 116,122 C110,118 90,118 84,122 C72,120 64,112 60,98Z" fill="${c}" stroke="${o}" stroke-width="2" stroke-linejoin="round"/><path d="M88,110 C94,107 106,107 112,110 C106,112 94,112 88,110Z" fill="${c}" stroke="${o}" stroke-width="1.6"/>`;
    if (p.beard === "short")
      return `<path d="M62,104 C64,126 82,138 100,138 C118,138 136,126 138,104 C134,118 124,126 112,128 C106,124 94,124 88,128 C76,126 66,118 62,104Z" fill="${c}" opacity=".85"/>`;
    if (p.beard === "mustache") return `<path d="M88,110 C92,106 98,108 100,110 C102,108 108,106 112,110 C108,113 92,113 88,110Z" fill="${c}" stroke="${o}" stroke-width="1.4"/>`;
    return "";
  }

  function glasses(p) {
    const g = p.glasses;
    if (!g) return "";
    const c = p.glasses_color || "#2d2a33";
    if (g === "round")
      return `<g fill="#ffffff22" stroke="${c}" stroke-width="2.6"><circle cx="81" cy="95" r="11"/><circle cx="119" cy="95" r="11"/></g><path d="M92,94 C96,91 104,91 108,94 M70,93 L58,90 M130,93 L142,90" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round"/><path d="M75,89 L79,86 M113,89 L117,86" stroke="#fff" stroke-width="2" stroke-linecap="round" opacity=".8"/>`;
    if (g === "half")
      return `<path d="M69,96 L93,96 C93,104 89,107 81,107 C73,107 69,104 69,96Z M107,96 L131,96 C131,104 127,107 119,107 C111,107 107,104 107,96Z" fill="#ffffff22" stroke="${c}" stroke-width="2.4" stroke-linejoin="round"/><path d="M93,97 C96,95 104,95 107,97 M69,96 L58,92 M131,96 L142,92" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round"/>`;
    if (g === "square")
      return `<g fill="#ffffff22" stroke="${c}" stroke-width="2.6"><rect x="69" y="86" width="24" height="18" rx="5"/><rect x="107" y="86" width="24" height="18" rx="5"/></g><path d="M93,94 L107,94 M69,92 L58,89 M131,92 L142,89" stroke="${c}" stroke-width="2.4" stroke-linecap="round"/>`;
    if (g === "browline")
      return `<path d="M68,88 L94,88 M106,88 L132,88" stroke="${c}" stroke-width="4.2" stroke-linecap="round"/><g fill="#ffffff22" stroke="${c}" stroke-width="1.6" opacity=".9"><path d="M69,88 C69,100 73,105 81,105 C89,105 93,100 93,88"/><path d="M107,88 C107,100 111,105 119,105 C127,105 131,100 131,88"/></g><path d="M94,90 C97,88 103,88 106,90 M68,88 L58,86 M132,88 L142,86" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round"/>`;
    return "";
  }

  function headgear(p) {
    let s = "";
    for (const a of p.accessories || []) {
      if (a === "goggles") {
        s += `<path d="M58,64 C70,56 130,56 142,64" fill="none" stroke="#3a3f4a" stroke-width="7" stroke-linecap="round"/>`;
        s += `<g stroke="#3a3f4a" stroke-width="3"><rect x="70" y="52" width="26" height="18" rx="8" fill="#9fe0f0"/><rect x="104" y="52" width="26" height="18" rx="8" fill="#9fe0f0"/></g>`;
        s += `<path d="M75,57 L81,55 M109,57 L115,55" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>`;
      }
      if (a === "bandana") {
        s += `<path d="M58,70 C70,52 130,52 142,70 C130,64 70,64 58,70Z" fill="#e98a8a" stroke="${dark("#e98a8a")}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<circle cx="80" cy="62" r="2" fill="#fff"/><circle cx="100" cy="58" r="2" fill="#fff"/><circle cx="120" cy="62" r="2" fill="#fff"/>`;
      }
      if (a === "catear_headphones") {
        s += `<path d="M52,92 C48,46 72,28 100,28 C128,28 152,46 148,92" fill="none" stroke="#f2a6c4" stroke-width="7" stroke-linecap="round"/>`;
        s += `<path d="M62,46 L58,18 L82,34Z M138,46 L142,18 L118,34Z" fill="#f2a6c4" stroke="${dark("#f2a6c4")}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<path d="M63,40 L62,28 L72,35Z M137,40 L138,28 L128,35Z" fill="#fff" opacity=".7"/>`;
        s += `<rect x="40" y="82" width="16" height="26" rx="7" fill="#f2a6c4" stroke="${dark("#f2a6c4")}" stroke-width="2.4"/><rect x="144" y="82" width="16" height="26" rx="7" fill="#f2a6c4" stroke="${dark("#f2a6c4")}" stroke-width="2.4"/>`;
      }
      if (a === "earrings") {
        s += `<circle cx="55" cy="108" r="3.4" fill="#f2c14e" stroke="${dark("#f2c14e")}" stroke-width="1.2"/><circle cx="145" cy="108" r="3.4" fill="#f2c14e" stroke="${dark("#f2c14e")}" stroke-width="1.2"/>`;
      }
      if (a === "hoops") {
        s += `<circle cx="55" cy="114" r="7" fill="none" stroke="#e0b23e" stroke-width="2.6"/><circle cx="145" cy="114" r="7" fill="none" stroke="#e0b23e" stroke-width="2.6"/>`;
      }
      if (a === "nose_stud") s += `<circle cx="104" cy="104" r="1.6" fill="#f2c14e" stroke="${dark("#f2c14e")}" stroke-width=".6"/>`;
      if (a === "star_pin") {
        s += `<path d="M134,58 l3,6 6.6,1 -4.8,4.6 1.2,6.6 -6,-3.2 -6,3.2 1.2,-6.6 -4.8,-4.6 6.6,-1Z" fill="#ffd54a" stroke="#c99a1e" stroke-width="1.6" stroke-linejoin="round"/>`;
        s += `<path d="M126,72 L138,58" stroke="#5ec2b6" stroke-width="2.4" stroke-linecap="round"/>`;
      }
      if (a === "hard_hat") {
        s += `<path d="M50,72 C48,40 74,24 100,24 C126,24 152,40 150,72Z" fill="#f4f4f2" stroke="#9aa0a8" stroke-width="2.6" stroke-linejoin="round"/>`;
        s += `<path d="M42,72 L158,72 C158,78 154,80 150,80 L50,80 C46,80 42,78 42,72Z" fill="#f4f4f2" stroke="#9aa0a8" stroke-width="2.6" stroke-linejoin="round"/>`;
        s += `<path d="M100,26 L100,70 M84,30 C80,44 80,58 82,70 M116,30 C120,44 120,58 118,70" fill="none" stroke="#d3d7dc" stroke-width="3" stroke-linecap="round"/>`;
        s += `<rect x="88" y="48" width="24" height="12" rx="2" fill="#3a78d0"/>`;
      }
    }
    return s;
  }

  function head(p) {
    const skin = p.skin, so = dark(skin, 0.4);
    const id = "f" + uid++;
    const FACE = FACES[p.face || "round"];
    let s = "";
    s += hairBack(p);
    s += `<ellipse cx="57" cy="96" rx="8" ry="10" fill="${skin}" stroke="${so}" stroke-width="2.4"/><path d="M56,92 C59,94 59,99 56,101" fill="none" stroke="${so}" stroke-width="1.6" opacity=".6"/>`;
    s += `<ellipse cx="143" cy="96" rx="8" ry="10" fill="${skin}" stroke="${so}" stroke-width="2.4"/><path d="M144,92 C141,94 141,99 144,101" fill="none" stroke="${so}" stroke-width="1.6" opacity=".6"/>`;
    s += `<clipPath id="${id}"><path d="${FACE}"/></clipPath>`;
    s += `<path d="${FACE}" fill="${skin}" stroke="${so}" stroke-width="2.6"/>`;
    s += `<g clip-path="url(#${id})"><path d="M128,40 C150,70 146,120 104,140 L160,140 L160,40Z" fill="${dark(skin, 0.12)}" opacity=".55"/></g>`;
    s += faceDetails(p);
    s += beard(p);
    s += eyes(p);
    s += brows(p);
    s += mouth(p);
    s += hairFront(p);
    s += streak(p);
    s += glasses(p);
    s += headgear(p);
    return s;
  }

  // ---------- 半身：衣服 ----------
  function outfit(p) {
    const prof = PROF[p.profession].color;
    const main = p.outfit_color || prof;
    const mo = dark(main, 0.4);
    const torso = "M30,232 C30,184 56,156 100,152 C144,156 170,184 170,232Z";
    const st = (c) => `fill="${c}" stroke="${dark(c, 0.4)}" stroke-width="2.6" stroke-linejoin="round"`;
    let s = "";
    s += `<path d="M88,124 L88,154 C94,160 106,160 112,154 L112,124Z" fill="${p.skin}" stroke="${dark(p.skin, 0.4)}" stroke-width="2.4"/>`;
    s += `<path d="M88,136 C96,142 104,142 112,136 L112,128 L88,128Z" fill="${dark(p.skin, 0.18)}" opacity=".6"/>`;
    switch (p.outfit) {
      case "hoodie": {
        s += `<path d="M58,164 C66,146 134,146 142,164 C130,178 70,178 58,164Z" ${st(dark(main, 0.12))}/>`;
        s += `<path d="${torso}" ${st(main)}/>`;
        s += `<path d="M76,162 C86,174 114,174 124,162" fill="none" stroke="${mo}" stroke-width="2.4"/>`;
        s += `<path d="M90,170 L88,196 M110,170 L112,196" stroke="#fff" stroke-width="3" stroke-linecap="round"/><circle cx="88" cy="198" r="3" fill="#fff"/><circle cx="112" cy="198" r="3" fill="#fff"/>`;
        s += `<path d="M70,214 C86,206 114,206 130,214 L130,232 L70,232Z" fill="${dark(main, 0.1)}" stroke="${mo}" stroke-width="2"/>`;
        break;
      }
      case "apron": {
        s += `<path d="${torso}" ${st(p.inner || "#f4efe6")}/>`;
        s += `<path d="M78,158 L82,150 M122,158 L118,150" stroke="${mo}" stroke-width="4" stroke-linecap="round"/>`;
        s += `<path d="M74,160 L126,160 L134,232 L66,232Z" ${st(main)}/>`;
        s += `<rect x="88" y="190" width="24" height="18" rx="4" fill="${light(main, 0.25)}" stroke="${mo}" stroke-width="2"/>`;
        s += `<path d="M84,160 C90,166 110,166 116,160" fill="none" stroke="${mo}" stroke-width="2"/>`;
        break;
      }
      case "coat":
      case "coat_hoodie": {
        const inner = p.inner || main;
        if (p.outfit === "coat_hoodie") {
          s += `<path d="M62,166 C68,146 132,146 138,166 C126,178 74,178 62,166Z" ${st(dark(inner, 0.1))}/>`;
          s += `<path d="M74,156 L126,156 L120,232 L80,232Z" fill="${inner}" stroke="${dark(inner, 0.4)}" stroke-width="2.4"/>`;
          s += `<path d="M90,168 L89,190 M110,168 L111,190" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>`;
          s += `<path d="M92,206 l4,-8 4,8 4,-8 4,8" fill="none" stroke="${light(inner, 0.6)}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`;
        } else {
          s += `<path d="M80,154 L120,154 L114,232 L86,232Z" fill="${inner}" stroke="${dark(inner, 0.4)}" stroke-width="2.4"/>`;
        }
        const w = p.outfit === "coat_hoodie" ? 6 : 0;
        s += `<path d="M30,232 C30,184 56,156 ${88 - w},152 L${98 - w * 2},232Z" ${st("#fbfcfd")}/>`;
        s += `<path d="M170,232 C170,184 144,156 ${112 + w},152 L${102 + w * 2},232Z" ${st("#fbfcfd")}/>`;
        s += `<path d="M${88 - w},152 L${80 - w},182 L${94 - w * 2},178 L${98 - w * 2},232 M${112 + w},152 L${120 + w},182 L${106 + w * 2},178 L${102 + w * 2},232" fill="none" stroke="#c9cfd8" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<rect x="128" y="196" width="22" height="16" rx="3" fill="#fbfcfd" stroke="#c9cfd8" stroke-width="2"/>`;
        s += `<path d="M134,196 L134,188" stroke="${prof}" stroke-width="3" stroke-linecap="round"/>`;
        s += `<path d="M44,196 L60,190 L62,204 L46,210Z" fill="${prof}" stroke="${dark(prof, 0.4)}" stroke-width="2"/>`;
        break;
      }
      case "blazer": {
        s += `<path d="M82,154 L118,154 L112,232 L88,232Z" fill="${p.inner || "#f6f2ea"}" stroke="#c9c3b8" stroke-width="2.2"/>`;
        if (p.inner_style === "turtle") s += `<path d="M86,142 L114,142 L116,160 C108,164 92,164 84,160Z" fill="${p.inner}" stroke="${dark(p.inner, 0.4)}" stroke-width="2.2"/>`;
        s += `<path d="M30,232 C30,184 56,156 86,152 L98,232Z" ${st(main)}/>`;
        s += `<path d="M170,232 C170,184 144,156 114,152 L102,232Z" ${st(main)}/>`;
        s += `<path d="M86,152 L76,186 L92,180 L98,232 M114,152 L124,186 L108,180 L102,232" fill="${dark(main, 0.15)}" stroke="${mo}" stroke-width="2.2" stroke-linejoin="round"/>`;
        s += `<path d="M136,204 L156,202" stroke="${mo}" stroke-width="2" opacity=".6"/>`;
        break;
      }
      case "cardigan": {
        s += `<path d="M82,154 L118,154 L112,232 L88,232Z" fill="${p.inner || "#f6f2ea"}" stroke="#c9c3b8" stroke-width="2.2"/>`;
        s += `<path d="M30,232 C30,184 56,156 86,152 L100,232Z" ${st(main)}/>`;
        s += `<path d="M170,232 C170,184 144,156 114,152 L100,232Z" ${st(main)}/>`;
        s += `<circle cx="95" cy="200" r="2.6" fill="${light(main, 0.5)}"/><circle cx="96" cy="216" r="2.6" fill="${light(main, 0.5)}"/>`;
        break;
      }
      case "vest": {
        s += `<path d="${torso}" ${st(p.inner || "#f2efe8")}/>`;
        s += `<path d="M60,170 C70,158 84,154 90,154 L98,232 L58,232Z" ${st(main)}/>`;
        s += `<path d="M140,170 C130,158 116,154 110,154 L102,232 L142,232Z" ${st(main)}/>`;
        s += `<circle cx="92" cy="200" r="2.4" fill="${light(main, 0.4)}"/><circle cx="93" cy="216" r="2.4" fill="${light(main, 0.4)}"/>`;
        break;
      }
      case "safety_vest": {
        s += `<path d="${torso}" ${st(p.inner || "#e9eef4")}/>`;
        s += `<path d="M84,154 L100,170 L116,154" fill="none" stroke="${dark(p.inner || "#e9eef4", 0.4)}" stroke-width="2.2"/>`;
        s += `<path d="M58,170 C68,158 82,154 88,154 L96,232 L54,232Z" ${st(main)}/>`;
        s += `<path d="M142,170 C132,158 118,154 112,154 L104,232 L146,232Z" ${st(main)}/>`;
        s += `<path d="M56,196 L95,198 M56,212 L96,214 M144,196 L105,198 M144,212 L104,214" stroke="#f4f4f2" stroke-width="5"/>`;
        s += `<path d="M56,196 L95,198 M56,212 L96,214 M144,196 L105,198 M144,212 L104,214" stroke="#c9ccd1" stroke-width="1" opacity=".8"/>`;
        break;
      }
      case "turtleneck": {
        s += `<path d="${torso}" ${st(main)}/>`;
        s += `<path d="M84,142 L116,142 L118,162 C108,168 92,168 82,162Z" ${st(dark(main, 0.08))}/>`;
        s += `<path d="M86,148 L114,148 M85,154 L115,154" stroke="${mo}" stroke-width="1.6" opacity=".5"/>`;
        break;
      }
      case "shirt_tie": {
        s += `<path d="${torso}" ${st(p.inner || "#eaf2fb")}/>`;
        s += `<path d="M84,152 L100,166 L94,172 L80,160Z M116,152 L100,166 L106,172 L120,160Z" fill="${p.inner || "#eaf2fb"}" stroke="${dark(p.inner || "#eaf2fb", 0.4)}" stroke-width="2.2" stroke-linejoin="round"/>`;
        s += `<path d="M96,166 L104,166 L108,206 L100,216 L92,206Z" fill="${main}" stroke="${mo}" stroke-width="2.2" stroke-linejoin="round"/>`;
        s += `<path d="M54,232 C56,200 62,184 70,176 L72,232Z M146,232 C144,200 138,184 130,176 L128,232Z" fill="${dark(p.inner || "#eaf2fb", 0.06)}" opacity=".8"/>`;
        s += `<path d="M58,200 L64,200 M136,200 L142,200" stroke="${dark(p.inner || "#eaf2fb", 0.3)}" stroke-width="1.6"/>`;
        break;
      }
      case "polo": {
        s += `<path d="${torso}" ${st(main)}/>`;
        s += `<path d="M82,152 L100,164 L94,174 L78,160Z M118,152 L100,164 L106,174 L122,160Z" fill="${light(main, 0.12)}" stroke="${mo}" stroke-width="2.2" stroke-linejoin="round"/>`;
        s += `<path d="M100,164 L100,190" stroke="${mo}" stroke-width="2.2"/><circle cx="100" cy="176" r="1.8" fill="${light(main, 0.6)}"/><circle cx="100" cy="186" r="1.8" fill="${light(main, 0.6)}"/>`;
        break;
      }
      default: {
        s += `<path d="${torso}" ${st(main)}/>`;
        s += `<path d="M84,154 L100,176 L116,154" fill="${p.inner || "#f4f1ea"}" stroke="${mo}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<path d="M100,176 L100,232" stroke="${mo}" stroke-width="2.4"/>`;
        s += `<rect x="116" y="192" width="24" height="16" rx="3" fill="${light(main, 0.2)}" stroke="${mo}" stroke-width="2"/>`;
        break;
      }
    }
    return s;
  }

  function neckwear(p) {
    let s = "";
    for (const a of p.accessories || []) {
      if (a === "headphones_neck") {
        s += `<path d="M70,152 C70,170 130,170 130,152" fill="none" stroke="#2f3a44" stroke-width="5"/>`;
        s += `<rect x="60" y="146" width="16" height="20" rx="6" fill="#2f3a44"/><rect x="124" y="146" width="16" height="20" rx="6" fill="#2f3a44"/>`;
        s += `<rect x="63" y="150" width="6" height="10" rx="3" fill="#e57b2e"/><rect x="131" y="150" width="6" height="10" rx="3" fill="#e57b2e"/>`;
      }
      if (a === "stethoscope") {
        s += `<path d="M80,154 C72,186 84,200 96,196 M120,154 C128,186 116,200 104,196" fill="none" stroke="#3d566e" stroke-width="3.4" stroke-linecap="round"/>`;
        s += `<path d="M100,196 L100,212" stroke="#3d566e" stroke-width="3.4"/><circle cx="100" cy="216" r="6" fill="#c9d3dc" stroke="#3d566e" stroke-width="2.4"/>`;
      }
      if (a === "scarf") {
        const c = p.scarf || "#1f8a8a";
        s += `<path d="M78,146 C88,160 112,160 122,146 L126,158 C112,170 88,170 74,158Z" fill="${c}" stroke="${dark(c)}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<path d="M112,162 L120,200 L106,198 L102,164Z" fill="${c}" stroke="${dark(c)}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<path d="M108,192 L118,193" stroke="${light(c, 0.4)}" stroke-width="2"/>`;
      }
      if (a === "lanyard") {
        s += `<path d="M84,154 L98,196 M116,154 L102,196" stroke="${p.lanyard || "#f2c14e"}" stroke-width="3.4"/>`;
        s += `<rect x="88" y="194" width="24" height="30" rx="3" fill="#fff" stroke="#8a8f99" stroke-width="2"/><rect x="92" y="200" width="16" height="8" rx="1" fill="${PROF[p.profession].color}"/><path d="M92,214 L108,214 M92,219 L104,219" stroke="#b5bac3" stroke-width="2"/>`;
        s += `<rect x="112" y="200" width="14" height="18" rx="2" fill="#9cc0e0" stroke="#5f7f9a" stroke-width="1.6" transform="rotate(12 119 209)"/>`;
      }
      if (a === "badge") {
        s += `<rect x="124" y="186" width="26" height="14" rx="2" fill="#fff" stroke="#8a8f99" stroke-width="1.6"/><rect x="127" y="189" width="8" height="8" rx="1" fill="${PROF[p.profession].color}"/><path d="M138,191 L147,191 M138,196 L144,196" stroke="#b5bac3" stroke-width="1.6"/>`;
      }
      if (a === "bow_tie") {
        s += `<path d="M100,160 L86,152 L86,168Z M100,160 L114,152 L114,168Z" fill="#c0392b" stroke="#7a2318" stroke-width="2" stroke-linejoin="round"/><circle cx="100" cy="160" r="3.6" fill="#a93226"/>`;
      }
      if (a === "pearls") {
        for (let i = 0; i < 9; i++) {
          const t = i / 8, x = 82 + 36 * t, y = 158 + 10 * Math.sin(Math.PI * t);
          s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="2.6" fill="#fbf7ef" stroke="#c9c1b0" stroke-width="1"/>`;
        }
      }
      if (a === "pens") {
        s += `<path d="M122,194 L122,182 M127,194 L127,180 M132,194 L132,183" stroke-width="3.4" stroke-linecap="round" stroke="#d23a3a"/><path d="M127,194 L127,180" stroke="#3a78d0" stroke-width="3.4" stroke-linecap="round"/><path d="M132,194 L132,183" stroke="#3f9e66" stroke-width="3.4" stroke-linecap="round"/>`;
        s += `<rect x="116" y="192" width="24" height="16" rx="3" fill="${light(p.outfit_color || PROF[p.profession].color, 0.2)}" stroke="${dark(p.outfit_color || PROF[p.profession].color, 0.4)}" stroke-width="2"/>`;
      }
      if (a === "chalk_bag") {
        s += `<path d="M30,214 L170,214" stroke="#2f3a44" stroke-width="4"/><path d="M134,208 L154,208 L156,232 L132,232Z" fill="#f0b23a" stroke="#9a6c16" stroke-width="2.2" stroke-linejoin="round"/><path d="M134,208 C140,204 148,204 154,208" fill="#fff" stroke="#c9c1b0" stroke-width="1.6"/>`;
      }
      if (a === "laurel_pin") {
        // 学术专家的金色月桂徽章
        s += `<g transform="translate(66 190)"><circle r="7.5" fill="#f2c14e" stroke="#9a7416" stroke-width="1.8"/><path d="M-3.5,2 C-5,-1 -4,-4 -1,-5 M3.5,2 C5,-1 4,-4 1,-5" fill="none" stroke="#9a7416" stroke-width="1.4" stroke-linecap="round"/><circle r="1.6" fill="#fff8de"/></g>`;
      }
      if (a === "tie") {
        s += `<path d="M96,158 L104,158 L107,190 L100,198 L93,190Z" fill="${p.tie_color || "#2c3e66"}" stroke="${dark(p.tie_color || "#2c3e66", 0.4)}" stroke-width="2" stroke-linejoin="round"/>`;
      }
    }
    return s;
  }

  // ---------- 道具（半身，放在胸前） ----------
  function prop(p, x = 0, y = 0, k = 1) {
    const t = `transform="translate(${x} ${y}) scale(${k})"`;
    const pc = PROF[p.profession].color;
    switch (p.prop) {
      case "flask":
        return `<g ${t}><path d="M-6,-22 L6,-22 L6,-8 L18,14 C20,20 16,24 10,24 L-10,24 C-16,24 -20,20 -18,14 L-6,-8Z" fill="#e9f7fb" stroke="#4a6070" stroke-width="2.4" stroke-linejoin="round"/><path d="M-14,8 L14,8 L18,14 C20,20 16,24 10,24 L-10,24 C-16,24 -20,20 -18,14Z" fill="#f29b4a"/><circle cx="-4" cy="14" r="2.4" fill="#fff" opacity=".8"/><circle cx="6" cy="2" r="1.8" fill="#f29b4a"/><path d="M-8,-22 L8,-22" stroke="#4a6070" stroke-width="3" stroke-linecap="round"/></g>`;
      case "tray":
        return `<g ${t}><rect x="-24" y="-4" width="48" height="10" rx="3" fill="#d9c3a0" stroke="#8a6f4a" stroke-width="2.2"/><g stroke="#7a8aa6" stroke-width="1.6"><ellipse cx="-12" cy="-8" rx="7" ry="4" fill="#fff"/><ellipse cx="2" cy="-8" rx="7" ry="4" fill="#cfe3ff"/><ellipse cx="15" cy="-8" rx="7" ry="4" fill="#fff"/></g></g>`;
      case "tablet":
        return `<g ${t}><rect x="-16" y="-20" width="32" height="40" rx="5" fill="#2d3540" stroke="#1d232b" stroke-width="2"/><rect x="-12" y="-16" width="24" height="30" rx="2" fill="#dff3ef"/><path d="M-9,8 L-3,0 L2,4 L9,-8" fill="none" stroke="${pc}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M-9,-11 L3,-11" stroke="#9fb5b0" stroke-width="2"/></g>`;
      case "survival":
        return `<g ${t}><rect x="-18" y="-20" width="36" height="40" rx="5" fill="#2d3540" stroke="#1d232b" stroke-width="2"/><rect x="-14" y="-16" width="28" height="30" rx="2" fill="#fff4f2"/><path d="M-11,-10 L-4,-10 L-4,-4 L3,-4 L3,4 L10,4" fill="none" stroke="${pc}" stroke-width="2.4" stroke-linejoin="round"/><path d="M-11,-10 L-7,-10 L-7,0 L-1,0 L-1,10 L10,10" fill="none" stroke="#8a8f99" stroke-width="2" stroke-linejoin="round" stroke-dasharray="3 2"/></g>`;
      case "clipboard":
        return `<g ${t}><rect x="-16" y="-20" width="32" height="42" rx="3" fill="#c8a06a" stroke="#7d5f36" stroke-width="2.2"/><rect x="-12" y="-14" width="24" height="32" fill="#fff"/><rect x="-7" y="-23" width="14" height="7" rx="2" fill="#9aa3ad" stroke="#5f6770" stroke-width="1.6"/><path d="M-8,-6 L8,-6" stroke="#d23a3a" stroke-width="2"/><path d="M-8,0 L8,0" stroke="#3a78d0" stroke-width="2"/><path d="M-8,6 L4,6" stroke="#3f9e66" stroke-width="2"/><path d="M-9,12 L-5,15 L1,8" fill="none" stroke="#3f9e66" stroke-width="2.4" stroke-linecap="round"/></g>`;
      case "sample_box":
        return `<g ${t}><rect x="-20" y="-12" width="40" height="24" rx="4" fill="#f4f1ea" stroke="#5f6770" stroke-width="2.2"/><g stroke="#5f6770" stroke-width="1.4">${[-12, -4, 4, 12].map((cx) => `<circle cx="${cx}" cy="0" r="4" fill="${cx > 0 ? "#9fd3d3" : "#cfe8e8"}"/>`).join("")}</g></g>`;
      case "red_pen":
        return `<g ${t}><rect x="-14" y="-18" width="30" height="38" rx="2" fill="#fff" stroke="#8a8f99" stroke-width="2" transform="rotate(-6)"/><path d="M-8,-8 L10,-10 M-8,-2 L6,-4 M-8,4 L10,2" stroke="#c9cdd4" stroke-width="2"/><path d="M-6,8 C-2,4 4,14 10,6" fill="none" stroke="#d23a3a" stroke-width="2.6" stroke-linecap="round"/><path d="M8,-26 L22,10" stroke="#d23a3a" stroke-width="5" stroke-linecap="round"/><path d="M21,8 L23,13" stroke="#3a3a3a" stroke-width="3" stroke-linecap="round"/></g>`;
      case "notebook":
        return `<g ${t}><rect x="-16" y="-20" width="32" height="40" rx="3" fill="${p.book_color || "#4f6b52"}" stroke="${dark(p.book_color || "#4f6b52")}" stroke-width="2.2"/><rect x="-10" y="-14" width="18" height="10" rx="1" fill="#f2efe6"/><path d="M-16,-12 L-20,-12 M-16,-4 L-20,-4 M-16,4 L-20,4 M-16,12 L-20,12" stroke="${dark(p.book_color || "#4f6b52")}" stroke-width="2.4" stroke-linecap="round"/></g>`;
      case "journal":
        return `<g ${t}><rect x="-18" y="-22" width="36" height="44" rx="2" fill="${p.book_color || "#283a5e"}" stroke="${dark(p.book_color || "#283a5e")}" stroke-width="2.2"/><path d="M-12,-22 L-12,22" stroke="${dark(p.book_color || "#283a5e")}" stroke-width="2"/><path d="M-6,-12 L12,-12 M-6,-7 L8,-7" stroke="#f2c14e" stroke-width="2.4" stroke-linecap="round"/><g transform="translate(3 6)"><path d="M-6,4 C-8,0 -7,-4 -4,-6 M6,4 C8,0 7,-4 4,-6" fill="none" stroke="#f2c14e" stroke-width="1.8" stroke-linecap="round"/><circle r="2.2" fill="#f2c14e"/></g></g>`;
      case "teacup":
        return `<g ${t}><path d="M-16,-6 L16,-6 C16,10 8,16 0,16 C-8,16 -16,10 -16,-6Z" fill="#fff" stroke="#6a7a70" stroke-width="2.2"/><path d="M16,-2 C24,-2 24,8 15,8" fill="none" stroke="#6a7a70" stroke-width="2.2"/><ellipse cx="0" cy="-6" rx="16" ry="3.4" fill="#c9b36a" stroke="#6a7a70" stroke-width="1.6"/><path d="M-4,-14 C-8,-18 0,-22 -4,-26 M4,-14 C0,-18 8,-22 4,-26" fill="none" stroke="#b9c4bf" stroke-width="2" stroke-linecap="round"/><path d="M-6,4 C-4,6 4,6 6,4" stroke="#4caf7a" stroke-width="2" fill="none"/></g>`;
      case "pipette":
        return `<g ${t}><path d="M-4,-26 L4,-26 L6,-6 L2,14 L0,24 L-2,14 L-6,-6Z" fill="#e9eef4" stroke="#4a5568" stroke-width="2.2" stroke-linejoin="round"/><rect x="-7" y="-30" width="14" height="8" rx="3" fill="${pc}" stroke="${dark(pc)}" stroke-width="1.8"/><path d="M-1,10 L1,10 L0,22Z" fill="#f29b4a"/><circle cx="12" cy="18" r="3" fill="#f29b4a" opacity=".85"/></g>`;
      case "model":
        return `<g ${t}><g stroke="#5a5f6a" stroke-width="3" stroke-linecap="round"><path d="M-14,8 L0,-2 L14,8 M0,-2 L0,-18 M-14,8 L-14,20 M14,8 L22,0"/></g><circle cx="0" cy="-2" r="6" fill="#3a3f4a"/><circle cx="-14" cy="8" r="5.5" fill="#d23a3a"/><circle cx="14" cy="8" r="5.5" fill="#3a78d0"/><circle cx="0" cy="-18" r="5" fill="#f4f4f2" stroke="#9aa0a8" stroke-width="1.6"/><circle cx="-14" cy="20" r="5" fill="#f4f4f2" stroke="#9aa0a8" stroke-width="1.6"/><circle cx="22" cy="0" r="5" fill="${pc}"/><circle cx="-2" cy="-4" r="1.8" fill="#fff" opacity=".7"/></g>`;
      case "camera":
        return `<g ${t}><rect x="-22" y="-12" width="44" height="28" rx="5" fill="#2b2d33" stroke="#15161a" stroke-width="2"/><rect x="-14" y="-17" width="12" height="6" rx="2" fill="#2b2d33"/><circle cx="2" cy="2" r="10" fill="#4a4f5a" stroke="#15161a" stroke-width="2"/><circle cx="2" cy="2" r="5.5" fill="#7fb6d6"/><circle cx="0" cy="0" r="1.8" fill="#fff"/></g>`;
      case "laptop":
        return `<g ${t}><path d="M-22,-16 L22,-16 L22,10 L-22,10Z" fill="#cfd5dd" stroke="#6a727e" stroke-width="2.2" stroke-linejoin="round"/><rect x="-18" y="-12" width="36" height="18" rx="1" fill="#eaf2fb"/><path d="M-14,2 L-8,-4 L-2,0 L4,-8 L10,-6" fill="none" stroke="${pc}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="8" cy="-6" r="3.6" fill="none" stroke="#2c3e66" stroke-width="1.8"/><path d="M-26,10 L26,10 L22,16 L-22,16Z" fill="#aab2bd" stroke="#6a727e" stroke-width="2" stroke-linejoin="round"/></g>`;
      case "walkie":
        return `<g ${t}><rect x="-10" y="-16" width="20" height="34" rx="4" fill="#2f3a44" stroke="#151b20" stroke-width="2"/><path d="M6,-16 L6,-30" stroke="#151b20" stroke-width="3.4" stroke-linecap="round"/><rect x="-6" y="-11" width="12" height="9" rx="1" fill="#a7e3c7"/><g fill="#5a6672">${[2, 6, 10].map((yy) => `<rect x="-6" y="${yy}" width="12" height="2" rx="1"/>`).join("")}</g></g>`;
      case "thermos":
        return `<g ${t}><rect x="-10" y="-18" width="20" height="38" rx="6" fill="#56606a" stroke="#2c323a" stroke-width="2.2"/><rect x="-11" y="-24" width="22" height="9" rx="3" fill="#2c323a"/><rect x="-10" y="-2" width="20" height="6" fill="${pc}"/></g>`;
      case "holo":
        // 李天天：会发光的 DNA 全息板
        return `<g ${t}><ellipse cx="0" cy="-10" rx="22" ry="26" fill="#bff3ec" opacity=".75" stroke="#7fe3d5" stroke-width="1.6"/><rect x="-18" y="8" width="36" height="12" rx="4" fill="#2d3540" stroke="#1d232b" stroke-width="2"/><path d="M-14,10 L14,10" stroke="#7fe3d5" stroke-width="2.4" stroke-linecap="round"/><g stroke-width="2.4" stroke-linecap="round" fill="none"><path d="M-8,4 C8,-2 -8,-10 8,-16 C-8,-22 8,-28 -2,-32" stroke="${pc}"/><path d="M8,4 C-8,-2 8,-10 -8,-16 C8,-22 -8,-28 2,-32" stroke="#5ec2b6"/></g><g stroke="#fff" stroke-width="1.6" opacity=".9"><path d="M-4,1 L4,1 M-4,-13 L4,-13 M-4,-19 L4,-19"/></g><path d="M18,-24 l1.6,3.4 3.4,1.6 -3.4,1.6 -1.6,3.4 -1.6,-3.4 -3.4,-1.6 3.4,-1.6Z" fill="#ffd54a"/></g>`;
      default:
        return "";
    }
  }

  function hands(p, x, y) {
    const skin = p.skin, so = dark(skin, 0.4);
    return `<ellipse cx="${x - 20}" cy="${y + 6}" rx="8" ry="7" fill="${skin}" stroke="${so}" stroke-width="2.2"/><ellipse cx="${x + 20}" cy="${y + 6}" rx="8" ry="7" fill="${skin}" stroke="${so}" stroke-width="2.2"/>`;
  }

  // 半身立绘：200×232
  function portrait(p) {
    const ring = light(PROF[p.profession].color, 0.78);
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 232" role="img" aria-label="${p.name}">`;
    s += `<circle cx="100" cy="110" r="92" fill="${ring}"/>`;
    if (p.tier === 5) s += `<circle cx="100" cy="110" r="88" fill="none" stroke="#ffd54a" stroke-width="3" stroke-dasharray="2 7" stroke-linecap="round"/>`;
    s += `<g>${outfit(p)}${neckwear(p)}</g>`;
    s += `<g>${head(p)}</g>`;
    if (p.prop && p.prop_side) s += prop(p, 152, 176, 1.15);
    else if (p.prop) s += prop(p, 100, 206, 1.05) + hands(p, 100, 206);
    s += `</svg>`;
    return s;
  }

  // Q 版全身：头缩到 0.62，配小身体。120×176
  function chibi(p) {
    const coat = p.outfit === "coat" || p.outfit === "coat_hoodie";
    const main = coat ? "#fbfcfd" : p.outfit === "shirt_tie" ? p.inner || "#eaf2fb" : p.outfit === "safety_vest" ? p.outfit_color : p.outfit_color || PROF[p.profession].color;
    const inner = coat ? p.inner || PROF[p.profession].color : p.outfit === "shirt_tie" ? p.outfit_color : p.inner || light(main, 0.5);
    const mo = dark(main, 0.4);
    const pants = p.pants || "#3a4252";
    const skin = p.skin, so = dark(skin, 0.4);
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 176" role="img" aria-label="${p.name}">`;
    s += `<ellipse cx="60" cy="170" rx="30" ry="5" fill="#000" opacity=".12"/>`;
    s += `<rect x="47" y="136" width="11" height="28" rx="4" fill="${pants}" stroke="${dark(pants)}" stroke-width="2"/><rect x="62" y="136" width="11" height="28" rx="4" fill="${pants}" stroke="${dark(pants)}" stroke-width="2"/>`;
    s += `<path d="M44,164 L59,164 L59,170 L42,170 C41,167 42,165 44,164Z M61,164 L76,164 C78,165 79,167 78,170 L61,170Z" fill="${p.shoes || "#3a3030"}"/>`;
    const arm = (d) => `<path d="${d}" fill="none" stroke="${mo}" stroke-width="12" stroke-linecap="round"/><path d="${d}" fill="none" stroke="${main}" stroke-width="8" stroke-linecap="round"/>`;
    s += arm("M38,104 C30,116 30,128 34,134") + arm("M82,104 C90,116 90,128 86,134");
    s += `<circle cx="34" cy="137" r="5" fill="${skin}" stroke="${so}" stroke-width="1.8"/><circle cx="86" cy="137" r="5" fill="${skin}" stroke="${so}" stroke-width="1.8"/>`;
    s += `<path d="M40,104 C40,96 48,92 60,92 C72,92 80,96 80,104 L82,142 L38,142Z" fill="${main}" stroke="${mo}" stroke-width="2.2" stroke-linejoin="round"/>`;
    s += `<path d="M52,93 L60,110 L68,93Z" fill="${inner}" stroke="${dark(inner)}" stroke-width="1.6" stroke-linejoin="round"/>`;
    if (coat) {
      s += `<path d="M53,96 L67,96 L66,142 L54,142Z" fill="${inner}" stroke="${dark(inner)}" stroke-width="1.4"/>`;
      s += `<path d="M40,116 L48,114 L48,120 L41,122Z" fill="${PROF[p.profession].color}"/>`;
    }
    if (p.outfit === "shirt_tie") s += `<path d="M58,96 L62,96 L64,122 L60,127 L56,122Z" fill="${p.outfit_color}"/>`;
    if (p.outfit === "apron") s += `<path d="M48,104 L72,104 L76,142 L44,142Z" fill="${p.outfit_color}" stroke="${dark(p.outfit_color)}" stroke-width="1.8"/>`;
    if (p.outfit === "vest" || p.outfit === "safety_vest") s += `<path d="M40,104 L54,96 L58,142 L38,142Z M80,104 L66,96 L62,142 L82,142Z" fill="${p.outfit === "safety_vest" ? p.outfit_color : dark(main, 0.15)}" stroke="${mo}" stroke-width="1.6"/>`;
    if (p.outfit === "safety_vest") s += `<path d="M39,124 L57,125 M81,124 L63,125" stroke="#f4f4f2" stroke-width="3"/>`;
    if (p.outfit === "blazer" || p.outfit === "cardigan") s += `<path d="M53,96 L60,128 L67,96" fill="none" stroke="${mo}" stroke-width="1.6"/>`;
    if ((p.accessories || []).includes("laurel_pin")) s += `<circle cx="47" cy="110" r="3.4" fill="#f2c14e" stroke="#9a7416" stroke-width="1.2"/>`;
    s += `<g transform="translate(60 56) scale(0.62) translate(-100 -92)">${head(p)}</g>`;
    if (p.prop) s += prop(p, 92, 132, 0.5);
    s += `</svg>`;
    return s;
  }

  // ---------- 图片缓存：同一角色、同一种图只生成一次 ----------
  const cache = new Map();
  const RES = 3;
  function entry(art, kind) {
    const key = kind + ":" + JSON.stringify(art);
    let e = cache.get(key);
    if (!e) {
      const img = new Image();
      e = { img, ready: false, waiters: [] };
      cache.set(key, e);
      img.onload = () => {
        e.ready = true;
        for (const fn of e.waiters.splice(0)) fn();
      };
      // 写明像素尺寸（3 倍），否则浏览器按 300×150 处理只有 viewBox 的 SVG
      const [w, h] = kind === "portrait" ? [200, 232] : [120, 176];
      const svg = (kind === "portrait" ? portrait(art) : chibi(art)).replace(
        "<svg ",
        `<svg width="${w * RES}" height="${h * RES}" `,
      );
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    }
    return e;
  }
  function image(art, kind) {
    if (!art || typeof Image === "undefined") return null;
    const e = entry(art, kind);
    return e.ready ? e.img : null;
  }
  // 图片加载好以后要重画的地方（头像画布、图鉴）
  function whenReady(art, kind, fn) {
    if (!art || typeof Image === "undefined") return;
    const e = entry(art, kind);
    if (e.ready) fn();
    else e.waiters.push(fn);
  }

  global.DrugstoryArt = { PROF, portrait, chibi, image, whenReady, RES };
})(typeof window === "undefined" ? globalThis : window);
