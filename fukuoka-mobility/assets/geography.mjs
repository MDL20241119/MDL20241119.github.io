// Coordinate sanity check for Fukuoka and nearby journey endpoints.
// Include the northern islands and western Itoshima; this is not a municipal boundary test.
export function isFukuokaAreaPoint(point) {
  return !!point && Number.isFinite(point.lat) && Number.isFinite(point.lon)
    && point.lat >= 32.7 && point.lat <= 34.4
    && point.lon >= 129.9 && point.lon <= 131.5;
}
