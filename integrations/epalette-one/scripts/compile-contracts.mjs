import fs from 'node:fs';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import standaloneCode from 'ajv/dist/standalone/index.js';
const ajv=new Ajv({strict:false,allErrors:true,code:{source:true,esm:true},validateFormats:true});addFormats(ajv);ajv.addFormat('int32',{type:'number',validate:n=>Number.isInteger(n)&&n>=-2147483648&&n<=2147483647});ajv.addFormat('double',{type:'number',validate:Number.isFinite});
const exports={};
for(const file of ['demand','qr-maas']){
 const doc=JSON.parse(fs.readFileSync(`lib/integration/contracts/${file}.json`,'utf8'));ajv.addSchema(doc,file);
 for(const [path,ops]of Object.entries(doc.paths))for(const [method,op]of Object.entries(ops)){
  if(!op.operationId)continue;const prefix=(file+'_'+op.operationId).replaceAll('-','_');
  const ptr=`${file}#/paths/${path.replaceAll('~','~0').replaceAll('/','~1')}/${method}`;
  if(op.requestBody){const ref=op.requestBody.$ref?file+op.requestBody.$ref:`${ptr}/requestBody`;const pointer=ref+'/content/application~1json/schema';exports[prefix+'_request']=pointer;}
  for(const [code,response]of Object.entries(op.responses??{})){
   const ref=response.$ref?file+response.$ref:`${ptr}/responses/${code}`;const resolved=response.$ref?doc.components.responses[response.$ref.split('/').pop()]:response;
   if(resolved.content?.['application/json']?.schema)exports[prefix+'_'+code]=ref+'/content/application~1json/schema';
  }
 }
}
let output=standaloneCode(ajv,exports);
output=output.replaceAll('require("ajv-formats/dist/formats").fullFormats','fullFormats').replaceAll('require("ajv/dist/runtime/ucs2length").default','ucs2length');
output='// Generated from pinned COMmmmONS schemas. Do not edit.\nimport {fullFormats} from "ajv-formats/dist/formats.js";\nimport ucs2length from "ajv/dist/runtime/ucs2length.js";\n'+output;
fs.writeFileSync('lib/integration/contracts/validators.mjs',output);
console.log(`${Object.keys(exports).length} request/response validators generated`);
