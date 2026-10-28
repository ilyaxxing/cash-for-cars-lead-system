// Shrinking photos in the browser before upload.
//
// Phone photos are 3-12 MB; on a weak connection that is the difference
// between an upload that finishes and one the seller gives up on. Photos are
// redrawn to at most 1600 px on the long side and saved as JPEG, which also
// turns iPhone HEIC into something every browser can show. The server
// re-encodes again and strips metadata, so this step is about speed only.

const MAX_SIDE = 1600
const QUALITY = 0.82

async function decode(file: Blob): Promise<ImageBitmap | HTMLImageElement> {
  try {
    return await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    // Safari decodes HEIC through <img> even where createImageBitmap refuses.
    const url = URL.createObjectURL(file)
    try {
      const image = new Image()
      image.src = url
      await image.decode()
      return image
    } finally {
      URL.revokeObjectURL(url)
    }
  }
}

export async function compressPhoto(file: Blob): Promise<Blob> {
  const image = await decode(file)
  const width = 'naturalWidth' in image ? image.naturalWidth : image.width
  const height = 'naturalHeight' in image ? image.naturalHeight : image.height
  const scale = Math.min(1, MAX_SIDE / Math.max(width, height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(width * scale)
  canvas.height = Math.round(height * scale)
  canvas.getContext('2d')!.drawImage(image, 0, 0, canvas.width, canvas.height)
  if ('close' in image) image.close()
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('encode failed'))), 'image/jpeg', QUALITY),
  )
}

export function isPhotoFile(file: File): boolean {
  return file.type.startsWith('image/') || /\.(heic|heif)$/i.test(file.name)
}

export function isPlainImage(file: File): boolean {
  return /^image\/(jpeg|png|webp)$/.test(file.type) || /\.(jpe?g|png|webp)$/i.test(file.name)
}

export const MAX_FILE_BYTES = 15 * 1024 * 1024
