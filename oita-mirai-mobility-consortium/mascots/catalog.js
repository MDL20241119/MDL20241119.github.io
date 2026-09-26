(() => {
  const input = document.getElementById('character-search');
  const cards = [...document.querySelectorAll('#character-list .mascot-card')];
  const count = document.getElementById('result-count');
  const empty = document.getElementById('character-empty');
  input.addEventListener('input', () => {
    const term = input.value.normalize('NFKC').trim().toLocaleLowerCase('ja');
    let visible = 0;
    cards.forEach(card => {
      const matches = card.dataset.search.normalize('NFKC').toLocaleLowerCase('ja').includes(term);
      card.hidden = !matches;
      if (matches) visible++;
    });
    count.textContent = `${visible}案`;
    empty.hidden = visible !== 0;
  });
})();
