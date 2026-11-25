(() => {
  const SHOT_STARTS = [0, 6.9166667, 21.3333333, 34.3333333, 47.9166667, 56.5, 68.125, 79.75,
    91.9166667, 103, 115.1666667, 127.9166667, 135.375, 150.875, 161.375, 176.0416667];
  const NIGHT = '#202635', WALL = '#343849', WOOD = '#66574C', LAMP = '#E8B96E', PAPER = '#E5D7BD';

  function room(t, options = {}) {
    const open = clamp(options.open || 0), lamp = options.lamp ?? .45;
    boilSeed('room-wall');
    paint(rectPts(-160, -100, 2240, 920), { wash: WALL, fill: '#3A3B46', fillOp: 110, tex: .35, ink: null });
    paint([[0, 700], [1920, 700], [1920, 1200], [0, 1200]], { wash: '#272B38', fill: '#171D29', fillOp: 150, tex: .3, ink: PAL.ink, sw: 2 });

    // The only warm light stays close to the lamp; the room remains legible in the shadows.
    glow(1080, 540, 240 + 20 * Math.sin(t * 2.7), '#D9A865', lamp);
    paint(rectPts(120, 190, 300, 260, 2), { wash: '#151D2A', fill: '#101824', fillOp: 230, ink: PAL.ink, sw: 3 });
    paint(rectPts(138, 208, 264, 222, 1), { wash: '#243346', fill: '#1C2A3C', fillOp: 210, ink: null });
    inkLine([[270, 210], [270, 430]], 3, '#64616A', 'inkfine', 0);
    inkLine([[140, 320], [400, 320]], 3, '#64616A', 'inkfine', 0);
    for (let i = 0; i < 3; i++) {
      const y = 492 + i * 68;
      paint(rectPts(40, y, 390, 22, 2), { wash: '#49424A', fill: '#292C38', fillOp: 120, ink: null });
      inkLine([[42, y + 17], [420, y + 19]], 1.5, '#776C65', 'inkfine', 0);
    }

    // Bed, pillow and stool are fixed landmarks so every move can be read against them.
    paint(rectPts(620, 852, 870, 128, 4), { wash: '#4C4141', fill: '#2B2D38', fillOp: 180, ink: PAL.ink, sw: 3 });
    paint(rectPts(660, 640, 820, 260, 10), { wash: '#8E887D', fill: '#4D4A4A', fillOp: 210, tex: .25, ink: PAL.ink, sw: 3 });
    paint(rectPts(1130, 650, 280, 125, 12), { wash: '#C7BFAE', fill: '#958B7B', fillOp: 200, ink: PAL.ink, sw: 2 });
    paint(rectPts(690, 866, 740, 35, 2), { wash: '#77614E', fill: '#493D3A', fillOp: 180, ink: null });
    for (const x of [700, 1400]) paint(rectPts(x, 955, 36, 110, 3), { wash: WOOD, fill: '#413B3D', fillOp: 180, ink: PAL.ink, sw: 2 });
    paint(rectPts(490, 710, 240, 38, 3), { wash: '#7A6555', fill: '#433B3B', fillOp: 180, ink: PAL.ink, sw: 2 });
    for (const x of [510, 700]) paint(rectPts(x, 744, 18, 92, 2), { wash: WOOD, fill: '#38363C', fillOp: 160, ink: PAL.ink, sw: 2 });

    const dx = open * 300;
    paint(rectPts(1570, 180, 270, 570, 3), { wash: '#171C27', fill: '#121923', fillOp: 230, ink: '#75665C', sw: 4 });
    paint(rectPts(1590 + dx, 195, 216, 540, 3), { wash: '#725C4E', fill: '#3D3740', fillOp: 230, ink: '#211F29', sw: 4 });
    paint(rectPts(1606 + dx, 220, 182, 488, 1), { wash: '#635247', fill: '#51463F', fillOp: 160, ink: null });
    paint(ellPts(1762 + dx, 476, 10, 10, 16), { wash: LAMP, fill: '#E1B45E', fillOp: 230, ink: PAL.ink, sw: 1 });
    const latchX = 1605 + dx;
    paint(rectPts(latchX - 16, 526, 78, 30, 1), { wash: '#97918B', fill: '#504C4D', fillOp: 220, ink: PAL.ink, sw: 2 });
    paint(rectPts(latchX + 30, 530, 84, 20, 1), { wash: '#B6AA91', fill: '#77706A', fillOp: 210, ink: PAL.ink, sw: 2 });

    // A small oil lamp on the bedside table, with restrained flame movement.
    paint(rectPts(960, 532, 150, 20, 2), { wash: '#6F594A', fill: '#36343A', fillOp: 190, ink: PAL.ink, sw: 2 });
    paint(rectPts(1010, 492, 50, 42, 2), { wash: '#B5A78D', fill: '#62584F', fillOp: 200, ink: PAL.ink, sw: 2 });
    paint(ellPts(1035, 482, 9, 18 + 3 * Math.sin(t * 9), 12), { wash: '#F0C16B', fill: '#CF8D44', fillOp: 190, ink: null });

    // Small wear marks keep the room lived in without turning it into a ruin.
    for (let i = 0; i < 7; i++) {
      const x = 500 + i * 143, y = 300 + (i % 3) * 102;
      inkLine([[x, y], [x + 24, y + 8], [x + 39, y + 2]], .9, '#716B68', 'inkfine', .1);
    }
  }

  function paperClawd(x, y, options = {}) {
    const u = options.u || 14;
    const mood = options.mood || {};
    clawd(x, y, u, {
      ...mood,
      boilKey: 'paper-clawd',
      col: '#D8C8AA', dk: '#827464', lt: '#F2E8D5',
      draw(unit, sw) {
        paint(rectPts(-4.2 * unit, -3.1 * unit, 8.4 * unit, 1.05 * unit, .4), {
          wash: '#9A463F', fill: '#A04C43', fillOp: 210, tex: .2, ink: PAL.ink, sw: Math.max(.5, sw * .45)
        });
        paint(rectPts(-3.7 * unit, -2.05 * unit, 7.4 * unit, .55 * unit, .2), {
          wash: '#687451', fill: '#65714B', fillOp: 220, tex: .15, ink: PAL.ink, sw: Math.max(.4, sw * .35)
        });
        inkLine([[-2.6 * unit, -2.7 * unit], [-1.2 * unit, -2.3 * unit], [0, -2.6 * unit], [1.4 * unit, -2.25 * unit], [2.8 * unit, -2.55 * unit]],
          Math.max(.5, sw * .3), '#E4CFAC', 'inkfine', .05);
      }
    });
  }

  function povHands(t, paper = false) {
    const col = paper ? '#E5D7BD' : '#88746C';
    const left = paper
      ? [[720, 1080], [728, 1012], [749, 973], [766, 962], [779, 976], [788, 953], [802, 958], [807, 989], [825, 1006], [828, 1080]]
      : [[610, 1080], [664, 988], [724, 970], [770, 1014], [796, 1080]];
    const right = paper
      ? [[1200, 1080], [1193, 1018], [1171, 979], [1155, 962], [1141, 976], [1131, 953], [1117, 959], [1112, 990], [1095, 1007], [1090, 1080]]
      : [[1310, 1080], [1260, 994], [1200, 980], [1155, 1024], [1130, 1080]];
    paint(left, { wash: col, fill: paper ? '#C7B799' : '#695954', fillOp: 220, ink: PAL.ink, sw: 2 });
    paint(right, { wash: col, fill: paper ? '#C7B799' : '#695954', fillOp: 220, ink: PAL.ink, sw: 2 });
    if (paper) {
      inkLine([[744, 1012], [766, 1000], [793, 1018]], 2, '#756B62', 'inkfine', .05);
      inkLine([[1177, 1012], [1155, 1000], [1128, 1018]], 2, '#756B62', 'inkfine', .05);
      for (let i = 0; i < 3; i++) {
        inkLine([[754 + i * 12, 974], [755 + i * 12, 997]], 1.2, '#756B62', 'inkfine', 0);
        inkLine([[1166 - i * 12, 974], [1165 - i * 12, 997]], 1.2, '#756B62', 'inkfine', 0);
      }
    }
    if (!paper) {
      const tremble = 3 * Math.sin(t * 28);
      inkLine([[738, 988], [762 + tremble, 1000], [780, 1024]], 2, '#A58E7F', 'inkfine', .1);
    }
  }

  function shot01(t, lt, dur) {
    room(t, { lamp: .28 });
    // Empty stool and still-latched door: the first absence is the establishing image.
    if (lt < .45) iris(610, 726, lerp(0, 1500, easeIn(lt / .45)));
    if (lt > 2.1) {
      const q = seg(lt, 2.1, 3.3);
      paint(rectPts(522, 660, 18 + q * 5, 86, 1), { wash: '#453B39', fill: '#272B34', fillOp: 130, ink: null });
    }
  }

  function shot02(t, lt) {
    room(t, { lamp: .6 });
    const set = ease(seg(lt, 1, 2.4));
    const hx = lerp(580, 580, set), hy = lerp(628, 628, set);
    paperClawd(610, 709 - 12 * Math.sin(Math.PI * set), { u: 14, mood: { eyes: 'open', mouth: 'smile', blush: .45 } });
    if (lt < 4.2) {
      paint([[hx - 80, hy - 120], [hx - 45, hy - 120], [hx - 14, hy - 30], [hx + 4, hy - 12], [hx - 18, hy + 5], [hx - 68, hy - 30]],
        { wash: '#8E7E72', fill: '#5C514D', fillOp: 180, ink: PAL.ink, sw: 2 });
    }
  }

  function shot03(t, lt) {
    const k = ease(seg(lt, 0, 1.8));
    camBegin(610, 720, 1.28 + .14 * k);
    room(t, { lamp: .5 });
    paperClawd(610, 709, { u: 14, mood: { eyes: 'open', mouth: 'smile', blush: .45 } });
    camEnd();
  }

  function shot04(t, lt) {
    const k = ease(seg(lt, 2, 5));
    room(t, { open: 1 - k, lamp: .35 });
    if (lt > 5.4) {
      const q = ease(seg(lt, 5.4, 7.2));
      paint(rectPts(1597, 516, 80 * q, 30, 1), { wash: '#A99F8D', fill: '#706A63', fillOp: 220, ink: PAL.ink, sw: 2 });
    }
    paperClawd(610, 709, { u: 14, mood: { eyes: 'open', mouth: 'line' } });
  }

  function shot05(t) {
    room(t, { lamp: .58 });
    paperClawd(610, 709, { u: 14, mood: { eyes: 'open', mouth: 'smile', blush: .45 } });
    clawd(1110, 852, 34, { view: 'side', eyes: 'closed', mouth: 'line', boilKey: 'sleeping-clawd', col: '#514B51', dk: '#2B2C36', lt: '#797178', noShadow: true });
  }

  function shot06(t, lt) {
    room(t, { lamp: .27 + .1 * Math.sin(lt * 6) });
    clawd(1050, 872, 31, { view: 'back', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    paperClawd(610, 709, { u: 14, mood: { eyes: 'open', mouth: 'line', lookX: .35 } });
    if (lt > 8.4) {
      const k = seg(lt, 8.4, 9.8);
      paint(ellPts(1035, 455, 9 + 20 * k, 18 + 34 * k, 14), { wash: '#F7D08A', fill: '#D39648', fillOp: 130, ink: null });
    }
  }

  function shot07(t, lt) {
    room(t, { lamp: .23 });
    clawd(1050, 872, 31, { view: 'back', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    const k = ease(seg(lt, 1.8, 2.8));
    const x = lerp(610, 805, k), y = lerp(709, 856, k);
    paperClawd(x, y, { u: 14, mood: { eyes: 'open', mouth: 'line', lookX: .55 } });
  }

  function shot08(t, lt) {
    room(t, { lamp: .22 });
    clawd(1050, 872, 31, { view: 'back', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    paperClawd(805, 856, { u: 14, mood: { eyes: 'open', mouth: 'line', lookX: .4 } });
    povHands(lt, false);
    const k = Math.max(0, 1 - lt / 2.2);
    paint(rectPts(1589, 526, 108, 24, 1), { wash: '#B4A98F', fill: '#817667', fillOp: 230, ink: PAL.ink, sw: 2 });
    if (k > 0) inkLine([[650, 1010], [720, 994 + 3 * Math.sin(lt * 3)], [770, 1020]], 2 + k * 2, '#9A8274', 'inkfine', .1);
  }

  function shot09(t, lt) {
    room(t, { lamp: .22 });
    paperClawd(1180, 776, { u: 14, mood: { eyes: 'open', mouth: 'line', lookX: -.25 } });
    const k = ease(seg(lt, 3.6, 7.4));
    const x = lerp(1196, 1190, k), y = lerp(702, 760, k);
    paint(ellPts(x, y, 3 + k * 2, 4 + k * 2, 12), { wash: '#161922', fill: '#12151D', fillOp: 240, ink: null });
    paint(ellPts(1164, 818, 8 + 5 * k, 6 + 3 * k, 16), { wash: '#262A34', fill: '#161B25', fillOp: 210, ink: null });
  }

  function shot10(t, lt) {
    room(t, { lamp: .2 });
    clawd(1120, 852, 31, { view: 'back', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    const k = ease(seg(lt, 1.8, 3.4));
    paperClawd(1280, 710, { u: 14, mood: { eyes: 'open', mouth: 'smile', blush: .4, lookX: -.5 } });
    if (k > .7) {
      inkLine([[1270, 690], [1284, 680], [1294, 700]], 1.5, '#8B806E', 'inkfine', .05);
      inkLine([[1290, 702], [1304, 690], [1312, 711]], 1.3, '#8B806E', 'inkfine', .05);
    }
  }

  function shot11(t, lt) {
    room(t, { lamp: .18 });
    clawd(1060, 876, 31, { view: 'back', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    const x = lerp(1290, 1510, ease(seg(lt, 1, 11.4)));
    const walk = seg(lt, 1, 11.4) * 1.4;
    paperClawd(x, 824, { u: 14, mood: { view: 'back', walk, eyes: 'open', mouth: 'line', aL: -.5, aR: -.5 } });
    inkLine([[x - 14, 786], [x - 6, 778], [x + 3, 788]], 1, '#B8A27E', 'inkfine', .05);
  }

  function shot12(t, lt) {
    room(t, { lamp: .18 });
    clawd(1130, 865, 31, { view: 'side', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    paperClawd(1290, 780, { u: 14, mood: { eyes: 'open', mouth: 'line' } });
    paint(rectPts(1160, 755, 235, 18, 2), { wash: '#C6B8A1', fill: '#8B8173', fillOp: 120, ink: null });
  }

  function shot13(t, lt, dur) {
    const open = ease(seg(lt, 4.5, 13.5));
    room(t, { open, lamp: .3 });
    clawd(1090, 870, 31, { view: 'back', eyes: 'closed', boilKey: 'sleeping-clawd', col: '#55515B', dk: '#252834', lt: '#77717B', noShadow: true });
    paperClawd(1470, 824, { u: 14, mood: { view: 'back', eyes: 'open', mouth: 'line' } });
    if (lt > dur - .5) iris(1690, 465, lerp(1500, 0, easeIn((lt - (dur - .5)) / .5)));
  }

  function shot14(t, lt) {
    const open = ease(seg(lt, 0, 1.6));
    room(t, { open, lamp: .36 });
    paperClawd(1470, 824, { u: 14, mood: { view: 'back', eyes: 'open', mouth: 'line' } });
    const walk = seg(lt, 1.5, 9.4) * 1.6;
    clawd(1510 + walk * 70, 735, 22, { view: 'back', walk, boilKey: 'leaving-clawd', col: '#A64E43', dk: '#622F36', lt: '#D39768', noShadow: true });
  }

  function shot15(t, lt) {
    room(t, { open: .42, lamp: .22 });
    // The point of view has dropped to the doll's scale; two folded-paper hands reveal the exchange.
    clawd(1190, 748, 14, { view: 'back', eyes: 'closed', boilKey: 'tiny-self', col: '#D8C8AA', dk: '#827464', lt: '#F2E8D5' });
    povHands(lt, true);
    const k = ease(seg(lt, 6.8, 10.2));
    paint(rectPts(831, 967, 16 + 24 * k, 5, .5), { wash: '#7F7165', fill: '#564D49', fillOp: 230, ink: null });
    paint(rectPts(1084, 970, 16 + 24 * k, 5, .5), { wash: '#7F7165', fill: '#564D49', fillOp: 230, ink: null });
  }

  function shot16(t, lt, dur) {
    room(t, { open: .98, lamp: .17 });
    povHands(lt, true);
    const walk = seg(lt, .2, dur - .2) * 1.4;
    clawd(1510 + walk * 60, 740, 22, { view: 'back', walk, boilKey: 'leaving-clawd', col: '#A64E43', dk: '#622F36', lt: '#D39768', noShadow: true });
    if (lt > dur - 1.2) {
      const fade = seg(lt, dur - 1.2, dur);
      paint(rectPts(0, 0, W, H), { wash: NIGHT, fill: NIGHT, fillOp: 210 * fade, ink: null });
    }
  }

  const scene = [shot01, shot02, shot03, shot04, shot05, shot06, shot07, shot08,
    shot09, shot10, shot11, shot12, shot13, shot14, shot15, shot16];
  shots(scene.map((fn, i) => [SHOT_STARTS[i], fn]));
})();
