<script lang="ts">
  // The brand in the headers: the client's logo, or the default mark square,
  // with the name in spaced capitals as in both designs. A wordmark logo
  // already spells the name, so it stands alone.
  import type { Brand } from './config'
  import TagGlyph from './TagGlyph.svelte'

  interface Props {
    brand: Brand
    size?: 'large' | 'medium' | 'small'
    // false: the name alone, under a larger logo drawn by the page.
    mark?: boolean
  }

  let { brand, size = 'large', mark = true }: Props = $props()
  const logo = $derived(mark ? brand.logo : null)
</script>

<span class="brand {size}">
  {#if logo}
    <img
      class="logo"
      class:wordmark={logo.wordmark}
      src={logo.url}
      width={logo.width}
      height={logo.height}
      alt={logo.wordmark ? brand.name : ''}
    />
  {:else if mark}
    <span class="mark" aria-hidden="true"><TagGlyph /></span>
  {/if}
  {#if !logo?.wordmark}<span class="name">{brand.name}</span>{/if}
</span>

<style>
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .mark {
    width: 22px;
    height: 22px;
    border-radius: 7px;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .logo {
    display: block;
    flex: none;
    width: auto;
    height: 28px;
    object-fit: contain;
  }

  .logo.wordmark {
    max-width: 190px;
  }

  .name {
    font: 700 14px/1 var(--font-sans);
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .medium {
    gap: 9px;
  }

  .medium .mark {
    width: 18px;
    height: 18px;
    border-radius: 6px;
  }

  .medium .logo {
    height: 24px;
  }

  .medium .logo.wordmark {
    max-width: 170px;
  }

  .medium .name {
    font-size: 13px;
  }

  .small {
    gap: 8px;
  }

  .small .mark {
    width: 16px;
    height: 16px;
    border-radius: 5px;
  }

  .small .logo {
    height: 22px;
  }

  .small .logo.wordmark {
    max-width: 150px;
  }

  .small .name {
    font-size: 12.5px;
  }
</style>
