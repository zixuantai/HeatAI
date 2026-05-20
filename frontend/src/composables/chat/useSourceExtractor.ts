export interface SourceItem {
  label: string
  title: string
  documentId?: string
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

  // 2. Try to match "【知识来源X】文档名称" format (from prompt instruction)
  const sourceBlockRegex = /【(?:知识)?来源(\d+)】\s*([^\n【]+)/g
  let match: RegExpExecArray | null
  while ((match = sourceBlockRegex.exec(plainText)) !== null) {
    sources.push({
      label: `参考${match[1]}`,
      title: match[2].trim(),
    })
  }
  if (sources.length > 0) return sources

  // 3. Find "知识来源" heading — use indexOf to avoid greedy \s* swallowing \r\n
  const headingIdx = plainText.indexOf('知识来源')
  if (headingIdx === -1) return sources

  // 4. Find end of the heading line (handles both \n and \r\n)
  const afterHeading = plainText.substring(headingIdx)
  const lineEnd = afterHeading.search(/[\r\n]+/)
  if (lineEnd === -1) return sources

  // 5. Extract everything after the heading line
  const sourceText = afterHeading.substring(lineEnd).replace(/^[\r\n]+/, '')

  // 6. Parse lines like "- [参考1]《title》" or "* 《title》"
  const lineRegex = /[-*]\s*(?:\[参考\d+\])?\s*[《「](.+?)[》」]/g
  while ((match = lineRegex.exec(sourceText)) !== null) {
    sources.push({
      label: `参考${sources.length + 1}`,
      title: match[1],
    })
  }

  return sources
}