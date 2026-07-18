<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { initializeLanguage, language, setLanguage } from '$lib/i18n';

  let { children } = $props();
  let menuOpen = $state(false);

  const closeMenu = () => {
    menuOpen = false;
  };

  const navigation = {
    de: {
      open: 'Navigation öffnen',
      aria: 'Hauptnavigation',
      planner: 'Planen',
      results: 'Ergebnisse',
      faq: 'FAQ',
      sources: 'Datenquellen',
      language: 'Sprache auswählen'
    },
    en: {
      open: 'Open navigation',
      aria: 'Main navigation',
      planner: 'Plan',
      results: 'Results',
      faq: 'FAQ',
      sources: 'Data sources',
      language: 'Select language'
    }
  } as const;

  onMount(initializeLanguage);
</script>

<header class="site-header">
  <a class="brand" href="/planner" onclick={closeMenu}>
    <img class="brand-mark" src="/onpoint-logo.svg" alt="" aria-hidden="true" />
    <span class="brand-text">OnPoint.</span>
  </a>

  <div class="header-right">
    <div class="language-switch" role="group" aria-label={navigation[$language].language}>
      <button
        type="button"
        class:active={$language === 'de'}
        aria-pressed={$language === 'de'}
        onclick={() => setLanguage('de')}>DE</button
      >
      <button
        type="button"
        class:active={$language === 'en'}
        aria-pressed={$language === 'en'}
        onclick={() => setLanguage('en')}>EN</button
      >
    </div>

    <button
      class="menu-button"
      type="button"
      onclick={() => (menuOpen = !menuOpen)}
      aria-controls="site-navigation"
      aria-expanded={menuOpen}
    >
      <span class="sr-only">{navigation[$language].open}</span>
      <span></span>
      <span></span>
      <span></span>
    </button>

    <nav
      id="site-navigation"
      class={`site-nav ${menuOpen ? 'open' : ''}`}
      aria-label={navigation[$language].aria}
    >
      <a href="/planner#plan" onclick={closeMenu}>{navigation[$language].planner}</a>
      <a href="/planner#results" onclick={closeMenu}>{navigation[$language].results}</a>
      <a href="/planner#faq" onclick={closeMenu}>{navigation[$language].faq}</a>
      <a href="/planner#sources" onclick={closeMenu}>{navigation[$language].sources}</a>
      <a href="https://github.com/Avonik" target="_blank" rel="noreferrer" onclick={closeMenu}
        >GitHub</a
      >
    </nav>
  </div>
</header>

{@render children()}
