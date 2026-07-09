<script lang="ts">
  let name = '';
  let email = '';
  let message = '';
  let successMessage = '';

  const handleSubmit = async (e: Event) => {
    e.preventDefault();

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, email, message }),
      });

      if (res.ok) {
        successMessage = 'Your message has been sent!';
        name = '';
        email = '';
        message = '';
      } else {
        successMessage = 'Failed to send message.';
      }
    } catch (error) {
      console.error(error);
      successMessage = 'An error occurred.';
    }
  };
</script>

<section class="py-12" data-aos="fade-up">
  <div class="container mx-auto px-4">
    <div class="max-w-xl mx-auto bg-white shadow-md rounded-lg p-8">
      <h2 class="text-2xl font-bold mb-6 text-center">Get in Touch</h2>
      {#if successMessage}
        <div class="mb-4 text-green-500">{successMessage}</div>
      {/if}
      <form on:submit|preventDefault={handleSubmit}>
        <div class="mb-4">
          <label class="block text-gray-700">Name</label>
          <input
            type="text"
            bind:value={name}
            class="input input-bordered w-full"
            required
          />
        </div>
        <div class="mb-4">
          <label class="block text-gray-700">Email</label>
          <input
            type="email"
            bind:value={email}
            class="input input-bordered w-full"
            required
          />
        </div>
        <div class="mb-4">
          <label class="block text-gray-700">Message</label>
          <textarea
            bind:value={message}
            class="textarea textarea-bordered w-full"
            rows="5"
            required
          ></textarea>
        </div>
        <div class="text-center">
          <button type="submit" class="btn btn-primary w-full">
            Send Message
          </button>
        </div>
      </form>
    </div>
  </div>
</section>
