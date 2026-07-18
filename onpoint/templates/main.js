document.getElementById('journeyForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const startingLocation = document.getElementById('startingLocation').value;
    const endLocation = document.getElementById('endLocation').value;
    const departureTime = document.getElementById('departureTime').value;

    const requestBody = {
        starting_location: startingLocation,
        end_location: endLocation,
        time: departureTime
    };

    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = ''; // Clear previous results

    try {
        const response = await fetch('/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();
        const journeys = data.journeys;

        if (journeys.length === 0) {
            resultsContainer.innerHTML = '<p>No journeys found.</p>';
        } else {
            journeys.forEach((journey, index) => {
                const journeyDiv = document.createElement('div');
                journeyDiv.classList.add('card', 'bg-white', 'shadow-lg', 'p-4');

                journeyDiv.innerHTML = `
                    <h3 class="text-lg font-bold">Journey ${index + 1}</h3>
                    <p><strong>Duration:</strong> ${journey.duration}</p>
                    <p><strong>Success Rate:</strong> ${journey.odds_of_successful_journey}%</p>
                    <div class="mt-2">
                        <h4 class="font-bold">Legs:</h4>
                        <ul class="list-disc pl-5">
                            ${journey.legs.map(leg => `
                                <li>
                                    <strong>${leg.layover_at}</strong> - Feasible: ${leg.layover_feasible ? 'Yes' : 'No'}
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `;
                resultsContainer.appendChild(journeyDiv);
            });
        }

        document.getElementById('journeyResults').classList.remove('hidden');
    } catch (error) {
        resultsContainer.innerHTML = '<p>Error fetching journey data. Please try again.</p>';
    }
});
