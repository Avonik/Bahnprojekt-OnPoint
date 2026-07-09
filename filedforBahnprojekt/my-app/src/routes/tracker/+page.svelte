<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, slide } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import 'aos/dist/aos.css';
  import AOS from 'aos';

  let startingLocation = '';
  let endLocation = '';
  let time = '';
  let data: any;
  let duration = "";

  async function sendData() {
    // Function to send data to the backend
    try {
      const response = await fetch('/api/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          starting_location: startingLocation,
          end_location: endLocation,
          time: time
        }),
      });
      data = await response.json();
    } catch (error) {
      console.error('Error sending data:', error);
    }
    duration = data.journeys.journeys[0].duration;
  }

  onMount(() => {
    AOS.init({
      duration: 1000,
      easing: 'ease-in-out',
      once: true,
    });
  });
</script>

<main class="bg-gray-50 min-h-screen font-sans">
  <!-- Navigation -->
  <nav class="bg-white shadow-md" in:fade={{ duration: 800 }}>
    <div class="container mx-auto px-6 py-4 flex justify-between items-center">
      <a href="#" class="text-3xl font-bold text-indigo-600">Journey Planner</a>
      <div>
        <a href="#" class="text-gray-600 hover:text-indigo-600 mx-4">Home</a>
        <a href="#plan" class="text-gray-600 hover:text-indigo-600 mx-4">Plan Journey</a>
        <a href="#" class="text-gray-600 hover:text-indigo-600 mx-4">Contact</a>
      </div>
    </div>
  </nav>

  <!-- Hero Section -->
  <section class="relative h-screen flex items-center justify-center text-center bg-indigo-600">
    <div class="absolute inset-0 bg-gradient-to-r from-indigo-600 to-purple-600 opacity-75"></div>
    <div class="relative z-10 max-w-2xl mx-auto px-6">
      <h1 class="text-5xl font-extrabold text-white mb-4" in:slide={{ duration: 800, easing: cubicOut }}>Your Journey Begins Here</h1>
      <p class="text-xl text-gray-200 mb-6" in:fade={{ delay: 200, duration: 800 }}>Plan, explore, and embark on unforgettable journeys.</p>
      <a href="#plan" class="inline-block px-8 py-4 bg-white text-indigo-600 font-semibold rounded-full shadow-lg hover:bg-indigo-50 transition duration-300" in:slide={{ delay: 400, duration: 800 }}>Get Started</a>
    </div>
  </section>

  <!-- Features Section -->
  <section class="py-16 bg-white">
    <div class="container mx-auto px-6">
      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold text-gray-800 mb-4" in:fade={{ duration: 800 }}>Why Choose Us</h2>
        <p class="text-gray-600" in:fade={{ delay: 200, duration: 800 }}>We make journey planning effortless and enjoyable.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="text-center" in:fade={{ delay: 200, duration: 800 }}>
          <div class="mb-4">
            <i class="fas fa-map-marked-alt text-6xl text-indigo-600"></i>
          </div>
          <h3 class="text-xl font-semibold text-gray-800 mb-2">Comprehensive Maps</h3>
          <p class="text-gray-600">Navigate with confidence using our detailed maps.</p>
        </div>
        <div class="text-center" in:fade={{ delay: 400, duration: 800 }}>
          <div class="mb-4">
            <i class="fas fa-clock text-6xl text-indigo-600"></i>
          </div>
          <h3 class="text-xl font-semibold text-gray-800 mb-2">Real-Time Updates</h3>
          <p class="text-gray-600">Stay informed with the latest journey information.</p>
        </div>
        <div class="text-center" in:fade={{ delay: 600, duration: 800 }}>
          <div class="mb-4">
            <i class="fas fa-user-friends text-6xl text-indigo-600"></i>
          </div>
          <h3 class="text-xl font-semibold text-gray-800 mb-2">Community Support</h3>
          <p class="text-gray-600">Join a community of fellow travelers.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Journey Planner -->
  <section id="plan" class="py-16 bg-gray-50">
    <div class="container mx-auto px-6">
      <div class="text-center mb-12">
        <h2 class="text-4xl font-bold text-gray-800 mb-4" in:fade={{ duration: 800 }}>Plan Your Journey</h2>
        <p class="text-gray-600" in:fade={{ delay: 200, duration: 800 }}>Get started by entering your journey details below.</p>
      </div>
      <div class="max-w-2xl mx-auto">
        <div class="bg-white shadow-md rounded-lg p-8" in:fade={{ duration: 800 }}>
          <div class="grid gap-6">
            <div class="form-control">
              <label for="starting" class="label">
                <span class="label-text text-lg text-gray-800">Starting Location:</span>
              </label>
              <input type="text" id="starting" bind:value={startingLocation} placeholder="Enter starting location"
                class="input input-bordered w-full" />
            </div>

            <div class="form-control">
              <label for="end" class="label">
                <span class="label-text text-lg text-gray-800">End Location:</span>
              </label>
              <input type="text" id="end" bind:value={endLocation} placeholder="Enter end location"
                class="input input-bordered w-full" />
            </div>

            <div class="form-control">
              <label for="time" class="label">
                <span class="label-text text-lg text-gray-800">Time:</span>
              </label>
              <input type="datetime-local" id="time" bind:value={time} placeholder="Departure Time"
                class="input input-bordered w-full" />
            </div>

            <button on:click={sendData} class="btn bg-indigo-600 text-white mt-6 hover:bg-indigo-700" in:slide={{ duration: 800 }}>
              Plan Journey
            </button>
          </div>
        </div>

        {#if data?.journeys?.journeys?.length}
          <div class="mt-16" in:fade={{ duration: 800 }}>
            <div class="stats shadow">
              <div class="stat">
                <div class="stat-title">Total Journeys</div>
                <div class="stat-value">{data.journeys.journeys.length}</div>
              </div>
            </div>
          </div>

          <div class="mt-12">
            <h2 class="text-3xl font-bold mb-8 text-center text-gray-800" in:fade={{ duration: 800 }}>Journey Details</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
              {#each data.journeys.journeys as journey, index}
                <div class="bg-white shadow-md rounded-lg p-6" in:slide={{ duration: 800, easing: cubicOut }}>
                  <h3 class="text-xl font-semibold text-indigo-600 mb-4">Journey {index + 1}</h3>
                  <p class="text-gray-700"><strong>Duration:</strong> {journey.duration}</p>
                  <p class="text-gray-700"><strong>Number of Layovers:</strong> {journey.legs.length}</p>
                  <p class="text-gray-700"><strong>Odds of Success:</strong> {journey.odds_of_successful_journey}</p>

                  <div class="mt-4">
                    <div tabindex="0" class="collapse collapse-arrow border border-gray-200 bg-white rounded-box">
                      <input type="checkbox" class="peer" />
                      <div class="collapse-title text-lg font-medium text-indigo-600 peer-checked:text-indigo-800">
                        Legs Details
                      </div>
                      <div class="collapse-content">
                        <ul class="list-disc list-inside">
                          {#each journey.legs as leg}
                            <li class="mb-2">
                              <p class="text-gray-700"><strong>Layover at:</strong> {leg.layover_at}</p>
                              <p class="text-gray-700"><strong>Feasible:</strong>
                                {#if leg.layover_feasible}
                                  <span class="text-green-600">Yes</span>
                                {:else}
                                  <span class="text-red-600">No</span>
                                {/if}
                              </p>
                              <p class="text-gray-700"><strong>Next Train:</strong> {leg.next_train}</p>
                            </li>
                          {/each}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  </section>

  <!-- Call to Action -->
  <section class="py-16 bg-gradient-to-r from-indigo-600 to-purple-600">
    <div class="container mx-auto px-6 text-center">
      <h2 class="text-4xl font-bold text-white mb-4" in:fade={{ duration: 800 }}>Ready to Explore?</h2>
      <p class="text-xl text-gray-200 mb-6" in:fade={{ delay: 200, duration: 800 }}>Join us today and start your adventure.</p>
      <a href="#plan" class="inline-block px-8 py-4 bg-white text-indigo-600 font-semibold rounded-full shadow-lg hover:bg-indigo-50 transition duration-300" in:slide={{ delay: 400, duration: 800 }}>Plan Your Journey</a>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-white py-6" in:fade={{ duration: 800 }}>
    <div class="container mx-auto px-6 flex justify-between items-center">
      <p class="text-gray-600">&copy; {new Date().getFullYear()} Journey Planner. All rights reserved.</p>
      <div>
        <a href="#" class="text-gray-600 hover:text-indigo-600 mx-2"><i class="fab fa-facebook-f"></i></a>
        <a href="#" class="text-gray-600 hover:text-indigo-600 mx-2"><i class="fab fa-twitter"></i></a>
        <a href="#" class="text-gray-600 hover:text-indigo-600 mx-2"><i class="fab fa-instagram"></i></a>
      </div>
    </div>
  </footer>
</main>

<style>
  /* Custom Fonts */
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

  html {
    scroll-behavior: smooth;
  }

  main {
    font-family: 'Poppins', sans-serif;
  }

  /* Custom Animations */
  .fade-in {
    animation: fadeIn 2s ease-in-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>
