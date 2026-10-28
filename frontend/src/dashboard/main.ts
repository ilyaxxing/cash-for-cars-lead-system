import '../shared/fonts'
import '../shared/base.css'
import './dashboard.css'
import { mount } from 'svelte'
import { loadConfig } from '../shared/config'
import { preventPageZoom } from '../shared/noZoom'
import { prepareRegion } from '../shared/region'
import App from './App.svelte'

const config = await loadConfig()
await prepareRegion(config.preset)
mount(App, { target: document.getElementById('root')!, props: { config } })
preventPageZoom()

// The service worker keeps the installed app opening offline and, from the
// push notifications stage on, receives the notifications.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/app/sw.js', { scope: '/app/' }).catch(() => {
    // Not fatal: the dashboard works without it, only offline start is lost.
  })
}
