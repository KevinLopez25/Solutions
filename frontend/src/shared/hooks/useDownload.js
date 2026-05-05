export function useDownload() {
  function download(base64, filename, mimeType) {
    const bytes  = atob(base64)
    const buffer = new Uint8Array(bytes.length)
    for (let i = 0; i < bytes.length; i++) buffer[i] = bytes.charCodeAt(i)
    const blob = new Blob([buffer], { type: mimeType })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }
  return { download }
}
