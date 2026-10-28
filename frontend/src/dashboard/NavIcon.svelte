<script lang="ts">
  // Navigation icons from the design: inbox, bars, sliders.
  let { screen, on, size = 18 }: { screen: 'leads' | 'stats' | 'settings'; on: boolean; size?: number } = $props()
  const stroke = $derived(on ? 'var(--accent)' : '#7C7E7A')
</script>

<svg width={size} height={size} viewBox="0 0 18 18" fill="none" style="stroke: {stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  {#if screen === 'leads'}
    <rect x="2.5" y="3.5" width="13" height="11" rx="2" />
    <path d="M2.5 10h3.5l1 1.8h4l1-1.8h3.5" />
  {:else if screen === 'stats'}
    <path d="M4 15V10M9 15V4M14 15v-7" />
  {:else}
    <path d="M3 6h12M3 12h12" />
    <circle cx="7" cy="6" r="1.9" fill="#0B0C0C" />
    <circle cx="11.5" cy="12" r="1.9" fill="#0B0C0C" />
  {/if}
</svg>
