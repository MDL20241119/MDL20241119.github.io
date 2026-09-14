// Public links carry selected controls only. Free text and local records stay out.
const gapKeys = ['schema','cityCode','date','resolution','populatedOnly','combine','distanceOn','distanceM','frequencyOn','frequencyRadius','intervalOn','maximumInterval','wheelchair','reservation','minimumTrips','serviceStart','serviceEnd','activityOn','destinations','destinationRule','departure','deadline','activityFrom','activityTo','dwell','legMinutes','maxWalk','totalWalk','walkSpeed','walkFactor','transfers','activityScope','files'];

export function publicGapProfile(profile) {
  const result = {name:'共有した判定条件',note:''};
  for (const key of gapKeys) if (Object.hasOwn(profile,key)) result[key] = structuredClone(profile[key]);
  return result;
}

export function accessShareUrl(href,{category,city}) {
  const url = new URL(href); url.search=''; url.hash='';
  if (category && category!=='all') url.searchParams.set('category',category);
  if (city && city!=='all') url.searchParams.set('city',city);
  return url.href;
}
