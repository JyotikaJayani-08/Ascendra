/**
 * LinkUtils — URL/Markdown/HTML link parser & sanitizer.
 *
 * Handles three raw link formats commonly found in job descriptions,
 * AI-generated email content, and extracted resume text:
 *   1. Plain URLs:     https://example.com/apply
 *   2. Markdown links: [Apply Here](https://example.com/apply)
 *   3. HTML anchors:   <a href="https://example.com/apply">Apply Here</a>
 *
 * Converts all of them into structured { text, url } segments for safe rendering.
 */

export interface LinkSegment {
  type: 'text' | 'link';
  content: string;
  url?: string;
}

/**
 * Parse a raw text string and extract all link segments.
 * Returns an array of LinkSegment objects that can be rendered
 * as a mix of plain text and interactive links.
 */
export function parseLinkSegments(raw: string): LinkSegment[] {
  if (!raw) return [];

  // Combined regex to match:
  // 1. Markdown links: [text](url)
  // 2. HTML anchor tags: <a href="url">text</a> (with optional attributes)
  // 3. Plain URLs: http(s)://... (greedy until whitespace or certain punctuation)
  const combinedPattern =
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)|<a\s[^>]*href=["'](https?:\/\/[^"']+)["'][^>]*>(.*?)<\/a>|(https?:\/\/[^\s<>\[\]"')\],]+)/gi;

  const segments: LinkSegment[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = combinedPattern.exec(raw)) !== null) {
    // Add preceding plain text if any
    if (match.index > lastIndex) {
      const preceding = raw.slice(lastIndex, match.index);
      if (preceding) {
        segments.push({ type: 'text', content: preceding });
      }
    }

    if (match[1] && match[2]) {
      // Markdown: [text](url)
      segments.push({ type: 'link', content: match[1], url: match[2] });
    } else if (match[3]) {
      // HTML: <a href="url">text</a>
      const linkText = match[4]?.trim() || match[3];
      segments.push({ type: 'link', content: linkText, url: match[3] });
    } else if (match[5]) {
      // Plain URL
      let url = match[5];
      // Strip trailing punctuation that's likely sentence-ending, not part of URL
      url = url.replace(/[.,;:!?]+$/, '');
      segments.push({ type: 'link', content: prettifyUrl(url), url });
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last match
  if (lastIndex < raw.length) {
    segments.push({ type: 'text', content: raw.slice(lastIndex) });
  }

  return segments.length > 0 ? segments : [{ type: 'text', content: raw }];
}

/**
 * Check if a raw string contains any parseable links.
 */
export function containsLinks(raw: string): boolean {
  if (!raw) return false;
  const linkPattern =
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)|<a\s[^>]*href=["'](https?:\/\/[^"']+)["']|(https?:\/\/[^\s<>\[\]"')\],]+)/i;
  return linkPattern.test(raw);
}

/**
 * Create a user-friendly display label from a URL.
 * e.g. https://careers.hpe.com/us/en/job/1209772 → careers.hpe.com/…/1209772
 */
function prettifyUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, '');
    const pathParts = parsed.pathname.split('/').filter(Boolean);

    if (pathParts.length <= 2) {
      return host + parsed.pathname;
    }
    // Show host + first segment + last segment for long paths
    return `${host}/…/${pathParts[pathParts.length - 1]}`;
  } catch {
    // If URL parsing fails, truncate
    return url.length > 50 ? url.slice(0, 47) + '...' : url;
  }
}
