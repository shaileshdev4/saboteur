# Misconception Library - Specification

> This is the heart of _The Saboteur_. Random corruption would be obvious and boring; these are calibrated errors that mirror how real students (and AIs) actually fail.

Each entry below is implemented in `engine/misconceptions/` as a class with:

- a **predicate** (`applies_to(step, solution, step_index)`) deciding whether the misconception can attack a particular step in context
- a **transform** (`apply(step, solution, step_index)`) returning a corrupted Step
- metadata: `id`, `name`, `description`, `category`, `difficulty` (1 = easy to catch, 5 = subtle)

**Invariants every misconception must satisfy** (enforced by `tests/test_misconceptions.py`):

1. There exists at least one canonical problem in our generators where the predicate matches some step.
2. After `apply()`, the resulting expression is well-formed (no NaN, no infinity, parses cleanly via SymPy).
3. The resulting expression is _not_ SymPy-equivalent to the canonical truth - i.e., a real error was introduced.

The sabotage engine has a final safety net: if a misconception silently no-ops (returns an equivalent step), the engine retries with a different candidate before falling back to "clean."

---

## Categories

| Category             | Count | What it attacks                                                                |
| -------------------- | ----- | ------------------------------------------------------------------------------ |
| `sign`               | 7     | Sign errors during transposition, distribution, factoring, formula application |
| `distribution`       | 3     | Failing to distribute multiplication/exponents across a sum                    |
| `coefficient`        | 3     | Dropping/off-by-one slips and combining unlike terms                           |
| `cancellation`       | 1     | Illegal cancellation across a sum in fractions                                 |
| `operation_one_side` | 1     | Applying an operation to one side of an equation only                          |

**Total: 15 misconceptions** in v1.2. Phase 2 plan called for ~25 by end of phase; current state is 15 with the remaining 10 spec'd as additions in the table below.

---

## sign - Sign-related errors

### 1. `sign_flip_transpose` - Sign flip on transposition · difficulty 2

**Description:** When moving a term across the equals sign, the sign is _kept the same_ instead of flipping.

**Mechanism (delta-based):** Given the canonical transpose `LHS_prev → LHS_curr`, we compute `delta = LHS_prev - LHS_curr` (the term that moved). The correct result has `RHS_curr = RHS_prev - delta`. The buggy result keeps the sign: `RHS_bug = RHS_prev + delta`.

**Example:**

```
Truth:  3x + 6 = 21  →  3x = 15
Shown:  3x + 6 = 21  →  3x = 27       (added 6 instead of subtracting)
```

**Real-world source:** The single most common arithmetic error in school algebra. Reported by Hart (1981), Kieran (1992); reproduced by LLMs as documented in Frieder et al. (2023) GHOSTS benchmark.

---

### 2. `distribute_neg_misses_second_term` - Distributing a negative only to the first term · difficulty 3

**Description:** When distributing a negative across a sum, only the first term gets negated.

**Example:**

```
Truth:  −(x + 3) = −x − 3
Shown:  −(x + 3) = −x + 3
```

**Why it's subtle:** The first sign is correct, which builds confidence. The student often doesn't notice the second sign was left positive.

---

### 3. `wrong_root_in_factoring` - Wrong root from factoring · difficulty 2

**Description:** The student factors correctly but reads one root with the wrong sign.

**Example:**

```
Truth:  (x − 3)(x + 5) = 0  →  x = 3, x = −5
Shown:  (x − 3)(x + 5) = 0  →  x = 3, x = 5
```

**Why it's subtle:** One root is right, so a quick check ("is one of these a root?") passes.

---

### 4. `qf_sign_error` - Sign error applying the quadratic formula · difficulty 3

**Description:** In `x = (−b ± √D)/(2a)`, the student forgets to negate `b`. Most common when `b` is already negative (the double-negative trips them up).

**Example:** For `x² − 5x + 6 = 0` (where `b = −5`):

```
Truth:  x = (5 + 1)/2 = 3   and   x = (5 − 1)/2 = 2
Shown:  x = (−5 + 1)/2 = −2   and   x = (−5 − 1)/2 = −3
```

**Implementation:** We reconstruct the buggy formula `(+b ± √D)/(2a)` from the canonical quadratic and present its branches.

---

### 5. `qf_discriminant_error` - Wrong discriminant calculation · difficulty 4

**Description:** The student computes `b² − 4ac` with a sign slip, most commonly `b² + 4ac` (forgetting the `−`).

**Why it's hard to catch:** This corrupts the discriminant number itself. Players who don't recompute it from scratch can miss it - they see _a_ number, and the rest of the formula application is mechanically correct.

**Example:**

```
For 2x² − 5x − 3 = 0:
Truth:  D = (−5)² − 4(2)(−3) = 25 + 24 = 49
Shown:  D = (−5)² + 4(2)(−3) = 25 − 24 = 1
```

---

### 6. `incorrect_factoring` - Incorrect factoring · difficulty 3

**Description:** A quadratic is factored into a product that _doesn't equal_ the original. Common pattern: correct magnitudes, wrong signs.

**Example:**

```
Truth:  x² − 5x + 6 = (x − 2)(x − 3)
Shown:  x² − 5x + 6 = (x + 2)(x + 3)
```

**Implementation note:** We flip the sign on the constant in one of the factors, producing a factoring whose expansion differs from the canonical quadratic.

---

## distribution - Failure to distribute properly

### 7. `exponent_over_sum` - Distributing exponent over a sum · difficulty 3

**Description:** `(a + b)² → a² + b²` - the cross term `2ab` is dropped.

**Example:**

```
Truth:  (x + 4)² = x² + 8x + 16
Shown:  (x + 4)² = x² + 16
```

**Real-world source:** "Freshman's dream" - one of the most-documented misconceptions in algebra education research (Matz 1982, Tirosh & Stavy 1999). LLMs reproduce this in symbolic chain-of-thought.

---

### 8. `distribution_drops_term` - Distribution misses a term · difficulty 2

**Description:** When distributing a factor over a sum of 2+ terms, one inner term doesn't get multiplied.

**Example:**

```
Truth:  3(x + 2y + 1) = 3x + 6y + 3
Shown:  3(x + 2y + 1) = 3x + 2y + 3   (the middle term wasn't multiplied)
```

---

## coefficient - Numeric slips

### 9. `dropped_coefficient` - Coefficient dropped · difficulty 2

**Description:** A coefficient silently vanishes from a term. E.g., `3x` becomes `x`.

**Example:**

```
Truth:  5x + 2 = 17  →  5x = 15
Shown:  5x + 2 = 17  →   x = 15
```

---

### 10. `off_by_one_constant` - Off-by-one constant slip · difficulty 4

**Description:** A constant changes by ±1 during a simplification.

**Why it's hard:** It's _just_ one off. There's no structural cue - only the player who recomputes the arithmetic catches it. This is the calibration challenge: when the AI's work _looks_ careful, do you still check?

**Example:**

```
Truth:  3x = 21  →  x = 7
Shown:  3x = 21  →  x = 8
```

---

## cancellation - Illegal cancellation

### 11. `cancellation_across_sum` - Illegal cancellation across a sum · difficulty 4

**Description:** A common factor is "cancelled" across a sum, dropping the additive structure of the rest.

**Example:**

```
Truth:  (3x + 6)/3 = x + 2
Shown:  (3x + 6)/3 = x + 6      (the 3 in 6/3 was "cancelled" but only the first term divided)
```

**Real-world source:** Documented persistently in Brown (1981) "BUGGY" project; the canonical "subtract-the-smaller-from-the-larger" cousin in algebra.

---

## operation_one_side - One-sided operations

### 12. `operation_one_side_only` - Operation applied to only one side · difficulty 3

**Description:** An arithmetic operation is applied to one side of an equation but forgotten on the other.

**Example:**

```
Truth:  2x + 6 = 10  →  2x = 4
Shown:  2x + 6 = 10  →  2x = 10
```

**Why it's a real failure mode:** Students who "move things across the equals sign" mechanically sometimes forget the equation is a relation, not a procedure.

---

## Phase 2 additions (planned, not yet implemented)

These extend the library to ~25 entries. None require new infrastructure - each is one class.

| Planned ID                     | Category     | Difficulty | Description                                                  |
| ------------------------------ | ------------ | ---------- | ------------------------------------------------------------ |
| `sqrt_over_sum`                | distribution | 4          | `√(a² + b²) → a + b`                                         |
| `inverse_distribution`         | distribution | 3          | `a/(b + c) → a/b + a/c`                                      |
| `linear_inequality_sign`       | sign         | 3          | Forgetting to flip inequality on multiply/divide by negative |
| `extraneous_square_root`       | sign         | 4          | Dropping the ± from `x² = k → x = ±√k`                       |
| `like_terms_misgroup`          | coefficient  | 3          | Combining `2x + 3x²` into `5x²`                              |
| `fraction_invert_only_one`     | fraction     | 4          | `(a/b) / (c/d) → (a/b) × (c/d)` (forgetting to invert)       |
| `factor_by_grouping_sign`      | sign         | 3          | Sign error in factor-by-grouping                             |
| `square_completion_constant`   | coefficient  | 4          | Off-by-(b/2)² when completing the square                     |
| `vieta_sign_flip`              | sign         | 3          | Mixing up sum/product sign in Vieta's formulas               |
| `power_of_product`             | distribution | 2          | `(ab)² → ab²` instead of `a²b²`                              |
| `negative_exponent_arithmetic` | sign         | 4          | `x⁻¹ + y⁻¹ → (x + y)⁻¹`                                      |
| `radical_simplification`       | distribution | 4          | `√(ab) → √a + √b`                                            |
| `equation_squaring_intro`      | sign         | 5          | Squaring both sides introduces extraneous roots              |

---

## How difficulty was chosen

Difficulty ratings 1–5 will be **empirically calibrated** by Pilot Test #1, not just hand-picked. Initial values are based on:

- The depth of conceptual mistake (e.g., `cancellation_across_sum` exposes a deep misunderstanding of fractions; `off_by_one_constant` is just an arithmetic slip)
- The visual cue available to the player (a sign change is more visible than an arithmetic slip)
- The number of steps between the corruption and a place where a quick consistency check would catch it

After Pilot #1, the difficulty score for each misconception will be replaced by `1 + 4 * (1 - empirical_catch_rate)`, where `empirical_catch_rate` is the fraction of pilot players who caught it. This is what makes the difficulty score "real" rather than guessed.

---

## What this library is _not_

- **Not a curriculum.** We're not teaching algebra; we're training verification skill. A player who already knows algebra has nothing new to learn about the math - they have something new to learn about _paying attention to AI work_.
- **Not exhaustive.** Twelve in v1, ~25 planned. Real classrooms see hundreds. We focus on the most-reproduced-by-LLM patterns because that's what makes the trainer relevant to the 2026 problem.
- **Not a replacement for symbolic verification.** Every transform is verified _wrong_ by SymPy. The library is "things students/AIs do that produce a wrong result." The library itself doesn't decide correctness - `engine/verifier.py` does.

---

## Phase 2 expansion (added in v1.2)

### 13. `combining_unlike_terms` - Combining unlike terms · difficulty 3

**Description:** Different-degree terms are added as if they were like terms. E.g., `2x` and `3x²` combined into `5x²`.

**Example:**

```
Truth:  x² + 2x + 1 = b   →   (next step preserves all three terms)
Shown:  x² + 3 = b         (the 2x got absorbed into the constant)
```

**Category:** `coefficient`

---

### 14. `squaring_as_diff_of_squares` - Squaring a binomial as a difference of squares · difficulty 4

**Description:** Confuses two distinct identities. `(x - a)²` is incorrectly expanded as `x² - a²` (the difference-of-squares factoring pattern) instead of `x² - 2ax + a²`.

**Example:**

```
Truth:  (x - 3)² = 25  →  x² - 6x + 9 = 25
Shown:  (x - 3)² = 25  →  x² - 9 = 25
```

**Why it's subtle (difficulty 4):** Both identities feel familiar; a quick check ("squaring gives me an x² and a constant") passes. The missing middle term is what catches it.

**Category:** `distribution`

---

### 15. `negative_factor_distribution_sign` - Sign error when distributing a negative coefficient · difficulty 3

**Description:** When distributing a negative coefficient (other than -1) across a sum, one or more terms keep the wrong sign.

**Example:**

```
Truth:  -3(x - 2) = 12  →  -3x + 6 = 12
Shown:  -3(x - 2) = 12  →  -3x - 6 = 12
```

**Distinction from `distribute_neg_misses_second_term`:** That one is specific to the `-(a+b)` (unit-negative) case. This one handles `-k(a-b)` for any `k`, which is the more common form in real algebra problems.

**Category:** `sign`
