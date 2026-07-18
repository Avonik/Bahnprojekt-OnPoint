import type { Config } from 'tailwindcss';
import daisyui from 'daisyui'; // Import DaisyUI as an ES module

export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],

  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        customFont: ['"Comic Sans MS"', 'cursive'],
        myFont: ['Jaro'],
        Poppins: ['Poppins'],
        // You can add other fonts here
      },
    },
  },

  plugins: [
    daisyui, // Use the imported plugin here
  ],

  daisyui: {
    themes: ['light', 'dark'], // Optional: Customize DaisyUI themes
    base: true,
    utils: true,
    logs: true,
    rtl: true,
  },
} satisfies Config;


