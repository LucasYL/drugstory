// v0.11 人物原型：按参数生成 SVG。半身立绘（卡片）、Q 版全身（场景）共用同一个头。
// 只用于讨论画风，不接入游戏。
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

  let uid = 0;

  // ---------- 头部 ----------
  const FACES = {
    round: "M56,88 C56,56 76,42 100,42 C124,42 144,56 144,88 C144,114 128,134 100,134 C72,134 56,114 56,88Z",
    long: "M58,86 C58,54 78,42 100,42 C122,42 142,54 142,86 C142,118 126,139 100,139 C74,139 58,118 58,86Z",
    square: "M56,86 C56,54 76,42 100,42 C124,42 144,54 144,86 C144,112 137,128 119,134 C110,137 90,137 81,134 C63,128 56,112 56,86Z",
  };

  function hairBack(p) {
    const c = p.hair_color, o = dark(c, 0.45);
    const st = `fill="${c}" stroke="${o}" stroke-width="2.5" stroke-linejoin="round"`;
    switch (p.hair) {
      case "long":
        return `<path ${st} d="M50,86 C46,46 72,30 100,30 C128,30 154,46 150,86 L154,168 C140,176 124,172 118,160 L118,120 L82,120 L82,160 C76,172 60,176 46,168Z"/>`;
      case "bob_sleek":
        return `<path ${st} d="M50,90 C44,48 72,30 100,30 C128,30 156,48 150,90 L152,136 C140,144 126,142 122,134 L78,134 C74,142 60,144 48,136Z"/>`;
      case "wavy":
        return `<path ${st} d="M50,88 C44,46 72,30 100,30 C128,30 156,46 150,88 C158,104 150,118 156,132 C150,146 136,146 128,138 L72,138 C64,146 50,146 44,132 C50,118 42,104 50,88Z"/>`;
      case "bun":
        return `<circle ${st} cx="100" cy="30" r="17"/><path fill="${light(c, 0.18)}" d="M92,22 C96,18 104,18 108,22" stroke="${light(c, 0.35)}" stroke-width="2" stroke-linecap="round"/>`;
      case "low_bun":
        return `<ellipse ${st} cx="142" cy="104" rx="15" ry="14"/>`;
      default:
        return "";
    }
  }

  function hairFront(p) {
    const c = p.hair_color, o = dark(c, 0.45), hl = light(c, 0.28);
    const st = `fill="${c}" stroke="${o}" stroke-width="2.5" stroke-linejoin="round"`;
    const shine = (d) => `<path d="${d}" fill="none" stroke="${hl}" stroke-width="3" stroke-linecap="round" opacity=".8"/>`;
    switch (p.hair) {
      case "spiky":
        return `<path ${st} d="M52,92 C48,70 54,56 60,50 L54,34 L70,42 L72,22 L86,36 L96,16 L106,34 L120,20 L122,40 L138,32 L136,50 C146,58 150,74 148,92 C142,76 134,68 124,64 L118,74 L110,62 L100,72 L92,62 L84,74 L78,64 C66,68 56,78 52,92Z"/>${shine("M80,40 L86,36 M104,32 L108,30")}`;
      case "bun":
        return `<path ${st} d="M54,92 C50,58 72,42 100,42 C128,42 150,58 146,92 C140,74 130,66 118,64 C110,72 92,74 80,70 C70,72 60,80 54,92Z"/>${shine("M76,52 C84,47 94,46 102,47")}`;
      case "long":
        return `<path ${st} d="M54,96 C50,58 72,40 100,40 C128,40 150,58 146,96 C144,80 140,72 136,68 L136,76 L124,70 L120,78 L110,70 L100,80 L90,70 L80,78 L76,70 L64,76 L64,68 C60,74 56,84 54,96Z"/>${shine("M78,50 C88,45 100,44 110,46")}`;
      case "short_side":
        return `<path ${st} d="M54,88 C50,52 74,38 102,38 C130,38 150,54 146,88 C144,72 136,62 126,58 C112,64 90,62 76,54 C66,62 58,72 54,88Z"/><path d="M76,54 C90,50 104,46 118,48" fill="none" stroke="${o}" stroke-width="2" stroke-linecap="round" opacity=".5"/>${shine("M86,44 C96,41 108,41 118,44")}`;
      case "wavy":
        return `<path ${st} d="M54,94 C48,56 72,38 100,38 C130,38 152,58 146,94 C142,80 136,70 128,66 C122,74 112,64 104,70 C96,62 86,70 78,64 C66,70 58,80 54,94Z"/>${shine("M80,48 C90,44 102,43 112,45")}`;
      case "bob_sleek":
        return `<path ${st} d="M52,98 C48,58 72,40 100,40 C128,40 152,58 148,98 C144,80 138,70 130,64 C116,66 100,60 92,54 C86,62 74,70 64,72 C58,80 54,88 52,98Z"/>${shine("M74,50 C86,44 100,43 112,46")}`;
      case "pixie":
        return `<path ${st} d="M54,90 C50,54 74,38 102,38 C130,38 150,54 146,88 C142,74 138,66 132,62 L128,72 C120,64 112,60 104,60 C92,64 80,74 66,76 C60,80 56,84 54,90Z"/>${shine("M84,44 C94,41 106,41 116,44")}`;
      case "slick_back":
        return `<path ${st} d="M56,82 C54,52 76,38 100,38 C124,38 146,52 144,82 C138,66 130,58 120,56 C106,54 92,54 80,56 C68,60 60,70 56,82Z"/><path d="M78,48 C94,44 110,44 124,48 M82,54 C96,50 110,50 122,53" fill="none" stroke="${o}" stroke-width="1.6" stroke-linecap="round" opacity=".45"/>`;
      case "low_bun":
        return `<path ${st} d="M54,90 C50,54 74,38 100,38 C126,38 150,54 146,92 C142,74 134,64 124,60 C112,56 100,56 92,58 C80,60 70,64 64,70 C58,76 55,82 54,90Z"/><path d="M72,62 C88,52 110,50 130,60" fill="none" stroke="${o}" stroke-width="1.6" stroke-linecap="round" opacity=".45"/>${shine("M82,46 C92,42 104,42 114,45")}`;
      default:
        return "";
    }
  }

  function streak(p) {
    if (!p.streak) return "";
    return `<path d="M86,44 C80,52 74,60 66,70" fill="none" stroke="${p.streak}" stroke-width="5" stroke-linecap="round"/>`;
  }

  function eyes(p) {
    const iris = p.eye || "#3b2a2a";
    const y = 94;
    const one = (x) =>
      `<ellipse cx="${x}" cy="${y}" rx="6.6" ry="8.4" fill="#2a2030"/>` +
      `<ellipse cx="${x}" cy="${y + 2}" rx="4.6" ry="5.6" fill="${iris}"/>` +
      `<circle cx="${x - 2.2}" cy="${y - 3}" r="2.6" fill="#fff"/>` +
      `<circle cx="${x + 2.4}" cy="${y + 3.4}" r="1.2" fill="#fff" opacity=".85"/>`;
    let lids = "";
    if (p.age === "senior") {
      lids = `<path d="M74,84 C78,82 84,82 88,84 M112,84 C116,82 122,82 126,84" fill="none" stroke="${dark(p.skin, 0.25)}" stroke-width="1.6" stroke-linecap="round"/>`;
    }
    if (p.eyes === "smile") {
      return `<path d="M74,96 C77,90 85,90 88,96 M112,96 C115,90 123,90 126,96" fill="none" stroke="#2a2030" stroke-width="3.2" stroke-linecap="round"/>` + lids;
    }
    if (p.eyes === "calm") {
      return (
        `<path d="M74,93 C78,97 85,97 88,93" fill="none" stroke="#2a2030" stroke-width="3" stroke-linecap="round"/>` +
        `<path d="M112,93 C116,97 123,97 126,93" fill="none" stroke="#2a2030" stroke-width="3" stroke-linecap="round"/>` +
        lids
      );
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
    };
    return `<path d="${shapes[p.brow_shape || "soft"]}" fill="none" stroke="${c}" stroke-width="${p.age === "senior" ? 3.4 : 3}" stroke-linecap="round"/>`;
  }

  function mouth(p) {
    const lip = "#9a4a4a";
    switch (p.mouth) {
      case "grin":
        return `<path d="M90,112 C94,120 106,120 110,112 Z" fill="#7a2f38" stroke="#5a2228" stroke-width="1.5" stroke-linejoin="round"/><path d="M93,113 L107,113" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>`;
      case "open":
        return `<ellipse cx="100" cy="115" rx="5" ry="4.5" fill="#7a2f38"/><path d="M96,117 C98,119 102,119 104,117" stroke="#e98a95" stroke-width="2" fill="none" stroke-linecap="round"/>`;
      case "flat":
        return `<path d="M93,115 L107,115" stroke="${lip}" stroke-width="2.6" stroke-linecap="round"/>`;
      case "smirk":
        return `<path d="M92,115 C98,118 104,116 109,111" fill="none" stroke="${lip}" stroke-width="2.6" stroke-linecap="round"/>`;
      default:
        return `<path d="M92,113 C96,118 104,118 108,113" fill="none" stroke="${lip}" stroke-width="2.6" stroke-linecap="round"/>`;
    }
  }

  function faceDetails(p) {
    let s = "";
    s += `<ellipse cx="73" cy="107" rx="7" ry="4" fill="#f08a8a" opacity="${p.age === "senior" ? 0.18 : 0.32}"/>`;
    s += `<ellipse cx="127" cy="107" rx="7" ry="4" fill="#f08a8a" opacity="${p.age === "senior" ? 0.18 : 0.32}"/>`;
    s += `<path d="M99,101 C98,104 99,106 101,106" fill="none" stroke="${dark(p.skin, 0.28)}" stroke-width="1.6" stroke-linecap="round"/>`;
    if (p.age === "senior") {
      s += `<path d="M68,100 C70,103 70,105 69,107 M132,100 C130,103 130,105 131,107" fill="none" stroke="${dark(p.skin, 0.2)}" stroke-width="1.4" stroke-linecap="round" opacity=".7"/>`;
      s += `<path d="M86,121 C90,123 94,123 96,122 M104,122 C106,123 110,123 114,121" fill="none" stroke="${dark(p.skin, 0.2)}" stroke-width="1.3" stroke-linecap="round" opacity=".6"/>`;
    }
    if (p.age === "mid") {
      s += `<path d="M66,99 C67,102 67,104 66,106" fill="none" stroke="${dark(p.skin, 0.18)}" stroke-width="1.2" stroke-linecap="round" opacity=".55"/>`;
    }
    return s;
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
    return "";
  }

  function headgear(p, layer) {
    let s = "";
    for (const a of p.accessories || []) {
      if (layer === "front" && a === "goggles") {
        s += `<path d="M58,64 C70,56 130,56 142,64" fill="none" stroke="#3a3f4a" stroke-width="7" stroke-linecap="round"/>`;
        s += `<g stroke="#3a3f4a" stroke-width="3"><rect x="70" y="52" width="26" height="18" rx="8" fill="#9fe0f0"/><rect x="104" y="52" width="26" height="18" rx="8" fill="#9fe0f0"/></g>`;
        s += `<path d="M75,57 L81,55 M109,57 L115,55" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>`;
      }
      if (layer === "front" && a === "bandana") {
        s += `<path d="M58,70 C70,52 130,52 142,70 C130,64 70,64 58,70Z" fill="#e98a8a" stroke="${dark("#e98a8a")}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<circle cx="80" cy="62" r="2" fill="#fff"/><circle cx="100" cy="58" r="2" fill="#fff"/><circle cx="120" cy="62" r="2" fill="#fff"/>`;
      }
      if (layer === "front" && a === "catear_headphones") {
        s += `<path d="M52,92 C48,46 72,28 100,28 C128,28 152,46 148,92" fill="none" stroke="#f2a6c4" stroke-width="7" stroke-linecap="round"/>`;
        s += `<path d="M62,46 L58,18 L82,34Z M138,46 L142,18 L118,34Z" fill="#f2a6c4" stroke="${dark("#f2a6c4")}" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<path d="M63,40 L62,28 L72,35Z M137,40 L138,28 L128,35Z" fill="#fff" opacity=".7"/>`;
        s += `<rect x="40" y="82" width="16" height="26" rx="7" fill="#f2a6c4" stroke="${dark("#f2a6c4")}" stroke-width="2.4"/><rect x="144" y="82" width="16" height="26" rx="7" fill="#f2a6c4" stroke="${dark("#f2a6c4")}" stroke-width="2.4"/>`;
      }
      if (layer === "front" && a === "earrings") {
        s += `<circle cx="55" cy="108" r="3.4" fill="#f2c14e" stroke="${dark("#f2c14e")}" stroke-width="1.2"/><circle cx="145" cy="108" r="3.4" fill="#f2c14e" stroke="${dark("#f2c14e")}" stroke-width="1.2"/>`;
      }
      if (layer === "front" && a === "pencil_ear") {
        s += `<path d="M140,76 L156,60" stroke="#f2c14e" stroke-width="5" stroke-linecap="round"/><path d="M155,61 L158,58" stroke="#3a3a3a" stroke-width="5" stroke-linecap="round"/>`;
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
    // 耳朵
    s += `<ellipse cx="57" cy="96" rx="8" ry="10" fill="${skin}" stroke="${so}" stroke-width="2.4"/><path d="M56,92 C59,94 59,99 56,101" fill="none" stroke="${so}" stroke-width="1.6" opacity=".6"/>`;
    s += `<ellipse cx="143" cy="96" rx="8" ry="10" fill="${skin}" stroke="${so}" stroke-width="2.4"/><path d="M144,92 C141,94 141,99 144,101" fill="none" stroke="${so}" stroke-width="1.6" opacity=".6"/>`;
    s += `<clipPath id="${id}"><path d="${FACE}"/></clipPath>`;
    s += `<path d="${FACE}" fill="${skin}" stroke="${so}" stroke-width="2.6"/>`;
    // 背光面
    s += `<g clip-path="url(#${id})"><path d="M128,40 C150,70 146,120 104,140 L160,140 L160,40Z" fill="${dark(skin, 0.12)}" opacity=".55"/></g>`;
    s += faceDetails(p);
    s += eyes(p);
    s += brows(p);
    s += mouth(p);
    if (p.beard) s += `<path d="M84,124 C90,134 110,134 116,124 C112,128 88,128 84,124Z" fill="${p.hair_color}" stroke="${dark(p.hair_color, 0.4)}" stroke-width="1.8"/>`;
    s += hairFront(p);
    s += streak(p);
    s += glasses(p);
    s += headgear(p, "front");
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
    // 脖子
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
      case "coat": {
        // 内衬 + 白大褂
        s += `<path d="M80,154 L120,154 L114,232 L86,232Z" fill="${p.inner || main}" stroke="${dark(p.inner || main, 0.4)}" stroke-width="2.4"/>`;
        s += `<path d="M30,232 C30,184 56,156 88,152 L98,232Z" ${st("#fbfcfd")}/>`;
        s += `<path d="M170,232 C170,184 144,156 112,152 L102,232Z" ${st("#fbfcfd")}/>`;
        s += `<path d="M88,152 L80,182 L94,178 L98,232 M112,152 L120,182 L106,178 L102,232" fill="none" stroke="#c9cfd8" stroke-width="2.4" stroke-linejoin="round"/>`;
        s += `<rect x="126" y="196" width="22" height="16" rx="3" fill="#fbfcfd" stroke="#c9cfd8" stroke-width="2"/>`;
        s += `<path d="M132,196 L132,188" stroke="${main}" stroke-width="3" stroke-linecap="round"/>`;
        s += `<circle cx="110" cy="206" r="2.4" fill="#c9cfd8"/><circle cx="110" cy="222" r="2.4" fill="#c9cfd8"/>`;
        // 专业色袖章
        s += `<path d="M44,196 L60,190 L62,204 L46,210Z" fill="${main}" stroke="${mo}" stroke-width="2"/>`;
        break;
      }
      case "blazer": {
        s += `<path d="M82,154 L118,154 L112,232 L88,232Z" fill="${p.inner || "#f6f2ea"}" stroke="#c9c3b8" stroke-width="2.2"/>`;
        s += `<path d="M30,232 C30,184 56,156 86,152 L98,232Z" ${st(main)}/>`;
        s += `<path d="M170,232 C170,184 144,156 114,152 L102,232Z" ${st(main)}/>`;
        s += `<path d="M86,152 L76,186 L92,180 L98,232 M114,152 L124,186 L108,180 L102,232" fill="${dark(main, 0.15)}" stroke="${mo}" stroke-width="2.2" stroke-linejoin="round"/>`;
        break;
      }
      case "cardigan": {
        s += `<path d="M82,154 L118,154 L112,232 L88,232Z" fill="${p.inner || "#f6f2ea"}" stroke="#c9c3b8" stroke-width="2.2"/>`;
        s += `<path d="M30,232 C30,184 56,156 86,152 L100,232Z" ${st(main)}/>`;
        s += `<path d="M170,232 C170,184 144,156 114,152 L100,232Z" ${st(main)}/>`;
        s += `<circle cx="95" cy="200" r="2.6" fill="${light(main, 0.5)}"/><circle cx="96" cy="216" r="2.6" fill="${light(main, 0.5)}"/>`;
        s += `<path d="M40,206 C46,204 52,204 58,206 M142,206 C148,204 154,204 160,206" stroke="${mo}" stroke-width="1.6" opacity=".5"/>`;
        break;
      }
      case "vest": {
        s += `<path d="${torso}" ${st(p.inner || "#f2efe8")}/>`;
        s += `<path d="M60,170 C70,158 84,154 90,154 L98,232 L58,232Z" ${st(main)}/>`;
        s += `<path d="M140,170 C130,158 116,154 110,154 L102,232 L142,232Z" ${st(main)}/>`;
        s += `<circle cx="92" cy="200" r="2.4" fill="${light(main, 0.4)}"/><circle cx="93" cy="216" r="2.4" fill="${light(main, 0.4)}"/>`;
        break;
      }
      case "turtleneck": {
        s += `<path d="${torso}" ${st(main)}/>`;
        s += `<path d="M84,142 L116,142 L118,162 C108,168 92,168 82,162Z" ${st(dark(main, 0.08))}/>`;
        s += `<path d="M86,148 L114,148 M85,154 L115,154" stroke="${mo}" stroke-width="1.6" opacity=".5"/>`;
        break;
      }
      default: {
        // work：专业色工作服
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
      if (a === "bow_tie") {
        s += `<path d="M100,160 L86,152 L86,168Z M100,160 L114,152 L114,168Z" fill="#c0392b" stroke="#7a2318" stroke-width="2" stroke-linejoin="round"/><circle cx="100" cy="160" r="3.6" fill="#a93226"/>`;
      }
      if (a === "pearls") {
        for (let i = 0; i < 9; i++) {
          const t = i / 8, x = 82 + 36 * t, y = 158 + 10 * Math.sin(Math.PI * t);
          s += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6" fill="#fbf7ef" stroke="#c9c1b0" stroke-width="1"/>`;
        }
      }
    }
    return s;
  }

  // ---------- 道具（半身，放在胸前） ----------
  function prop(p, x = 0, y = 0, k = 1) {
    const t = `transform="translate(${x} ${y}) scale(${k})"`;
    switch (p.prop) {
      case "flask":
        return `<g ${t}><path d="M-6,-22 L6,-22 L6,-8 L18,14 C20,20 16,24 10,24 L-10,24 C-16,24 -20,20 -18,14 L-6,-8Z" fill="#e9f7fb" stroke="#4a6070" stroke-width="2.4" stroke-linejoin="round"/><path d="M-14,8 L14,8 L18,14 C20,20 16,24 10,24 L-10,24 C-16,24 -20,20 -18,14Z" fill="#f29b4a"/><circle cx="-4" cy="14" r="2.4" fill="#fff" opacity=".8"/><circle cx="6" cy="2" r="1.8" fill="#f29b4a"/><path d="M-8,-22 L8,-22" stroke="#4a6070" stroke-width="3" stroke-linecap="round"/></g>`;
      case "tray":
        return `<g ${t}><rect x="-24" y="-4" width="48" height="10" rx="3" fill="#d9c3a0" stroke="#8a6f4a" stroke-width="2.2"/><g stroke="#7a8aa6" stroke-width="1.6"><ellipse cx="-12" cy="-8" rx="7" ry="4" fill="#fff"/><ellipse cx="2" cy="-8" rx="7" ry="4" fill="#cfe3ff"/><ellipse cx="15" cy="-8" rx="7" ry="4" fill="#fff"/></g><path d="M-14,-8 L-10,-8" stroke="#7a8aa6" stroke-width="1.4"/></g>`;
      case "tablet":
        return `<g ${t}><rect x="-16" y="-20" width="32" height="40" rx="5" fill="#2d3540" stroke="#1d232b" stroke-width="2"/><rect x="-12" y="-16" width="24" height="30" rx="2" fill="#dff3ef"/><path d="M-9,8 L-3,0 L2,4 L9,-8" fill="none" stroke="${PROF[p.profession].color}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M-9,-11 L3,-11" stroke="#9fb5b0" stroke-width="2"/></g>`;
      case "clipboard":
        return `<g ${t}><rect x="-16" y="-20" width="32" height="42" rx="3" fill="#c8a06a" stroke="#7d5f36" stroke-width="2.2"/><rect x="-12" y="-14" width="24" height="32" fill="#fff"/><rect x="-7" y="-23" width="14" height="7" rx="2" fill="#9aa3ad" stroke="#5f6770" stroke-width="1.6"/><path d="M-8,-6 L8,-6 M-8,0 L8,0 M-8,6 L4,6" stroke="#9aa3ad" stroke-width="2"/><path d="M-9,12 L-5,15 L1,8" fill="none" stroke="#3f9e66" stroke-width="2.4" stroke-linecap="round"/></g>`;
      case "sample_box":
        return `<g ${t}><rect x="-20" y="-12" width="40" height="24" rx="4" fill="#f4f1ea" stroke="#5f6770" stroke-width="2.2"/><g stroke="#5f6770" stroke-width="1.4">${[-12, -4, 4, 12].map((cx) => `<circle cx="${cx}" cy="0" r="4" fill="${cx > 0 ? "#9fd3d3" : "#cfe8e8"}"/>`).join("")}</g></g>`;
      case "red_pen":
        return `<g ${t}><rect x="-14" y="-18" width="30" height="38" rx="2" fill="#fff" stroke="#8a8f99" stroke-width="2" transform="rotate(-6)"/><path d="M-8,-8 L10,-10 M-8,-2 L6,-4 M-8,4 L10,2" stroke="#c9cdd4" stroke-width="2"/><path d="M-6,8 C-2,4 4,14 10,6" fill="none" stroke="#d23a3a" stroke-width="2.6" stroke-linecap="round"/><path d="M8,-26 L22,10" stroke="#d23a3a" stroke-width="5" stroke-linecap="round"/><path d="M21,8 L23,13" stroke="#3a3a3a" stroke-width="3" stroke-linecap="round"/></g>`;
      case "notebook":
        return `<g ${t}><rect x="-16" y="-20" width="32" height="40" rx="3" fill="#4f6b52" stroke="#2f4232" stroke-width="2.2"/><rect x="-10" y="-14" width="18" height="10" rx="1" fill="#f2efe6"/><path d="M-16,-12 L-20,-12 M-16,-4 L-20,-4 M-16,4 L-20,4 M-16,12 L-20,12" stroke="#2f4232" stroke-width="2.4" stroke-linecap="round"/></g>`;
      case "teacup":
        return `<g ${t}><path d="M-16,-6 L16,-6 C16,10 8,16 0,16 C-8,16 -16,10 -16,-6Z" fill="#fff" stroke="#6a7a70" stroke-width="2.2"/><path d="M16,-2 C24,-2 24,8 15,8" fill="none" stroke="#6a7a70" stroke-width="2.2"/><ellipse cx="0" cy="-6" rx="16" ry="3.4" fill="#c9b36a" stroke="#6a7a70" stroke-width="1.6"/><path d="M-4,-14 C-8,-18 0,-22 -4,-26 M4,-14 C0,-18 8,-22 4,-26" fill="none" stroke="#b9c4bf" stroke-width="2" stroke-linecap="round"/><path d="M-6,4 C-4,6 4,6 6,4" stroke="#4caf7a" stroke-width="2" fill="none"/></g>`;
      case "pencil":
        return `<g ${t}><rect x="-16" y="-18" width="32" height="38" rx="2" fill="#fff" stroke="#8a8f99" stroke-width="2"/><path d="M-12,-12 L12,-12 M-12,-6 L12,-6 M-12,0 L12,0 M-12,6 L12,6 M-12,12 L12,12 M-6,-16 L-6,18 M0,-16 L0,18 M6,-16 L6,18" stroke="#c9d6e6" stroke-width="1"/><path d="M-10,10 C-4,2 2,6 10,-8" fill="none" stroke="#5f7f9a" stroke-width="2.4" stroke-linecap="round"/></g>`;
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
    s += `<g>${outfit(p)}${neckwear(p)}</g>`;
    s += `<g>${head(p)}</g>`;
    if (p.prop) s += prop(p, 100, 206, 1.05) + hands(p, 100, 206);
    s += `</svg>`;
    return s;
  }

  // Q 版全身：头缩到 0.62，配小身体。120×176
  function chibi(p) {
    const main = p.outfit === "coat" ? "#fbfcfd" : p.outfit_color || PROF[p.profession].color;
    const inner = p.outfit === "coat" ? p.inner || PROF[p.profession].color : p.inner || light(main, 0.5);
    const mo = dark(main, 0.4);
    const pants = p.pants || "#3a4252";
    const skin = p.skin, so = dark(skin, 0.4);
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 176" role="img" aria-label="${p.name}">`;
    s += `<ellipse cx="60" cy="170" rx="30" ry="5" fill="#000" opacity=".12"/>`;
    // 腿
    s += `<rect x="47" y="136" width="11" height="28" rx="4" fill="${pants}" stroke="${dark(pants)}" stroke-width="2"/><rect x="62" y="136" width="11" height="28" rx="4" fill="${pants}" stroke="${dark(pants)}" stroke-width="2"/>`;
    s += `<path d="M44,164 L59,164 L59,170 L42,170 C41,167 42,165 44,164Z M61,164 L76,164 C78,165 79,167 78,170 L61,170Z" fill="#3a3030"/>`;
    // 手臂
    s += `<path d="M38,104 C30,116 30,128 34,134" fill="none" stroke="${mo}" stroke-width="12" stroke-linecap="round"/><path d="M38,104 C30,116 30,128 34,134" fill="none" stroke="${main}" stroke-width="8" stroke-linecap="round"/>`;
    s += `<path d="M82,104 C90,116 90,128 86,134" fill="none" stroke="${mo}" stroke-width="12" stroke-linecap="round"/><path d="M82,104 C90,116 90,128 86,134" fill="none" stroke="${main}" stroke-width="8" stroke-linecap="round"/>`;
    s += `<circle cx="34" cy="137" r="5" fill="${skin}" stroke="${so}" stroke-width="1.8"/><circle cx="86" cy="137" r="5" fill="${skin}" stroke="${so}" stroke-width="1.8"/>`;
    // 躯干
    s += `<path d="M40,104 C40,96 48,92 60,92 C72,92 80,96 80,104 L82,142 L38,142Z" fill="${main}" stroke="${mo}" stroke-width="2.2" stroke-linejoin="round"/>`;
    s += `<path d="M52,93 L60,110 L68,93Z" fill="${inner}" stroke="${dark(inner)}" stroke-width="1.6" stroke-linejoin="round"/>`;
    if (p.outfit === "coat") {
      s += `<path d="M60,110 L60,142" stroke="#c9cfd8" stroke-width="2"/><path d="M38,128 L82,128" stroke="${PROF[p.profession].color}" stroke-width="0" />`;
      s += `<path d="M40,116 L48,114 L48,120 L41,122Z" fill="${PROF[p.profession].color}"/>`;
    }
    if (p.outfit === "apron") s += `<path d="M48,104 L72,104 L76,142 L44,142Z" fill="${main}" stroke="${mo}" stroke-width="1.8"/>`;
    if (p.outfit === "vest") s += `<path d="M40,104 L54,96 L58,142 L38,142Z M80,104 L66,96 L62,142 L82,142Z" fill="${dark(main, 0.15)}" stroke="${mo}" stroke-width="1.6"/>`;
    // 头（缩放）
    s += `<g transform="translate(60 56) scale(0.62) translate(-100 -92)">${head(p)}</g>`;
    // 小道具
    if (p.prop) s += prop(p, 92, 132, 0.5);
    s += `</svg>`;
    return s;
  }

  global.ProtoFigures = { PROF, portrait, chibi };
})(window);
