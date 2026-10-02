export function parseRules(markdown: string): {
  id: string;
  condition: string;
  status: string | null;
  reasonCodes: string[];
}[];
export function renderRules(markdown: string): string;
