/**
 * Request caps. api/resolve.py enforces them (src/effectivity/service.py);
 * tests/test_service.py fails if any value here differs from the Python side.
 */
export const MAX_BODY_BYTES = 262144;
export const MAX_ROWS = {
  units: 1000,
  changes: 200,
  material: 5000,
  incorporations: 5000,
} as const;
export const MAX_PAIRS = 5000;
