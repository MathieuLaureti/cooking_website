import { useCallback, useEffect, useState } from 'react'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

function isStandaloneDisplay(): boolean {
  if (typeof window === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  )
}

function isIosSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  return /iPhone|iPad|iPod/i.test(ua) && !/CriOS|FxiOS|EdgiOS/i.test(ua)
}

export default function MobileInstallButton() {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [showHelp, setShowHelp] = useState(false)

  useEffect(() => {
    const onInstallable = (event: Event) => {
      event.preventDefault()
      setInstallPrompt(event as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', onInstallable)
    return () => window.removeEventListener('beforeinstallprompt', onInstallable)
  }, [])

  const onMobileClick = useCallback(async () => {
    if (installPrompt) {
      await installPrompt.prompt()
      await installPrompt.userChoice
      setInstallPrompt(null)
      return
    }
    setShowHelp((open) => !open)
  }, [installPrompt])

  if (isStandaloneDisplay()) {
    return null
  }

  return (
    <div className="relative flex items-center">
      <button
        type="button"
        onClick={onMobileClick}
        className="text-[10px] uppercase tracking-widest text-[#5E7161] hover:text-[#FFA500] font-bold"
        aria-expanded={showHelp}
        aria-haspopup="dialog"
      >
        Mobile
      </button>
      {showHelp && (
        <div
          role="dialog"
          aria-label="Install on your phone"
          className="absolute right-0 top-full z-50 mt-2 w-[min(18rem,calc(100vw-2rem))] rounded border border-[#5E7161]/40 bg-[#3d4a40] p-3 text-left text-[11px] leading-relaxed text-[#c8d4ca] shadow-lg"
        >
          <p className="mb-2 font-bold uppercase tracking-wider text-[#FFA500]">
            Add to home screen
          </p>
          {isIosSafari() ? (
            <p>
              Tap <strong>Share</strong> in Safari, then <strong>Add to Home Screen</strong>. Open
              the app from that icon so login and recipes work like a native app.
            </p>
          ) : installPrompt ? (
            <p>Tap <strong>Mobile</strong> again and accept the install prompt.</p>
          ) : (
            <p>
              In Chrome: menu → <strong>Install app</strong> or <strong>Add to Home screen</strong>.
              Use the same URL you use on desktop (with <strong>/recipes/</strong> in prod).
            </p>
          )}
          <button
            type="button"
            onClick={() => setShowHelp(false)}
            className="mt-2 text-[10px] uppercase tracking-widest text-[#5E7161] hover:text-[#FFA500]"
          >
            Close
          </button>
        </div>
      )}
    </div>
  )
}
