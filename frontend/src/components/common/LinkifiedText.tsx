'use client';

import React from 'react';
import { ExternalLink } from 'lucide-react';
import { parseLinkSegments, containsLinks, type LinkSegment } from '@/lib/linkUtils';

interface LinkifiedTextProps {
  /** The raw text that may contain URLs, Markdown links, or HTML anchors. */
  text: string;
  /** Additional CSS class names for the wrapper. */
  className?: string;
  /** Max number of characters to show before truncating (0 = no truncation). */
  maxLength?: number;
}

/**
 * LinkifiedText — Renders raw text with auto-detected links as styled,
 * clickable anchor elements. Safely handles Markdown, HTML, and plain URLs.
 *
 * Usage:
 *   <LinkifiedText text={job.description} className="text-xs text-slate-800" />
 */
export default function LinkifiedText({ text, className = '', maxLength = 0 }: LinkifiedTextProps) {
  if (!text) return null;

  // If no links detected, render as plain text for performance
  if (!containsLinks(text)) {
    const displayText = maxLength > 0 && text.length > maxLength
      ? text.slice(0, maxLength) + '...'
      : text;
    return <span className={className}>{displayText}</span>;
  }

  // Apply maxLength truncation before parsing
  const truncatedText = maxLength > 0 && text.length > maxLength
    ? text.slice(0, maxLength) + '...'
    : text;

  const segments: LinkSegment[] = parseLinkSegments(truncatedText);

  return (
    <span className={className}>
      {segments.map((seg, idx) => {
        if (seg.type === 'link' && seg.url) {
          return (
            <a
              key={idx}
              href={seg.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-emerald-600 hover:text-emerald-800 underline underline-offset-2 decoration-emerald-300 hover:decoration-emerald-600 transition-colors font-medium break-all"
              title={seg.url}
            >
              {seg.content}
              <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-60" />
            </a>
          );
        }
        return <React.Fragment key={idx}>{seg.content}</React.Fragment>;
      })}
    </span>
  );
}
