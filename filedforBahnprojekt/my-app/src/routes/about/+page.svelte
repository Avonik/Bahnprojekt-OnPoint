<script>
  import AOS from 'aos';
  import { onMount } from 'svelte';
  import 'aos/dist/aos.css';

  // Initialize AOS
  onMount(() => {
    AOS.init();
  });
</script>

<div class="min-h-screen bg-base-200 p-8">
  <div class="container mx-auto text-center">
    <h1 class="text-4xl font-bold mb-4" data-aos="fade-up">
      OnPoint.
    </h1>
    <p class="text-lg text-purple-400" data-aos="fade-up" data-aos-delay="200">
      Das Reisen von Morgen.

    </p>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-10">

    </div>

  </div>
</div>

<style>
  /* Optional: Anpassen von DaisyUI und Tailwind CSS */
  .card-title {
    color: #ff5722; /* Anpassung der Farbpalette */
  }
</style>
