<script lang="ts">
  // The car and the headline on the phone welcome screen. Drawn behind the
  // scrolling area rather than inside it, so they never move: not when the
  // text scrolls, not with the iPhone's rubber-band bounce, not with the
  // screen's entrance. The text panel slides over them.
  import { getContext } from 'svelte'
  import { hero } from './illustrations'
  import type { FormState } from './state.svelte'

  const form = getContext<FormState>('form')
  // The client's own photo (BRAND_PHOTO) replaces the designs' car.
  const own = form.config.brand.photo

  // A headline longer than the design's (German, Polish) shrinks to the
  // phone's width instead of running off it; the design's size is the most.
  function fit(node: HTMLElement) {
    const size = () => {
      node.style.fontSize = ''
      const room = node.clientWidth
      const need = node.scrollWidth
      if (need > room) {
        const base = parseFloat(getComputedStyle(node).fontSize)
        node.style.fontSize = `${Math.floor((base * room) / need)}px`
      }
    }
    const observer = new ResizeObserver(size)
    observer.observe(node)
    // The width is right only once the self-hosted font has loaded.
    document.fonts?.ready.then(size)
    return { destroy: () => observer.disconnect() }
  }
</script>

<div class="backdrop">
  <div class="picture">
    {#if own}
      <img src={own.src} srcset={own.srcset} sizes="100vw" alt="" class="hero-img own" style:--ratio={own.width / own.height} />
    {:else if hero}
      <img
        src={hero.src}
        srcset={hero.srcset}
        sizes="100vw"
        alt={form.t('form.welcome.hero_alt')}
        class="hero-img"
        style:--ratio={hero.ratio}
      />
    {/if}
    <div aria-hidden="true" class="fade-top"></div>
    <div aria-hidden="true" class="fade-bottom"></div>
  </div>
  <h1 class="headline" use:fit>{form.t('form.welcome.headline1')}<br />{form.t('form.welcome.headline2')}</h1>
</div>

<style>
  .backdrop {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    z-index: -1;
    --height: 500px;
    height: var(--height);
    pointer-events: none;
  }

  .picture {
    position: absolute;
    inset: 0;
    overflow: hidden;
    --mask: linear-gradient(
      180deg,
      #000 0%,
      #000 52%,
      rgba(0, 0, 0, 0.92) 62%,
      rgba(0, 0, 0, 0.74) 71%,
      rgba(0, 0, 0, 0.5) 80%,
      rgba(0, 0, 0, 0.27) 88%,
      rgba(0, 0, 0, 0.1) 95%,
      rgba(0, 0, 0, 0) 100%
    );
    -webkit-mask-image: var(--mask);
    mask-image: var(--mask);
  }

  /* Covers the backdrop as object-fit: cover would, with object-position
     24% 50%, but by the image's own box in the photo's shape: Safari on the
     iPhone now and then ignores object-fit on an image with a srcset and
     stretches the photo to the box (WebKit bug 227682). */
  .hero-img {
    position: absolute;
    left: 24%;
    top: 50%;
    width: max(100%, var(--height) * var(--ratio));
    aspect-ratio: var(--ratio);
    transform: translate(-24%, -50%);
  }

  /* The designs' car sits left of center; a client's photo is centered. */
  .hero-img.own {
    left: 50%;
    transform: translate(-50%, -50%);
  }

  .fade-top {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 46%;
    background: linear-gradient(
      180deg,
      rgba(17, 18, 18, 0.9) 0%,
      rgba(17, 18, 18, 0.74) 28%,
      rgba(17, 18, 18, 0.4) 62%,
      rgba(17, 18, 18, 0) 100%
    );
  }

  .fade-bottom {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 55%;
    background: linear-gradient(
      180deg,
      rgba(17, 18, 18, 0) 0%,
      rgba(17, 18, 18, 0.04) 12%,
      rgba(17, 18, 18, 0.12) 24%,
      rgba(17, 18, 18, 0.24) 36%,
      rgba(17, 18, 18, 0.4) 48%,
      rgba(17, 18, 18, 0.58) 60%,
      rgba(17, 18, 18, 0.75) 71%,
      rgba(17, 18, 18, 0.88) 81%,
      rgba(17, 18, 18, 0.96) 90%,
      #111212 97%,
      #111212 100%
    );
  }


  .headline {
    position: absolute;
    left: 20px;
    right: 12px;
    top: 82px;
    margin: 0;
    font-family: var(--font-sans);
    font-weight: 800;
    font-size: 50px;
    line-height: 0.9;
    letter-spacing: -0.05em;
    color: var(--text);
    white-space: nowrap;
  }
</style>
