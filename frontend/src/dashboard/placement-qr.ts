/** Render locally so a seller link never goes to an external QR service. */
export async function placementQR(url: string, code: string) {
  const qr = await import('qrcode')
  const options = { errorCorrectionLevel: 'H' as const, margin: 4, scale: 12 }
  const [canvas, svg] = await Promise.all([qr.toCanvas(url, options), qr.toString(url, { ...options, type: 'svg' })])
  const png = await new Promise<Blob>((resolve, reject) => canvas.toBlob(
    (blob) => blob ? resolve(blob) : reject(new Error('PNG export failed')), 'image/png'))
  const file = new File([png], `qr-${code}.png`, { type: 'image/png' })
  const print = new Blob([svg], { type: 'image/svg+xml' })
  return { file, png: URL.createObjectURL(file), svg: URL.createObjectURL(print) }
}
