import { onBeforeUnmount, ref, type Ref } from 'vue'

interface UseResizablePanelOptions {
  panelRef: Ref<HTMLElement | null>
  storageKey: string
  defaultWidth: number
  minWidth: number
  maxWidth: number
  disabledBreakpoint?: number
}

type ResizeEvent = MouseEvent | TouchEvent

export const useResizablePanel = ({
  panelRef,
  storageKey,
  defaultWidth,
  minWidth,
  maxWidth,
  disabledBreakpoint = 1200,
}: UseResizablePanelOptions) => {
  const panelWidth = ref(defaultWidth)
  let cleanupResize: (() => void) | null = null

  const clampWidth = (width: number) => Math.min(maxWidth, Math.max(minWidth, width))

  const persistWidth = (width = panelWidth.value) => {
    const normalized = clampWidth(width)
    panelWidth.value = normalized
    window.localStorage.setItem(storageKey, String(normalized))
  }

  const hydrateWidth = () => {
    const savedWidth = Number(window.localStorage.getItem(storageKey) || 0)
    if (Number.isFinite(savedWidth) && savedWidth >= minWidth && savedWidth <= maxWidth) {
      panelWidth.value = savedWidth
    }
  }

  const isResizeDisabled = () => window.innerWidth <= disabledBreakpoint

  const readClientX = (event: ResizeEvent) => {
    if ('touches' in event) {
      return event.touches[0]?.clientX ?? event.changedTouches[0]?.clientX ?? 0
    }
    return event.clientX
  }

  const stopResize = () => {
    cleanupResize?.()
    cleanupResize = null
  }

  const startResize = (event: ResizeEvent) => {
    if (isResizeDisabled() || !panelRef.value) return

    event.preventDefault()
    stopResize()

    const panelLeft = panelRef.value.getBoundingClientRect().left
    const body = document.body
    const previousCursor = body.style.cursor
    const previousUserSelect = body.style.userSelect

    const updateWidth = (clientX: number) => {
      panelWidth.value = clampWidth(clientX - panelLeft)
    }

    const handleMove = (moveEvent: ResizeEvent) => {
      if ('cancelable' in moveEvent && moveEvent.cancelable) {
        moveEvent.preventDefault()
      }
      updateWidth(readClientX(moveEvent))
    }

    const handleUp = () => {
      persistWidth()
      stopResize()
    }

    body.style.cursor = 'col-resize'
    body.style.userSelect = 'none'
    updateWidth(readClientX(event))

    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseup', handleUp, { once: true })
    window.addEventListener('touchmove', handleMove, { passive: false })
    window.addEventListener('touchend', handleUp, { once: true })

    cleanupResize = () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseup', handleUp)
      window.removeEventListener('touchmove', handleMove)
      window.removeEventListener('touchend', handleUp)
      body.style.cursor = previousCursor
      body.style.userSelect = previousUserSelect
    }
  }

  onBeforeUnmount(stopResize)

  return {
    panelWidth,
    hydrateWidth,
    persistWidth,
    startResize,
  }
}
