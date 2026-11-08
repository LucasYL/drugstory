/* 新药物语 · 人物绘制（明快画风）。
 * 每个人由外观数据画出来：体型、身高、年龄、肤色、发型、服装、配饰、手里的道具和小动作。
 * 坐标原点在脚底中心，y 向上为负。场景、头像、图鉴共用这一份代码。 */
(function (root) {
  "use strict";

  const BASE = { legs: 7.6, torso: 11.4, head: 8.6, shoulders: 12.8 };
  const INK = "#2d2725";

  /* ---------- 颜色 ---------- */
  function rgb(hex) {
    const v = hex.replace("#", "");
    const n = parseInt(
      v.length === 3
        ? v
            .split("")
            .map((c) => c + c)
            .join("")
        : v,
      16,
    );
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function shade(hex, k) {
    if (!hex || hex[0] !== "#") return hex;
    const [r, g, b] = rgb(hex);
    const f = (c) =>
      Math.round(k >= 0 ? c + (255 - c) * k : c * (1 + k))
        .toString(16)
        .padStart(2, "0");
    return `#${f(r)}${f(g)}${f(b)}`;
  }
  function alpha(hex, a) {
    const [r, g, b] = rgb(hex);
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  }
  const light = (hex) => {
    const [r, g, b] = rgb(hex);
    return 0.299 * r + 0.587 * g + 0.114 * b > 150;
  };

  /* ---------- 形状 ---------- */
  function rr(ctx, x, y, w, h, r) {
    const q = Math.max(0, Math.min(r, w / 2, h / 2));
    ctx.beginPath();
    ctx.moveTo(x + q, y);
    ctx.arcTo(x + w, y, x + w, y + h, q);
    ctx.arcTo(x + w, y + h, x, y + h, q);
    ctx.arcTo(x, y + h, x, y, q);
    ctx.arcTo(x, y, x + w, y, q);
    ctx.closePath();
  }
  // 上宽下略窄的躯干
  function torsoPath(ctx, top, w, bottomW, h, r) {
    const a = w / 2,
      b = bottomW / 2;
    ctx.beginPath();
    ctx.moveTo(-a + r, top);
    ctx.lineTo(a - r, top);
    ctx.quadraticCurveTo(a, top, a, top + r);
    ctx.lineTo(b, top + h - 1.2);
    ctx.quadraticCurveTo(b, top + h, b - 1.2, top + h);
    ctx.lineTo(-b + 1.2, top + h);
    ctx.quadraticCurveTo(-b, top + h, -b, top + h - 1.2);
    ctx.lineTo(-a, top + r);
    ctx.quadraticCurveTo(-a, top, -a + r, top);
    ctx.closePath();
  }
  function paint(ctx, color, line = 0.9, edge = null) {
    ctx.fillStyle = color;
    ctx.fill();
    if (line) {
      ctx.strokeStyle = edge || shade(color, light(color) ? -0.32 : -0.5);
      ctx.lineWidth = line;
      ctx.lineJoin = "round";
      ctx.stroke();
    }
  }
  // 右侧背光：在当前路径里叠一层暗面
  function sideShadow(ctx, x0, y0, w, h, k = 0.1) {
    ctx.save();
    ctx.clip();
    ctx.fillStyle = `rgba(40, 30, 20, ${k})`;
    ctx.fillRect(x0, y0, w, h);
    ctx.restore();
  }

  /* ---------- 体型与动作 ---------- */
  function dims(look) {
    const h = look.height || 0;
    const build = look.build || "average";
    const senior = look.age === "senior";
    const R = BASE.head + (look.age === "young" ? 0.25 : 0);
    const SW =
      BASE.shoulders + (build === "broad" ? 2.8 : build === "slim" ? -1.3 : 0);
    return {
      L: BASE.legs + h * 1.2 - (senior ? 0.6 : 0),
      T: BASE.torso + h * 0.6 + (build === "broad" ? 0.6 : 0),
      R,
      SW,
      HW: SW - (build === "broad" ? 1.6 : 2.4),
      LW: build === "broad" ? 3.9 : build === "slim" ? 3.1 : 3.5,
    };
  }
  function height(look) {
    const d = dims(look || {});
    return d.L + d.T + d.R * 1.9;
  }

  // 小动作：前臂角度、是否举到脸边、身体起伏、点头
  function pose(o, look) {
    if (o.still) return { arm: -0.62, toFace: false, bob: 0, nod: 0, up: false };
    const t = o.phase || 0;
    if (o.walking)
      return {
        arm: Math.sin(t * 2) * 0.4,
        toFace: false,
        bob: Math.abs(Math.sin(t * 2)) * 1.1,
        nod: 0,
        up: false,
      };
    if (o.working)
      return {
        arm: -0.85 + Math.sin(t * 3.2) * 0.2,
        toFace: false,
        bob: Math.sin(t * 0.7) * 0.3,
        nod: 0,
        up: false,
      };
    const cycle = (t / 2.6) % 6;
    const active = cycle < 1.4;
    const idle = look.idle;
    const base = {
      arm: 0.1,
      toFace: false,
      bob: Math.sin(t * 0.7) * 0.35,
      nod: 0,
      up: false,
    };
    if (["sip", "radio", "photo", "glasses"].includes(idle) && active)
      return { ...base, arm: -2.45, toFace: true };
    if (["write", "tap", "type", "check", "weigh", "pipette"].includes(idle))
      return { ...base, arm: -1.0 + Math.sin(t * 4) * (active ? 0.16 : 0.04) };
    if (idle === "bounce")
      return {
        ...base,
        bob: Math.abs(Math.sin(t * 3.2)) * 1.6,
        arm: Math.sin(t * 3.2) * 0.5,
      };
    if (idle === "stretch" && active) return { ...base, arm: -2.9, up: true };
    if (idle === "twirl" || idle === "shake")
      return { ...base, arm: -1.15 + (active ? Math.sin(t * 9) * 0.12 : 0) };
    if (idle === "watch" && active) return { ...base, arm: -1.5 };
    if (idle === "nod")
      return { ...base, nod: active ? Math.abs(Math.sin(t * 3)) * 0.9 : 0 };
    return base;
  }

  /* ---------- v0.11 新画法：用 art.js 生成的 Q 版全身图 ---------- */
  const ART = () => root.DrugstoryArt;
  // 新画法的人物比旧画法高一些、头更大，场景里更好认
  const SPRITE = { w: 120, h: 176, feet: 170, body: 155, grow: 1.25 };
  function drawSprite(ctx, look, o, img) {
    const ps = pose(o, look);
    const H = height(look) * SPRITE.grow;
    const k = H / SPRITE.body;
    ctx.save();
    ctx.translate(o.x || 0, o.y || 0);
    ctx.globalAlpha = (o.alpha ?? 1) * (o.away ? 0.92 : 1);
    if (!o.noShadow) {
      ctx.fillStyle = "rgba(40, 50, 45, 0.16)";
      ctx.beginPath();
      ctx.ellipse(0, 0, 9, 3.6, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    if (o.ring) {
      ctx.strokeStyle = o.ring;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(0, 0, 13, 5.4, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.translate(0, -(o.jump || 0) - ps.bob * 1.2);
    if (o.walking) ctx.rotate(Math.sin((o.phase || 0) * 2) * 0.05);
    if (o.flip) ctx.scale(-1, 1);
    ctx.drawImage(img, -SPRITE.w * k * 0.5, -SPRITE.feet * k, SPRITE.w * k, SPRITE.h * k);
    ctx.restore();
  }

  /* ---------- 主函数 ---------- */
  function drawPerson(ctx, look, o) {
    const sprite = look.art && ART()?.image(look.art, "chibi");
    if (sprite) return drawSprite(ctx, look, o, sprite);
    const D = dims(look);
    const { L, T, R, SW, HW, LW } = D;
    const ps = pose(o, look);
    const walk = o.walking ? Math.sin((o.phase || 0) * 2) : 0;
    const acc = new Set(look.accessories || []);
    const skin = look.skin || "#eec3a0";
    const hair = look.hair_color || "#2a2220";
    const top = look.top_color || "#7a8a99";
    const away = !!o.away;
    ctx.save();
    ctx.translate(o.x || 0, o.y || 0);
    ctx.globalAlpha = o.alpha ?? 1;
    if (!o.noShadow) {
      ctx.fillStyle = "rgba(40, 50, 45, 0.16)";
      ctx.beginPath();
      ctx.ellipse(0, 0, SW * 0.62, 3.6, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    if (o.ring) {
      ctx.strokeStyle = o.ring;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(0, 0, SW * 0.9, 5.4, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.translate(0, -(o.jump || 0) - ps.bob);
    if (o.flip) ctx.scale(-1, 1);
    const topY = -L - T;
    const hy = topY - R * 0.86 + ps.nod;
    const g = { look, acc, skin, hair, top, L, T, R, SW, HW, LW, topY, hy, away, ps, walk, o };

    if (!away) backHair(ctx, g);
    legs(ctx, g);
    backArm(ctx, g);
    torso(ctx, g);
    if (away) backDetails(ctx, g);
    frontArm(ctx, g);
    head(ctx, g);
    ctx.restore();
  }

  function legs(ctx, g) {
    const { L, LW, walk, look } = g;
    const pants = look.pants || "#3c4751";
    const shoe = shade(pants, -0.45);
    for (const side of [-1, 1]) {
      const dx = side < 0 ? -LW - 0.3 + walk * 1.7 : 0.3 - walk * 1.7;
      rr(ctx, dx, -L - 0.5, LW, L + 0.5, 1.4);
      paint(ctx, side < 0 ? pants : shade(pants, -0.12), 0.8);
      rr(ctx, dx - 0.5, -2.1, LW + 1.2, 2.4, 1.1);
      paint(ctx, shoe, 0.6, shade(shoe, -0.4));
    }
  }
  function sleeveColor(g) {
    const { look, top } = g;
    if (look.coat) return "#ffffff";
    if (look.top === "safety_vest" || look.top === "vest") return shade(top, 0.62);
    return top;
  }
  function backArm(ctx, g) {
    const { SW, T, topY, ps, skin, acc, look } = g;
    const s = sleeveColor(g);
    ctx.save();
    ctx.translate(SW / 2 - 1.1, topY + 1.6);
    ctx.rotate(ps.up ? -2.9 : 0.12);
    rr(ctx, -1.6, 0, 3.2, T - 2.4, 1.6);
    paint(ctx, shade(s, -0.1), 0.8);
    ctx.beginPath();
    ctx.arc(0, T - 2.2, 1.75, 0, Math.PI * 2);
    paint(ctx, acc.has("gloves") ? look.accent : shade(skin, -0.04), 0.6);
    ctx.restore();
  }
  function frontArm(ctx, g) {
    const { SW, T, topY, ps, skin, acc, look, away, o } = g;
    const s = sleeveColor(g);
    ctx.save();
    ctx.translate(-SW / 2 + 1.1, topY + 1.6);
    ctx.rotate(ps.arm);
    rr(ctx, -1.6, 0, 3.2, T - 2.4, 1.6);
    paint(ctx, s, 0.8);
    if (look.coat) {
      ctx.fillStyle = "#e3ecef";
      ctx.fillRect(-1.6, T - 4.6, 3.2, 1.1);
    }
    ctx.beginPath();
    ctx.arc(0, T - 2.2, 1.75, 0, Math.PI * 2);
    paint(ctx, acc.has("gloves") ? look.accent : skin, 0.6);
    if (acc.has("watch") || acc.has("bracelet")) {
      ctx.fillStyle = acc.has("bracelet") ? look.accent : "#2c3036";
      ctx.fillRect(-1.7, T - 4.4, 3.4, 1.1);
    }
    if (!away) prop(ctx, look, T - 2.2, o);
    ctx.restore();
  }

  /* ---------- 衣服 ---------- */
  function torso(ctx, g) {
    const { look, top, topY, T, SW, HW, away, acc } = g;
    const bottom = topY + T;
    if (look.coat) {
      // 白大褂：比身体长，前襟露出里面的衣服
      torsoPath(ctx, topY, SW, HW + 1.2, T + 3.6, 3.2);
      paint(ctx, "#ffffff", 0.9, "#a9b9c0");
      torsoPath(ctx, topY, SW, HW + 1.2, T + 3.6, 3.2);
      sideShadow(ctx, SW * 0.18, topY, SW, T + 4, 0.07);
      if (away) return;
      ctx.fillStyle = top;
      ctx.beginPath();
      ctx.moveTo(-3.1, topY + 0.2);
      ctx.lineTo(3.1, topY + 0.2);
      ctx.lineTo(0, topY + 7.2);
      ctx.closePath();
      ctx.fill();
      if (look.top === "hoodie") {
        rr(ctx, -4.6, topY - 1.9, 9.2, 3.4, 1.7);
        paint(ctx, shade(top, -0.06), 0.7);
        ctx.strokeStyle = "#fbf6ee";
        ctx.lineWidth = 0.6;
        ctx.beginPath();
        ctx.moveTo(-1.1, topY + 1.2);
        ctx.lineTo(-1.3, topY + 5.2);
        ctx.moveTo(1.1, topY + 1.2);
        ctx.lineTo(1.3, topY + 5.2);
        ctx.stroke();
      } else if (look.top === "turtleneck") {
        rr(ctx, -2.8, topY - 2.1, 5.6, 3.2, 1.2);
        paint(ctx, top, 0.6);
      } else if (look.top === "shirt" || look.top === "polo") {
        ctx.fillStyle = shade(top, 0.35);
        ctx.beginPath();
        ctx.moveTo(-2.6, topY + 0.1);
        ctx.lineTo(0, topY + 2.4);
        ctx.lineTo(2.6, topY + 0.1);
        ctx.closePath();
        ctx.fill();
      }
      // 翻领
      ctx.strokeStyle = "#b8c7cd";
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(-3.3, topY + 0.3);
      ctx.lineTo(-0.4, topY + 7.6);
      ctx.lineTo(-0.4, bottom + 3.4);
      ctx.moveTo(3.3, topY + 0.3);
      ctx.lineTo(0.4, topY + 7.6);
      ctx.stroke();
      ctx.strokeRect(-SW / 2 + 1.8, topY + T * 0.6, 2.8, 2.2);
      ctx.fillStyle = "#c9d6db";
      ctx.beginPath();
      ctx.arc(1.4, topY + 9.4, 0.45, 0, Math.PI * 2);
      ctx.arc(1.4, topY + 12.4, 0.45, 0, Math.PI * 2);
      ctx.fill();
      if (look.top === "apron") {
        rr(ctx, -SW / 2 + 1.6, topY + T * 0.32, SW - 3.2, T * 0.84, 1.6);
        paint(ctx, top, 0.7);
        ctx.strokeStyle = shade(top, -0.25);
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.moveTo(-2.4, topY + T * 0.32);
        ctx.lineTo(-1.6, topY + 0.8);
        ctx.moveTo(2.4, topY + T * 0.32);
        ctx.lineTo(1.6, topY + 0.8);
        ctx.stroke();
        rr(ctx, -2, topY + T * 0.62, 4, 2.4, 0.8);
        paint(ctx, shade(top, 0.18), 0.5);
      }
    } else {
      const kind = look.top;
      const main = kind === "safety_vest" || kind === "vest" ? shade(top, 0.62) : top;
      torsoPath(ctx, topY, SW, HW, T + 0.8, 3.2);
      paint(ctx, main, 0.9);
      torsoPath(ctx, topY, SW, HW, T + 0.8, 3.2);
      sideShadow(ctx, SW * 0.18, topY, SW, T + 2, 0.09);
      if (!away) clothesFront(ctx, g, kind, main);
    }
    if (away) return;
    chest(ctx, g, acc);
  }

  function clothesFront(ctx, g, kind, main) {
    const { top, topY, T, SW } = g;
    const bottom = topY + T + 0.8;
    if (kind === "blazer" || kind === "jacket") {
      ctx.fillStyle = kind === "blazer" ? "#f6f2ea" : shade(top, 0.25);
      ctx.beginPath();
      ctx.moveTo(-2.6, topY + 0.2);
      ctx.lineTo(2.6, topY + 0.2);
      ctx.lineTo(0, topY + 7.4);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = shade(top, -0.38);
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.moveTo(-3, topY + 0.2);
      ctx.lineTo(-0.5, topY + 7.8);
      ctx.lineTo(-0.5, bottom);
      ctx.moveTo(3, topY + 0.2);
      ctx.lineTo(0.5, topY + 7.8);
      ctx.stroke();
      if (kind === "jacket") {
        ctx.strokeStyle = shade(top, 0.35);
        ctx.lineWidth = 0.6;
        ctx.beginPath();
        ctx.moveTo(0, topY + 7.8);
        ctx.lineTo(0, bottom);
        ctx.stroke();
      }
    } else if (kind === "vest") {
      ctx.fillStyle = top;
      ctx.beginPath();
      ctx.moveTo(-SW / 2 + 1.5, topY + 1.2);
      ctx.lineTo(-1.8, topY + 1.2);
      ctx.lineTo(0, topY + 6.4);
      ctx.lineTo(1.8, topY + 1.2);
      ctx.lineTo(SW / 2 - 1.5, topY + 1.2);
      ctx.lineTo(SW / 2 - 1.9, bottom - 0.4);
      ctx.lineTo(-SW / 2 + 1.9, bottom - 0.4);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = shade(top, -0.3);
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.arc(0, topY + 8 + i * 2.6, 0.45, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (kind === "safety_vest") {
      ctx.fillStyle = "#f28a22";
      rr(ctx, -SW / 2 + 0.9, topY + 0.9, SW - 1.8, T - 0.2, 2);
      ctx.fill();
      ctx.fillStyle = "#fbf7e8";
      ctx.fillRect(-SW / 2 + 0.9, topY + T * 0.42, SW - 1.8, 1.4);
      ctx.fillRect(-SW / 2 + 0.9, topY + T * 0.7, SW - 1.8, 1.4);
      ctx.fillStyle = shade(top, 0.62);
      ctx.beginPath();
      ctx.moveTo(-2.2, topY + 0.6);
      ctx.lineTo(2.2, topY + 0.6);
      ctx.lineTo(0, topY + 4.4);
      ctx.closePath();
      ctx.fill();
    } else if (kind === "cardigan") {
      ctx.fillStyle = "#f6f1e8";
      ctx.beginPath();
      ctx.moveTo(-2.2, topY + 0.3);
      ctx.lineTo(2.2, topY + 0.3);
      ctx.lineTo(1.4, bottom);
      ctx.lineTo(-1.4, bottom);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = shade(top, -0.25);
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.arc(2.6, topY + 4 + i * 3, 0.5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.strokeStyle = shade(main, -0.18);
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(-SW / 2 + 0.9, bottom - 1.4);
      ctx.lineTo(SW / 2 - 0.9, bottom - 1.4);
      ctx.stroke();
    } else if (kind === "turtleneck") {
      rr(ctx, -3, topY - 2.2, 6, 3.4, 1.3);
      paint(ctx, shade(top, -0.12), 0.6);
    } else if (kind === "polo" || kind === "shirt") {
      ctx.fillStyle = shade(top, kind === "polo" ? 0.3 : 0.2);
      ctx.beginPath();
      ctx.moveTo(-3.2, topY - 0.4);
      ctx.lineTo(-0.2, topY + 2.9);
      ctx.lineTo(-1.2, topY + 0.6);
      ctx.closePath();
      ctx.moveTo(3.2, topY - 0.4);
      ctx.lineTo(0.2, topY + 2.9);
      ctx.lineTo(1.2, topY + 0.6);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = shade(top, -0.32);
      for (let i = 0; i < (kind === "shirt" ? 3 : 1); i++) {
        ctx.beginPath();
        ctx.arc(0, topY + 4.2 + i * 3, 0.45, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (kind === "sweater") {
      ctx.strokeStyle = shade(top, -0.2);
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.moveTo(-SW / 2 + 1, bottom - 1.6);
      ctx.lineTo(SW / 2 - 1, bottom - 1.6);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, topY - 0.2, 3, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();
    } else if (kind === "tee" || kind === "hoodie") {
      ctx.strokeStyle = shade(top, -0.25);
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.arc(0, topY - 0.4, 2.8, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();
    }
  }

  function chest(ctx, g, acc) {
    const { look, topY, T, SW } = g;
    if (acc.has("tie")) {
      ctx.fillStyle = look.accent;
      ctx.beginPath();
      ctx.moveTo(-0.9, topY + 1.4);
      ctx.lineTo(0.9, topY + 1.4);
      ctx.lineTo(1.3, topY + 8.6);
      ctx.lineTo(0, topY + 10.2);
      ctx.lineTo(-1.3, topY + 8.6);
      ctx.closePath();
      ctx.fill();
    }
    if (acc.has("bow_tie")) {
      ctx.fillStyle = look.accent;
      ctx.beginPath();
      ctx.moveTo(0, topY + 1.5);
      ctx.lineTo(-3.2, topY);
      ctx.lineTo(-3.2, topY + 3.1);
      ctx.closePath();
      ctx.moveTo(0, topY + 1.5);
      ctx.lineTo(3.2, topY);
      ctx.lineTo(3.2, topY + 3.1);
      ctx.closePath();
      ctx.fill();
      ctx.beginPath();
      ctx.arc(0, topY + 1.5, 0.8, 0, Math.PI * 2);
      ctx.fill();
    }
    if (acc.has("lanyard")) {
      ctx.strokeStyle = look.accent;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(-2.6, topY + 0.2);
      ctx.lineTo(0, topY + 7.2);
      ctx.lineTo(2.6, topY + 0.2);
      ctx.stroke();
      rr(ctx, -1.8, topY + 7, 3.6, 4, 0.6);
      paint(ctx, "#fbfaf6", 0.5, "#9aa4a8");
      ctx.fillStyle = look.accent;
      ctx.fillRect(-1.8, topY + 7, 3.6, 1.1);
    }
    if (acc.has("stethoscope")) {
      ctx.strokeStyle = "#3c4650";
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.moveTo(-3.2, topY + 0.3);
      ctx.quadraticCurveTo(-3.8, topY + 7.4, 0.5, topY + 8.8);
      ctx.moveTo(3.2, topY + 0.3);
      ctx.quadraticCurveTo(3.6, topY + 5.2, 1.6, topY + 7.8);
      ctx.stroke();
      ctx.fillStyle = "#a9b4bb";
      ctx.beginPath();
      ctx.arc(0.8, topY + 9.1, 1.2, 0, Math.PI * 2);
      ctx.fill();
    }
    if (acc.has("scarf")) {
      rr(ctx, -4, topY - 1.3, 8, 3, 1.4);
      paint(ctx, look.accent, 0.7);
      rr(ctx, 1.1, topY + 0.8, 2.3, 7.2, 1);
      paint(ctx, shade(look.accent, -0.08), 0.7);
    }
    if (acc.has("camera_strap")) {
      ctx.strokeStyle = "#2f3237";
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.moveTo(-3.4, topY + 0.5);
      ctx.lineTo(SW / 2 - 1.6, topY + T * 0.82);
      ctx.stroke();
    }
    if (acc.has("headphones")) {
      ctx.strokeStyle = look.accent;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.arc(0, topY + 0.6, 3.9, 0.12 * Math.PI, 0.88 * Math.PI);
      ctx.stroke();
      rr(ctx, -5.2, topY - 0.9, 2.4, 3, 1);
      paint(ctx, look.accent, 0.5);
      rr(ctx, 2.8, topY - 0.9, 2.4, 3, 1);
      paint(ctx, look.accent, 0.5);
    }
  }

  function backDetails(ctx, g) {
    const { look, topY, T } = g;
    if (look.coat) {
      ctx.strokeStyle = "#c6d3d8";
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(0, topY + T * 0.55);
      ctx.lineTo(0, topY + T + 3.4);
      ctx.stroke();
    }
    if (look.top === "safety_vest") {
      ctx.fillStyle = "#f28a22";
      rr(ctx, -g.SW / 2 + 0.9, topY + 0.9, g.SW - 1.8, T - 0.2, 2);
      ctx.fill();
      ctx.fillStyle = "#fbf7e8";
      ctx.fillRect(-g.SW / 2 + 0.9, topY + T * 0.5, g.SW - 1.8, 1.4);
    }
  }

  /* ---------- 头 ---------- */
  function head(ctx, g) {
    const { R, hy, skin, away, look, acc } = g;
    // 耳朵
    if (!away && !["long", "bob", "sleek_bob", "wavy"].includes(look.hair)) {
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * R * 0.95, hy + R * 0.18, R * 0.2, R * 0.26, 0, 0, Math.PI * 2);
        paint(ctx, shade(skin, -0.05), 0.7, shade(skin, -0.32));
      }
    }
    ctx.beginPath();
    ctx.ellipse(0, hy, R, R * 0.96, 0, 0, Math.PI * 2);
    paint(ctx, skin, 0.9, shade(skin, -0.34));
    if (away) {
      hairAway(ctx, g);
      headwear(ctx, g);
      return;
    }
    // 下巴一侧的影子
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(0, hy, R, R * 0.96, 0, 0, Math.PI * 2);
    ctx.clip();
    ctx.fillStyle = "rgba(160, 90, 60, 0.08)";
    ctx.beginPath();
    ctx.ellipse(R * 0.55, hy + R * 0.25, R * 0.6, R * 0.9, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
    face(ctx, g);
    hairFront(ctx, g);
    headwear(ctx, g);
    glasses(ctx, g, acc);
  }

  function face(ctx, g) {
    const { R, hy, look, acc, hair, o } = g;
    const ey = hy + R * 0.16;
    const ex = R * 0.37;
    const senior = look.age === "senior";
    const blink = !o.still && ((o.phase || 0) * 0.9) % 7 < 0.12;
    // 眉毛
    ctx.strokeStyle = senior ? shade(hair, -0.15) : shade(hair, 0.05);
    ctx.lineWidth = Math.max(0.55, R * (senior ? 0.1 : 0.08));
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(-ex - R * 0.15, ey - R * 0.3);
    ctx.quadraticCurveTo(-ex, ey - R * 0.37, -ex + R * 0.15, ey - R * 0.31);
    ctx.moveTo(ex - R * 0.15, ey - R * 0.31);
    ctx.quadraticCurveTo(ex, ey - R * 0.37, ex + R * 0.15, ey - R * 0.3);
    ctx.stroke();
    // 眼睛
    if (blink) {
      ctx.strokeStyle = INK;
      ctx.lineWidth = Math.max(0.6, R * 0.07);
      ctx.beginPath();
      ctx.moveTo(-ex - R * 0.1, ey);
      ctx.lineTo(-ex + R * 0.1, ey);
      ctx.moveTo(ex - R * 0.1, ey);
      ctx.lineTo(ex + R * 0.1, ey);
      ctx.stroke();
    } else {
      ctx.fillStyle = INK;
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * ex, ey, R * (senior ? 0.1 : 0.115), R * (senior ? 0.12 : 0.155), 0, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.arc(side * ex + R * 0.04, ey - R * 0.06, R * 0.045, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    // 腮红
    if (!acc.has("beard")) {
      ctx.fillStyle = look.age === "young" ? "rgba(240, 120, 110, 0.32)" : "rgba(225, 120, 100, 0.18)";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * R * 0.58, hy + R * 0.44, R * 0.17, R * 0.1, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    // 嘴
    ctx.strokeStyle = "rgba(120, 55, 45, 0.85)";
    ctx.lineWidth = Math.max(0.55, R * 0.075);
    ctx.beginPath();
    if (senior) {
      ctx.moveTo(-R * 0.17, hy + R * 0.56);
      ctx.quadraticCurveTo(0, hy + R * 0.64, R * 0.17, hy + R * 0.56);
    } else if (look.age === "young") {
      ctx.arc(0, hy + R * 0.4, R * 0.2, 0.18 * Math.PI, 0.82 * Math.PI);
    } else {
      ctx.moveTo(-R * 0.16, hy + R * 0.55);
      ctx.quadraticCurveTo(0, hy + R * 0.66, R * 0.16, hy + R * 0.55);
    }
    ctx.stroke();
    // 胡子
    if (acc.has("mustache") || acc.has("beard") || acc.has("goatee")) {
      const beard = look.age === "senior" || look.hair === "bald" ? "#ebe8e3" : shade(hair, 0.05);
      if (acc.has("beard")) {
        ctx.beginPath();
        ctx.moveTo(-R * 0.82, hy + R * 0.18);
        ctx.quadraticCurveTo(-R * 0.75, hy + R * 1.08, 0, hy + R * 1.12);
        ctx.quadraticCurveTo(R * 0.75, hy + R * 1.08, R * 0.82, hy + R * 0.18);
        ctx.quadraticCurveTo(R * 0.4, hy + R * 0.62, 0, hy + R * 0.6);
        ctx.quadraticCurveTo(-R * 0.4, hy + R * 0.62, -R * 0.82, hy + R * 0.18);
        paint(ctx, beard, 0.6, shade(beard, -0.25));
      }
      if (acc.has("mustache") || acc.has("beard")) {
        ctx.beginPath();
        ctx.moveTo(0, hy + R * 0.42);
        ctx.quadraticCurveTo(-R * 0.3, hy + R * 0.36, -R * 0.46, hy + R * 0.56);
        ctx.quadraticCurveTo(-R * 0.2, hy + R * 0.52, 0, hy + R * 0.5);
        ctx.quadraticCurveTo(R * 0.2, hy + R * 0.52, R * 0.46, hy + R * 0.56);
        ctx.quadraticCurveTo(R * 0.3, hy + R * 0.36, 0, hy + R * 0.42);
        paint(ctx, beard, 0.5, shade(beard, -0.3));
      }
      if (acc.has("goatee")) {
        ctx.beginPath();
        ctx.moveTo(-R * 0.18, hy + R * 0.7);
        ctx.quadraticCurveTo(0, hy + R * 1.18, R * 0.18, hy + R * 0.7);
        ctx.closePath();
        paint(ctx, beard, 0.5, shade(beard, -0.3));
      }
    }
    if (acc.has("earrings")) {
      ctx.fillStyle = "#f6f0e2";
      ctx.strokeStyle = "#b8a983";
      ctx.lineWidth = 0.4;
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.arc(side * R * 0.97, hy + R * 0.48, R * 0.12, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    }
  }

  function glasses(ctx, g, acc) {
    const { R, hy } = g;
    const ey = hy + R * 0.16;
    if (acc.has("round_glasses")) {
      ctx.strokeStyle = "#3a3330";
      ctx.lineWidth = Math.max(0.6, R * 0.075);
      ctx.fillStyle = "rgba(220, 240, 250, 0.25)";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.arc(side * R * 0.38, ey, R * 0.29, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
      ctx.beginPath();
      ctx.moveTo(-R * 0.1, ey - R * 0.04);
      ctx.quadraticCurveTo(0, ey - R * 0.12, R * 0.1, ey - R * 0.04);
      ctx.moveTo(-R * 0.67, ey - R * 0.05);
      ctx.lineTo(-R * 0.95, ey - R * 0.12);
      ctx.moveTo(R * 0.67, ey - R * 0.05);
      ctx.lineTo(R * 0.95, ey - R * 0.12);
      ctx.stroke();
    }
    if (acc.has("half_glasses")) {
      ctx.strokeStyle = "#2f2a28";
      ctx.lineWidth = Math.max(0.7, R * 0.09);
      ctx.beginPath();
      for (const side of [-1, 1]) {
        ctx.moveTo(side * R * 0.66, ey + R * 0.02);
        ctx.quadraticCurveTo(side * R * 0.4, ey + R * 0.32, side * R * 0.12, ey + R * 0.02);
      }
      ctx.moveTo(-R * 0.66, ey + R * 0.02);
      ctx.lineTo(-R * 0.12, ey + R * 0.02);
      ctx.moveTo(R * 0.12, ey + R * 0.02);
      ctx.lineTo(R * 0.66, ey + R * 0.02);
      ctx.stroke();
    }
  }

  /* ---------- 头发 ---------- */
  // 头顶的发片：外沿包住头顶，前沿是刘海
  function cap(ctx, g, opt = {}) {
    const { R, hy, hair } = g;
    const vol = opt.vol ?? 0.7;
    const drop = opt.drop ?? 0.08;
    const fringe = opt.fringe ?? 0.3;
    const lift = opt.lift ?? 0;
    ctx.beginPath();
    ctx.arc(0, hy - lift, R + vol, Math.PI * (1 - drop), Math.PI * (2 + drop));
    const yR = hy - lift + Math.sin(Math.PI * drop) * (R + vol);
    if (opt.part === "side") {
      ctx.quadraticCurveTo(R * 0.85, hy - R * fringe * 0.5, R * 0.35, hy - R * fringe);
      ctx.quadraticCurveTo(-R * 0.2, hy - R * (fringe + 0.25), -R * 0.55, hy - R * (fringe - 0.05));
      ctx.quadraticCurveTo(-R * 0.85, hy - R * 0.1, -(R + vol) * Math.cos(Math.PI * drop), yR);
    } else if (opt.part === "center") {
      ctx.quadraticCurveTo(R * 0.7, hy - R * 0.1, R * 0.12, hy - R * (fringe + 0.3));
      ctx.lineTo(-R * 0.12, hy - R * (fringe + 0.3));
      ctx.quadraticCurveTo(-R * 0.7, hy - R * 0.1, -(R + vol) * Math.cos(Math.PI * drop), yR);
    } else if (opt.part === "back") {
      ctx.quadraticCurveTo(R * 0.6, hy - R * (fringe + 0.2), 0, hy - R * (fringe + 0.32));
      ctx.quadraticCurveTo(-R * 0.6, hy - R * (fringe + 0.2), -(R + vol) * Math.cos(Math.PI * drop), yR);
    } else {
      // 齐刘海带一点弧度和小尖
      const n = opt.tips ?? 4;
      const xs = [];
      for (let i = 0; i <= n; i++) xs.push(R * 0.95 - (i * R * 1.9) / n);
      ctx.lineTo(xs[0], hy - R * fringe + R * 0.05);
      for (let i = 1; i <= n; i++) {
        const mid = (xs[i - 1] + xs[i]) / 2;
        ctx.quadraticCurveTo(mid, hy - R * (fringe - 0.16), xs[i], hy - R * fringe + R * 0.05);
      }
      ctx.lineTo(-(R + vol) * Math.cos(Math.PI * drop), yR);
    }
    ctx.closePath();
    paint(ctx, hair, 0.9, shade(hair, light(hair) ? -0.3 : -0.45));
    if (opt.shine !== false) shine(ctx, g, lift);
  }
  function shine(ctx, g, lift = 0) {
    const { R, hy, hair } = g;
    ctx.strokeStyle = light(hair) ? "rgba(255, 255, 255, 0.55)" : "rgba(255, 255, 255, 0.28)";
    ctx.lineWidth = Math.max(0.6, R * 0.12);
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.arc(0, hy - lift, R * 0.72, Math.PI * 1.22, Math.PI * 1.42);
    ctx.stroke();
  }
  function lock(ctx, g, x, y, w, h, r) {
    rr(ctx, x, y, w, h, r);
    paint(ctx, g.hair, 0.8, shade(g.hair, light(g.hair) ? -0.3 : -0.45));
  }

  function backHair(ctx, g) {
    const { look, R, hy, hair } = g;
    const h = look.hair;
    const edge = shade(hair, light(hair) ? -0.3 : -0.45);
    ctx.fillStyle = hair;
    if (h === "long") {
      rr(ctx, -R - 1.1, hy - R * 0.6, R * 2 + 2.2, R * 2.75, R * 0.9);
      paint(ctx, hair, 0.9, edge);
    } else if (h === "wavy") {
      ctx.beginPath();
      ctx.moveTo(-R - 1.2, hy - R * 0.4);
      ctx.lineTo(-R - 1.6, hy + R * 0.9);
      ctx.quadraticCurveTo(-R - 0.4, hy + R * 1.35, -R * 0.6, hy + R * 1.2);
      ctx.lineTo(R * 0.6, hy + R * 1.2);
      ctx.quadraticCurveTo(R + 0.4, hy + R * 1.35, R + 1.6, hy + R * 0.9);
      ctx.lineTo(R + 1.2, hy - R * 0.4);
      ctx.closePath();
      paint(ctx, hair, 0.9, edge);
    } else if (h === "bob" || h === "sleek_bob") {
      rr(ctx, -R - 1, hy - R * 0.5, R * 2 + 2, R * 1.45, R * 0.6);
      paint(ctx, hair, 0.9, edge);
    } else if (h === "low_bun") {
      ctx.beginPath();
      ctx.arc(R * 0.62, hy + R * 0.62, R * 0.5, 0, Math.PI * 2);
      paint(ctx, hair, 0.8, edge);
    } else if (h === "high_ponytail") {
      ctx.beginPath();
      ctx.moveTo(R * 0.5, hy - R * 0.9);
      ctx.quadraticCurveTo(R * 1.9, hy - R * 0.6, R * 1.35, hy + R * 0.9);
      ctx.quadraticCurveTo(R * 1.1, hy - R * 0.1, R * 0.4, hy - R * 0.4);
      ctx.closePath();
      paint(ctx, hair, 0.8, edge);
    } else if (h === "ponytail") {
      ctx.beginPath();
      ctx.ellipse(R * 0.82, hy + R * 0.95, R * 0.3, R * 0.85, 0.25, 0, Math.PI * 2);
      paint(ctx, hair, 0.8, edge);
    } else if (h === "pigtails") {
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * R * 1.12, hy + R * 0.55, R * 0.33, R * 0.72, side * 0.32, 0, Math.PI * 2);
        paint(ctx, hair, 0.8, edge);
      }
    }
  }

  function hairFront(ctx, g) {
    const { look, R, hy, hair } = g;
    const h = look.hair;
    const edge = shade(hair, light(hair) ? -0.3 : -0.45);
    if (h === "bald") {
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * R * 0.9, hy - R * 0.02, R * 0.24, R * 0.4, 0, 0, Math.PI * 2);
        paint(ctx, hair, 0.6, edge);
      }
      ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
      ctx.beginPath();
      ctx.ellipse(-R * 0.28, hy - R * 0.6, R * 0.3, R * 0.15, -0.4, 0, Math.PI * 2);
      ctx.fill();
      return;
    }
    if (h === "buzz" || h === "short_gray") {
      cap(ctx, g, { vol: h === "buzz" ? 0.35 : 0.6, drop: 0.04, fringe: h === "buzz" ? 0.62 : 0.5, part: h === "buzz" ? "back" : "side", shine: h !== "buzz" });
      return;
    }
    if (h === "slick_back") {
      cap(ctx, g, { vol: 0.6, drop: 0.05, fringe: 0.55, part: "back" });
      ctx.strokeStyle = shade(hair, light(hair) ? -0.18 : 0.18);
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      for (const x of [-0.35, 0, 0.35]) {
        ctx.moveTo(R * x, hy - R * 0.62);
        ctx.quadraticCurveTo(R * (x * 1.2), hy - R * 0.95, R * x * 0.8, hy - R * 1.05);
      }
      ctx.stroke();
      return;
    }
    if (h === "spiky") {
      ctx.beginPath();
      const spikes = [
        [-0.95, -0.2],
        [-0.85, -1.2],
        [-0.5, -0.75],
        [-0.3, -1.55],
        [0.05, -0.9],
        [0.3, -1.6],
        [0.55, -0.85],
        [0.9, -1.25],
        [0.98, -0.2],
      ];
      ctx.moveTo(-R * 1.05, hy - R * 0.05);
      for (const [x, y] of spikes) ctx.lineTo(R * x, hy + R * y);
      ctx.lineTo(R * 1.05, hy - R * 0.05);
      ctx.quadraticCurveTo(R * 0.7, hy - R * 0.5, R * 0.45, hy - R * 0.32);
      ctx.lineTo(R * 0.2, hy - R * 0.55);
      ctx.lineTo(-R * 0.05, hy - R * 0.3);
      ctx.lineTo(-R * 0.35, hy - R * 0.55);
      ctx.lineTo(-R * 0.6, hy - R * 0.3);
      ctx.quadraticCurveTo(-R * 0.8, hy - R * 0.45, -R * 1.05, hy - R * 0.05);
      ctx.closePath();
      paint(ctx, hair, 0.9, edge);
      shine(ctx, g, R * 0.15);
      return;
    }
    if (h === "bun" || h === "manbun") {
      const big = h === "bun";
      ctx.beginPath();
      ctx.arc(R * (big ? 0.05 : -0.05), hy - R * (big ? 1.12 : 1.05), R * (big ? 0.5 : 0.38), 0, Math.PI * 2);
      paint(ctx, hair, 0.8, edge);
      cap(ctx, g, { vol: 0.6, fringe: big ? 0.38 : 0.5, part: big ? "center" : "back" });
      return;
    }
    if (h === "bob" || h === "sleek_bob") {
      cap(ctx, g, { vol: 1, drop: 0.12, fringe: h === "bob" ? 0.22 : 0.3, part: h === "bob" ? undefined : "side", tips: 5 });
      lock(ctx, g, -R - 1, hy - R * 0.3, R * 0.5, R * 1.32, R * 0.25);
      lock(ctx, g, R + 1 - R * 0.5, hy - R * 0.3, R * 0.5, R * 1.32, R * 0.25);
      if (h === "sleek_bob") shine(ctx, g);
      grayStreak(ctx, g);
      return;
    }
    if (h === "long" || h === "wavy") {
      cap(ctx, g, { vol: 1, drop: 0.1, fringe: 0.3, part: h === "long" ? "center" : "side" });
      const len = h === "long" ? 1.9 : 1.4;
      lock(ctx, g, -R - 1.1, hy - R * 0.2, R * 0.5, R * len, R * 0.25);
      lock(ctx, g, R + 1.1 - R * 0.5, hy - R * 0.2, R * 0.5, R * len, R * 0.25);
      grayStreak(ctx, g);
      return;
    }
    if (h === "pigtails") {
      cap(ctx, g, { vol: 0.8, fringe: 0.26, tips: 5 });
      for (const side of [-1, 1]) {
        ctx.fillStyle = g.look.accent;
        ctx.beginPath();
        ctx.arc(side * R * 1.0, hy + R * 0.02, R * 0.16, 0, Math.PI * 2);
        ctx.fill();
      }
      return;
    }
    if (h === "undercut") {
      cap(ctx, g, { vol: 0.3, drop: 0.03, fringe: 0.6, part: "back", shine: false });
      ctx.beginPath();
      ctx.moveTo(-R * 0.95, hy - R * 0.45);
      ctx.quadraticCurveTo(-R * 0.6, hy - R * 1.55, R * 0.4, hy - R * 1.32);
      ctx.quadraticCurveTo(R * 0.95, hy - R * 1.1, R * 0.85, hy - R * 0.6);
      ctx.quadraticCurveTo(R * 0.2, hy - R * 0.9, -R * 0.35, hy - R * 0.38);
      ctx.closePath();
      paint(ctx, hair, 0.9, edge);
      shine(ctx, g, R * 0.25);
      return;
    }
    if (h === "high_ponytail" || h === "ponytail" || h === "low_bun") {
      cap(ctx, g, { vol: 0.65, fringe: h === "high_ponytail" ? 0.42 : 0.48, part: h === "high_ponytail" ? "side" : "back" });
      if (h === "high_ponytail") {
        ctx.fillStyle = g.look.accent;
        ctx.beginPath();
        ctx.arc(R * 0.62, hy - R * 0.86, R * 0.15, 0, Math.PI * 2);
        ctx.fill();
      }
      grayStreak(ctx, g);
      return;
    }
    if (h === "side_part") {
      cap(ctx, g, { vol: 0.8, fringe: 0.4, part: "side" });
      return;
    }
    if (h === "pixie") {
      cap(ctx, g, { vol: 0.55, fringe: 0.3, part: "side" });
      return;
    }
    cap(ctx, g, { vol: 0.7, fringe: 0.35 });
  }
  function grayStreak(ctx, g) {
    if (!g.acc.has("gray_streak")) return;
    const { R, hy } = g;
    ctx.fillStyle = "rgba(236, 236, 236, 0.92)";
    ctx.beginPath();
    ctx.ellipse(-R * 0.38, hy - R * 0.7, R * 0.16, R * 0.42, 0.5, 0, Math.PI * 2);
    ctx.fill();
  }

  function hairAway(ctx, g) {
    const { look, R, hy, hair } = g;
    const h = look.hair;
    const edge = shade(hair, light(hair) ? -0.3 : -0.45);
    if (h === "bald") {
      ctx.beginPath();
      ctx.arc(0, hy + R * 0.2, R * 0.92, 0.08 * Math.PI, 0.92 * Math.PI);
      paint(ctx, hair, 0.6, edge);
      return;
    }
    ctx.beginPath();
    ctx.ellipse(0, hy - R * 0.02, R + (h === "buzz" ? 0.3 : 0.7), R * 0.98 + 0.5, 0, 0, Math.PI * 2);
    paint(ctx, hair, 0.9, edge);
    if (h === "long" || h === "wavy" || h === "bob" || h === "sleek_bob") {
      const len = h === "long" ? 1.9 : h === "wavy" ? 1.35 : 0.95;
      rr(ctx, -R - 0.9, hy, R * 2 + 1.8, R * len, R * 0.5);
      paint(ctx, hair, 0.9, edge);
    }
    if (h === "bun" || h === "manbun" || h === "low_bun") {
      ctx.beginPath();
      ctx.arc(0, h === "low_bun" ? hy + R * 0.55 : hy - R * 0.98, R * 0.48, 0, Math.PI * 2);
      paint(ctx, hair, 0.8, edge);
    }
    if (h === "high_ponytail" || h === "ponytail") {
      ctx.beginPath();
      ctx.ellipse(0, hy + (h === "ponytail" ? R * 1.05 : R * 0.45), R * 0.34, R * 0.95, 0, 0, Math.PI * 2);
      paint(ctx, hair, 0.8, edge);
    }
    if (h === "pigtails") {
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * R * 1.1, hy + R * 0.5, R * 0.32, R * 0.7, side * 0.3, 0, Math.PI * 2);
        paint(ctx, hair, 0.8, edge);
      }
    }
    if (h === "spiky") {
      ctx.beginPath();
      for (const x of [-0.6, -0.2, 0.2, 0.6]) {
        ctx.moveTo(R * (x - 0.22), hy - R * 0.8);
        ctx.lineTo(R * x, hy - R * 1.45);
        ctx.lineTo(R * (x + 0.22), hy - R * 0.8);
      }
      paint(ctx, hair, 0.8, edge);
    }
  }

  function headwear(ctx, g) {
    const { R, hy, look, acc, away } = g;
    if (acc.has("hard_hat")) {
      const c = look.accent || "#f4f4f2";
      ctx.beginPath();
      ctx.arc(0, hy - R * 0.18, R * 1.06, Math.PI, Math.PI * 2);
      ctx.closePath();
      paint(ctx, c, 0.9, shade(c, -0.35));
      rr(ctx, -R * 1.32, hy - R * 0.26, R * 2.64, R * 0.26, R * 0.1);
      paint(ctx, shade(c, -0.06), 0.7, shade(c, -0.35));
      ctx.fillStyle = shade(c, -0.14);
      ctx.fillRect(-R * 0.12, hy - R * 1.2, R * 0.24, R * 0.98);
    }
    if (acc.has("bandana")) {
      ctx.beginPath();
      ctx.arc(0, hy - R * 0.08, R * 1.04, Math.PI * 1.06, Math.PI * 1.94);
      ctx.quadraticCurveTo(0, hy - R * 0.55, -R * 0.98, hy - R * 0.36);
      ctx.closePath();
      paint(ctx, look.accent, 0.8);
      ctx.fillStyle = "rgba(255,255,255,0.7)";
      for (const [x, y] of [[-0.4, -0.75], [0.15, -0.88], [0.6, -0.62]]) {
        ctx.beginPath();
        ctx.arc(R * x, hy + R * y, R * 0.07, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    if (acc.has("catear_headphones")) {
      ctx.strokeStyle = look.accent;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(0, hy, R + 1, Math.PI * 1.05, Math.PI * 1.95);
      ctx.stroke();
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(side * R * 0.28, hy - R * 0.98);
        ctx.lineTo(side * R * 0.75, hy - R * 1.72);
        ctx.lineTo(side * R * 1.0, hy - R * 0.72);
        ctx.closePath();
        paint(ctx, look.accent, 0.7);
        ctx.fillStyle = "#fff4f8";
        ctx.beginPath();
        ctx.moveTo(side * R * 0.45, hy - R * 1.0);
        ctx.lineTo(side * R * 0.74, hy - R * 1.45);
        ctx.lineTo(side * R * 0.88, hy - R * 0.9);
        ctx.closePath();
        ctx.fill();
        if (!away) {
          rr(ctx, side * (R + 0.5) - 1.5, hy - R * 0.25, 3, R * 0.8, 1.2);
          paint(ctx, look.accent, 0.7);
        }
      }
    }
    if (acc.has("goggles") && !away) {
      rr(ctx, -R * 1.02, hy - R * 0.74, R * 2.04, R * 0.32, R * 0.12);
      paint(ctx, look.accent, 0.6);
      for (const side of [-1, 1]) {
        rr(ctx, side * R * 0.47 - R * 0.33, hy - R * 0.86, R * 0.66, R * 0.52, R * 0.2);
        paint(ctx, "#bfe7f2", 0.7, "#3b4a52");
      }
    }
    if (acc.has("hairclips") && !away) {
      ctx.fillStyle = look.accent;
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.ellipse(side * R * 0.62, hy - R * 0.6, R * 0.2, R * 0.12, side * 0.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  /* ---------- 道具 ---------- */
  function prop(ctx, look, y, o) {
    const p = look.prop;
    ctx.save();
    if (p === "flask") {
      ctx.beginPath();
      ctx.moveTo(-1, y - 1.4);
      ctx.lineTo(1, y - 1.4);
      ctx.lineTo(3.2, y + 4.6);
      ctx.lineTo(-3.2, y + 4.6);
      ctx.closePath();
      paint(ctx, "rgba(205, 238, 247, 0.95)", 0.6, "#6c97a5");
      ctx.fillStyle = "#ff9b55";
      ctx.fillRect(-2.6, y + 2.4, 5.2, 2);
    } else if (p === "tray") {
      rr(ctx, -4.2, y, 8.4, 1.6, 0.6);
      paint(ctx, "#d7dde0", 0.5);
      ctx.fillStyle = "#fff8ec";
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        ctx.arc(-2.6 + i * 2.6, y - 0.4, 0.95, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (p === "notebook" || p === "clipboard") {
      rr(ctx, -2.8, y - 1.2, 5.6, 6.8, 0.6);
      paint(ctx, p === "notebook" ? "#3f6e8c" : "#c18f5c", 0.6);
      ctx.fillStyle = "#fbf9f3";
      ctx.fillRect(-2, y - 0.3, 4, 5);
      if (p === "clipboard") {
        ctx.fillStyle = "#6b6f75";
        ctx.fillRect(-1.1, y - 1.9, 2.2, 1.3);
      } else {
        ctx.fillStyle = "#c9d3d8";
        ctx.fillRect(-1.4, y + 0.8, 2.8, 0.5);
        ctx.fillRect(-1.4, y + 2.2, 2.8, 0.5);
      }
    } else if (p === "tablet" || p === "laptop") {
      rr(ctx, -3.2, y - 1.2, 6.4, p === "laptop" ? 4.2 : 7.2, 0.8);
      paint(ctx, "#2f3a44", 0.5);
      ctx.fillStyle = "#93d9ea";
      ctx.fillRect(-2.5, y - 0.5, 5, p === "laptop" ? 2.8 : 5.8);
    } else if (p === "pipette" || p === "pen" || p === "pencil" || p === "red_pen") {
      ctx.strokeStyle =
        p === "red_pen" ? "#c0392b" : p === "pencil" ? "#e2b23c" : p === "pipette" ? "#eef3f5" : "#2c2c2c";
      ctx.lineWidth = p === "pipette" ? 1.6 : 1.1;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(0, y - 3.4);
      ctx.lineTo(0.6, y + 4);
      ctx.stroke();
      if (p === "pipette") {
        ctx.fillStyle = "#7fb8d8";
        ctx.fillRect(-1, y - 5, 2, 2.2);
      }
    } else if (p === "thermos") {
      rr(ctx, -1.5, y - 3.2, 3, 7.4, 1);
      paint(ctx, "#56606a", 0.5);
      ctx.fillStyle = "#9aa6ae";
      ctx.fillRect(-1.5, y - 3.2, 3, 1.2);
    } else if (p === "teacup") {
      rr(ctx, -2, y - 0.6, 4, 2.8, 1);
      paint(ctx, "#f6f2ea", 0.5, "#b7aa94");
      ctx.fillStyle = "#93bf80";
      ctx.fillRect(-1.6, y - 0.6, 3.2, 0.8);
    } else if (p === "camera") {
      rr(ctx, -3, y - 1.2, 6, 3.8, 0.8);
      paint(ctx, "#26282c", 0.4);
      ctx.fillStyle = "#7f93a3";
      ctx.beginPath();
      ctx.arc(0, y + 0.7, 1.25, 0, Math.PI * 2);
      ctx.fill();
    } else if (p === "model") {
      const r = (o.phase || 0) * 1.5;
      const pts = [0, 1, 2].map((i) => [
        Math.cos(r + (i * 2 * Math.PI) / 3) * 2.5,
        y + 1 + Math.sin(r + (i * 2 * Math.PI) / 3) * 1.7,
      ]);
      ctx.strokeStyle = "#8a8f95";
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      ctx.lineTo(pts[1][0], pts[1][1]);
      ctx.lineTo(pts[2][0], pts[2][1]);
      ctx.closePath();
      ctx.stroke();
      ["#e04f4f", "#3d7fd1", "#f6f6f6"].forEach((col, i) => {
        ctx.beginPath();
        ctx.arc(pts[i][0], pts[i][1], 1.15, 0, Math.PI * 2);
        paint(ctx, col, 0.4);
      });
    } else if (p === "sample_box") {
      rr(ctx, -2.4, y - 0.6, 4.8, 3.2, 0.5);
      paint(ctx, look.accent, 0.5);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(-1.7, y, 3.4, 0.8);
    } else if (p === "walkie") {
      rr(ctx, -1.4, y - 2.2, 2.8, 5.2, 0.6);
      paint(ctx, "#2a2c30", 0.4);
      ctx.fillRect(0.6, y - 4.6, 0.7, 2.6);
      ctx.fillStyle = "#7fd27a";
      ctx.fillRect(-0.8, y - 1.4, 1.6, 0.8);
    }
    ctx.restore();
  }

  /* ---------- 头像 ---------- */
  const waitingPortraits = new WeakSet();
  function portrait(target, look, opts = {}) {
    if (!target || !look) return;
    const c2 = target.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    const w = target.clientWidth || 44,
      hgt = target.clientHeight || w;
    target.width = Math.round(w * dpr);
    target.height = Math.round(hgt * dpr);
    c2.setTransform(dpr, 0, 0, dpr, 0, 0);
    c2.clearRect(0, 0, w, hgt);
    const art = look.art && ART();
    const img = art && art.image(look.art, "portrait");
    if (img) {
      // 半身立绘 200×232：小头像取头和肩，竖长或「全身」取景多给身体
      const tall = opts.full || hgt > w * 1.15;
      const sw = tall ? 184 : 144;
      const sh = Math.min(232 - 8, (sw * hgt) / w);
      const sx = (200 - sw) / 2;
      const sy = tall ? 8 : 14;
      const r = art.RES || 1;
      c2.drawImage(img, sx * r, sy * r, sw * r, sh * r, 0, 0, w, hgt);
      return;
    }
    if (art && !waitingPortraits.has(target)) {
      waitingPortraits.add(target);
      art.whenReady(look.art, "portrait", () => {
        waitingPortraits.delete(target);
        portrait(target, look, opts);
      });
    }
    const D = dims(look);
    // 取景：从头顶（留出发髻、帽子、猫耳）到胸口或腰
    const top = -D.L - D.T - D.R * 2.95;
    const bottom = opts.full ? 0 : -D.L - D.T * (hgt > w * 1.15 ? 0.05 : 0.3);
    const scale = Math.min((hgt * 0.94) / (bottom - top), (w * 0.98) / (D.SW + D.R * 2.6));
    c2.save();
    c2.translate(w / 2, hgt * 0.04 - top * scale);
    c2.scale(scale, scale);
    drawPerson(c2, look, { x: 0, y: 0, still: true, noShadow: !opts.full });
    c2.restore();
  }

  const api = { drawPerson, dims, pose, height, portrait, shade };
  root.DrugstoryFigures = api;
  if (typeof module !== "undefined") module.exports = api;
})(typeof window === "undefined" ? globalThis : window);
