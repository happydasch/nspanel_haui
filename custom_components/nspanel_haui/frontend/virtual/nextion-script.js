/**
 * NSPanel HAUI - Nextion script interpreter for the virtual panel.
 *
 * Runs the subset of Nextion script the HMI's event code and the hub's
 * display commands use:
 *
 * - assignments `obj.attr=expr`, `obj.attr+=expr` (also -=, *=, /=, %=), to
 *   `sysN` globals, page-qualified `page.obj.attr` and indexed `b[expr].attr`
 * - `if(...)` / `else` and `for(init;cond;step)` blocks with braces on their own
 *   lines
 * - the commands `vis`, `click`, `tsw`, `ref`, `xpic`, `cirs`, `cls`, `covx`,
 *   `page`, `sendme`, `doevents`
 *
 * Arithmetic is integer and strictly left to right, as on the Nextion.
 * Anything else is reported through `host.warn()`, never silently skipped.
 *
 * The interpreter knows nothing about pages or rendering; it talks to a host
 * (see nextion-display.js) through `getAttr`, `setAttr`, `command` and `warn`.
 */

const ASSIGN_RE = /^([A-Za-z_][\w]*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*)*)\s*([+\-*/%]?=)(?!=)(.*)$/;
const COMMAND_RE = /^([a-z_]\w*)(?:\s+(.*))?$/;

/** Commands handled by the host; their arguments are evaluated first. */
const COMMANDS = new Set([
  'vis', 'click', 'tsw', 'ref', 'xpic', 'cirs', 'cls', 'covx', 'page',
  'sendme', 'doevents', 'printh', 'prints',
]);

// ---------------------------------------------------------------------------
// Parsing
// ---------------------------------------------------------------------------

/** Remove a trailing `//` comment that is not inside a string literal. */
function stripComment(line) {
  let inString = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    // Inside a literal a backslash escapes the next character (\r, \", \\).
    if (inString && ch === '\\') {
      i++;
      continue;
    }
    if (ch === '"') inString = !inString;
    if (!inString && ch === '/' && line[i + 1] === '/') return line.slice(0, i);
  }
  return line;
}

function cleanLines(code) {
  return code
    .split(/\r?\n/)
    .map(l => stripComment(l).trim())
    .filter(l => l !== '');
}

/** Return the index after the `{ ... }` block starting at `start` and its body lines. */
function readBlock(lines, start) {
  if (lines[start] !== '{') throw new SyntaxError(`expected "{" before: ${lines[start] ?? 'end'}`);
  let depth = 0;
  for (let i = start; i < lines.length; i++) {
    const line = lines[i];
    if (line === '{') depth++;
    else if (line === '}' || line === '}else') depth--;
    if (depth === 0) {
      // `}else` closes this block and opens the else branch on the next lines.
      return { body: lines.slice(start + 1, i), next: i, closesWithElse: line === '}else' };
    }
  }
  throw new SyntaxError('unclosed "{"');
}

function parseLines(lines) {
  const nodes = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const ifMatch = /^if\s*\((.*)\)$/.exec(line);
    const forMatch = /^for\s*\((.*);(.*);(.*)\)$/.exec(line);
    if (ifMatch) {
      const then = readBlock(lines, i + 1);
      let elseBody = [];
      i = then.next + 1;
      if (then.closesWithElse || lines[i] === 'else') {
        if (!then.closesWithElse) i++;
        const other = readBlock(lines, i);
        elseBody = other.body;
        i = other.next + 1;
      }
      nodes.push({ kind: 'if', cond: ifMatch[1], then: parseLines(then.body), else: parseLines(elseBody) });
    } else if (forMatch) {
      const body = readBlock(lines, i + 1);
      nodes.push({
        kind: 'for', init: forMatch[1].trim(), cond: forMatch[2].trim(), step: forMatch[3].trim(),
        body: parseLines(body.body),
      });
      i = body.next + 1;
    } else {
      nodes.push({ kind: 'stmt', text: line });
      i++;
    }
  }
  return nodes;
}

const parseCache = new Map();

/** Parse script source into statement nodes (cached; event code is reused). */
function parseScript(code) {
  let nodes = parseCache.get(code);
  if (!nodes) {
    nodes = parseLines(cleanLines(code));
    parseCache.set(code, nodes);
  }
  return nodes;
}

// ---------------------------------------------------------------------------
// Expressions
// ---------------------------------------------------------------------------

function tokenize(expr) {
  const tokens = [];
  let i = 0;
  while (i < expr.length) {
    const ch = expr[i];
    if (ch === ' ' || ch === '\t') { i++; continue; }
    if (ch === '"') {
      let j = i + 1;
      let text = '';
      while (j < expr.length && expr[j] !== '"') {
        if (expr[j] === '\\' && j + 1 < expr.length) {
          const esc = expr[j + 1];
          text += esc === 'r' ? '\n' : esc;
          j += 2;
        } else {
          text += expr[j++];
        }
      }
      if (j >= expr.length) throw new SyntaxError(`unterminated string: ${expr}`);
      tokens.push({ t: 'str', v: text });
      i = j + 1;
      continue;
    }
    const num = /^-?\d+/.exec(expr.slice(i));
    // A leading "-" is a sign only where an operand is expected.
    if (num && (ch !== '-' || !tokens.length || tokens[tokens.length - 1].t === 'op')) {
      tokens.push({ t: 'num', v: parseInt(num[0], 10) });
      i += num[0].length;
      continue;
    }
    const ref = /^[A-Za-z_]\w*(?:\[[^\]]+\])?(?:\.[A-Za-z_]\w*)*/.exec(expr.slice(i));
    if (ref) {
      tokens.push({ t: 'ref', v: ref[0] });
      i += ref[0].length;
      continue;
    }
    const op = /^(==|!=|<=|>=|&&|\|\||[+\-*/%<>])/.exec(expr.slice(i));
    if (op) {
      tokens.push({ t: 'op', v: op[0] });
      i += op[0].length;
      continue;
    }
    throw new SyntaxError(`unexpected "${ch}" in: ${expr}`);
  }
  return tokens;
}

function applyOp(op, a, b) {
  switch (op) {
    case '+': return typeof a === 'string' || typeof b === 'string' ? `${a}${b}` : (a + b) | 0;
    case '-': return (a - b) | 0;
    case '*': return Math.imul(a, b);
    case '/': return b === 0 ? 0 : Math.trunc(a / b);
    case '%': return b === 0 ? 0 : a % b;
    case '==': return a === b ? 1 : 0;
    case '!=': return a !== b ? 1 : 0;
    case '<': return a < b ? 1 : 0;
    case '>': return a > b ? 1 : 0;
    case '<=': return a <= b ? 1 : 0;
    case '>=': return a >= b ? 1 : 0;
    case '&&': return a && b ? 1 : 0;
    case '||': return a || b ? 1 : 0;
    default: throw new SyntaxError(`unknown operator ${op}`);
  }
}

/** Evaluate an expression left to right (no operator precedence, as on the Nextion). */
export function evaluate(expr, host) {
  const tokens = tokenize(expr);
  if (!tokens.length) throw new SyntaxError('empty expression');
  const operand = tok => {
    if (tok.t === 'num' || tok.t === 'str') return tok.v;
    if (tok.t === 'ref') return host.getAttr(resolveRef(tok.v, host));
    throw new SyntaxError(`expected a value in: ${expr}`);
  };
  let value = operand(tokens[0]);
  for (let i = 1; i < tokens.length; i += 2) {
    const op = tokens[i];
    if (op.t !== 'op' || i + 1 >= tokens.length) throw new SyntaxError(`bad expression: ${expr}`);
    value = applyOp(op.v, value, operand(tokens[i + 1]));
  }
  return value;
}

/**
 * Resolve a reference into `{ page, comp, attr }` or `{ global }`.
 *
 * `sys0` is a global; `obj.attr` a widget of the current page (`page` null);
 * `pageName.obj.attr` a widget of another page; `b[expr].attr` the widget with
 * that id on the current page.
 */
function resolveRef(ref, host) {
  const indexed = /^b\[(.+)\]\.(\w+)$/.exec(ref);
  if (indexed) return { page: null, comp: Number(evaluate(indexed[1], host)), attr: indexed[2] };
  const parts = ref.split('.');
  if (parts.length === 1) return { global: parts[0] };
  if (parts.length === 2) return { page: null, comp: parts[0], attr: parts[1] };
  if (parts.length === 3) return { page: parts[0], comp: parts[1], attr: parts[2] };
  throw new SyntaxError(`unsupported reference: ${ref}`);
}

// ---------------------------------------------------------------------------
// Statements
// ---------------------------------------------------------------------------

function splitArgs(args) {
  const out = [];
  let depth = 0;
  let inString = false;
  let current = '';
  for (let i = 0; i < args.length; i++) {
    const ch = args[i];
    if (inString && ch === '\\' && i + 1 < args.length) {
      current += ch + args[i + 1];
      i++;
      continue;
    }
    if (ch === '"') inString = !inString;
    if (!inString && ch === '[') depth++;
    if (!inString && ch === ']') depth--;
    if (!inString && depth === 0 && ch === ',') {
      out.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  if (current.trim() !== '') out.push(current.trim());
  return out;
}

/** The text of a Nextion string literal: \r is a line break, \" and \\ the characters. */
function unescapeText(literal) {
  return literal.replace(/\\(["\\r])/g, (_, ch) => (ch === 'r' ? '\n' : ch));
}

/** Commands whose first argument names a widget (not a value to evaluate). */
const NAMED_FIRST_ARG = new Set(['vis', 'click', 'tsw', 'ref', 'page']);

function runStatement(text, host) {
  // Hub text writes are by far the most common command; their text may hold
  // characters the expression tokenizer would reject, so take them verbatim.
  const txt = /^([\w.[\]]+)\.txt="(.*)"$/s.exec(text);
  if (txt && !/[^\\]"\s*\+/.test(text)) {
    host.setAttr(resolveRef(`${txt[1]}.txt`, host), unescapeText(txt[2]));
    return;
  }
  const assign = ASSIGN_RE.exec(text);
  if (assign) {
    const [, target, op, expr] = assign;
    const ref = resolveRef(target, host);
    let value = evaluate(expr.trim(), host);
    if (op !== '=') value = applyOp(op[0], host.getAttr(ref), value);
    host.setAttr(ref, value);
    return;
  }
  const cmd = COMMAND_RE.exec(text);
  if (cmd && COMMANDS.has(cmd[1])) {
    const args = splitArgs(cmd[2] ?? '');
    const values = args.map((arg, i) => (i === 0 && NAMED_FIRST_ARG.has(cmd[1]) ? arg : evaluate(arg, host)));
    if (cmd[1] === 'covx') {
      // covx src,dst,len,format: dst is a reference to write, src a value.
      const dst = resolveRef(args[1], host);
      const src = evaluate(args[0], host);
      host.setAttr(dst, typeof src === 'string' ? (parseInt(src, 10) || 0) : String(src));
      return;
    }
    host.command(cmd[1], values);
    return;
  }
  host.warn(`unsupported statement: ${text}`);
}

function runNodes(nodes, host, budget) {
  for (const node of nodes) {
    if (node.kind === 'stmt') {
      try {
        runStatement(node.text, host);
      } catch (err) {
        host.warn(`${err.message} (in: ${node.text})`);
      }
    } else if (node.kind === 'if') {
      runNodes(evaluate(node.cond, host) ? node.then : node.else, host, budget);
    } else if (node.kind === 'for') {
      runStatement(node.init, host);
      while (evaluate(node.cond, host)) {
        if (--budget.loops < 0) {
          host.warn(`loop limit reached in for(${node.cond})`);
          return;
        }
        runNodes(node.body, host, budget);
        runStatement(node.step.replace(/^(.+)\+\+$/, '$1+=1').replace(/^(.+)--$/, '$1-=1'), host);
      }
    }
  }
}

/**
 * Run script source against a host.
 *
 * @param {string} code - event code or one or more commands, one per line
 * @param {object} host - `{ getAttr(ref), setAttr(ref, value), command(name, args), warn(msg) }`
 */
export function runScript(code, host) {
  let nodes;
  try {
    nodes = parseScript(code);
  } catch (err) {
    host.warn(`${err.message} (in: ${code.slice(0, 80)})`);
    return;
  }
  runNodes(nodes, host, { loops: 10000 });
}
