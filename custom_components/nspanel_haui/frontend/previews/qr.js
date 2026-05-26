/**
 * NSPanel HAUI - Editor - Panel preview: QR.
 */
import { html } from '../lit-import.js';

/**
 * Generate a flat 15x15 QR-like pattern with three proper finder patterns
 * (top-left, top-right, bottom-left) and a dense data area in bottom-right.
 * The finder patterns follow the standard QR 7x7 square-in-square layout.
 */
function generateQRMatrix15() {
  const finder = [
    [1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1],
    [1,0,1,1,1,0,1],
    [1,0,1,1,1,0,1],
    [1,0,1,1,1,0,1],
    [1,0,0,0,0,0,1],
    [1,1,1,1,1,1,1],
  ];
  const data = [
    [1,0,1,0,1,0,1],
    [0,1,1,1,0,0,1],
    [1,0,0,1,1,1,0],
    [1,1,0,0,0,1,0],
    [0,1,1,0,1,0,1],
    [1,0,0,1,1,1,0],
    [0,1,1,0,0,1,1],
  ];
  const cells = [];
  for (let r = 0; r < 15; r++) {
    for (let c = 0; c < 15; c++) {
      if (r < 7 && c < 7) cells.push(finder[r][c]);
      else if (r < 7 && c >= 8) cells.push(finder[r][c - 8]);
      else if (r >= 8 && c < 7) cells.push(finder[r - 8][c]);
      else if (r >= 8 && c >= 8) cells.push(data[r - 8][c - 8]);
      else cells.push(0);
    }
  }
  return cells;
}

const QR_MATRIX = generateQRMatrix15();

function renderQRMatrix(size, isBig) {
  const px = size || '4px';
  const gridStyle = isBig
    ? ''
    : `grid-template-columns:repeat(15,${px});grid-template-rows:repeat(15,${px})`;
  return html`
    <div class="pg-qr-matrix-bg${isBig ? ' pg-qr-matrix-bg--big' : ''}">
      <div class="pg-preview-qr-matrix${isBig ? ' pg-preview-qr-matrix--big' : ''}" style="${gridStyle}">
        ${QR_MATRIX.map(v => html`<div class="pg-preview-qr-cell${v ? ' fill' : ' empty'}"></div>`)}
      </div>
    </div>`;
}

export function renderQRPreview(_host, p, _pIdx, _pt) {
  if (p.start_big_qr === true) {
    return {
      content: html`
        <div class="pg-preview-center-col" style="width:100%;flex:1;justify-content:center;">
          <div class="pg-qr-preview-big-wrap">
            ${renderQRMatrix(undefined, true)}
          </div>
        </div>`,
      headerButtonOverrides: { rightSec: { icon: 'mdi:loupe', accent: true } },
    };
  }
  const showInfo = p.show_info !== false;
  const items = p.items || [];
  let sideContent;
  if (showInfo) {
    sideContent = html`
      <div class="pg-preview-qr-info-row">
        <ha-icon icon="mdi:wifi" class="pg-qr-icon"></ha-icon>
        <div class="pg-preview-qr-info-text">
          <div class="pg-preview-text-line narrow" style="width:45%;"></div>
          <div class="pg-preview-text-line wide" style="width:80%;"></div>
        </div>
      </div>
      <div class="pg-preview-qr-info-row">
        <ha-icon icon="mdi:key" class="pg-qr-icon"></ha-icon>
        <div class="pg-preview-qr-info-text">
          <div class="pg-preview-text-line narrow" style="width:50%;"></div>
          <div class="pg-preview-text-line wide" style="width:70%;"></div>
        </div>
      </div>`;
  } else if (items.length) {
    sideContent = items.slice(0, 2).map(item => html`
      <div class="pg-preview-qr-info-row">
        <ha-icon icon="${item.icon || 'mdi:help-circle-outline'}" class="pg-qr-icon"></ha-icon>
        <div class="pg-preview-qr-info-text">
          <div class="pg-preview-text-line narrow" style="width:45%;"></div>
          <div class="pg-preview-text-line wide" style="width:80%;"></div>
        </div>
      </div>`);
  } else {
    sideContent = html`
      <div class="pg-card-preview-line" style="width:80px;"></div>
      <div class="pg-card-preview-line" style="width:50px;"></div>`;
  }
  return {
    content: html`
      <div class="pg-preview-qr-matrix-wrap">
        ${renderQRMatrix('clamp(3px, 1.4cqi, 5px)')}
      </div>
      <div class="pg-preview-qr-side">
        ${sideContent}
      </div>`,
    contentClass: 'pg-card-preview-qr-small',
  };
}
