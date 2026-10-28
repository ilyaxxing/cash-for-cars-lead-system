<script lang="ts">
  // Inline error under a field: red text with a round "!" badge.
  let { text, gap = '0' }: { text: string; gap?: string } = $props()
</script>

{#if text}
  <span role="alert" class="error" style:margin-top={gap}>
    <span aria-hidden="true" class="badge">!</span>{text}
  </span>
{/if}

<style>
  .error {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 13.5px/1.35 var(--font-sans);
    color: var(--error);
    animation: ui-in 0.2s both;
  }

  .badge {
    flex: none;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    background: var(--error);
    color: #111212;
    font: 700 11px/16px var(--font-sans);
    text-align: center;
  }
</style>
