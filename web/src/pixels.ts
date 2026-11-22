// Original code-drawn pixel art. No Pixel Agents sprites or assets are copied.
type C = CanvasRenderingContext2D;
export type Facing = "down" | "up" | "left" | "right";
export const WORLD_W = 1280,
  WORLD_H = 768;
export const homes: Record<string, { x: number; y: number }> = {
  supervisor: { x: 135, y: 255 },
  developer: { x: 365, y: 255 },
  qa: { x: 595, y: 255 },
  devops: { x: 825, y: 255 },
  security: { x: 1055, y: 255 },
};
const r = (c: C, x: number, y: number, w: number, h: number, color: string) => {
  c.fillStyle = color;
  c.fillRect(Math.round(x), Math.round(y), w, h);
};
function shadow(c: C, x: number, y: number, w: number, h: number) {
  r(c, x, y, w, h, "#292b3044");
}
export function character(
  c: C,
  x: number,
  y: number,
  color: string,
  id: string,
  step = 0,
  selected = false,
  facing: Facing = "down",
) {
  x = Math.round(x);
  y = Math.round(y);
  shadow(c, x - 8, y + 1, 17, 4);
  if (selected) {
    r(c, x - 12, y + 4, 25, 2, "#d7ecb6");
    r(c, x - 14, y - 1, 2, 5, "#d7ecb6");
    r(c, x + 13, y - 1, 2, 5, "#d7ecb6");
  }
  const hair =
    (
      {
        supervisor: "#564636",
        developer: "#302e35",
        qa: "#957b59",
        devops: "#7c4c37",
        security: "#3e343b",
      } as Record<string, string>
    )[id] || "#302e35";
  const skin =
    id === "devops" ? "#bc8c68" : id === "security" ? "#d8a88c" : "#edc4a0";
  const stride = step === 0 ? 0 : step === 1 ? 2 : -2;
  const side = facing === "left" || facing === "right";
  const look = facing === "left" ? -1 : 1;
  // The stride changes both feet and arms, even at pixel scale.
  r(c, x - 6, y - 5 + stride, 5, 6, "#313744");
  r(c, x + 2, y - 5 - stride, 5, 6, "#313744");
  r(c, x - 7 + (side ? stride : 0), y + stride, 7, 3, "#292c34");
  r(c, x + 2 - (side ? stride : 0), y - stride, 7, 3, "#292c34");
  r(c, x - 8, y - 18, 17, 14, color);
  r(c, x - 8, y - 18, 3, 13, "#00000018");
  r(c, x - 11, y - 15 - stride, 3, 9, color);
  r(c, x + 9, y - 15 + stride, 3, 9, color);
  r(c, x - 11, y - 7 - stride, 3, 4, skin);
  r(c, x + 9, y - 7 + stride, 3, 4, skin);
  r(c, x - 3, y - 21, 6, 5, skin);
  r(c, x - 8, y - 34, 17, 16, hair);
  if (facing === "up") {
    r(c, x - 8, y - 34, 17, 18, hair);
    r(c, x - 6, y - 31, 12, 3, "#ffffff16");
    return;
  }
  r(c, x - 7 + (side ? 3 * look : 0), y - 28, 15, 12, skin);
  r(c, x - 10, y - 31, 3, 12, hair);
  r(c, x - 7, y - 35, 13, 8, hair);
  r(c, x + 6, y - 32, 4, 7, hair);
  if (side) {
    r(c, x + look * 6, y - 25, 2, 2, "#34343a");
    r(c, x + look * 8, y - 22, 3, 2, skin);
  } else {
    r(c, x - 4, y - 25, 2, 2, "#34343a");
    r(c, x + 3, y - 25, 2, 2, "#34343a");
    r(c, x, y - 20, 3, 1, "#a77663");
  }
  if (id === "supervisor" && !side) {
    r(c, x - 6, y - 27, 5, 4, "#504d4a");
    r(c, x + 1, y - 27, 5, 4, "#504d4a");
    r(c, x - 1, y - 26, 2, 1, "#504d4a");
    r(c, x - 5, y - 26, 3, 1, "#b4c1b9");
    r(c, x + 2, y - 26, 3, 1, "#b4c1b9");
  }
  if (id === "qa") {
    r(c, x - 10, y - 28, 3, 17, hair);
    r(c, x + 8, y - 28, 3, 17, hair);
    r(c, x + 8, y - 31, 3, 3, "#c8a4d4");
  }
  if (id === "security") {
    r(c, x - 11, y - 27, 3, 9, "#3b444e");
    r(c, x + 10, y - 27, 3, 9, "#3b444e");
    r(c, x - 10, y - 33, 21, 2, "#3b444e");
  }
  if (id === "devops") {
    r(c, x - 9, y - 36, 19, 5, "#638a76");
    r(c, x - 11, y - 32, 23, 3, "#446855");
  }
  r(c, x - 2, y - 16, 4, 2, "#ffffff70");
  r(c, x - 6, y - 13, 2, 8, "#ffffff22");
  r(c, x + 5, y - 15, 2, 10, "#00000020");
  r(c, x - 7, y - 29, 3, 8, "#ffffff12");
  r(c, x + 6, y - 23, 2, 5, "#00000018");
  if (id === "developer") {
    r(c, x - 10, y - 28, 3, 8, "#334d64");
    r(c, x + 10, y - 28, 3, 8, "#334d64");
    r(c, x - 8, y - 35, 17, 2, "#334d64");
  }
  if (id === "qa") {
    r(c, x - 7, y - 33, 3, 3, "#d4b8e5");
    r(c, x - 5, y - 14, 10, 2, "#e4d4ed");
  }
  if (id === "security") {
    r(c, x + 3, y - 14, 3, 5, "#eee0c4");
    r(c, x + 4, y - 13, 1, 3, "#a97762");
  }
}
function plant(c: C, x: number, y: number, size = 1) {
  c.save();
  c.translate(x, y);
  c.scale(size, size);
  shadow(c, -10, 2, 22, 4);
  r(c, -8, -12, 16, 15, "#6e5144");
  r(c, -10, -14, 20, 4, "#a0795c");
  r(c, -5, -10, 4, 11, "#b18b69");
  r(c, -2, -39, 4, 27, "#47684c");
  r(c, -14, -31, 4, 11, "#527459");
  r(c, -10, -27, 10, 8, "#659069");
  r(c, 3, -34, 10, 7, "#5c865e");
  r(c, 10, -39, 4, 10, "#719a6e");
  r(c, -7, -43, 7, 10, "#7da578");
  r(c, -18, -36, 7, 6, "#45654c");
  r(c, -15, -22, 12, 6, "#3f6349");
  r(c, 1, -23, 14, 6, "#73936c");
  c.restore();
}
function bookshelf(c: C, x: number, y: number, w = 90) {
  shadow(c, x + 3, y + 6, w, 48);
  r(c, x, y, w, 45, "#51413d");
  r(c, x + 3, y + 3, w - 6, 38, "#352f32");
  for (let shelf = 0; shelf < 2; shelf++) {
    for (let i = 0; i < 10; i++) {
      const h = 10 + ((i * 7) % 7);
      r(
        c,
        x + 6 + i * 7,
        y + 7 + shelf * 18,
        4,
        h,
        ["#a66e63", "#a99468", "#7c9990", "#73839b", "#b8ac87"][i % 5],
      );
      r(c, x + 7 + i * 7, y + 10 + shelf * 18, 2, 1, "#dfc49c");
    }
    r(c, x + 1, y + 20 + shelf * 18, w - 2, 3, "#957654");
  }
  r(c, x, y - 2, w, 4, "#ad8e66");
  r(c, x + 3, y + 42, 5, 6, "#3e3532");
  r(c, x + w - 8, y + 42, 5, 6, "#3e3532");
}
function windowFrame(c: C, x: number, y: number) {
  r(c, x - 3, y - 3, 94, 51, "#1d2c35");
  r(c, x, y, 88, 44, "#b6a282");
  r(c, x + 3, y + 3, 82, 38, "#8da8b2");
  r(c, x + 3, y + 24, 82, 17, "#688c7e");
  r(c, x + 8, y + 18, 18, 7, "#80a493");
  r(c, x + 17, y + 12, 9, 8, "#80a493");
  r(c, x + 48, y + 22, 27, 19, "#486d68");
  r(c, x + 61, y + 14, 10, 12, "#486d68");
  r(c, x + 40, y, 4, 44, "#b6a282");
  r(c, x, y + 20, 88, 3, "#b6a282");
  r(c, x - 5, y + 43, 98, 4, "#c4ac86");
  r(c, x + 5, y + 3, 8, 15, "#d7e4da44");
}
function desk(c: C, x: number, y: number, color: string, screenOn = false) {
  shadow(c, x - 3, y + 43, 101, 10);
  r(c, x + 5, y + 32, 5, 26, "#514942");
  r(c, x + 81, y + 32, 5, 26, "#514942");
  r(c, x - 2, y + 3, 96, 39, "#6a4f40");
  r(c, x - 2, y, 96, 35, "#bf9971");
  r(c, x + 1, y + 2, 90, 2, "#d1ad82");
  r(c, x + 1, y + 34, 90, 4, "#88654b");
  r(c, x + 28, y - 23, 36, 28, "#252f39");
  r(c, x + 30, y - 22, 32, 23, "#9baba9");
  r(c, x + 32, y - 20, 28, 19, "#263f45");
  r(c, x + 34, y - 18, 24, 1, "#425b59");
  if (screenOn) {
    for (let i = 0; i < 4; i++)
      r(
        c,
        x + 35,
        y - 14 + i * 3,
        9 + (i % 3) * 5,
        1,
        i % 2 ? "#9cbb9c" : "#7d97af",
      );
  } else {
    r(c, x + 43, y - 12, 7, 5, "#738d88");
    r(c, x + 45, y - 15, 3, 3, "#738d88");
  }
  r(c, x + 43, y + 4, 6, 5, "#535e62");
  r(c, x + 38, y + 9, 17, 3, "#84908e");
  r(c, x + 29, y + 17, 33, 8, "#5f625e");
  r(c, x + 30, y + 17, 30, 5, "#b7b7a2");
  for (let i = 0; i < 8; i++) r(c, x + 32 + i * 3, y + 18, 1, 3, "#8c9286");
  r(c, x + 66, y + 17, 5, 7, "#cdc6ae");
  r(c, x + 11, y + 15, 10, 12, color);
  r(c, x + 20, y + 18, 3, 6, color);
  r(c, x + 12, y + 15, 8, 2, "#51483e");
  r(c, x + 79, y + 8, 9, 15, "#bfc2ad");
  r(c, x + 80, y + 10, 6, 1, "#8c9b8a");
  r(c, x + 80, y + 13, 6, 1, "#8c9b8a");
  // Empty chair, actual characters are independently depth-sorted.
  r(c, x + 34, y + 47, 24, 17, "#3b4948");
  r(c, x + 36, y + 45, 20, 12, "#7f9d8c");
  r(c, x + 37, y + 58, 18, 5, "#638574");
  r(c, x + 44, y + 64, 4, 5, "#474c47");
}
function lounge(c: C) {
  r(c, 529, 125, 201, 173, "#394952");
  r(c, 533, 129, 193, 165, "#647a80");
  r(c, 537, 133, 185, 157, "#6b8286");
  for (let i = 0; i < 3; i++) {
    r(c, 538 + i * 3, 133 + i * 3, 183 - i * 6, 1, "#8c9a9444");
    r(c, 538 + i * 3, 288 - i * 3, 183 - i * 6, 1, "#8c9a9444");
  }
  // Sofa and pillows.
  shadow(c, 571, 167, 130, 14);
  r(c, 568, 143, 132, 34, "#6b6650");
  r(c, 571, 139, 126, 28, "#b49a68");
  r(c, 574, 144, 120, 20, "#c8ae77");
  r(c, 567, 148, 9, 34, "#9a8058");
  r(c, 692, 148, 9, 34, "#9a8058");
  r(c, 577, 164, 113, 16, "#b69a66");
  r(c, 580, 180, 4, 4, "#514b43");
  r(c, 685, 180, 4, 4, "#514b43");
  r(c, 580, 147, 20, 15, "#8faba0");
  r(c, 665, 148, 18, 14, "#c3b6a0");
  r(c, 603, 147, 27, 13, "#b79b69");
  // Lounge table.
  shadow(c, 594, 236, 83, 8);
  r(c, 594, 203, 78, 35, "#795c47");
  r(c, 592, 199, 80, 33, "#bc996d");
  r(c, 596, 202, 72, 26, "#c7a579");
  r(c, 603, 209, 18, 13, "#9a8175");
  r(c, 603, 209, 16, 11, "#e2d2b0");
  r(c, 605, 212, 12, 1, "#9d9f88");
  r(c, 645, 207, 9, 10, "#e5d9b8");
  r(c, 648, 208, 4, 3, "#765a48");
  r(c, 653, 210, 3, 5, "#e5d9b8");
  r(c, 545, 216, 31, 43, "#8e6d66");
  r(c, 541, 220, 10, 32, "#ad8279");
  r(c, 548, 220, 22, 29, "#bf9687");
  r(c, 547, 248, 25, 12, "#a77b70");
  plant(c, 718, 196, 0.75);
}
function kitchen(c: C) {
  for (let y = 321; y < 416; y += 16)
    for (let x = 524; x < 736; x += 16)
      r(
        c,
        x,
        y,
        16,
        16,
        ((x - 524) / 16 + (y - 321) / 16) % 2 ? "#8c9590" : "#a9afa1",
      );
  r(c, 526, 308, 208, 28, "#5c6159");
  r(c, 526, 303, 208, 10, "#cec8ad");
  r(c, 530, 314, 62, 20, "#a19372");
  r(c, 597, 314, 62, 20, "#a19372");
  r(c, 664, 314, 66, 20, "#a19372");
  r(c, 557, 317, 12, 2, "#4f5e56");
  r(c, 623, 317, 12, 2, "#4f5e56");
  r(c, 687, 317, 12, 2, "#4f5e56");
  // Espresso machine, sink, a small fridge.
  r(c, 540, 283, 26, 24, "#283b40");
  r(c, 543, 284, 20, 17, "#c0c4b2");
  r(c, 546, 289, 14, 10, "#384d4c");
  r(c, 547, 300, 11, 5, "#efe3c9");
  r(c, 545, 304, 16, 2, "#456055");
  r(c, 611, 305, 31, 5, "#7b8d86");
  r(c, 614, 306, 25, 3, "#4a6666");
  r(c, 627, 297, 3, 10, "#c2cac2");
  r(c, 629, 296, 6, 3, "#c2cac2");
  r(c, 696, 266, 31, 41, "#4d5a57");
  r(c, 699, 267, 27, 37, "#bdc3b4");
  r(c, 701, 283, 23, 2, "#8a9b90");
  r(c, 701, 275, 2, 5, "#6b7a70");
  r(c, 701, 290, 2, 7, "#6b7a70");
  r(c, 548, 360, 63, 35, "#594b40");
  r(c, 545, 356, 67, 31, "#c09d73");
  r(c, 552, 361, 53, 2, "#d3b88c");
  for (const x of [552, 592]) {
    r(c, x, 390, 14, 16, "#4f6355");
    r(c, x - 2, 389, 18, 6, "#829a7d");
  }
}
function roomLabel(c: C, text: string, x: number, y: number) {
  c.font = "12px monospace";
  c.fillStyle = "#bdc9bb";
  c.fillText(text, x, y);
}
function meeting(c: C) {
  r(c, 49, 489, 440, 218, "#526966");
  r(c, 55, 495, 428, 206, "#5c7470");
  r(c, 60, 500, 418, 1, "#81988a");
  r(c, 60, 695, 418, 1, "#81988a");
  r(c, 67, 464, 136, 47, "#2b3b44");
  r(c, 71, 468, 128, 38, "#d0d5bf");
  r(c, 80, 475, 65, 3, "#718b85");
  r(c, 80, 483, 87, 2, "#9da687");
  r(c, 80, 491, 43, 2, "#bf9a71");
  r(c, 212, 464, 118, 45, "#99744e");
  r(c, 216, 468, 110, 37, "#6f7866");
  for (let i = 0; i < 4; i++) {
    r(
      c,
      222 + i * 23,
      477,
      16,
      16,
      ["#c5ac83", "#b0c3a2", "#d1b8b4", "#a7b8c1"][i],
    );
    r(c, 228 + i * 23, 475, 2, 3, "#dbd4b2");
  }
  shadow(c, 119, 600, 295, 32);
  r(c, 120, 551, 288, 70, "#5f4736");
  r(c, 115, 544, 292, 67, "#b98e60");
  r(c, 120, 548, 282, 59, "#c59a6b");
  r(c, 122, 551, 277, 2, "#dbb584");
  r(c, 122, 601, 277, 2, "#997046");
  for (const x of [142, 229, 321]) {
    r(c, x, 520, 35, 24, "#3d4c4c");
    r(c, x + 2, 517, 31, 21, "#7d9b8a");
    r(c, x, 618, 35, 24, "#3d4c4c");
    r(c, x + 2, 615, 31, 21, "#7d9b8a");
  }
  for (const x of [151, 245, 338]) {
    r(c, x, 562, 20, 17, "#d6d8be");
    r(c, x + 3, 565, 14, 1, "#8e9f8f");
    r(c, x + 3, 569, 10, 1, "#8e9f8f");
  }
  r(c, 221, 572, 28, 18, "#435557");
  r(c, 223, 574, 24, 14, "#76968e");
  r(c, 277, 576, 9, 10, "#e2d7b7");
  r(c, 279, 577, 5, 3, "#715541");
  plant(c, 463, 533, 1.1);
  plant(c, 76, 687, 0.85);
}
export function room(c: C, grid: boolean, active: Set<string> = new Set()) {
  r(c, 0, 0, WORLD_W, WORLD_H, "#14212a");
  // A campus-sized floor plan, three times the original navigable floor area.
  shadow(c, 34, 42, 1220, 699);
  r(c, 24, 26, 1232, 710, "#10202a");
  r(c, 31, 33, 1218, 697, "#304551");
  r(c, 38, 40, 1204, 76, "#405765");
  r(c, 38, 40, 1204, 4, "#68838b");
  r(c, 38, 110, 1204, 10, "#253b46");
  for (let y = 120; y < 722; y += 16) {
    r(
      c,
      38,
      y,
      1204,
      16,
      ["#916b4e", "#987253", "#9b7655", "#94704f"][((y - 120) / 16) % 4],
    );
    r(c, 38, y + 15, 1204, 1, "#76573e");
    for (let x = 38 + (((y - 120) / 16) % 2) * 36; x < 1242; x += 72) {
      r(c, x, y, 1, 16, "#77583f");
      r(c, x + 9, y + 5, 29, 1, "#b8996d33");
      r(c, x + 33, y + 10, 21, 1, "#5e463522");
    }
  }
  for (let i = 0; i < 5; i++) {
    const x = 72 + i * 230;
    windowFrame(c, x, 55);
    bookshelf(c, x + 108, 53, 78);
  }
  const stations = [
    ["supervisor", "#dfb973"],
    ["developer", "#8fb8e3"],
    ["qa", "#bca0df"],
    ["devops", "#8ec5ae"],
    ["security", "#e2a0a0"],
  ];
  const names = [
    "SUPERVISOR",
    "DEVELOPER",
    "QA ENGINEER",
    "DEVOPS",
    "SECURITY",
  ];
  stations.forEach(([id, color], i) => {
    const x = 66 + i * 230;
    r(c, x, 144, 176, 153, "#465c5c");
    r(c, x + 4, 148, 168, 145, "#607a72");
    r(c, x + 8, 152, 160, 1, "#8ca392");
    r(c, x + 8, 287, 160, 1, "#8ca392");
    c.font = "10px monospace";
    c.fillStyle = color;
    c.fillText(names[i], x + 17, 168);
    desk(c, x + 24, 190, color, active.has(id));
    // Paper tray, notebook, and personal shelves make each workstation distinct.
    r(c, x + 140, 194, 20, 33, "#4e5449");
    r(c, x + 142, 196, 16, 7, "#d4c8aa");
    r(c, x + 142, 207, 16, 7, "#a99f7b");
    r(c, x + 142, 219, 16, 5, color);
    plant(c, x + 155, 282, 0.6);
  });
  // A broad circulation spine keeps movement away from desks and furniture.
  r(c, 49, 347, 1181, 79, "#756d56");
  r(c, 52, 350, 1175, 73, "#9d9474");
  for (let x = 56; x < 1227; x += 24) {
    r(c, x, 355, 10, 1, "#c2b38c");
    r(c, x, 417, 10, 1, "#c2b38c");
  }
  r(c, 67, 315, 165, 22, "#5b4f42");
  r(c, 64, 310, 171, 19, "#aa845b");
  r(c, 73, 305, 30, 8, "#789f9b");
  r(c, 110, 302, 20, 11, "#caad7e");
  r(c, 144, 304, 47, 7, "#b8b89b");
  // Compact server racks are scenery; their LEDs do not represent live systems.
  for (let k = 0; k < 3; k++) {
    const x = 1000 + k * 57;
    r(c, x, 301, 45, 41, "#273a44");
    r(c, x + 3, 304, 39, 34, "#3b515a");
    for (let j = 0; j < 4; j++) {
      r(c, x + 6, 307 + j * 7, 31, 4, "#20323d");
      r(c, x + 31, 308 + j * 7, 3, 2, j % 2 ? "#9abc97" : "#d9b872");
    }
  }
  plant(c, 478, 327, 0.85);
  plant(c, 935, 327, 0.85);
  // Lower wing, with wide openings into independent meeting, lounge and kitchen areas.
  r(c, 38, 447, 1204, 12, "#293c47");
  r(c, 38, 447, 1204, 3, "#60747b");
  for (const x of [224, 640, 1058]) {
    r(c, x, 447, 83, 12, "#927153");
    r(c, x, 447, 83, 2, "#b8976c");
  }
  r(c, 507, 459, 14, 263, "#2b404a");
  r(c, 507, 459, 4, 263, "#5b7278");
  r(c, 842, 459, 14, 263, "#2b404a");
  r(c, 842, 459, 4, 263, "#5b7278");
  meeting(c);
  r(c, 532, 485, 298, 220, "#3b555c");
  r(c, 537, 490, 288, 210, "#607c80");
  c.save();
  c.translate(17, 365);
  lounge(c);
  c.restore();
  r(c, 570, 669, 155, 17, "#4f685e");
  r(c, 572, 666, 151, 14, "#92a58c");
  r(c, 774, 528, 35, 60, "#4b4240");
  r(c, 777, 531, 29, 53, "#96725b");
  for (let i = 0; i < 5; i++)
    r(
      c,
      781,
      537 + i * 9,
      20,
      5,
      ["#a6b19a", "#b6a384", "#7a9a9c", "#b49a8b", "#cebd91"][i],
    );
  for (let y = 485; y < 706; y += 20)
    for (let x = 869; x < 1231; x += 20)
      r(
        c,
        x,
        y,
        20,
        20,
        ((x - 869) / 20 + (y - 485) / 20) % 2 ? "#768b85" : "#a9b6a5",
      );
  c.save();
  c.translate(344, 235);
  kitchen(c);
  c.restore();
  r(c, 1110, 557, 84, 60, "#766044");
  r(c, 1107, 551, 88, 59, "#c49d69");
  r(c, 1112, 555, 78, 50, "#d2b280");
  r(c, 1126, 569, 18, 17, "#e1d7b3");
  r(c, 1159, 569, 14, 17, "#a7b6a0");
  for (const x of [1111, 1170]) {
    r(c, x, 623, 25, 25, "#4d695d");
    r(c, x + 2, 620, 21, 20, "#91a88b");
  }
  plant(c, 1211, 537, 1.0);
  plant(c, 1222, 702, 0.85);
  roomLabel(c, "MEETING ROOM", 343, 481);
  roomLabel(c, "LOUNGE & LIBRARY", 550, 481);
  roomLabel(c, "COFFEE CORNER", 887, 481);
  plant(c, 55, 329, 0.9);
  plant(c, 1222, 329, 0.9);
  r(c, 38, 722, 1204, 8, "#3e4c4a");
  r(c, 31, 730, 1218, 7, "#0e1b24");
  if (grid) {
    for (let x = 38; x < 1242; x += 20) r(c, x, 120, 1, 602, "#f2f6da18");
    for (let y = 120; y < 722; y += 20) r(c, 38, y, 1204, 1, "#f2f6da18");
  }
}
export function cat(c: C, t: number) {
  const x = 791,
    y = 685;
  r(c, x - 7, y - 9, 17, 10, "#b9a68c");
  r(c, x - 8, y - 13, 9, 8, "#c6b297");
  r(c, x - 8, y - 16, 3, 5, "#c6b297");
  r(c, x - 2, y - 15, 3, 4, "#c6b297");
  r(c, x - 7, y - 10, 2, 1, "#56534b");
  r(c, x + 10, y - 6, 5, 3, "#b9a68c");
  r(c, x + 13, y - 8 - Math.floor(Math.sin(t) * 1), 3, 4, "#b9a68c");
}
