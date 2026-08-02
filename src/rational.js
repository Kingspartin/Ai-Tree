/**
 * Exact rational arithmetic.
 *
 * Pattern discovery lives or dies on exact comparisons: 1/3 fitted from floats
 * would never match the term it is supposed to reproduce. Every candidate law is
 * therefore fitted and validated in rationals, and only converted to plain
 * numbers on the way out.
 *
 * Any operation that leaves the safe integer range throws `Overflow`, which the
 * search engine treats as "this method does not fit" rather than a crash.
 */

export class Overflow extends Error {}

const safe = (value, context) => {
  if (!Number.isSafeInteger(value)) {
    throw new Overflow(`rational overflow in ${context}`);
  }
  return value;
};

function gcd(a, b) {
  a = Math.abs(a);
  b = Math.abs(b);
  while (b) [a, b] = [b, a % b];
  return a;
}

export class Rational {
  /** @param {number} n numerator @param {number} d denominator */
  constructor(n, d = 1) {
    if (d === 0) throw new RangeError('division by zero');
    safe(n, 'numerator');
    safe(d, 'denominator');
    if (d < 0) {
      n = -n;
      d = -d;
    }
    const g = gcd(n, d) || 1;
    this.n = n / g;
    this.d = d / g;
    Object.freeze(this);
  }

  /** Build from a number (integers and short decimals are exact) or a Rational. */
  static from(value) {
    if (value instanceof Rational) return value;
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new TypeError(`cannot convert to rational: ${value}`);
    }
    if (Number.isInteger(value)) return new Rational(value);

    const text = value.toString();
    const match = /^(-?)(\d+)\.(\d+)$/.exec(text);
    if (!match) throw new Overflow(`cannot represent exactly: ${text}`);
    const [, sign, whole, fraction] = match;
    const d = 10 ** fraction.length;
    const n = Number(whole) * d + Number(fraction);
    return new Rational(sign === '-' ? -n : n, d);
  }

  add(other) {
    const o = Rational.from(other);
    return new Rational(safe(this.n * o.d, 'add') + safe(o.n * this.d, 'add'), safe(this.d * o.d, 'add'));
  }

  sub(other) {
    return this.add(Rational.from(other).neg());
  }

  mul(other) {
    const o = Rational.from(other);
    return new Rational(safe(this.n * o.n, 'mul'), safe(this.d * o.d, 'mul'));
  }

  div(other) {
    const o = Rational.from(other);
    if (o.isZero()) throw new RangeError('division by zero');
    return new Rational(safe(this.n * o.d, 'div'), safe(this.d * o.n, 'div'));
  }

  neg() {
    return new Rational(-this.n, this.d);
  }

  pow(exponent) {
    if (!Number.isInteger(exponent) || exponent < 0) {
      throw new RangeError('exponent must be an integer >= 0');
    }
    let result = ONE;
    let base = this;
    let e = exponent;
    while (e > 0) {
      if (e & 1) result = result.mul(base);
      e >>= 1;
      if (e) base = base.mul(base);
    }
    return result;
  }

  eq(other) {
    const o = Rational.from(other);
    return this.n === o.n && this.d === o.d;
  }

  isZero() {
    return this.n === 0;
  }

  isInteger() {
    return this.d === 1;
  }

  abs() {
    return this.n < 0 ? this.neg() : this;
  }

  toNumber() {
    return this.n / this.d;
  }

  toString() {
    return this.d === 1 ? String(this.n) : `${this.n}/${this.d}`;
  }
}

export const R = (n, d = 1) => new Rational(n, d);
export const ZERO = R(0);
export const ONE = R(1);

/** Convert a list of numbers to rationals. */
export function toRationals(values) {
  return values.map((value) => Rational.from(value));
}

/**
 * Solve a square linear system by Gauss-Jordan elimination over rationals.
 *
 * @param {Rational[][]} matrix  rows of coefficients
 * @param {Rational[]} vector    right hand side
 * @returns {Rational[]|null}    solution, or null when the system is singular
 */
export function solve(matrix, vector) {
  const size = vector.length;
  const rows = matrix.map((row, i) => [...row, vector[i]]);

  for (let column = 0; column < size; column++) {
    let pivot = -1;
    for (let row = column; row < size; row++) {
      if (!rows[row][column].isZero()) {
        pivot = row;
        break;
      }
    }
    if (pivot === -1) return null;
    [rows[column], rows[pivot]] = [rows[pivot], rows[column]];

    const head = rows[column][column];
    rows[column] = rows[column].map((cell) => cell.div(head));

    for (let row = 0; row < size; row++) {
      if (row === column || rows[row][column].isZero()) continue;
      const factor = rows[row][column];
      rows[row] = rows[row].map((cell, i) => cell.sub(factor.mul(rows[column][i])));
    }
  }
  return rows.map((row) => row[size]);
}
