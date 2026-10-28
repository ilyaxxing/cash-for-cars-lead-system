// Self-hosted Geist: no request ever leaves for a font CDN, and the installed
// dashboard keeps its typography offline. Only the weights the designs use.
// Latin always; latin-ext (accented names such as Škoda, Müller, and the
// letters of Turkish, Polish or Czech texts), Vietnamese and Cyrillic are
// downloaded by the browser only when such a character is on screen, so they
// cost an English page nothing. Scripts Geist does not draw (Chinese, Greek,
// Thai...) come from the phone's own fonts (system-ui in base.css).
import '@fontsource/geist/latin-400.css'
import '@fontsource/geist/latin-500.css'
import '@fontsource/geist/latin-600.css'
import '@fontsource/geist/latin-700.css'
import '@fontsource/geist/latin-800.css'
import '@fontsource/geist/latin-ext-400.css'
import '@fontsource/geist/latin-ext-500.css'
import '@fontsource/geist/latin-ext-600.css'
import '@fontsource/geist/latin-ext-700.css'
import '@fontsource/geist/latin-ext-800.css'
import '@fontsource/geist/vietnamese-400.css'
import '@fontsource/geist/vietnamese-500.css'
import '@fontsource/geist/vietnamese-600.css'
import '@fontsource/geist/vietnamese-700.css'
import '@fontsource/geist/vietnamese-800.css'
import '@fontsource/geist/cyrillic-400.css'
import '@fontsource/geist/cyrillic-500.css'
import '@fontsource/geist/cyrillic-600.css'
import '@fontsource/geist/cyrillic-700.css'
import '@fontsource/geist/cyrillic-800.css'
import '@fontsource/geist-mono/latin-400.css'
import '@fontsource/geist-mono/latin-500.css'
import '@fontsource/geist-mono/latin-ext-400.css'
import '@fontsource/geist-mono/latin-ext-500.css'
import '@fontsource/geist-mono/vietnamese-400.css'
import '@fontsource/geist-mono/vietnamese-500.css'
import '@fontsource/geist-mono/cyrillic-400.css'
import '@fontsource/geist-mono/cyrillic-500.css'
