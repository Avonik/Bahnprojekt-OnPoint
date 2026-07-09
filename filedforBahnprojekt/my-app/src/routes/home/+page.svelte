<script lang="ts">
  interface leg {
    layover_at: string;
    planned_arrival: string;
    planned_departure: string;
    expected_arrival: string;
    expected_departure: string;
    next_train: string;
    next_train_average_departure_delay: number;
    layover_feasible: boolean;
  }

  interface Journey {
    duration: string;
    odds_of_successful_journey: number;
    legs: leg[];
  }

  let startingLocation = ''; // Variable to hold the starting location input
  let endLocation = '';      // Variable to hold the end location input
  let time = '';             // Variable to hold the time input
  let Arrayjourneys: Journey[] = []; // Variable to hold the journeys data

  async function sendData() {
    console.log('sendData function called'); // Log function call
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

      const result = await response.json();
      console.log('Fetched journeys:', result.journeys); // Log the fetched journeys
      Arrayjourneys = [...result.journeys]; // Use spread operator to update Arrayjourneys
      console.log('Updated Arrayjourneys:', Arrayjourneys); // Log the updated Arrayjourneys

    } catch (error) {
      console.error('Error sending data:', error);
    }
  }
</script>

<main class="p-6">
  <h1 class="text-3xl font-bold text-center mb-6">Travel Planner</h1>

  <div class="grid gap-4 max-w-md mx-auto">
    <div>
      <label for="starting" class="block text-sm font-medium text-gray-700">Starting Location:</label>
      <input type="text" id="starting" bind:value={startingLocation} placeholder="Enter starting location"
        class="mt-1 block w-full p-2 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring focus:ring-red-300" />
    </div>

    <div>
      <label for="end" class="block text-sm font-medium text-gray-700">End Location:</label>
      <input type="text" id="end" bind:value={endLocation} placeholder="Enter end location"
        class="mt-1 block w-full p-2 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring focus:ring-red-300" />
    </div>

    <div>
      <label for="time" class="block text-sm font-medium text-gray-700">Time:</label>
      <input type="datetime-local" id="time" bind:value={time}
        class="mt-1 block w-full p-2 border border-gray-300 rounded shadow-sm focus:outline-none focus:ring focus:ring-red-300" />
    </div>

    <button on:click={sendData} class="bg-red-500 text-white font-semibold py-2 px-4 rounded shadow hover:bg-red-600">
      Plan Journey
    </button>
  </div>

  <section class="mt-8">
    <h2 class="text-2xl font-bold mb-4">Journeys</h2>

    {#if Arrayjourneys.length === 0}
      <p class="text-gray-500">No journeys found. Submit your details above.</p>
    {:else}
      <div class="space-y-4">
        {#each Arrayjourneys as journey, index}
          <div class="p-4 bg-white border border-gray-200 rounded shadow-sm">
            <h3 class="text-lg font-semibold mb-2">Journey {index + 1}</h3>
            <p><span class="font-medium">Duration:</span> {journey.duration}</p>
            <p><span class="font-medium">Odds of Success:</span> {journey.odds_of_successful_journey}%</p>
            <div class="mt-4">
              <h4 class="font-medium">Legs:</h4>
              <ul class="list-disc list-inside">
                {#each journey.legs as leg}
                  <li class="mt-2">
                    <p><span class="font-medium">Layover at:</span> {leg.layover_at}</p>
                    <p><span class="font-medium">Planned Arrival:</span> {leg.planned_arrival} |
                      <span class="font-medium">Planned Departure:</span> {leg.planned_departure}</p>
                    <p><span class="font-medium">Expected Arrival:</span> {leg.expected_arrival} |
                      <span class="font-medium">Expected Departure:</span> {leg.expected_departure}</p>
                    <p><span class="font-medium">Next Train:</span> {leg.next_train} |
                      <span class="font-medium">Average Departure Delay:</span> {leg.next_train_average_departure_delay.toFixed(2)} minutes</p>
                    <p><span class="font-medium">Layover Feasible:</span>
                      {leg.layover_feasible ? 'Yes' : 'No'}
                    </p>
                  </li>
                {/each}
              </ul>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </section>
</main>
