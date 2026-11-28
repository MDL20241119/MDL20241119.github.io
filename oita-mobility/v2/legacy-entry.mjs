const p = new URLSearchParams(location.search);
const h = location.hash.slice(1);
const tripAnchors = new Set(['area-entry','people-work','journey-form','journey-when','result','opportunity-section','people-map']);
const mapAnchors = new Set(['atlas-time-gaps','start-map-frame']);
const oldAnalysis = new Set(['map','ridership','od','forecast','cost','bc','sources']);
if (p.get('view') === 'trip' || tripAnchors.has(h)) {
  p.delete('view');
  location.replace('journey.html' + (p.size ? '?' + p : '') + location.hash);
} else if (mapAnchors.has(h)) {
  const city = /^44\d{3}$/.test(p.get('city') || '') ? p.get('city') : '44201';
  location.replace('atlas.html?city=' + city + '#atlas-time-gaps');
} else if (oldAnalysis.has(h)) {
  location.replace('analysis.html' + location.search + location.hash);
} else if (h === 'atlas-toc') {
  location.replace('tools.html');
}
