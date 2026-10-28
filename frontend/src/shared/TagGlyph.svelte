<script lang="ts">
  // The drawing inside the brand mark's accent square: a price tag, for a
  // business that buys cars for cash. The $ appears only where the mark is
  // large enough to read it. app/branding/mark.py draws the same shape for
  // the home-screen icons.
  let { dollar = false }: { dollar?: boolean } = $props()
</script>

<svg viewBox="0 0 24 24" aria-hidden="true">
  <path
    d="M5 6.8v4.6c0 .5.2 1 .6 1.4l6.1 6.1c.8.8 2 .8 2.8 0l4.1-4.1c.8-.8.8-2 0-2.8l-6.1-6.1c-.4-.4-.9-.6-1.4-.6H6.8C5.8 5.3 5 6 5 6.8z"
    class="tag"
  />
  <circle cx="8.4" cy="8.6" r="1.3" class="hole" />
  {#if dollar}
    <text x="13.6" y="15.3" transform="rotate(-45 13.6 13)" text-anchor="middle" class="dollar">$</text>
  {/if}
</svg>

<style>
  svg {
    display: block;
    width: 100%;
    height: 100%;
  }

  .tag {
    fill: var(--on-accent);
  }

  .hole,
  .dollar {
    fill: var(--accent);
  }

  .dollar {
    font: 700 7.5px var(--font-sans);
  }
</style>
