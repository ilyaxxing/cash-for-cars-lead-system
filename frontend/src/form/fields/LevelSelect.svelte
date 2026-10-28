<script lang="ts">
  // Options with a level meter (condition): label, description, tick.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import Check from '../Check.svelte'
  import ErrorText from '../ErrorText.svelte'
  import { pulse } from '../motion'
  import type { FormState } from '../state.svelte'

  let { field }: { field: FieldSpec } = $props()
  const form = getContext<FormState>('form')
  const t = form.t
  const BARS = [8, 12, 16, 20]
</script>

<div role="group" aria-label={form.fieldLabel(field)} class="list">
  {#each field.options as option (option.id)}
    {@const on = form.answers[field.id] === option.id}
    <button
      data-st
      class="opt card"
      class:on
      aria-pressed={on}
      onclick={(event) => {
        pulse(event)
        form.set(field.id, option.id)
        form.autoAdvance()
      }}
    >
      <span aria-hidden="true" class="bars">
        {#each BARS as height, index (index)}
          <span
            class="bar"
            class:lit={index < (option.level ?? 0)}
            class:accent={on && index < (option.level ?? 0)}
            style:height="{height}px"
          ></span>
        {/each}
      </span>
      <span class="text">
        <span class="title">{t(`preset.options.${field.id}.${option.id}.label`)}</span>
        <span class="description">{t(`preset.options.${field.id}.${option.id}.description`)}</span>
      </span>
      <Check {on} size={22} tick={12} stroke={1.6} />
    </button>
  {/each}
</div>
<ErrorText text={form.errorText(field.id)} gap="12px" />

<style>
  .list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .card {
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 72px;
    padding: 14px 16px 14px 18px;
    border-radius: 18px;
    text-align: left;
  }

  .card:active {
    transform: scale(0.98);
  }

  .bars {
    flex: none;
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 20px;
  }

  .bar {
    width: 4px;
    border-radius: 2px;
    background: #3a3c3c;
  }

  .bar.lit {
    background: #d9d8d2;
  }

  .bar.accent {
    background: var(--accent);
  }

  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .title {
    font: 600 16px/1.2 var(--font-sans);
  }

  .description {
    font: 400 13.5px/1.35 var(--font-sans);
    color: var(--text-muted);
  }
</style>
