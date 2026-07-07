import { useEffect } from 'react'

/**
 * Attaches a window-level paste listener and fires onImage
 * whenever the clipboard contains an image file.
 * Pass disabled=true to temporarily suspend it.
 */
export function useClipboardPaste(onImage: (file: File) => void, disabled = false) {
  useEffect(() => {
    if (disabled) return

    function handlePaste(e: ClipboardEvent) {
      const items = e.clipboardData?.items
      if (!items) return
      for (const item of Array.from(items)) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile()
          if (file) {
            e.preventDefault()
            onImage(file)
            return
          }
        }
      }
    }

    window.addEventListener('paste', handlePaste)
    return () => window.removeEventListener('paste', handlePaste)
  }, [onImage, disabled])
}
