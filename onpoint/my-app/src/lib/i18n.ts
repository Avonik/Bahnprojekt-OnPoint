import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export type Language = 'de' | 'en';

export const language = writable<Language>('de');

export function initializeLanguage() {
  if (!browser) return;

  const storedLanguage = window.localStorage.getItem('onpoint-language');
  setLanguage(storedLanguage === 'en' ? 'en' : 'de');
}

export function setLanguage(value: Language) {
  language.set(value);

  if (!browser) return;

  window.localStorage.setItem('onpoint-language', value);
  document.documentElement.lang = value;
}
