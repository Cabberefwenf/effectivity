# ADR 0001: Effectivity key and hold point ordering

Status: Accepted (rule version 1.0.0)

## Context

Effectivity ranges name units by hull, serial, or lot. These are ordered
tokens, not dates and not always integers: a sample hull can be `0123A`. A plain
string compare puts `100` before `99`. A plain integer parse cannot represent
`0123A`. Hold points (`HP010`, `HP020`) need an order too, so that "has the
unit reached the incorporation hold point yet" can be answered.

## Decision

One grammar is used for both effectivity keys and hold point tokens.

```
key    = prefix number [suffix]
prefix = 0..8 characters from A-Z
number = 1 to 18 characters from 0-9
suffix = 0 or 1 character from A-Z
```

- The 18-digit cap keeps the integer conversion independent of the Python
  version and of `PYTHONINTMAXSTRDIGITS`; a longer number is rejected.
- ASCII only. Upper case only. No whitespace, no separators, no sign.
  Anything else is rejected with a `KeyFormatError` naming the offending
  value. Nothing is stripped, upper-cased, or otherwise coerced.
- Examples: `0123`, `0123A`, `HP010`, `SN00417`, `B0007`.
- Rejected: `` (empty), `123a`, ` 123`, `12 3`, `H-12`, `123AB`, `ABC`, `-1`,
  `123\n`, non-ASCII digits, numbers of more than 18 digits.

### Comparison

A parsed key is the tuple `(prefix, int(number), suffix)`. Keys compare as
tuples:

1. prefix, as a string (this only matters for sorting; see "Different
   prefixes" below);
2. number, as an integer, so zero padding is not significant:
   `0123` equals `123`, and `99 < 100`;
3. suffix, as a string, where the empty suffix sorts before any letter:
   `123 < 123A < 123B < 124`.

Because a suffix is at most one letter, there is no length-versus-alphabet
ambiguity (`Z` versus `AA`). That is why the grammar stops at one letter.

Equivalent definition, used as an independent oracle in the property test:
pad the number to a fixed width and compare the strings
`prefix + zero_padded_number + suffix`.

### Effectivity range

`effectivity_from` and `effectivity_to` are both inclusive. A change row is
rejected if:

- either bound is malformed;
- the two bounds have different prefixes (a range does not span series);
- `effectivity_from > effectivity_to`.

A unit is in effectivity when its key has the same prefix as the range and
`from <= key <= to`.

### Different prefixes

- Effectivity: a unit whose key prefix differs from the range prefix is
  **out of effectivity**. A `B0009` unit is simply not in the `0121..0124`
  series. This is intentional, not an error.
- Hold points: comparing hold points with different prefixes (`HP020` versus
  `GATE030`) has no defined order. The resolver raises
  `IncomparableKeysError` and the run fails. It does not guess. This is only
  evaluated for pairs that are in effectivity.

### Hold position

The unit row's `hold_point` is the latest hold point the unit has reached;
`hold_point_status` says whether it is still open there or closed.
Against the change's `incorporation_hold_point`:

| unit hold_point vs incorporation hold | unit status | position |
|---|---|---|
| `<` | any | not arrived |
| `==` | open | at the point |
| `==` | closed | passed |
| `>` | any | passed |

## Consequences

- Rule is small, total on valid keys, and tested table-driven plus with a
  seeded random property test.
- It is **not** a general hull-number parser. Hyphenated lots (`LOT-12`),
  multi-letter suffixes, lower-case keys, and date-based keys are rejected,
  not interpreted. See LIMITS.md.
- Hold point order depends on this naming convention. If a program numbers its
  hold points so that the token order is not the process order, this tool will
  classify wrongly. That cannot be tested away; it is listed in LIMITS.md.
