/**
 * NSPanel HAUI - QR code encoder for the virtual panel's QR widgets.
 *
 * Encodes text (UTF-8, byte mode) into a QR code symbol per ISO/IEC 18004:
 * versions 1-40, error correction L/M/Q/H, Reed-Solomon over GF(256) and the
 * lowest-penalty mask unless one is given. Follows the structure of Project
 * Nayuki's reference implementation (MIT).
 */

const ECL = {
  L: { ordinal: 0, formatBits: 1 },
  M: { ordinal: 1, formatBits: 0 },
  Q: { ordinal: 2, formatBits: 3 },
  H: { ordinal: 3, formatBits: 2 },
};

// Indexed [ecl ordinal][version]; index 0 is unused.
const ECC_CODEWORDS_PER_BLOCK = [
  [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
  [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
];
const NUM_ERROR_CORRECTION_BLOCKS = [
  [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
  [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
  [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
  [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
];

function numRawDataModules(ver) {
  let result = (16 * ver + 128) * ver + 64;
  if (ver >= 2) {
    const numAlign = Math.floor(ver / 7) + 2;
    result -= (25 * numAlign - 10) * numAlign - 55;
    if (ver >= 7) result -= 36;
  }
  return result;
}

function numDataCodewords(ver, ecl) {
  return Math.floor(numRawDataModules(ver) / 8)
    - ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver] * NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver];
}

// -- Reed-Solomon over GF(2^8 / 0x11D) --------------------------------------

function gfMultiply(x, y) {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  return z & 0xff;
}

function rsDivisor(degree) {
  const result = new Array(degree).fill(0);
  result[degree - 1] = 1;
  let root = 1;
  for (let i = 0; i < degree; i++) {
    for (let j = 0; j < result.length; j++) {
      result[j] = gfMultiply(result[j], root);
      if (j + 1 < result.length) result[j] ^= result[j + 1];
    }
    root = gfMultiply(root, 0x02);
  }
  return result;
}

function rsRemainder(data, divisor) {
  const result = divisor.map(() => 0);
  for (const b of data) {
    const factor = b ^ result.shift();
    result.push(0);
    divisor.forEach((coef, i) => { result[i] ^= gfMultiply(coef, factor); });
  }
  return result;
}

// -- codewords ----------------------------------------------------------------

function utf8Bytes(text) {
  return Array.from(new TextEncoder().encode(text));
}

function dataCodewords(bytes, ver, ecl) {
  const bits = [];
  const append = (val, len) => { for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
  append(0b0100, 4);
  append(bytes.length, ver < 10 ? 8 : 16);
  bytes.forEach(b => append(b, 8));
  const capacity = numDataCodewords(ver, ecl) * 8;
  append(0, Math.min(4, capacity - bits.length));
  append(0, (8 - (bits.length % 8)) % 8);
  for (let pad = 0xec; bits.length < capacity; pad ^= 0xec ^ 0x11) append(pad, 8);
  const codewords = [];
  for (let i = 0; i < bits.length; i += 8) {
    codewords.push(bits.slice(i, i + 8).reduce((acc, bit) => (acc << 1) | bit, 0));
  }
  return codewords;
}

function addEccAndInterleave(data, ver, ecl) {
  const numBlocks = NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver];
  const blockEccLen = ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver];
  const rawCodewords = Math.floor(numRawDataModules(ver) / 8);
  const numShortBlocks = numBlocks - (rawCodewords % numBlocks);
  const shortBlockLen = Math.floor(rawCodewords / numBlocks);
  const divisor = rsDivisor(blockEccLen);
  const blocks = [];
  for (let i = 0, k = 0; i < numBlocks; i++) {
    const dat = data.slice(k, k + shortBlockLen - blockEccLen + (i < numShortBlocks ? 0 : 1));
    k += dat.length;
    const ecc = rsRemainder(dat, divisor);
    if (i < numShortBlocks) dat.push(0);
    blocks.push(dat.concat(ecc));
  }
  const result = [];
  for (let i = 0; i < blocks[0].length; i++) {
    blocks.forEach((block, j) => {
      // Skip the padding byte of the short blocks.
      if (i !== shortBlockLen - blockEccLen || j >= numShortBlocks) result.push(block[i]);
    });
  }
  return result;
}

// -- symbol -------------------------------------------------------------------

class Symbol {
  constructor(ver) {
    this.ver = ver;
    this.size = ver * 4 + 17;
    this.modules = Array.from({ length: this.size }, () => new Array(this.size).fill(false));
    this.isFunction = Array.from({ length: this.size }, () => new Array(this.size).fill(false));
  }

  setFunction(x, y, dark) {
    this.modules[y][x] = dark;
    this.isFunction[y][x] = true;
  }

  alignmentPositions() {
    if (this.ver === 1) return [];
    const numAlign = Math.floor(this.ver / 7) + 2;
    const step = this.ver === 32 ? 26 : Math.ceil((this.ver * 4 + 4) / (numAlign * 2 - 2)) * 2;
    const result = [6];
    for (let pos = this.size - 7; result.length < numAlign; pos -= step) result.splice(1, 0, pos);
    return result;
  }

  drawFunctionPatterns() {
    for (let i = 0; i < this.size; i++) {
      this.setFunction(6, i, i % 2 === 0);
      this.setFunction(i, 6, i % 2 === 0);
    }
    const finder = (x, y) => {
      for (let dy = -4; dy <= 4; dy++) {
        for (let dx = -4; dx <= 4; dx++) {
          const dist = Math.max(Math.abs(dx), Math.abs(dy));
          const xx = x + dx;
          const yy = y + dy;
          if (xx >= 0 && xx < this.size && yy >= 0 && yy < this.size) {
            this.setFunction(xx, yy, dist !== 2 && dist !== 4);
          }
        }
      }
    };
    finder(3, 3);
    finder(this.size - 4, 3);
    finder(3, this.size - 4);
    const pos = this.alignmentPositions();
    const last = pos.length - 1;
    pos.forEach((y, i) => pos.forEach((x, j) => {
      if ((i === 0 && j === 0) || (i === 0 && j === last) || (i === last && j === 0)) return;
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          this.setFunction(x + dx, y + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
        }
      }
    }));
    this.drawFormatBits(ECL.M, 0); // placeholder, redrawn with the chosen mask
    this.drawVersion();
  }

  drawFormatBits(ecl, mask) {
    const data = (ecl.formatBits << 3) | mask;
    let rem = data;
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    const bits = ((data << 10) | rem) ^ 0x5412;
    const bit = i => ((bits >>> i) & 1) !== 0;
    for (let i = 0; i <= 5; i++) this.setFunction(8, i, bit(i));
    this.setFunction(8, 7, bit(6));
    this.setFunction(8, 8, bit(7));
    this.setFunction(7, 8, bit(8));
    for (let i = 9; i < 15; i++) this.setFunction(14 - i, 8, bit(i));
    for (let i = 0; i < 8; i++) this.setFunction(this.size - 1 - i, 8, bit(i));
    for (let i = 8; i < 15; i++) this.setFunction(8, this.size - 15 + i, bit(i));
    this.setFunction(8, this.size - 8, true);
  }

  drawVersion() {
    if (this.ver < 7) return;
    let rem = this.ver;
    for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
    const bits = (this.ver << 12) | rem;
    for (let i = 0; i < 18; i++) {
      const dark = ((bits >>> i) & 1) !== 0;
      const a = this.size - 11 + (i % 3);
      const b = Math.floor(i / 3);
      this.setFunction(a, b, dark);
      this.setFunction(b, a, dark);
    }
  }

  drawCodewords(data) {
    let i = 0;
    for (let right = this.size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vert = 0; vert < this.size; vert++) {
        for (let j = 0; j < 2; j++) {
          const x = right - j;
          const upward = ((right + 1) & 2) === 0;
          const y = upward ? this.size - 1 - vert : vert;
          if (!this.isFunction[y][x] && i < data.length * 8) {
            this.modules[y][x] = ((data[i >>> 3] >>> (7 - (i & 7))) & 1) !== 0;
            i++;
          }
        }
      }
    }
  }

  applyMask(mask) {
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        let invert;
        switch (mask) {
          case 0: invert = (x + y) % 2 === 0; break;
          case 1: invert = y % 2 === 0; break;
          case 2: invert = x % 3 === 0; break;
          case 3: invert = (x + y) % 3 === 0; break;
          case 4: invert = (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0; break;
          case 5: invert = ((x * y) % 2) + ((x * y) % 3) === 0; break;
          case 6: invert = (((x * y) % 2) + ((x * y) % 3)) % 2 === 0; break;
          default: invert = (((x + y) % 2) + ((x * y) % 3)) % 2 === 0;
        }
        if (!this.isFunction[y][x] && invert) this.modules[y][x] = !this.modules[y][x];
      }
    }
  }

  /** ISO/IEC 18004 penalty score (rules N1-N4). */
  penalty() {
    const n = this.size;
    const m = this.modules;
    let score = 0;
    const lines = [];
    for (let i = 0; i < n; i++) {
      lines.push(m[i]);
      lines.push(m.map(row => row[i]));
    }
    for (const line of lines) {
      let run = 1;
      for (let i = 1; i <= n; i++) {
        if (i < n && line[i] === line[i - 1]) {
          run++;
        } else {
          if (run >= 5) score += 3 + (run - 5);
          run = 1;
        }
      }
      // N3: 1:1:3:1:1 finder-like pattern with 4 light modules on one side.
      for (let i = 0; i + 7 <= n; i++) {
        const core = [1, 0, 1, 1, 1, 0, 1].every((v, k) => line[i + k] === Boolean(v));
        if (!core) continue;
        const lightBefore = [1, 2, 3, 4].every(k => i - k < 0 || !line[i - k]);
        const lightAfter = [0, 1, 2, 3].every(k => i + 7 + k >= n || !line[i + 7 + k]);
        if (lightBefore || lightAfter) score += 40;
      }
    }
    for (let y = 0; y + 1 < n; y++) {
      for (let x = 0; x + 1 < n; x++) {
        const c = m[y][x];
        if (c === m[y][x + 1] && c === m[y + 1][x] && c === m[y + 1][x + 1]) score += 3;
      }
    }
    const dark = m.reduce((acc, row) => acc + row.filter(Boolean).length, 0);
    const k = Math.ceil(Math.abs(dark * 20 - n * n * 10) / (n * n)) - 1;
    return score + Math.max(k, 0) * 10;
  }
}

/**
 * Encode `text` into a QR code.
 *
 * @param {string} text
 * @param {object} [opts]
 * @param {'L'|'M'|'Q'|'H'} [opts.ecl='M'] - error correction level
 * @param {number} [opts.mask] - force a mask (0-7) instead of the lowest penalty
 * @param {number} [opts.version] - force a version (1-40) instead of the smallest that fits
 * @returns {{ version: number, size: number, mask: number, modules: boolean[][] }}
 *   `modules[y][x]` is true for a dark module
 */
export function encodeQr(text, opts = {}) {
  const ecl = ECL[opts.ecl || 'M'];
  const bytes = utf8Bytes(text);
  let ver = opts.version;
  if (ver === undefined) {
    for (ver = 1; ver <= 40; ver++) {
      const needed = 4 + (ver < 10 ? 8 : 16) + bytes.length * 8;
      if (needed <= numDataCodewords(ver, ecl) * 8) break;
    }
  }
  if (ver > 40) throw new RangeError('text too long for a QR code');
  const codewords = addEccAndInterleave(dataCodewords(bytes, ver, ecl), ver, ecl);
  let best = null;
  for (const mask of opts.mask !== undefined ? [opts.mask] : [0, 1, 2, 3, 4, 5, 6, 7]) {
    const sym = new Symbol(ver);
    sym.drawFunctionPatterns();
    sym.drawCodewords(codewords);
    sym.applyMask(mask);
    sym.drawFormatBits(ecl, mask);
    const score = opts.mask !== undefined ? 0 : sym.penalty();
    if (!best || score < best.score) best = { sym, mask, score };
  }
  return { version: ver, size: best.sym.size, mask: best.mask, modules: best.sym.modules };
}
