<script lang="ts">


  let startingLocation = ''; // Variable to hold the starting location input
  let endLocation = '';      // Variable to hold the end location input
  let time = '';             // Variable to hold the time input
  let data: any;
  let duration: "";

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
      data = await response.json();

    } catch (error) {
      console.error('Error sending data:', error);
    }
    console.log('Received data:', data);
    alert(JSON.stringify(data));
    alert(JSON.stringify(data.journeys.journeys[0].duration));
    duration = data.journeys.journeys[0].duration;
  }
</script>

<main class="p-6">

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

  {#if duration}
    <div class="mt-6 p-4 bg-gray-100 rounded shadow">
      <h2 class="text-xl font-semibold mb-2">Journey Details</h2>
      <p><strong>Duration:</strong> {data.journeys.journeys[0].duration}</p>
      <p><strong>legs:</strong> {JSON.stringify(data.journeys.journeys[0].legs)}</p>
      <p><strong>legs:</strong> {data.journeys.journeys.length}</p>
    </div>
  {/if}

  {#if data?.journeys?.journeys?.length}
  <div class="mt-6 p-4 bg-gray-100 rounded shadow">
    <h2 class="text-xl font-semibold mb-2">Journey Details</h2>
    <ul>
      {#each data.journeys.journeys as journey, index}
        <li class="mb-4">
          <h3 class="text-lg font-semibold">Journey {index + 1}</h3>
          <p><strong>Duration:</strong> {journey.duration}</p>
          <p><strong>Number of Layovers:</strong> {journey.legs.length}</p>

          <!-- Loop over the legs of each journey -->
          <ul class="ml-4 mt-2">
            {#each journey.legs as leg}
              <li class="mb-2">
                <p><strong>Layover at:</strong> {leg.layover_at}</p>
                <p><strong>feasable:</strong> {leg.layover_feasible}</p>
                <p><strong>next train:</strong> {leg.next_train}</p>
                <!-- Include other leg details as needed -->
              </li>
            {/each}
          </ul>
        </li>
      {/each}
    </ul>
    <p><strong>Total Journeys:</strong> {data.journeys.journeys.length}</p>
  </div>
{/if}

</main>
