import '../shared/fonts'
import '../shared/base.css'
import { mount } from 'svelte'
import { loadConfig } from '../shared/config'
import { preventPageZoom } from '../shared/noZoom'
import { prepareRegion } from '../shared/region'
import Form from './Form.svelte'

const config = await loadConfig()
await prepareRegion(config.preset)
mount(Form, { target: document.getElementById('root')!, props: { config } })
preventPageZoom()
