/* Pure projection of the public API. This file contains no simulation rules. */
(function (root) {
  const ROOMS = {
    room_chem: "lab",
    room_proc: "lab",
    room_tox: "qc",
    room_clinical: "clinic",
    room_bio: "bio",
    room_academy: "academy",
  };
  function world(s, content) {
    const level = s.facility.level;
    const rooms = {
      lab: { built: true, level: 1 },
      qc: { built: true, level: 1 },
      clinic: { built: true, level: 1 },
      bio: { built: level >= 1, level: 1 },
      academy: { built: level >= 2, level: 1 },
      hall: { built: level >= 3, level: 1 },
    };
    for (const r of s.equipment)
      rooms[ROOMS[r.id]].level = Math.max(
        rooms[ROOMS[r.id]].level,
        r.level + 1,
      );
    const locate = (id) => {
      const room = ROOMS[id] || "clinic";
      return rooms[room]?.built ? room : room === "bio" ? "lab" : "clinic";
    };
    const heroes = s.heroes.map((h) => ({
      ...h,
      look: { ...h.look },
      mode: h.activity,
    }));
    const assignments = Object.fromEntries(
      heroes.map((h) => [
        h.id,
        {
          mode: h.activity,
          room: locate(h.room),
          role: h.profession,
          members: h.members,
          project:
            s.projects.find(
              (p) =>
                p.team.includes(h.id) &&
                ["running", "screening", "checkpoint"].includes(p.status),
            )?.id || h.busy,
        },
      ]),
    );
    const boards = {};
    for (const p of s.projects.filter((p) =>
      ["running", "checkpoint"].includes(p.status),
    )) {
      const readings = p.readings.filter(
        (r) => r.stage === p.key && r.candidate === p.chosen,
      );
      const room = locate(p.scene.room);
      if (!readings.length) continue;
      const limits = p.scene.limits;
      for (const stat of Object.keys(readings[0].values)) {
        if (!(stat in limits)) continue;
        (boards[room] ||= []).push({
          title: p.name,
          batches: 4,
          limit: limits[stat] || 0,
          readings: readings.map((r) => r.values[stat]),
        });
      }
    }
    return {
      heroes,
      assignments,
      rooms,
      equipment: Object.fromEntries(s.equipment.map((r) => [r.id, r.level])),
      boards,
      facility: level,
      cro: s.projects.some((p) => p.scene.executor === "cro"),
      locate,
    };
  }
  function blocked(s) {
    return s.game_over || s.pending > 0;
  }
  root.DrugstoryWorld = { world, blocked, ROOMS };
  if (typeof module !== "undefined") module.exports = root.DrugstoryWorld;
})(typeof window === "undefined" ? globalThis : window);
