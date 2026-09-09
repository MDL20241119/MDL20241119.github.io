export const TIME_VALUE = 304379 / (137.3 * 60);
export function calculateBC({share,minutes,annualCost,rate}) {
  if (![share,minutes,annualCost,rate].every(Number.isFinite) || share<0 || share>1 || minutes<0 || annualCost<0 || rate<0) return null;
  const annualBenefit=5391*share*minutes*TIME_VALUE;
  const factor=rate===0?5:(1-(1+rate)**-5)/rate;
  return {annualBenefit,factor,pvBenefit:annualBenefit*factor,pvCost:annualCost*factor,
    bc:annualCost>0?annualBenefit/annualCost:null,npv:(annualBenefit-annualCost)*factor,
    requiredMinutes:share>0?annualCost/(5391*share*TIME_VALUE):null,
    requiredShare:minutes>0?annualCost/(5391*minutes*TIME_VALUE):null};
}
export function forecastSeries(values) {
  const last=values.at(-1),r=values.slice(-3),slope=(r[2]-r[0])/2,mean=r.reduce((a,b)=>a+b,0)/3;
  return {flat:[last,last],linear:[Math.max(0,mean+2*slope),Math.max(0,mean+3*slope)]};
}
