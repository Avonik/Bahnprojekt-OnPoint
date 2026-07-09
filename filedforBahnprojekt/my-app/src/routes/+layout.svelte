<script lang="ts">
  import '../app.css';

  let { children } = $props();
  let menuOpen = $state(false);

  const closeMenu = () => {
    menuOpen = false;
  };
</script>

<header class="site-header">
  <a class="brand" href="/planner" onclick={closeMenu}>
    <img class="brand-mark" src="/onpoint-logo.svg" alt="" aria-hidden="true" />
    <span class="brand-text">OnPoint.</span>
  </a>

  <button
    class="menu-button"
    type="button"
    onclick={() => (menuOpen = !menuOpen)}
    aria-controls="site-navigation"
    aria-expanded={menuOpen}
  >
    <span class="sr-only">Navigation oeffnen</span>
    <span></span>
    <span></span>
    <span></span>
  </button>

  <nav id="site-navigation" class={`site-nav ${menuOpen ? 'open' : ''}`}>
    <a href="/planner#plan" onclick={closeMenu}>Planen</a>
    <a href="/planner#results" onclick={closeMenu}>Ergebnisse</a>
    <a href="/planner#faq" onclick={closeMenu}>FAQ</a>
    <a href="/planner#sources" onclick={closeMenu}>Datenquellen</a>
    <a href="https://github.com/Avonik" target="_blank" rel="noreferrer" onclick={closeMenu}>GitHub</a>
  </nav>
</header>

{@render children()}
