/* 新药物语 · 一屏研究所：等距场景。
 * 这个文件只负责“画”和“点”：房间、家具、人物全部由代码按数据绘制，没有图片素材。
 * 规则在 sim.js（示例驱动）里；以后换成真实引擎，只需要提供同样的 world 数据和事件。 */
(() => {
  "use strict";

  const TW = 56;
  const TH = 28;
  const HW = TW / 2;
  const HH = TH / 2;
  const iso = (x, y, z = 0) => ({ x: (x - y) * HW, y: (x + y) * HH - z });
  const toGrid = (sx, sy) => ({ x: (sy / HH + sx / HW) / 2, y: (sy / HH - sx / HW) / 2 });

  /* ---------- 两种画风：同一套代码，只换比例和配色 ---------- */
  const STYLES = {
    calm: {
      person: { legs: 12, torso: 16, head: 5.9, shoulders: 12, outline: 0 },
      wallH: 66,
      partH: 12,
      glassH: 15,
      outline: null,
      c: {
        floorLab: "#e3e8ea",
        floorLabLine: "#d2d9dc",
        floorOffice: "#dcd3c5",
        floorOfficeLine: "#d0c6b6",
        corridor: "#d7dcdb",
        corridorLine: "#c9d0cf",
        stripe: "#86b5ab",
        lot: "#c6c9c8",
        lotLine: "#b0b5b4",
        wall: "#dde2e3",
        wallTop: "#aab4b8",
        window: "#c3d7de",
        windowFrame: "#a0b0b6",
        part: "#cdd4d6",
        partTop: "#b2bcbf",
        glass: "rgba(165, 200, 212, 0.30)",
        benchTop: "#f3f5f5",
        cabinet: "#5f7586",
        wood: "#b68a5f",
        metal: "#c8cfd3",
        white: "#eef1f2",
        screen: "#2b3d47",
        glow: "#83c8d8",
        glassware: "#a5d6e2",
        liquid: "#e2a35c",
        plant: "#5b9867",
        pot: "#d8d1c6",
        board: "#fbfcfc",
        boardFrame: "#97a3a8",
        shadow: "rgba(25, 40, 45, 0.16)",
        pants: "#3c4751",
        shoe: "#2a2f35",
        coat: "#f6f7f7",
        coatShade: "#dbe1e3",
        helper: "#9fadb3",
        cro: "#6f7d86",
      },
    },
    bright: {
      person: { legs: 7, torso: 11, head: 8.2, shoulders: 12.5, outline: 1.3 },
      wallH: 58,
      partH: 11,
      glassH: 12,
      outline: "#2f3d44",
      c: {
        floorLab: "#e6f2ee",
        floorLabLine: "#d3e7e0",
        floorOffice: "#f7e7c8",
        floorOfficeLine: "#efd9b0",
        corridor: "#eef0e4",
        corridorLine: "#e0e3d2",
        stripe: "#f2b950",
        lot: "#d9d6cc",
        lotLine: "#c4c0b4",
        wall: "#fbf6ec",
        wallTop: "#e7a86a",
        window: "#bfe3f0",
        windowFrame: "#7fb7c9",
        part: "#f4ead8",
        partTop: "#e7a86a",
        glass: "rgba(180, 225, 240, 0.35)",
        benchTop: "#ffffff",
        cabinet: "#3fa39a",
        wood: "#e2a765",
        metal: "#d9e2e6",
        white: "#fbfdfd",
        screen: "#27434f",
        glow: "#8fe0f0",
        glassware: "#9fe6f2",
        liquid: "#ff9f6e",
        plant: "#5fbf6e",
        pot: "#f0c39a",
        board: "#ffffff",
        boardFrame: "#7a8c92",
        shadow: "rgba(40, 50, 60, 0.18)",
        pants: "#4a5a8a",
        shoe: "#33384a",
        coat: "#ffffff",
        coatShade: "#e3eef2",
        helper: "#b8c7cf",
        cro: "#7d8fa0",
      },
    },
  };

  /* ---------- 布局：全部是数据，扩建就是加一块格子 ---------- */
  const GRID_W = 16;
  const GRID_H = 12;
  const ROOMS = [
    { id: "lab", name: "化学与制剂实验室", x0: 0, y0: 0, x1: 8, y1: 5, floor: "lab", label: [4, 0] },
    { id: "qc", name: "质量与毒理室", x0: 8, y0: 0, x1: 16, y1: 5, floor: "lab", label: [12, 0] },
    { id: "clinic", name: "临床与数据办公室", x0: 0, y0: 7, x1: 8, y1: 12, floor: "office", label: [0, 9.5] },
    { id: "bio", name: "生物实验室", x0: 8, y0: 7, x1: 16, y1: 12, floor: "lab", label: [12, 9.5], buildable: true },
  ];
  const CORRIDOR = { x0: 0, y0: 5, x1: 16, y1: 7 };
  // 室内矮墙：axis "y" 表示墙在 y = at 这条线上、沿 x 方向延伸；doors 是留空的格子
  const PARTITIONS = [
    { axis: "y", at: 5, from: 0, to: 16, doors: [3, 12] },
    { axis: "y", at: 7, from: 0, to: 16, doors: [3, 12] },
    { axis: "x", at: 8, from: 0, to: 5, doors: [] },
    { axis: "x", at: 8, from: 7, to: 12, doors: [] },
  ];
  // 家具：station 是人站的位置；helpers 是团队成员站的位置（成员越多，画面里人越多）
  const FURNITURE = [
    { id: "hood", room: "lab", type: "hood", x: 1, y: 0, w: 2, d: 1, h: 54,
      station: { x: 2, y: 1.45, face: "up", roles: ["chem"], helpers: [[1.25, 1.75], [2.8, 1.8]] } },
    { id: "lab-bench", room: "lab", type: "bench", x: 4, y: 0, w: 3, d: 1, h: 20,
      station: { x: 5.5, y: 1.45, face: "up", roles: ["proc", "chem"], helpers: [[4.6, 1.75], [6.45, 1.75]] } },
    { id: "lab-island", room: "lab", type: "island", x: 4, y: 3, w: 3, d: 1, h: 20,
      station: { x: 5.5, y: 4.45, face: "up", roles: ["proc"], helpers: [[4.6, 4.55], [6.5, 4.5]] } },
    { id: "lab-shelf", room: "lab", type: "shelf", x: 0, y: 2, w: 1, d: 2, h: 40 },
    { id: "lab-plant", room: "lab", type: "plant", x: 7, y: 0, w: 1, d: 1, h: 26 },
    { id: "lab-granulator", room: "lab", type: "instrument", x: 7, y: 3, w: 1, d: 1, h: 28, minLevel: 2 },
    { id: "lab-coater", room: "lab", type: "chamber", x: 0, y: 4, w: 1, d: 1, h: 40, minLevel: 3 },

    { id: "qc-hplc", room: "qc", type: "bench", x: 9, y: 0, w: 3, d: 1, h: 20, items: "instrument",
      station: { x: 10.5, y: 1.45, face: "up", roles: ["tox", "proc"], helpers: [[9.6, 1.75], [11.45, 1.75]] } },
    { id: "qc-chamber", room: "qc", type: "chamber", x: 13, y: 0, w: 1, d: 1, h: 48,
      station: { x: 13.5, y: 1.45, face: "up", roles: ["proc", "tox"], helpers: [[14.4, 1.7]] } },
    { id: "qc-desk", room: "qc", type: "desk", x: 14, y: 4, w: 2, d: 1, h: 14, monitor: "back",
      station: { x: 15, y: 3.5, face: "down", roles: ["tox", "proc", "clinical"], helpers: [] } },
    { id: "qc-ms", room: "qc", type: "instrument", x: 8, y: 2, w: 1, d: 1, h: 30, minLevel: 2 },
    { id: "qc-ms2", room: "qc", type: "instrument", x: 8, y: 3, w: 1, d: 1, h: 24, minLevel: 3 },

    { id: "cl-desk1", room: "clinic", type: "desk", x: 1, y: 7, w: 2, d: 1, h: 14, monitor: "front",
      station: { x: 2, y: 8.45, face: "up", roles: ["clinical", "bio"], helpers: [[1.1, 8.7]] } },
    { id: "cl-desk2", room: "clinic", type: "desk", x: 5, y: 7, w: 2, d: 1, h: 14, monitor: "front",
      station: { x: 6, y: 8.45, face: "up", roles: ["clinical", "bio", "tox"], helpers: [[6.95, 8.7]] } },
    { id: "cl-table", room: "clinic", type: "table", x: 3, y: 10, w: 2, d: 1, h: 13,
      station: { x: 4, y: 11.45, face: "up", roles: ["clinical", "bio", "tox"], helpers: [[3.1, 11.5]] } },
    { id: "cl-cro", room: "clinic", type: "cro", x: 6, y: 10, w: 2, d: 1, h: 14 },
    { id: "cl-plant", room: "clinic", type: "plant", x: 7, y: 7, w: 1, d: 1, h: 26 },

    { id: "bio-bench", room: "bio", type: "bench", x: 9, y: 7, w: 3, d: 1, h: 20, items: "microscope",
      station: { x: 10.5, y: 8.45, face: "up", roles: ["bio"], helpers: [[9.6, 8.75], [11.45, 8.75]] } },
    { id: "bio-hood", room: "bio", type: "hood", x: 13, y: 7, w: 2, d: 1, h: 50,
      station: { x: 14, y: 8.45, face: "up", roles: ["bio", "tox"], helpers: [[14.9, 8.75]] } },
    { id: "bio-incubator", room: "bio", type: "chamber", x: 15, y: 9, w: 1, d: 1, h: 36 },
    { id: "bio-island", room: "bio", type: "island", x: 10, y: 10, w: 3, d: 1, h: 20, minLevel: 2 },

    { id: "coffee", room: "corridor", type: "coffee", x: 0, y: 5, w: 1, d: 1, h: 30 },
    { id: "cooler", room: "corridor", type: "cooler", x: 0, y: 6, w: 1, d: 1, h: 34 },
  ];
  const IDLE_SPOTS = [
    { x: 1.35, y: 5.55, face: "left" },
    { x: 1.4, y: 6.55, face: "left" },
    { x: 6.5, y: 5.9, face: "down" },
    { x: 9.6, y: 6.1, face: "down" },
    { x: 14.6, y: 6.0, face: "down" },
  ];
  const BOARDS = {
    clinic: { plane: "x", at: 0, from: 11.3, to: 8.5, zTop: 52, zBottom: 18 },
    qc: { plane: "y", at: 0, from: 14.15, to: 15.85, zTop: 54, zBottom: 22 },
  };
  const CRO_SPOT = { x: 6.95, y: 9.55, face: "down" };
  // 引擎事件里的 room 字段 → 场景里的房间（v0.7 的房间名还不统一，这张表负责收口）
  const ENGINE_ROOMS = {
    room_lab: "lab", room_chem: "lab", room_proc: "lab", room_tox: "qc",
    room_clinical: "clinic", room_bio: "bio", room_academy: "clinic",
  };

  /* ---------- 小工具 ---------- */
  function hexToRgb(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function shade(hex, k) {
    if (!hex.startsWith("#")) return hex;
    const [r, g, b] = hexToRgb(hex);
    const f = (v) => Math.round(k < 0 ? v * (1 + k) : v + (255 - v) * k);
    return `rgb(${f(r)}, ${f(g)}, ${f(b)})`;
  }
  function poly(ctx, pts, fill, stroke, lw = 1) {
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.closePath();
    if (fill) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = lw;
      ctx.stroke();
    }
  }
  function rrect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
  // 等距方块：顶面最亮，朝 +y 的面次之，朝 +x 的面最暗
  function box(ctx, S, x, y, w, d, h, color, z0 = 0, topColor = null) {
    const A = iso(x, y, z0 + h);
    const B = iso(x + w, y, z0 + h);
    const C = iso(x + w, y + d, z0 + h);
    const D = iso(x, y + d, z0 + h);
    const Bb = iso(x + w, y, z0);
    const Cb = iso(x + w, y + d, z0);
    const Db = iso(x, y + d, z0);
    const o = S.outline;
    poly(ctx, [D, C, Cb, Db], shade(color, -0.12), o, 1);
    poly(ctx, [B, C, Cb, Bb], shade(color, -0.26), o, 1);
    poly(ctx, [A, B, C, D], topColor || shade(color, 0.08), o, 1);
  }
  function quadOnWall(plane, at, a0, a1, z0, z1) {
    if (plane === "x") return [iso(at, a0, z1), iso(at, a1, z1), iso(at, a1, z0), iso(at, a0, z0)];
    return [iso(a0, at, z1), iso(a1, at, z1), iso(a1, at, z0), iso(a0, at, z0)];
  }

  /* ---------- 寻路：16×12 的格子，矮墙挡路，门可以过 ---------- */
  function buildBlocked(world) {
    const cells = new Set();
    for (const f of FURNITURE) {
      if (!furnitureVisible(f, world)) continue;
      for (let i = 0; i < f.w; i++) for (let j = 0; j < f.d; j++) cells.add(`${f.x + i},${f.y + j}`);
    }
    const bio = world.rooms?.bio;
    if (!bio || !bio.built) {
      for (let x = 8; x < 16; x++) for (let y = 7; y < 12; y++) cells.add(`${x},${y}`);
    }
    return cells;
  }
  function edgeBlocked(ax, ay, bx, by) {
    for (const p of PARTITIONS) {
      if (p.axis === "y" && ax === bx && Math.max(ay, by) === p.at && Math.min(ay, by) === p.at - 1) {
        if (ax >= p.from && ax < p.to && !p.doors.includes(ax)) return true;
      }
      if (p.axis === "x" && ay === by && Math.max(ax, bx) === p.at && Math.min(ax, bx) === p.at - 1) {
        if (ay >= p.from && ay < p.to && !p.doors.includes(ay)) return true;
      }
    }
    return false;
  }
  function findPath(blocked, from, to) {
    const start = `${Math.floor(from.x)},${Math.floor(from.y)}`;
    const goal = `${Math.floor(to.x)},${Math.floor(to.y)}`;
    if (start === goal) return [];
    const prev = new Map([[start, null]]);
    const queue = [start];
    while (queue.length) {
      const cur = queue.shift();
      if (cur === goal) break;
      const [cx, cy] = cur.split(",").map(Number);
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = cx + dx;
        const ny = cy + dy;
        const key = `${nx},${ny}`;
        if (nx < 0 || ny < 0 || nx >= GRID_W || ny >= GRID_H || prev.has(key)) continue;
        if (blocked.has(key) && key !== goal) continue;
        if (edgeBlocked(cx, cy, nx, ny)) continue;
        prev.set(key, cur);
        queue.push(key);
      }
    }
    if (!prev.has(goal)) return null;
    const path = [];
    for (let k = goal; k && k !== start; k = prev.get(k)) {
      const [x, y] = k.split(",").map(Number);
      path.unshift({ x: x + 0.5, y: y + 0.5 });
    }
    path.pop();
    return path;
  }
  function furnitureVisible(f, world) {
    if (f.room === "bio" && !world.rooms?.bio?.built) return false;
    const level = world.rooms?.[f.room]?.level ?? 1;
    return !f.minLevel || level >= f.minLevel;
  }

  /* ---------- 人物：几块形状 + 数据里的发型、配饰、颜色 ---------- */
  function drawPerson(ctx, S, look, o) {
    const P = S.person;
    const c = S.c;
    const ol = S.outline;
    const walk = o.walking ? Math.sin(o.phase * 2) : 0;
    const bob = o.walking ? Math.abs(walk) * 1.1 : Math.sin(o.phase * 0.7) * 0.35;
    const work = o.working ? Math.sin(o.phase * 3.2) : 0;
    ctx.save();
    ctx.translate(o.x, o.y);
    ctx.globalAlpha = o.alpha ?? 1;
    // 影子
    ctx.fillStyle = c.shadow;
    ctx.beginPath();
    ctx.ellipse(0, 0, 8, 3.6, 0, 0, Math.PI * 2);
    ctx.fill();
    if (o.ring) {
      ctx.strokeStyle = o.ring;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(0, 0, 11, 5, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.translate(0, -(o.jump || 0) - bob);
    if (o.flip) ctx.scale(-1, 1);
    const L = P.legs;
    const T = P.torso;
    const R = P.head;
    const SW = P.shoulders;
    const line = (fill) => {
      ctx.fillStyle = fill;
      ctx.fill();
      if (ol) {
        ctx.strokeStyle = ol;
        ctx.lineWidth = P.outline;
        ctx.stroke();
      }
    };
    // 腿
    rrect(ctx, -3.6 + walk * 1.6, -L, 3.1, L, 1.2);
    line(look.pants || c.pants);
    rrect(ctx, 0.5 - walk * 1.6, -L, 3.1, L, 1.2);
    line(look.pants || c.pants);
    ctx.fillStyle = c.shoe;
    ctx.fillRect(-4.2 + walk * 1.6, -1.6, 4, 1.8);
    ctx.fillRect(0.2 - walk * 1.6, -1.6, 4, 1.8);
    const top = -L - T;
    // 长发在身体后面
    if (look.hair === "long" && !o.away) {
      rrect(ctx, -R - 0.6, top - R * 1.2, R * 2 + 1.2, R * 2.6, R * 0.8);
      line(look.hairColor);
    }
    // 后臂
    rrect(ctx, SW / 2 - 2.2, top + 2, 2.8, T - 3, 1.3);
    line(look.coat === false ? look.shirt : c.coatShade);
    // 身体
    rrect(ctx, -SW / 2, top, SW, T + 1.5, 3);
    line(look.coat === false ? look.shirt : c.coat);
    if (look.coat !== false && !o.away) {
      ctx.fillStyle = look.shirt;
      ctx.beginPath();
      ctx.moveTo(-2.6, top + 0.5);
      ctx.lineTo(2.6, top + 0.5);
      ctx.lineTo(0, top + 5.5);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = c.coatShade;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(0, top + 5.5);
      ctx.lineTo(0, top + T);
      ctx.stroke();
    }
    if (look.coat === false) {
      ctx.fillStyle = shade(look.shirt, -0.15);
      ctx.fillRect(-SW / 2 + 1, top + T - 2, SW - 2, 2);
    }
    // 前臂：工作时抬起来
    ctx.save();
    ctx.translate(-SW / 2 + 1.2, top + 2.5);
    ctx.rotate(o.working ? -0.75 + work * 0.18 : walk * 0.35);
    rrect(ctx, -1.4, 0, 2.8, T - 3, 1.3);
    line(look.coat === false ? shade(look.shirt, 0.05) : c.coat);
    ctx.fillStyle = look.skin;
    ctx.beginPath();
    ctx.arc(0, T - 3, 1.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
    if (look.holds === "tablet" && !o.away) {
      rrect(ctx, -SW / 2 - 1, top + T * 0.45, 6, 7.5, 1);
      line("#3a4a55");
      ctx.fillStyle = c.glow;
      ctx.fillRect(-SW / 2, top + T * 0.45 + 1.2, 4, 5);
    }
    // 头
    const hy = top - R + 1.2;
    ctx.beginPath();
    ctx.arc(0, hy, R, 0, Math.PI * 2);
    line(look.skin);
    drawHair(ctx, S, look, hy, R, o.away);
    if (!o.away) {
      ctx.fillStyle = "#2a2a2a";
      const ey = hy + R * 0.12;
      ctx.beginPath();
      ctx.arc(-R * 0.38, ey, R * 0.11 + 0.25, 0, Math.PI * 2);
      ctx.arc(R * 0.38, ey, R * 0.11 + 0.25, 0, Math.PI * 2);
      ctx.fill();
      if (look.glasses) {
        ctx.strokeStyle = "#3b3b3b";
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.arc(-R * 0.4, ey, R * 0.28, 0, Math.PI * 2);
        ctx.moveTo(R * 0.4 + R * 0.28, ey);
        ctx.arc(R * 0.4, ey, R * 0.28, 0, Math.PI * 2);
        ctx.moveTo(-R * 0.12, ey);
        ctx.lineTo(R * 0.12, ey);
        ctx.stroke();
      }
    }
    drawAccessory(ctx, S, look, hy, R);
    ctx.restore();
  }
  function drawHair(ctx, S, look, hy, R, away) {
    ctx.fillStyle = look.hairColor;
    if (away) {
      ctx.beginPath();
      ctx.arc(0, hy, R + 0.4, 0, Math.PI * 2);
      ctx.fill();
    } else {
      ctx.beginPath();
      ctx.arc(0, hy, R + 0.4, Math.PI * 1.02, Math.PI * 1.98);
      ctx.quadraticCurveTo(R * 0.6, hy - R * 0.25, 0, hy - R * 0.35);
      ctx.quadraticCurveTo(-R * 0.7, hy - R * 0.2, -R - 0.4, hy - R * 0.05);
      ctx.fill();
      if (look.hair === "bob" || look.hair === "long") {
        rrect(ctx, -R - 0.6, hy - R * 0.4, R * 0.55, R * 1.35, R * 0.25);
        ctx.fill();
        rrect(ctx, R * 0.45, hy - R * 0.4, R * 0.55, R * 1.35, R * 0.25);
        ctx.fill();
      }
    }
    if (look.hair === "bun") {
      ctx.beginPath();
      ctx.arc(R * 0.15, hy - R * 1.05, R * 0.5, 0, Math.PI * 2);
      ctx.fill();
    }
    if (look.hair === "spiky") {
      ctx.beginPath();
      for (let i = -2; i <= 2; i++) {
        ctx.moveTo(i * R * 0.35 - R * 0.2, hy - R * 0.75);
        ctx.lineTo(i * R * 0.35, hy - R * 1.35);
        ctx.lineTo(i * R * 0.35 + R * 0.2, hy - R * 0.75);
      }
      ctx.fill();
    }
  }
  function drawAccessory(ctx, S, look, hy, R) {
    const a = look.accessory;
    if (a === "catears") {
      ctx.fillStyle = look.accent;
      for (const s of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(s * R * 0.25, hy - R * 0.85);
        ctx.lineTo(s * R * 0.75, hy - R * 1.55);
        ctx.lineTo(s * R * 0.95, hy - R * 0.62);
        ctx.closePath();
        ctx.fill();
      }
    } else if (a === "sprout") {
      ctx.strokeStyle = "#4f8f4a";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, hy - R);
      ctx.lineTo(0.5, hy - R * 1.6);
      ctx.stroke();
      ctx.fillStyle = "#6fbf5a";
      ctx.beginPath();
      ctx.ellipse(-1.6, hy - R * 1.65, 2, 1, -0.4, 0, Math.PI * 2);
      ctx.ellipse(2.4, hy - R * 1.7, 2, 1, 0.4, 0, Math.PI * 2);
      ctx.fill();
    } else if (a === "goggles") {
      ctx.fillStyle = look.accent;
      ctx.fillRect(-R, hy - R * 0.6, R * 2, R * 0.32);
      ctx.fillStyle = "rgba(190, 230, 240, 0.9)";
      ctx.fillRect(-R * 0.75, hy - R * 0.68, R * 0.55, R * 0.45);
      ctx.fillRect(R * 0.2, hy - R * 0.68, R * 0.55, R * 0.45);
    } else if (a === "clips") {
      ctx.fillStyle = look.accent;
      ctx.beginPath();
      ctx.arc(-R * 0.75, hy - R * 0.55, R * 0.22, 0, Math.PI * 2);
      ctx.arc(R * 0.75, hy - R * 0.55, R * 0.22, 0, Math.PI * 2);
      ctx.fill();
    } else if (a === "cap") {
      ctx.fillStyle = look.accent;
      ctx.beginPath();
      ctx.arc(0, hy - R * 0.2, R * 1.02, Math.PI, Math.PI * 2);
      ctx.fill();
      ctx.fillRect(-R * 0.2, hy - R * 0.32, R * 1.4, R * 0.25);
    }
  }

  /* ---------- 场景对象 ---------- */
  function create(canvas, hooks = {}) {
    const ctx = canvas.getContext("2d");
    const state = {
      styleKey: "calm",
      world: { heroes: [], assignments: {}, rooms: {}, boards: {}, cro: false },
      actors: new Map(),
      looks: {},
      blocked: new Set(),
      popups: [],
      particles: [],
      confetti: [],
      selected: null,
      hover: null,
      speed: 1,
      view: { k: 1, ox: 0, oy: 0, w: 0, h: 0, dpr: 1 },
      reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
      sceneBg: "#dfe6e3",
      accent: "#0f7a6b",
      make: "#c56d16",
      test: "#2a63a6",
      good: "#2c8546",
      bad: "#b23e33",
      time: 0,
      stationOf: new Map(),
      idleTimer: new Map(),
    };
    const S = () => STYLES[state.styleKey];

    function readTheme() {
      const cs = getComputedStyle(document.documentElement);
      const v = (name, fallback) => cs.getPropertyValue(name).trim() || fallback;
      state.sceneBg = v("--scene", state.sceneBg);
      state.accent = v("--accent", state.accent);
      state.make = v("--make", state.make);
      state.test = v("--test", state.test);
      state.good = v("--good", state.good);
      state.bad = v("--bad", state.bad);
      state.ink = v("--ink", "#1b272b");
      state.surface = v("--surface", "#f8faf9");
    }

    function resize() {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      const minX = iso(0, GRID_H).x - 12;
      const maxX = iso(GRID_W, 0).x + 12;
      const minY = iso(0, 0, S().wallH).y - 26;
      const maxY = iso(GRID_W, GRID_H).y + 14;
      const k = Math.min(rect.width / (maxX - minX), rect.height / (maxY - minY));
      state.view = {
        k,
        ox: (rect.width - (maxX - minX) * k) / 2 - minX * k,
        oy: (rect.height - (maxY - minY) * k) / 2 - minY * k,
        w: rect.width,
        h: rect.height,
        dpr,
      };
      hooks.onLayout?.();
    }

    function toScreen(p) {
      const v = state.view;
      return { x: v.ox + p.x * v.k, y: v.oy + p.y * v.k };
    }
    function anchor(kind, id) {
      if (kind === "room") {
        const r = ROOMS.find((q) => q.id === id);
        if (!r) return null;
        if (r.id === "bio" && !state.world.rooms?.bio?.built) return toScreen(iso(12, 9.5, 8));
        const [ax, ay] = r.label;
        const onWall = (ay === 0 || ax === 0) && r.id !== "bio";
        return toScreen(iso(ax, ay, onWall ? S().wallH + 4 : 8));
      }
      if (kind === "board") {
        const b = BOARDS[id];
        if (!b) return null;
        const mid = (b.from + b.to) / 2;
        return toScreen(b.plane === "x" ? iso(b.at, mid, b.zTop + 10) : iso(mid, b.at, b.zTop + 10));
      }
      if (kind === "hero") {
        const a = state.actors.get(id);
        if (!a) return null;
        return toScreen(iso(a.x, a.y, personHeight() + 10));
      }
      return null;
    }
    function personHeight() {
      const P = S().person;
      return P.legs + P.torso + P.head * 2;
    }

    /* ----- world 更新：谁该去哪里 ----- */
    function setWorld(world) {
      const roomsChanged = JSON.stringify(world.rooms) !== JSON.stringify(state.world.rooms);
      state.world = world;
      for (const h of world.heroes) {
        state.looks[h.id] = h.look;
        if (!state.actors.has(h.id)) {
          const spot = IDLE_SPOTS[state.actors.size % IDLE_SPOTS.length];
          state.actors.set(h.id, {
            id: h.id, x: spot.x, y: spot.y, path: [], target: null, face: spot.face, phase: Math.random() * 6,
            jump: 0, jumpT: 0, mode: "idle", key: null, helpers: 0, helperAlpha: 0,
          });
        }
      }
      if (roomsChanged || !state.blocked.size) state.blocked = buildBlocked(world);
      assign();
    }

    function assign() {
      const taken = new Map();
      const want = state.world.assignments || {};
      // 先保留已经站好的工位，避免两个人抢同一个位置
      for (const [id, a] of state.actors) {
        const job = want[id];
        if (job && job.mode !== "idle" && a.stationId) {
          const f = FURNITURE.find((q) => q.id === a.stationId);
          if (f && f.room === job.room && furnitureVisible(f, state.world)) taken.set(f.id, id);
        }
      }
      for (const [id, a] of state.actors) {
        const job = want[id] || { mode: "idle" };
        const key = `${job.mode}|${job.room || ""}|${job.project || ""}`;
        if (job.mode === "idle" || job.mode === "away") {
          if (a.key !== key) {
            a.key = key;
            a.mode = "idle";
            a.stationId = null;
            a.helpers = 0;
            sendIdle(id, a);
          }
          continue;
        }
        if (a.key === key && a.stationId) {
          a.helpers = job.members || 0;
          continue;
        }
        const options = FURNITURE.filter(
          (f) => f.room === job.room && f.station && furnitureVisible(f, state.world) && !taken.has(f.id),
        );
        const pick =
          options.find((f) => f.station.roles[0] === job.role) ||
          options.find((f) => f.station.roles.includes(job.role)) ||
          options[0];
        a.key = key;
        a.mode = job.mode;
        a.helpers = job.members || 0;
        if (!pick) {
          a.stationId = null;
          sendIdle(id, a);
          continue;
        }
        taken.set(pick.id, id);
        a.stationId = pick.id;
        walkTo(a, { x: pick.station.x, y: pick.station.y, face: pick.station.face });
      }
    }
    function sendIdle(id, a) {
      const used = new Set([...state.actors.values()].filter((q) => q !== a && q.idleSpot != null).map((q) => q.idleSpot));
      const free = IDLE_SPOTS.map((_, i) => i).filter((i) => !used.has(i));
      const i = free.length ? free[Math.floor(Math.random() * free.length)] : 0;
      a.idleSpot = i;
      state.idleTimer.set(id, 6 + Math.random() * 8);
      walkTo(a, IDLE_SPOTS[i]);
    }
    function walkTo(a, spot) {
      const path = findPath(state.blocked, a, spot);
      a.target = spot;
      a.path = path === null ? [] : [...path, { x: spot.x, y: spot.y }];
      if (path === null) {
        a.x = spot.x;
        a.y = spot.y;
        a.face = spot.face;
      }
    }

    /* ----- 事件 → 画面效果 ----- */
    function onEvent(e) {
      const where = () => {
        if (e.actors?.length && state.actors.has(e.actors[0])) {
          const a = state.actors.get(e.actors[0]);
          return { x: a.x, y: a.y, z: personHeight() + 6 };
        }
        const room = ROOMS.find((r) => r.id === (ENGINE_ROOMS[e.room] || e.room));
        if (room) return { x: (room.x0 + room.x1) / 2, y: (room.y0 + room.y1) / 2, z: 30 };
        return null;
      };
      if (e.type === "work_completed") {
        e.actors.forEach((id, i) => {
          const a = state.actors.get(id);
          if (!a) return;
          const parts = Object.entries(e.data.amounts || {}).map(
            ([k, v]) => `${v >= 0 ? "+" : ""}${v.toFixed(1)} ${e.data.labels?.[k] || k}`,
          );
          popup({ x: a.x, y: a.y, z: personHeight() + 8 }, parts.join("  "), state.make, i * 0.15);
          sparkle(a, state.make);
        });
      } else if (e.type === "evidence_received") {
        const b = BOARDS[ENGINE_ROOMS[e.room] || e.room];
        const at = b
          ? b.plane === "x"
            ? { x: b.at + 0.2, y: (b.from + b.to) / 2, z: b.zTop + 4 }
            : { x: (b.from + b.to) / 2, y: b.at + 0.2, z: b.zTop + 4 }
          : where();
        if (at) popup(at, `第 ${e.data.batch} 批数据`, state.test);
      } else if (e.type === "phase_finished") {
        const at = where();
        if (at) popup(at, e.data.passed === false ? "未通过" : "阶段通过", e.data.passed === false ? state.bad : state.good);
        if (e.data.passed !== false) e.actors.forEach((id) => celebrate(id));
      } else if (e.type === "service_completed") {
        const at = where();
        if (at) popup(at, `+¥${e.data.reward} 万`, state.good);
      } else if (e.type === "character_promoted") {
        const at = where();
        if (at) popup(at, `晋升${e.data.rank}`, state.accent);
        e.actors.forEach((id) => celebrate(id));
      } else if (e.type === "equipment_upgraded" || e.type === "room_built") {
        const room = ROOMS.find((r) => r.id === (ENGINE_ROOMS[e.room] || e.room));
        if (room) {
          popup({ x: (room.x0 + room.x1) / 2, y: (room.y0 + room.y1) / 2, z: 30 },
            e.type === "room_built" ? `${room.name}落成` : `设备升到 ${e.data.level} 级`, state.accent);
          dust(room);
        }
      } else if (e.type === "product_launched") {
        for (const id of state.actors.keys()) celebrate(id);
        confettiBurst();
      }
    }
    function popup(at, text, color, delay = 0) {
      // 同一位置已有飘字时往上叠，避免几条字压在一起
      const near = state.popups.filter((p) => Math.abs(p.x - at.x) < 0.8 && Math.abs(p.y - at.y) < 0.8 && p.t < p.dur * 0.6);
      state.popups.push({ ...at, lift: near.length, text, color, t: -delay, dur: 2.2 });
    }
    function sparkle(a, color) {
      if (state.reducedMotion) return;
      for (let i = 0; i < 6; i++) {
        state.particles.push({
          x: a.x, y: a.y, z: personHeight() - 4, vx: (Math.random() - 0.5) * 0.9, vy: (Math.random() - 0.5) * 0.9,
          vz: 18 + Math.random() * 16, t: 0, dur: 0.9, color, size: 2,
        });
      }
    }
    function dust(room) {
      if (state.reducedMotion) return;
      for (let i = 0; i < 24; i++) {
        state.particles.push({
          x: room.x0 + Math.random() * (room.x1 - room.x0), y: room.y0 + Math.random() * (room.y1 - room.y0), z: 2,
          vx: 0, vy: 0, vz: 10 + Math.random() * 14, t: 0, dur: 1.4, color: "rgba(200, 190, 170, 0.8)", size: 3,
        });
      }
    }
    function celebrate(id) {
      const a = state.actors.get(id);
      if (a && !state.reducedMotion) a.jumpT = 1.1;
    }
    function confettiBurst() {
      if (state.reducedMotion) return;
      const colors = [state.make, state.test, state.good, state.accent, "#e8c547"];
      for (let i = 0; i < 90; i++) {
        state.confetti.push({
          x: Math.random() * state.view.w, y: -10 - Math.random() * state.view.h * 0.4,
          vy: 50 + Math.random() * 70, vx: (Math.random() - 0.5) * 30, r: Math.random() * 6, vr: (Math.random() - 0.5) * 6,
          t: 0, dur: 3 + Math.random() * 1.5, color: colors[i % colors.length],
        });
      }
    }

    /* ----- 每帧 ----- */
    function update(dt) {
      state.time += dt;
      const walkSpeed = 2.6 * Math.max(1, state.speed);
      for (const [id, a] of state.actors) {
        a.phase += dt * (a.path.length ? 9 : 3);
        if (a.path.length) {
          const next = a.path[0];
          const dx = next.x - a.x;
          const dy = next.y - a.y;
          const dist = Math.hypot(dx, dy);
          const step = walkSpeed * dt;
          if (dist <= step) {
            a.x = next.x;
            a.y = next.y;
            a.path.shift();
            if (!a.path.length && a.target) a.face = a.target.face;
          } else {
            a.x += (dx / dist) * step;
            a.y += (dy / dist) * step;
            const sx = dx - dy;
            const sy = dx + dy;
            a.face = sy < -0.01 ? (sx >= 0 ? "up" : "left") : "down";
            a.flipWalk = sx < 0;
          }
        } else if (a.mode === "idle") {
          const left = (state.idleTimer.get(id) ?? 8) - dt;
          state.idleTimer.set(id, left);
          if (left <= 0) sendIdle(id, a);
        }
        if (a.jumpT > 0) {
          a.jumpT = Math.max(0, a.jumpT - dt);
          a.jump = Math.abs(Math.sin((1.1 - a.jumpT) * Math.PI * 2.7)) * 7 * (a.jumpT / 1.1);
        } else a.jump = 0;
        const target = a.mode !== "idle" && !a.path.length && a.stationId ? 1 : 0;
        a.helperAlpha += (target - a.helperAlpha) * Math.min(1, dt * 3);
      }
      state.popups = state.popups.filter((p) => (p.t += dt) < p.dur);
      for (const p of state.particles) {
        p.t += dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.z += p.vz * dt;
      }
      state.particles = state.particles.filter((p) => p.t < p.dur);
      for (const c of state.confetti) {
        c.t += dt;
        c.y += c.vy * dt;
        c.x += c.vx * dt;
        c.r += c.vr * dt;
      }
      state.confetti = state.confetti.filter((c) => c.t < c.dur);
      // 正在干活的人偶尔冒一点小粒子：橙色是做，蓝色是测
      if (!state.reducedMotion) {
        for (const a of state.actors.values()) {
          if (a.mode === "make" || a.mode === "test") {
            if (!a.path.length && Math.random() < dt * 0.9) {
              state.particles.push({
                x: a.x + (Math.random() - 0.5) * 0.4, y: a.y - 0.6, z: 22, vx: 0, vy: 0, vz: 12, t: 0, dur: 1.1,
                color: a.mode === "make" ? state.make : state.test, size: a.mode === "make" ? 2 : 2.4,
                square: a.mode === "test",
              });
            }
          }
        }
      }
    }

    function draw() {
      const v = state.view;
      const st = S();
      const c = st.c;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = state.sceneBg;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.setTransform(v.dpr * v.k, 0, 0, v.dpr * v.k, v.dpr * v.ox, v.dpr * v.oy);

      // 地面阴影
      ctx.fillStyle = c.shadow;
      poly(ctx, [iso(0.4, 0.4), iso(GRID_W + 0.5, 0.4), iso(GRID_W + 0.5, GRID_H + 0.5), iso(0.4, GRID_H + 0.5)], c.shadow);

      drawFloors(st);
      drawOuterWalls(st);
      drawBoards(st);

      // 需要排序的东西：家具、矮墙、人物
      const items = [];
      for (const f of FURNITURE) {
        if (!furnitureVisible(f, state.world)) continue;
        items.push({ depth: f.x + f.w / 2 + f.y + f.d / 2, draw: () => drawFurniture(st, f) });
      }
      for (const p of PARTITIONS) {
        for (let i = p.from; i < p.to; i++) {
          if (p.doors.includes(i)) continue;
          if (p.axis === "y" && p.at === 7 && i >= 8 && !state.world.rooms?.bio?.built) continue;
          if (p.axis === "x" && p.from === 7 && !state.world.rooms?.bio?.built) continue;
          const seg = p.axis === "y" ? { x: i, y: p.at - 0.06, w: 1, d: 0.12 } : { x: p.at - 0.06, y: i, w: 0.12, d: 1 };
          items.push({ depth: seg.x + seg.w / 2 + seg.y + seg.d / 2 - 0.02, draw: () => drawPartition(st, seg) });
        }
      }
      for (const [id, a] of state.actors) {
        const look = state.looks[id];
        if (!look) continue;
        items.push({ depth: a.x + a.y + 0.05, draw: () => drawActor(st, id, a, look) });
        if (a.helpers && a.helperAlpha > 0.02 && a.stationId) {
          const f = FURNITURE.find((q) => q.id === a.stationId);
          f?.station.helpers.slice(0, a.helpers).forEach(([hx, hy], i) => {
            items.push({
              depth: hx + hy,
              draw: () => drawPerson(ctx, st, helperLook(st, i), {
                x: iso(hx, hy).x, y: iso(hx, hy).y, phase: state.time * 3 + i, working: true, away: true,
                alpha: a.helperAlpha * 0.95, flip: i % 2 === 1,
              }),
            });
          });
        }
      }
      if (state.world.cro) {
        items.push({ depth: CRO_SPOT.x + CRO_SPOT.y, draw: () => drawCro(st) });
      }
      if (state.world.rooms?.bio?.building) items.push({ depth: 30, draw: () => drawScaffold(st) });
      items.sort((p, q) => p.depth - q.depth);
      for (const it of items) it.draw();

      // 粒子（世界坐标）
      for (const p of state.particles) {
        const s = iso(p.x, p.y, p.z);
        ctx.globalAlpha = Math.max(0, 1 - p.t / p.dur);
        ctx.fillStyle = p.color;
        if (p.square) ctx.fillRect(s.x - p.size / 2, s.y - p.size / 2, p.size, p.size);
        else {
          ctx.beginPath();
          ctx.arc(s.x, s.y, p.size / 2 + 0.4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;

      // 屏幕坐标层：名字、活动标记、飘字、彩纸
      ctx.setTransform(v.dpr, 0, 0, v.dpr, 0, 0);
      drawOverlays(st);
    }

    function drawFloors(st) {
      const c = st.c;
      const tiles = (r, fill, lineColor) => {
        poly(ctx, [iso(r.x0, r.y0), iso(r.x1, r.y0), iso(r.x1, r.y1), iso(r.x0, r.y1)], fill);
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        for (let x = r.x0 + 1; x < r.x1; x++) {
          const a = iso(x, r.y0);
          const b = iso(x, r.y1);
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
        }
        for (let y = r.y0 + 1; y < r.y1; y++) {
          const a = iso(r.x0, y);
          const b = iso(r.x1, y);
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
        }
        ctx.stroke();
      };
      tiles(CORRIDOR, c.corridor, c.corridorLine);
      // 走廊导向条
      poly(ctx, [iso(0.6, 5.93), iso(16, 5.93), iso(16, 6.07), iso(0.6, 6.07)], c.stripe);
      for (const r of ROOMS) {
        const room = state.world.rooms?.[r.id];
        if (r.buildable && !room?.built) {
          tiles(r, c.lot, c.lotLine);
          const build = room?.building;
          if (build) {
            const k = 1 - build.left / build.total;
            poly(ctx, [iso(r.x0, r.y0), iso(r.x0 + (r.x1 - r.x0) * k, r.y0), iso(r.x0 + (r.x1 - r.x0) * k, r.y1), iso(r.x0, r.y1)],
              hexAlpha(state.accent, 0.18));
          }
          ctx.setLineDash([6, 5]);
          poly(ctx, [iso(r.x0 + 0.15, r.y0 + 0.15), iso(r.x1 - 0.15, r.y0 + 0.15), iso(r.x1 - 0.15, r.y1 - 0.15), iso(r.x0 + 0.15, r.y1 - 0.15)],
            null, state.accent, 1.4);
          ctx.setLineDash([]);
        } else {
          tiles(r, r.floor === "office" ? c.floorOffice : c.floorLab, r.floor === "office" ? c.floorOfficeLine : c.floorLabLine);
        }
        const hot = state.hover?.type === "room" && state.hover.id === r.id;
        const sel = state.selected?.type === "room" && state.selected.id === r.id;
        if (hot || sel) {
          poly(ctx, [iso(r.x0, r.y0), iso(r.x1, r.y0), iso(r.x1, r.y1), iso(r.x0, r.y1)],
            hexAlpha(state.accent, sel ? 0.12 : 0.07), sel ? state.accent : null, 2);
        }
      }
    }

    function drawOuterWalls(st) {
      const c = st.c;
      const H = st.wallH;
      // 右后墙（y = 0）和左后墙（x = 0）
      poly(ctx, quadOnWall("y", 0, 0, GRID_W, 0, H), shade(c.wall, -0.06), st.outline);
      poly(ctx, quadOnWall("x", 0, 0, GRID_H, 0, H), c.wall, st.outline);
      // 窗户（避开柜子和白板）
      const panes = [
        { plane: "y", a0: 3.15, a1: 3.85 }, { plane: "y", a0: 7.15, a1: 7.85 },
        { plane: "y", a0: 8.2, a1: 8.9 }, { plane: "y", a0: 12.2, a1: 12.9 },
        { plane: "x", a0: 1.1, a1: 1.9 }, { plane: "x", a0: 4.15, a1: 4.85 },
      ];
      for (const w of panes) {
        poly(ctx, quadOnWall(w.plane, 0, w.a0, w.a1, H * 0.42, H * 0.86), c.window, c.windowFrame, 1);
        const mid = (w.a0 + w.a1) / 2;
        const p0 = w.plane === "y" ? iso(mid, 0, H * 0.42) : iso(0, mid, H * 0.42);
        const p1 = w.plane === "y" ? iso(mid, 0, H * 0.86) : iso(0, mid, H * 0.86);
        ctx.strokeStyle = c.windowFrame;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.stroke();
      }
      // 墙顶
      const cap = 3;
      poly(ctx, [iso(0, 0, H + cap), iso(GRID_W, 0, H + cap), iso(GRID_W, 0, H), iso(0, 0, H)], c.wallTop);
      poly(ctx, [iso(0, 0, H + cap), iso(0, GRID_H, H + cap), iso(0, GRID_H, H), iso(0, 0, H)], shade(c.wallTop, 0.1));
      // 踢脚线
      poly(ctx, quadOnWall("y", 0, 0, GRID_W, 0, 3), shade(c.wall, -0.18));
      poly(ctx, quadOnWall("x", 0, 0, GRID_H, 0, 3), shade(c.wall, -0.12));
    }

    function drawBoards(st) {
      const c = st.c;
      for (const [roomId, b] of Object.entries(BOARDS)) {
        poly(ctx, quadOnWall(b.plane, b.at, b.from, b.to, b.zBottom, b.zTop), c.board, c.boardFrame, 1.2);
        const series = state.world.boards?.[roomId] || [];
        const span = Math.abs(b.to - b.from);
        const Wb = span * 40;
        const Hb = b.zTop - b.zBottom;
        const origin = b.plane === "x" ? iso(b.at, b.from, b.zTop) : iso(b.from, b.at, b.zTop);
        const ux = b.plane === "x" ? HW / 40 : HW / 40;
        const uy = b.plane === "x" ? -HH / 40 : HH / 40;
        ctx.save();
        ctx.transform(ux, uy, 0, 1, origin.x, origin.y);
        if (!series.length) {
          ctx.fillStyle = "rgba(90, 110, 115, 0.55)";
          ctx.font = `600 7px ${fontFamily()}`;
          ctx.fillText("暂无进行中的验证", 6, Hb / 2 + 2);
        }
        const n = series.length;
        series.slice(0, 2).forEach((s, si) => {
          const x0 = 4 + (si * (Wb - 8)) / n;
          const w = (Wb - 8) / n - (n > 1 ? 4 : 0);
          ctx.fillStyle = "rgba(40, 60, 70, 0.85)";
          ctx.font = `600 6.5px ${fontFamily()}`;
          ctx.fillText(s.title, x0, 8);
          const top = 11;
          const bottom = Hb - 4;
          const lo = s.limit - 24;
          const hi = s.limit + 24;
          const yOf = (val) => bottom - ((Math.max(lo, Math.min(hi, val)) - lo) / (hi - lo)) * (bottom - top);
          ctx.strokeStyle = "rgba(178, 62, 51, 0.8)";
          ctx.setLineDash([2.5, 2]);
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(x0, yOf(s.limit));
          ctx.lineTo(x0 + w, yOf(s.limit));
          ctx.stroke();
          ctx.setLineDash([]);
          const step = w / (s.batches + 0.5);
          s.readings.forEach((val, i) => {
            ctx.fillStyle = state.test;
            ctx.beginPath();
            ctx.arc(x0 + step * (i + 0.75), yOf(val), 1.9, 0, Math.PI * 2);
            ctx.fill();
          });
          if (s.readings.length > 1) {
            const mean = s.readings.reduce((p, q) => p + q, 0) / s.readings.length;
            ctx.strokeStyle = state.test;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x0, yOf(mean));
            ctx.lineTo(x0 + w, yOf(mean));
            ctx.stroke();
          }
        });
        ctx.restore();
      }
    }

    function drawPartition(st, seg) {
      const c = st.c;
      box(ctx, st, seg.x, seg.y, seg.w, seg.d, st.partH, c.part, 0, c.partTop);
      const z0 = st.partH;
      const B = iso(seg.x + seg.w, seg.y, z0 + st.glassH);
      const C = iso(seg.x + seg.w, seg.y + seg.d, z0 + st.glassH);
      const D = iso(seg.x, seg.y + seg.d, z0 + st.glassH);
      const Cb = iso(seg.x + seg.w, seg.y + seg.d, z0);
      const Db = iso(seg.x, seg.y + seg.d, z0);
      const Bb = iso(seg.x + seg.w, seg.y, z0);
      poly(ctx, [D, C, Cb, Db], c.glass);
      poly(ctx, [B, C, Cb, Bb], c.glass);
      ctx.strokeStyle = shade(c.partTop, 0.2);
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(D.x, D.y);
      ctx.lineTo(C.x, C.y);
      ctx.lineTo(B.x, B.y);
      ctx.stroke();
    }

    function drawFurniture(st, f) {
      const c = st.c;
      const { x, y, w, d, h } = f;
      if (f.type === "bench" || f.type === "island") {
        box(ctx, st, x + 0.05, y + 0.05, w - 0.1, d - 0.1, h - 3, c.cabinet);
        box(ctx, st, x, y, w, d, 3, c.benchTop, h - 3, c.benchTop);
        // 台面上的东西
        if (f.items === "instrument") {
          box(ctx, st, x + 0.3, y + 0.15, 0.9, 0.6, 14, c.metal, h);
          box(ctx, st, x + 1.4, y + 0.2, 0.7, 0.55, 10, c.white, h);
          const s = iso(x + 0.75, y + 0.75, h + 9);
          ctx.fillStyle = c.screen;
          ctx.fillRect(s.x - 3, s.y - 2, 6, 3.5);
        } else if (f.items === "microscope") {
          box(ctx, st, x + 0.5, y + 0.3, 0.4, 0.35, 12, c.metal, h);
          box(ctx, st, x + 1.6, y + 0.25, 0.8, 0.5, 6, c.white, h);
        } else {
          for (let i = 0; i < Math.round(w * 2); i++) {
            const gx = x + 0.3 + i * 0.45;
            const gy = y + 0.3 + (i % 2) * 0.25;
            const s = iso(gx, gy, h);
            ctx.fillStyle = c.glassware;
            ctx.fillRect(s.x - 1.6, s.y - 7, 3.2, 7);
            ctx.fillStyle = i % 3 === 0 ? c.liquid : shade(c.glassware, -0.2);
            ctx.fillRect(s.x - 1.6, s.y - 3, 3.2, 3);
          }
        }
      } else if (f.type === "hood") {
        box(ctx, st, x, y, w, d, h, c.metal);
        // 正面玻璃窗（朝 +y）
        const g = [iso(x + 0.15, y + d, h - 8), iso(x + w - 0.15, y + d, h - 8), iso(x + w - 0.15, y + d, 24), iso(x + 0.15, y + d, 24)];
        poly(ctx, g, c.window, shade(c.metal, -0.3), 0.8);
        box(ctx, st, x, y + 0.02, w, d - 0.04, 20, c.cabinet);
        const s = iso(x + w / 2, y + d, h - 3);
        ctx.fillStyle = c.glow;
        ctx.fillRect(s.x - 6, s.y - 1.5, 12, 2);
      } else if (f.type === "shelf") {
        box(ctx, st, x, y, w * 0.6, d, h, c.wood);
        for (let k = 1; k < 4; k++) {
          const a = iso(x + w * 0.6, y, (h * k) / 4);
          const b = iso(x + w * 0.6, y + d, (h * k) / 4);
          ctx.strokeStyle = shade(c.wood, -0.35);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
          for (let j = 0; j < 5; j++) {
            const p = iso(x + w * 0.6, y + 0.2 + j * 0.33, (h * k) / 4);
            ctx.fillStyle = ["#6a8caf", "#c9a15a", "#8fa98a", "#b07a6a", "#7c8a99"][(j + k) % 5];
            ctx.fillRect(p.x - 1, p.y - 7, 2.6, 6.5);
          }
        }
      } else if (f.type === "instrument") {
        box(ctx, st, x + 0.15, y + 0.15, w - 0.3, d - 0.3, h, c.white);
        const s = iso(x + w / 2, y + d - 0.15, h * 0.7);
        ctx.fillStyle = c.screen;
        ctx.fillRect(s.x - 4, s.y - 3, 8, 5);
        ctx.fillStyle = c.glow;
        ctx.fillRect(s.x - 3, s.y - 2, 3, 1.5);
      } else if (f.type === "chamber") {
        box(ctx, st, x + 0.1, y + 0.1, w - 0.2, d - 0.2, h, c.white);
        const g = [iso(x + 0.25, y + d - 0.1, h - 6), iso(x + w - 0.25, y + d - 0.1, h - 6), iso(x + w - 0.25, y + d - 0.1, 8), iso(x + 0.25, y + d - 0.1, 8)];
        poly(ctx, g, c.window, shade(c.white, -0.3), 0.8);
      } else if (f.type === "desk" || f.type === "cro") {
        // 桌腿
        for (const [lx, ly] of [[x + 0.1, y + 0.1], [x + w - 0.1, y + 0.1], [x + 0.1, y + d - 0.1], [x + w - 0.1, y + d - 0.1]]) {
          const a = iso(lx, ly, 0);
          const b = iso(lx, ly, h - 2);
          ctx.strokeStyle = shade(c.metal, -0.35);
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
        box(ctx, st, x, y, w, d, 2.5, c.wood, h - 2.5, shade(c.wood, 0.12));
        if (f.type === "cro") {
          box(ctx, st, x + 0.3, y + 0.25, 0.35, 0.3, 3, "#3d4a52", h);
          box(ctx, st, x + 1.2, y + 0.2, 0.5, 0.4, 1.2, c.white, h);
          if (state.world.cro) {
            const s = iso(x + w / 2, y + 0.1, h + 26);
            ctx.font = `700 7px ${fontFamily()}`;
            ctx.fillStyle = c.cro;
            ctx.textAlign = "center";
            ctx.fillText("外包 CRO", s.x, s.y);
            ctx.textAlign = "left";
          }
        } else {
          const mx = x + w / 2 - 0.35;
          const my = f.monitor === "back" ? y + d - 0.4 : y + 0.15;
          box(ctx, st, mx, my, 0.7, 0.12, 13, f.monitor === "back" ? "#4a5761" : c.screen, h);
          if (f.monitor !== "back") {
            const s1 = iso(mx + 0.05, my + 0.12, h + 11);
            const s2 = iso(mx + 0.65, my + 0.12, h + 11);
            const s3 = iso(mx + 0.65, my + 0.12, h + 3);
            const s4 = iso(mx + 0.05, my + 0.12, h + 3);
            poly(ctx, [s1, s2, s3, s4], hexAlpha(c.glow, 0.75));
          }
          box(ctx, st, x + 0.25, y + 0.35, 0.45, 0.3, 1.5, "#d7dadc", h);
        }
      } else if (f.type === "table") {
        box(ctx, st, x + 0.05, y + 0.05, w - 0.1, d - 0.1, 2.5, c.wood, h - 2.5, shade(c.wood, 0.12));
        const s = iso(x + w / 2, y + d / 2, h - 2.5);
        ctx.fillStyle = shade(c.wood, -0.4);
        ctx.fillRect(s.x - 1, s.y, 2, h - 3);
        box(ctx, st, x + 0.3, y + 0.3, 0.5, 0.35, 0.8, c.white, h);
      } else if (f.type === "plant") {
        box(ctx, st, x + 0.3, y + 0.3, 0.4, 0.4, 8, c.pot);
        const s = iso(x + 0.5, y + 0.5, 8);
        ctx.fillStyle = c.plant;
        for (const [dx, dy, r] of [[0, -9, 6], [-4, -5, 4.5], [4, -6, 4.5], [0, -15, 4.2]]) {
          ctx.beginPath();
          ctx.arc(s.x + dx, s.y + dy, r, 0, Math.PI * 2);
          ctx.fill();
        }
      } else if (f.type === "coffee") {
        box(ctx, st, x + 0.15, y + 0.15, 0.7, 0.7, 12, c.wood);
        box(ctx, st, x + 0.25, y + 0.25, 0.5, 0.45, 16, "#3a3f44", 12);
        const s = iso(x + 0.6, y + 0.7, 18);
        ctx.fillStyle = "#e9e3d8";
        ctx.fillRect(s.x - 1.5, s.y - 2, 3, 3);
      } else if (f.type === "cooler") {
        box(ctx, st, x + 0.25, y + 0.25, 0.5, 0.5, 22, c.white);
        const s = iso(x + 0.5, y + 0.5, 22);
        ctx.fillStyle = "rgba(120, 180, 220, 0.85)";
        rrect(ctx, s.x - 3.5, s.y - 12, 7, 12, 3);
        ctx.fill();
      }
    }

    function helperLook(st, i) {
      return {
        skin: ["#e9c4a0", "#d9aa82", "#f1cfae"][i % 3],
        hair: i % 2 ? "short" : "bob",
        hairColor: ["#2c2420", "#4a3628", "#1e1b1a"][i % 3],
        shirt: st.c.helper,
        coat: true,
      };
    }

    function drawActor(st, id, a, look) {
      const p = iso(a.x, a.y);
      const working = !a.path.length && (a.mode === "make" || a.mode === "test" || a.mode === "service");
      const facing = a.path.length ? a.face : a.target?.face || a.face;
      const away = facing === "up" || facing === "left";
      const flip = a.path.length ? a.flipWalk : facing === "left";
      const sel = state.selected?.type === "hero" && state.selected.id === id;
      drawPerson(ctx, st, look, {
        x: p.x, y: p.y, phase: a.phase, walking: a.path.length > 0, working, away, flip, jump: a.jump,
        ring: sel ? state.accent : state.hover?.type === "hero" && state.hover.id === id ? hexAlpha(state.accent, 0.6) : null,
      });
    }

    function drawCro(st) {
      const p = iso(CRO_SPOT.x, CRO_SPOT.y);
      drawPerson(ctx, st, {
        skin: "#e2b894", hair: "short", hairColor: "#3a3a3a", shirt: st.c.cro, coat: false, holds: "tablet",
        pants: "#4b5560",
      }, { x: p.x, y: p.y, phase: state.time * 2, working: true, away: false });
    }

    function drawScaffold(st) {
      const r = ROOMS.find((q) => q.id === "bio");
      const b = state.world.rooms.bio.building;
      const k = 1 - b.left / b.total;
      const h = 14 + 40 * k;
      ctx.strokeStyle = shade("#c98b3a", -0.1);
      ctx.lineWidth = 1.4;
      for (const [x, y] of [[r.x0 + 0.3, r.y0 + 0.3], [r.x1 - 0.3, r.y0 + 0.3], [r.x1 - 0.3, r.y1 - 0.3], [r.x0 + 0.3, r.y1 - 0.3]]) {
        const a = iso(x, y, 0);
        const t = iso(x, y, h);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(t.x, t.y);
        ctx.stroke();
      }
      for (const z of [h * 0.5, h]) {
        poly(ctx, [iso(r.x0 + 0.3, r.y0 + 0.3, z), iso(r.x1 - 0.3, r.y0 + 0.3, z), iso(r.x1 - 0.3, r.y1 - 0.3, z), iso(r.x0 + 0.3, r.y1 - 0.3, z)],
          null, "#c98b3a", 1.1);
      }
    }

    function drawOverlays(st) {
      const fam = fontFamily();
      // 每个人头顶的小标记：橙=做，蓝=测，绿=服务，灰=空闲
      for (const [id, a] of state.actors) {
        const look = state.looks[id];
        if (!look) continue;
        const s = toScreen(iso(a.x, a.y, personHeight() + 5 + a.jump));
        const color = { make: state.make, test: state.test, service: state.good }[a.mode] || "rgba(120,130,135,0.7)";
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(s.x, s.y, 3.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = state.surface;
        ctx.lineWidth = 1.2;
        ctx.stroke();
        const showName =
          (state.selected?.type === "hero" && state.selected.id === id) ||
          (state.hover?.type === "hero" && state.hover.id === id);
        if (showName) {
          const name = state.world.heroes.find((h) => h.id === id)?.name || id;
          ctx.font = `600 12px ${fam}`;
          const w = ctx.measureText(name).width + 12;
          ctx.fillStyle = state.ink;
          rrect(ctx, s.x - w / 2, s.y - 26, w, 18, 9);
          ctx.fill();
          ctx.fillStyle = state.surface;
          ctx.textAlign = "center";
          ctx.fillText(name, s.x, s.y - 13);
          ctx.textAlign = "left";
        }
      }
      for (const p of state.popups) {
        if (p.t < 0) continue;
        const k = p.t / p.dur;
        const s = toScreen(iso(p.x, p.y, p.z + (state.reducedMotion ? 0 : k * 26)));
        s.y -= (p.lift || 0) * 17;
        ctx.globalAlpha = k < 0.75 ? 1 : 1 - (k - 0.75) / 0.25;
        ctx.font = `700 13px ${fam}`;
        ctx.textAlign = "center";
        ctx.lineWidth = 3.5;
        ctx.strokeStyle = state.surface;
        ctx.strokeText(p.text, s.x, s.y);
        ctx.fillStyle = p.color;
        ctx.fillText(p.text, s.x, s.y);
        ctx.textAlign = "left";
        ctx.globalAlpha = 1;
      }
      for (const c of state.confetti) {
        ctx.save();
        ctx.translate(c.x, c.y);
        ctx.rotate(c.r);
        ctx.globalAlpha = Math.max(0, 1 - c.t / c.dur);
        ctx.fillStyle = c.color;
        ctx.fillRect(-3, -1.5, 6, 3);
        ctx.restore();
      }
      ctx.globalAlpha = 1;
    }

    function fontFamily() {
      return getComputedStyle(document.body).fontFamily || "sans-serif";
    }

    /* ----- 点和悬停 ----- */
    function pick(clientX, clientY) {
      const rect = canvas.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;
      const v = state.view;
      const wx = (sx - v.ox) / v.k;
      const wy = (sy - v.oy) / v.k;
      const H = personHeight();
      const sorted = [...state.actors.entries()].sort((p, q) => q[1].x + q[1].y - (p[1].x + p[1].y));
      for (const [id, a] of sorted) {
        const p = iso(a.x, a.y);
        if (Math.abs(wx - p.x) < 10 && wy < p.y + 4 && wy > p.y - H - 6 - a.jump) return { type: "hero", id };
      }
      const g = toGrid(wx, wy);
      for (const r of ROOMS) {
        if (g.x >= r.x0 && g.x < r.x1 && g.y >= r.y0 && g.y < r.y1) return { type: "room", id: r.id };
      }
      return null;
    }
    canvas.addEventListener("pointermove", (e) => {
      state.hover = pick(e.clientX, e.clientY);
      canvas.style.cursor = state.hover ? "pointer" : "default";
    });
    canvas.addEventListener("pointerleave", () => {
      state.hover = null;
    });
    canvas.addEventListener("click", (e) => {
      const hit = pick(e.clientX, e.clientY);
      hooks.onSelect?.(hit);
    });

    function drawPortrait(target, look) {
      const c2 = target.getContext("2d");
      const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
      const size = target.clientWidth || 44;
      target.width = size * dpr;
      target.height = size * dpr;
      c2.setTransform(dpr, 0, 0, dpr, 0, 0);
      c2.clearRect(0, 0, size, size);
      const st = S();
      const P = st.person;
      const scale = (size * 0.9) / (P.head * 2 + P.torso * 0.75);
      c2.save();
      c2.translate(size / 2, size * 0.98 + (P.legs + P.torso * 0.25) * scale);
      c2.scale(scale, scale);
      drawPerson(c2, st, look, { x: 0, y: 0, phase: 0, walking: false, working: false, away: false });
      c2.restore();
    }

    function hexAlpha(color, a) {
      if (color.startsWith("#")) {
        const [r, g, b] = hexToRgb(color);
        return `rgba(${r}, ${g}, ${b}, ${a})`;
      }
      if (color.startsWith("rgb(")) return color.replace("rgb(", "rgba(").replace(")", `, ${a})`);
      return color;
    }

    let last = performance.now();
    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      update(dt);
      draw();
      hooks.onFrame?.(dt);
      requestAnimationFrame(frame);
    }

    readTheme();
    new ResizeObserver(resize).observe(canvas);
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", readTheme);
    new MutationObserver(readTheme).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    resize();
    requestAnimationFrame(frame);

    return {
      setWorld,
      event: onEvent,
      select(sel) {
        state.selected = sel;
      },
      setSpeed(k) {
        state.speed = k;
      },
      setStyle(key) {
        state.styleKey = key;
        resize();
      },
      get style() {
        return state.styleKey;
      },
      anchor,
      drawPortrait,
      rooms: ROOMS,
      engineRooms: ENGINE_ROOMS,
    };
  }

  window.DrugstoryScene = { create, ROOMS, ENGINE_ROOMS };
})();
