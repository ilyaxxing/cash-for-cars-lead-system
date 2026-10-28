<script lang="ts">
  // The round tick shown on selectable cards.
  let { on, size = 18, tick = 10, stroke = 1.7 }: { on: boolean; size?: number; tick?: number; stroke?: number } =
    $props()
</script>

<span
  aria-hidden="true"
  class="check"
  class:on
  style:width="{size}px"
  style:height="{size}px"
  style:border-radius="{size / 2}px"
>
  <svg width={tick} height={tick} viewBox="0 0 10 10">
    <path d="M2 5.2l2 2L8 3" stroke-width={stroke} fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</span>

<style>
  .check {
    flex: none;
    border: 1.5px solid #4a4c4b;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      background-color 0.2s,
      border-color 0.2s;
  }

  .check path {
    stroke: transparent;
  }

  .check.on {
    background: var(--accent);
    border-color: var(--accent);
  }

  .check.on path {
    stroke: var(--on-accent);
  }
</style>
