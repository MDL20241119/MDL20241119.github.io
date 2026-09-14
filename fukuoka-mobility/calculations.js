export const TIME_VALUE = 30;
export function calculateBC({share,minutes,annualCost,rate,users=10000,timeValue=TIME_VALUE}) {
  if (![share,minutes,annualCost,rate,users,timeValue].every(Number.isFinite) || share<0 || share>1 || minutes<0 || annualCost<0 || rate<0 || users<0 || timeValue<0) return null;
  const annualBenefit=users*share*minutes*timeValue;
  const factor=rate===0?5:(1-(1+rate)**-5)/rate;
  return {annualBenefit,factor,pvBenefit:annualBenefit*factor,pvCost:annualCost*factor,
    bc:annualCost>0?annualBenefit/annualCost:null,npv:(annualBenefit-annualCost)*factor,
    requiredMinutes:share>0&&users*timeValue>0?annualCost/(users*share*timeValue):null,
    requiredShare:minutes>0&&users*timeValue>0?annualCost/(users*minutes*timeValue):null};
}
export function forecastSeries(values) {
  const last=values.at(-1),r=values.slice(-3),slope=(r[2]-r[0])/2,mean=r.reduce((a,b)=>a+b,0)/3;
  return {flat:[last,last],linear:[Math.max(0,mean+2*slope),Math.max(0,mean+3*slope)]};
}
