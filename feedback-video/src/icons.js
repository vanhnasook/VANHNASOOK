// Line icons on a 24x24 grid, drawn with currentColor strokes.
const P = {
  phone: '<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M10.5 18.5h3"/>',
  laptop: '<rect x="4" y="4.5" width="16" height="11" rx="1.5"/><path d="M2 19h20"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/><path d="M12 15v2"/>',
  shield: '<path d="M12 2.5l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6z"/>',
  shieldCheck: '<path d="M12 2.5l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6z"/><path d="M8.5 12.2l2.5 2.5 4.5-4.8"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20.5a6.5 6.5 0 0 1 13 0"/><circle cx="17" cy="9" r="2.8"/><path d="M16.5 14.1a5.5 5.5 0 0 1 5.5 6.4"/>',
  badge: '<rect x="4.5" y="3" width="15" height="18" rx="2"/><circle cx="12" cy="10" r="2.8"/><path d="M8 17.5a4 4 0 0 1 8 0"/><path d="M10 6h4"/>',
  bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
  warning: '<path d="M12 3.5l9.5 16.5h-19z"/><path d="M12 10v4.5M12 17.2v.3"/>',
  megaphone: '<path d="M3 10v4a1 1 0 0 0 1 1h3l6 4V5L7 9H4a1 1 0 0 0-1 1z"/><path d="M16.5 9.2a4 4 0 0 1 0 5.6M19.2 6.6a8 8 0 0 1 0 10.8"/>',
  dots: '<circle cx="5.5" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="18.5" cy="12" r="1.3" fill="currentColor"/>',
  chat: '<path d="M4 4.5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H10l-5 4v-4H4a1 1 0 0 1-1-1v-10a1 1 0 0 1 1-1z"/><path d="M8 10.5h.01M12 10.5h.01M16 10.5h.01"/>',
  star: '<path d="M12 2.8l2.8 5.8 6.4.8-4.7 4.4 1.2 6.4L12 17.1l-5.7 3.1 1.2-6.4-4.7-4.4 6.4-.8z"/>',
  growth: '<path d="M3 20.5h18"/><path d="M5 16l5-5 4 3 6-7"/><path d="M15 7h5v5"/>',
  pencil: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
  pin: '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="9.5" r="2"/><path d="M21 16l-5-5-10 9"/>',
  file: '<path d="M6 2h8l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M14 2v5h5M8 13h8M8 17h5"/>',
  upload: '<path d="M7 18.5a5 5 0 0 1-.9-9.9A6 6 0 0 1 17.6 7.6 4.5 4.5 0 0 1 17 18.5"/><path d="M12 12.5v8M9 15.5l3-3 3 3"/>',
  send: '<path d="M21.5 2.5L10.5 13.5"/><path d="M21.5 2.5l-7 19-4-8-8-4z"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  headset: '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="2.5" y="13.5" width="4.5" height="6.5" rx="1.5"/><rect x="17" y="13.5" width="4.5" height="6.5" rx="1.5"/><path d="M19.5 20a3.5 3.5 0 0 1-3.5 2h-2.5"/>',
  whatsapp: '<path d="M3.5 20.5l1.4-4.3a8.6 8.6 0 1 1 3.1 3z"/><path d="M9 8.3c.2 3.5 3.2 6.5 6.7 6.7l1-1.5-2.2-1.1-1 .9a4.4 4.4 0 0 1-2.8-2.8l.9-1L10.5 7.3z"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3.5 6.5l8.5 6.5 8.5-6.5"/>',
  eyeOff: '<path d="M3 3l18 18"/><path d="M10.6 6.1A9.6 9.6 0 0 1 12 6c5 0 8.5 4 9.5 6-.5 1-1.4 2.3-2.7 3.5M6.6 6.6C4.6 8 3.2 10 2.5 12c1 2 4.5 6 9.5 6 1.6 0 3-.4 4.3-1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  heart: '<path d="M12 20s-7.5-4.6-9-9.3C2 7.4 4.3 4.5 7.4 4.5c2 0 3.4 1.1 4.6 2.7 1.2-1.6 2.6-2.7 4.6-2.7 3.1 0 5.4 2.9 4.4 6.2C19.5 15.4 12 20 12 20z"/>',
  arrowRight: '<path d="M4 12h15M13 6l6 6-6 6"/>',
  corner: '<rect x="5" y="2" width="14" height="20" rx="2.5"/><path d="M11 6h2"/>',
};

export function icon(name, cls = '', extra = '') {
  return `<svg class="ic ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${extra}>${P[name]}</svg>`;
}

// Material "touch_app" hand, used as the tapping finger. Fingertip is at about (11.5, 5.5).
export const HAND = 'M9 11.24V7.5C9 6.12 10.12 5 11.5 5S14 6.12 14 7.5v3.74c1.21-.81 2-2.18 2-3.74C16 5.01 13.99 3 11.5 3S7 5.01 7 7.5c0 1.56.79 2.93 2 3.74zm9.84 4.63l-4.54-2.26c-.17-.07-.35-.11-.54-.11H13v-6c0-.83-.67-1.5-1.5-1.5S10 6.67 10 7.5v10.74l-3.43-.72c-.08-.01-.15-.03-.24-.03-.31 0-.59.13-.79.33l-.79.8 4.94 4.94c.27.27.65.44 1.06.44h6.79c.75 0 1.33-.55 1.44-1.28l.75-5.27c.01-.07.02-.14.02-.2 0-.62-.38-1.16-.91-1.38z';
