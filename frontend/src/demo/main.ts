// Entry of the live demo's stand-in server. tools/make_demo.py puts this
// script before the app's own, so it is in place before the app makes its
// first request; on the policy page it only puts in the business's name and
// color. Never part of a client's instance.
import { install, personalizePolicy } from './browser'

if (document.getElementById('app-config')) install()
else personalizePolicy()
