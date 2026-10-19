'use strict';

function initializeDraft() {

// This draft does not collect data, submit forms, or persist choices.
document.querySelectorAll('.print-button').forEach((button) => {
  button.addEventListener('click', () => window.print());
});

document.querySelectorAll('.mobile-menu a').forEach((link) => {
  link.addEventListener('click', () => {
    link.closest('details').open = false;
  });
});

// Include the scope details in printouts without changing the reading state.
let wasScopeOpen = false;
const scopeNote = document.querySelector('.scope-note');
window.addEventListener('beforeprint', () => {
  wasScopeOpen = scopeNote.open;
  scopeNote.open = true;
});
window.addEventListener('afterprint', () => {
  scopeNote.open = wasScopeOpen;
});
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDraft, { once: true });
} else {
  initializeDraft();
}
