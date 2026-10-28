<script lang="ts">
  // Gate: sign-in, the one-time setup, then the dashboard itself.
  import { onMount, setContext } from 'svelte'
  import type { AppConfig } from '../shared/config'
  import Login from './Login.svelte'
  import Onboarding from './Onboarding.svelte'
  import Shell from './Shell.svelte'
  import { DashboardState } from './state.svelte'

  let { config }: { config: AppConfig } = $props()
  // svelte-ignore state_referenced_locally
  const dash = new DashboardState(config)
  setContext('dashboard', dash)

  onMount(() => {
    void dash.start()
  })
</script>

<div class="root" bind:clientWidth={dash.width}>
  {#if dash.auth === 'signed_in'}
    {#if dash.onboarded}
      <Shell />
    {:else}
      <Onboarding />
    {/if}
  {:else if dash.auth === 'signed_out' || dash.auth === 'logged_out'}
    <Login loggedOut={dash.auth === 'logged_out'} />
  {/if}
</div>

<style>
  /* Pinned to the window instead of height: 100dvh. In the iPhone home-screen
     app 100dvh comes out shorter than the screen, and the strip left below
     looked like a tall gap under the bottom menu. */
  .root {
    position: fixed;
    inset: 0;
    background: var(--bg);
    color: var(--text);
  }
</style>
