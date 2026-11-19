/**
 * Wrapper-ready platform abstraction layer (Design Doc v0.1 §2 Req 6).
 * Zero browser-only APIs exist outside src/platform/.
 */

export async function requestPersistentStorage(): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.storage && typeof navigator.storage.persist === 'function') {
    try {
      const already = typeof navigator.storage.persisted === 'function' ? await navigator.storage.persisted() : false;
      if (already) return true;
      return await navigator.storage.persist();
    } catch {
      return false;
    }
  }
  return false;
}

export async function checkPersistentStorage(): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.storage && typeof navigator.storage.persisted === 'function') {
    try {
      return await navigator.storage.persisted();
    } catch {
      return false;
    }
  }
  return false;
}

export function triggerHaptic(_style: 'light' | 'medium' | 'success' | 'error'): void {
  // PWA: navigator.vibrate is unsupported on iOS Safari; no-op here,
  // ready to swap for Capacitor Haptics plugin if wrapped later.
}

export function nowMs(): number {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now();
  }
  return Date.now();
}

export async function shareOrDownloadJson(filename: string, jsonText: string): Promise<'shared' | 'downloaded'> {
  const blob = new Blob([jsonText], { type: 'application/json' });

  // Prefer iOS / mobile Web Share Sheet with File attachment
  if (typeof navigator !== 'undefined' && typeof navigator.share === 'function' && typeof File !== 'undefined') {
    try {
      const file = new File([blob], filename, { type: 'application/json' });
      const canShareFiles =
        typeof navigator.canShare === 'function' ? navigator.canShare({ files: [file] }) : false;
      if (canShareFiles) {
        await navigator.share({
          files: [file],
          title: 'Manifold SRS Backup',
          text: 'Full offline review log and FSRS backup',
        });
        return 'shared';
      }
    } catch (err) {
      // If user explicitly aborted share sheet, surface cancellation cleanly
      if (err instanceof Error && err.name === 'AbortError') {
        throw err;
      }
    }
  }

  // Fallback for desktop / non-file-share browsers
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  return 'downloaded';
}

export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ''));
    reader.onerror = () => reject(reader.error ?? new Error('Failed to read file'));
    reader.readAsText(file);
  });
}
