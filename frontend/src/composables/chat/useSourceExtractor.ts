export interface SourceItem {
  label: string
  title: string
}

export function extractSources(content: string): SourceItem[] {
  const sources: SourceItem[] = []

  // 1. Strip HTML tags / entities (handles both raw markdown and rendered HTML)
  const plainText = content
    .replace(/<[^>]*>/g, '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")

  // 2. Find "知识来源" heading — use indexOf to avoid greedy \s* swallowing \r\n
  const headingIdx = plainText.indexOf('知识来源')
  if (headingIdx === -1) return sources

  // 3. Find end of the heading line (handles both \n and \r\n)
  const afterHeading = plainText.substring(headingIdx)
  const lineEnd = afterHeading.search(/[\r\n]+/)
  if (lineEnd === -1) return sources

  // 4. Extract everything after the heading line
  const sourceText = afterHeading.substring(lineEnd).replace(/^[\r\n]+/, '')

  // 5. Parse lines like "- [参考1]《title》" or "* 《title》"
  const lineRegex = /[-*]\s*(?:\[参考\d+\])?\s*[《「](.+?)[》」]/g
  let match: RegExpExecArray | null
  while ((match = lineRegex.exec(sourceText)) !== null) {
    sources.push({
      label: `参考${sources.length + 1}`,
      title: match[1],
    })
  }

  return sources
}