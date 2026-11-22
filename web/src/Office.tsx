import { useEffect, useRef, useState } from "react";
import type { Agent } from "./types";
import type { Facing } from "./pixels";
import { character, room, cat, homes, WORLD_W, WORLD_H } from "./pixels";
export function Avatar({ agent, size = 36 }: { agent: Agent; size?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current?.getContext("2d");
    if (!c) return;
    c.clearRect(0, 0, 32, 40);
    character(c, 16, 35, agent.color, agent.id);
  }, [agent]);
  return (
    <canvas
      className="avatar"
      width={32}
      height={40}
      ref={ref}
      style={{ width: size, height: size * 1.25 }}
      aria-hidden="true"
    />
  );
}
type Point = { x: number; y: number };
type Walk = { x: number; y: number; distance: number; facing: Facing };
const laneXs = [248, 365, 595, 825, 980];

function walkToDesk(home: Point, index: number) {
  const lane = laneXs[index] ?? home.x;
  // Cross the aisle via gaps between benches, plants and server racks.
  return [
    home,
    { x: home.x, y: 286 },
    { x: lane, y: 286 },
    { x: lane, y: 385 },
    { x: lane + (index % 2 ? -42 : 42), y: 385 },
  ];
}

function pointOnPath(points: Point[], distance: number): Walk {
  let left = distance;
  for (let i = 1; i < points.length; i++) {
    const from = points[i - 1],
      to = points[i];
    const dx = to.x - from.x,
      dy = to.y - from.y;
    const length = Math.hypot(dx, dy);
    if (!length) continue;
    if (left <= length)
      return {
        x: from.x + (dx * left) / length,
        y: from.y + (dy * left) / length,
        distance,
        facing: dx > 0 ? "right" : dx < 0 ? "left" : dy > 0 ? "down" : "up",
      };
    left -= length;
  }
  return { ...points.at(-1)!, distance, facing: "down" };
}

export default function Office({
  agents,
  selected,
  onSelect,
  paused,
  grid,
  zoom,
}: {
  agents: Agent[];
  selected: string | null;
  onSelect: (id: string) => void;
  paused: boolean;
  grid: boolean;
  zoom: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const hit = useRef<
    { id: string; x: number; y: number; rx: number; ry: number }[]
  >([]);
  const camera = useRef({ x: 0, y: 0 });
  const drag = useRef<{
    x: number;
    y: number;
    cx: number;
    cy: number;
    moved: boolean;
  } | null>(null);
  const sceneTime = useRef(0);
  const walks = useRef(new Map<string, Walk>());
  const scenery = useRef<{ canvas: HTMLCanvasElement; key: string } | null>(
    null,
  );
  const [tip, setTip] = useState<string | null>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const c = canvas.getContext("2d");
    if (!c) return;
    let frame = 0,
      last = performance.now(),
      time = sceneTime.current;
    const render = (now: number) => {
      const delta = paused ? 0 : Math.min((now - last) / 1000, 0.05);
      time += delta;
      last = now;
      sceneTime.current = time;
      const rect = canvas.getBoundingClientRect(),
        dpr = window.devicePixelRatio || 1;
      const w = Math.round(rect.width * dpr),
        h = Math.round(rect.height * dpr);
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      c.setTransform(1, 0, 0, 1, 0, 0);
      c.clearRect(0, 0, w, h);
      c.imageSmoothingEnabled = false;
      const scale =
        Math.max(Math.min(w / WORLD_W, h / WORLD_H), 0.65 * dpr) * zoom;
      const mx = Math.max(0, (WORLD_W * scale - w) / 2),
        my = Math.max(0, (WORLD_H * scale - h) / 2);
      camera.current.x = Math.max(
        -mx / dpr,
        Math.min(mx / dpr, camera.current.x),
      );
      camera.current.y = Math.max(
        -my / dpr,
        Math.min(my / dpr, camera.current.y),
      );
      const ox = (w - WORLD_W * scale) / 2 + camera.current.x * dpr,
        oy = (h - WORLD_H * scale) / 2 + camera.current.y * dpr;
      c.translate(Math.round(ox), Math.round(oy));
      c.scale(scale, scale);
      const working = agents
        .filter((a) => a.status === "working")
        .map((a) => a.id);
      const roomKey = [grid, ...working].join(",");
      if (scenery.current?.key !== roomKey) {
        const floor = document.createElement("canvas");
        floor.width = WORLD_W;
        floor.height = WORLD_H;
        const floorContext = floor.getContext("2d");
        if (floorContext) room(floorContext, grid, new Set(working));
        scenery.current = { canvas: floor, key: roomKey };
      }
      c.drawImage(scenery.current.canvas, 0, 0);
      hit.current = [];
      const positions = agents
        .map((a, index) => {
          const home = homes[a.id] || homes.supervisor;
          const path = walkToDesk(home, index);
          const length = path
            .slice(1)
            .reduce(
              (sum, point, i) =>
                sum + Math.hypot(point.x - path[i].x, point.y - path[i].y),
              0,
            );
          const phase = (time + index * 9) % 57;
          const target =
            a.enabled && a.status !== "working" && phase > 36 && phase < 46
              ? length
              : 0;
          const old = walks.current.get(a.id)?.distance ?? 0;
          const distance =
            old +
            Math.sign(target - old) *
              Math.min(Math.abs(target - old), delta * 39);
          const point = pointOnPath(path, distance);
          if (distance < old) {
            const reverse: Record<Facing, Facing> = {
              up: "down",
              down: "up",
              right: "left",
              left: "right",
            };
            point.facing = reverse[point.facing];
          }
          if (distance === 0)
            point.facing = a.status === "working" ? "up" : "down";
          walks.current.set(a.id, point);
          const step = old !== distance ? 1 + (Math.floor(time * 7) % 2) : 0;
          return { a, ...point, step };
        })
        .sort((a, b) => a.y - b.y);
      for (const { a, x, y, step, facing } of positions) {
        character(c, x, y, a.color, a.id, step, selected === a.id, facing);
        if (a.status === "working") {
          for (let i = 0; i < 3; i++) {
            c.fillStyle =
              Math.floor(time * 4) % 3 === i ? "#dff7bd" : "#748b68";
            c.fillRect(Math.round(x - 7 + i * 5), Math.round(y - 42), 3, 2);
          }
        }
        hit.current.push({
          id: a.id,
          x: (x * scale) / dpr + ox / dpr,
          y: ((y - 17) * scale) / dpr + oy / dpr,
          rx: Math.max(12, (14 * scale) / dpr),
          ry: Math.max(16, (21 * scale) / dpr),
        });
        if (selected === a.id || tip === a.id) {
          c.font = "10px monospace";
          const label = a.name,
            tw = c.measureText(label).width;
          c.fillStyle = "#18232c";
          c.fillRect(Math.round(x - tw / 2 - 7), y - 56, tw + 14, 16);
          c.fillStyle = "#d6e4cc";
          c.fillRect(x - 2, y - 40, 4, 3);
          c.fillText(label, Math.round(x - tw / 2), y - 45);
        }
      }
      cat(c, time);
      frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);
    return () => cancelAnimationFrame(frame);
  }, [agents, selected, paused, grid, zoom, tip]);
  return (
    <canvas
      ref={ref}
      className="office-canvas"
      role="img"
      aria-label="Besh AI agentli jonli piksel ofis. Agentni tanlash uchun ustiga bosing yoki pastdagi kartalardan foydalaning."
      tabIndex={0}
      onKeyDown={(e) => {
        if (
          ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)
        ) {
          e.preventDefault();
          camera.current.x +=
            e.key === "ArrowLeft" ? 60 : e.key === "ArrowRight" ? -60 : 0;
          camera.current.y +=
            e.key === "ArrowUp" ? 60 : e.key === "ArrowDown" ? -60 : 0;
        }
      }}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        drag.current = {
          x: e.clientX,
          y: e.clientY,
          cx: camera.current.x,
          cy: camera.current.y,
          moved: false,
        };
      }}
      onPointerMove={(e) => {
        if (drag.current) {
          const dx = e.clientX - drag.current.x,
            dy = e.clientY - drag.current.y;
          if (Math.abs(dx) + Math.abs(dy) > 5) drag.current.moved = true;
          if (drag.current.moved) {
            camera.current = {
              x: drag.current.cx + dx,
              y: drag.current.cy + dy,
            };
            e.currentTarget.style.cursor = "grabbing";
            setTip(null);
            return;
          }
        }
        const box = e.currentTarget.getBoundingClientRect();
        const found = hit.current.find(
          (p) =>
            Math.abs(p.x - (e.clientX - box.left)) < p.rx &&
            Math.abs(p.y - (e.clientY - box.top)) < p.ry,
        );
        setTip(found?.id || null);
        e.currentTarget.style.cursor = found ? "pointer" : "grab";
      }}
      onPointerUp={(e) => {
        if (drag.current && !drag.current.moved) {
          const box = e.currentTarget.getBoundingClientRect();
          const found = hit.current.find(
            (p) =>
              Math.abs(p.x - (e.clientX - box.left)) < p.rx &&
              Math.abs(p.y - (e.clientY - box.top)) < p.ry,
          );
          if (found) onSelect(found.id);
        }
        drag.current = null;
        e.currentTarget.releasePointerCapture(e.pointerId);
        e.currentTarget.style.cursor = "grab";
      }}
      onPointerCancel={() => {
        drag.current = null;
      }}
      onPointerLeave={() => {
        if (!drag.current) setTip(null);
      }}
    />
  );
}
