<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  onMount(() => {
    goto('/planner', { replaceState: true });
  });
</script>

<main class="redirect-page">
  <a href="/planner">OnPoint oeffnen</a>
</main>

<style>
  .redirect-page {
    display: grid;
    min-height: calc(100vh - 76px);
    place-items: center;
    background: #0f172a;
  }

  a {
    border-radius: 8px;
    background: #fbbf24;
    color: #1f2937;
    padding: 12px 16px;
    font-weight: 900;
    text-decoration: none;
  }
</style>
