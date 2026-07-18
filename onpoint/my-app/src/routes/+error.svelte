<script lang="ts">
  import { language } from '$lib/i18n';

  const copy = {
    de: {
      title: 'Etwas ist schiefgelaufen',
      message:
        'Diese Seite konnte gerade nicht geladen werden. Bitte versuchen Sie es erneut oder kehren Sie zum Routenplaner zurück.',
      action: 'Zum Routenplaner'
    },
    en: {
      title: 'Something went wrong',
      message:
        'This page could not be loaded right now. Please try again or return to the journey planner.',
      action: 'Go to journey planner'
    }
  } as const;

  $: t = copy[$language];
</script>

<svelte:head>
  <title>{t.title} | OnPoint.</title>
</svelte:head>

<main class="error-page">
  <section>
    <img src="/onpoint-logo.svg" alt="" aria-hidden="true" />
    <h1>{t.title}</h1>
    <p>{t.message}</p>
    <a href="/planner">{t.action}</a>
  </section>
</main>

<style>
  .error-page {
    display: grid;
    place-items: center;
    min-height: calc(100vh - 76px);
    padding: 32px 16px;
    color: #f8fafc;
    background:
      radial-gradient(circle at top, rgba(8, 145, 178, 0.2), transparent 45%),
      #0f172a;
  }

  section {
    width: min(520px, 100%);
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.9);
    padding: clamp(28px, 6vw, 48px);
    text-align: center;
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.3);
  }

  img {
    width: 58px;
    height: 58px;
    margin-bottom: 18px;
    border-radius: 10px;
  }

  h1 {
    margin: 0;
    font-size: clamp(2rem, 6vw, 3.2rem);
    line-height: 1.05;
  }

  p {
    margin: 18px auto 26px;
    color: #cbd5e1;
    line-height: 1.65;
  }

  a {
    display: inline-flex;
    min-height: 48px;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: #fbbf24;
    color: #1f2937;
    padding: 0 20px;
    font-weight: 900;
    text-decoration: none;
  }

  a:hover,
  a:focus-visible {
    background: #fcd34d;
  }
</style>
