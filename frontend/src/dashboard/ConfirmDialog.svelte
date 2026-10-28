<script lang="ts">
  // Confirmation in the style of the design's log-out dialog.
  let {
    title,
    text,
    action,
    cancel,
    onConfirm,
    onCancel,
  }: { title: string; text: string; action: string; cancel: string; onConfirm: () => void; onCancel: () => void } =
    $props()
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="backdrop" onclick={onCancel}>
  <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" tabindex="-1" onclick={(event) => event.stopPropagation()}>
    <div class="text">
      <span id="confirm-title" class="title">{title}</span>
      <span class="body">{text}</span>
    </div>
    <div class="actions">
      <button class="cancel" onclick={onCancel}>{cancel}</button>
      <!-- svelte-ignore a11y_autofocus -->
      <button class="confirm" onclick={onConfirm} autofocus>{action}</button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: absolute;
    inset: 0;
    z-index: 70;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    animation: ui-fade 0.18s both;
  }

  .dialog {
    width: 100%;
    max-width: 400px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 22px;
    border-radius: 18px;
    background: var(--surface);
    border: 1px solid var(--line);
    animation: ui-pop-in 0.2s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .text {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .title {
    font: 700 20px/1.2 var(--font-sans);
    letter-spacing: -0.02em;
  }

  .body {
    font: 400 14.5px/1.45 var(--font-sans);
    color: var(--text-soft);
  }

  .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .cancel {
    height: 46px;
    padding: 0 16px;
    border: 1px solid var(--line-strong);
    border-radius: 12px;
    background: transparent;
    font: 500 15px/1 var(--font-sans);
    cursor: pointer;
  }

  .cancel:hover {
    background: var(--surface-2);
  }

  .confirm {
    height: 46px;
    padding: 0 16px;
    border: 0;
    border-radius: 12px;
    background: var(--text);
    color: #111212;
    font: 600 15px/1 var(--font-sans);
    cursor: pointer;
  }

  .confirm:hover {
    background: #ffffff;
  }
</style>
