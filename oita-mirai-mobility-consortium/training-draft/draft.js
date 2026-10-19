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

// Include the budget scope in printouts without changing the reading state.
let wasBudgetOpen = false;
const budgetNote = document.querySelector('.budget-note');
window.addEventListener('beforeprint', () => {
  wasBudgetOpen = budgetNote.open;
  budgetNote.open = true;
});
window.addEventListener('afterprint', () => {
  budgetNote.open = wasBudgetOpen;
});
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDraft, { once: true });
} else {
  initializeDraft();
}
