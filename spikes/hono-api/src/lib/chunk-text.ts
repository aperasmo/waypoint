type ChunkTextPart = {
  chunk_index: number
  text: string
}

/**
 * Reassemble stored chunks into the original section text.
 *
 * Adjacent chunks can contain a 200-character overlap added during
 * ingestion, so that duplicated prefix is removed before joining.
 */
export function reassembleSectionText(chunks: ChunkTextPart[]): string {
  const ordered = [...chunks].sort(
    (left, right) => left.chunk_index - right.chunk_index,
  )

  const parts: string[] = []

  for (const chunk of ordered) {
    let text = chunk.text
    const previousPart = parts.at(-1)

    if (previousPart) {
      const previousTail = previousPart.slice(-200)

      if (text.startsWith(previousTail.slice(0, 50))) {
        text = text.slice(previousTail.length).trimStart()
      }
    }

    parts.push(text)
  }

  return parts.join('\n')
}