// Run the exact browser business bundle in Pyodide, without a browser renderer.
const fs=require('node:fs');
const path=require('node:path');
const {loadPyodide}=require('pyodide');
(async()=>{
  const root=path.resolve(__dirname,'../..');
  const py=await loadPyodide();
  await py.loadPackage('tzdata');
  const bundle=JSON.parse(fs.readFileSync(path.join(root,'danchi-elevator/demo/core-bundle.json'),'utf8'));
  for(const [name,source] of Object.entries(bundle.files)){
    py.FS.mkdirTree('/project/'+name.slice(0,name.lastIndexOf('/')));py.FS.writeFile('/project/'+name,source);
  }
  py.FS.writeFile('/project/demo_runtime.py',fs.readFileSync(path.join(root,'danchi-elevator/demo/demo_runtime.py'),'utf8'));
  py.FS.writeFile('/project/fixtures/browser-seed.json',JSON.stringify(bundle.database_seed));
  py.runPython("import sys; sys.path.insert(0,'/project')");
  py.runPython(fs.readFileSync(path.join(__dirname,'core_acceptance.py'),'utf8'));
  const result=JSON.parse(py.runPython('json.dumps(RESULT)'));
  result.runtime=py.runPython('sys.version');result.pyodide='314.0.7';
  result.scope='PYODIDE_WASM_CORE_NOT_BROWSER_RENDERER_OR_INDEXEDDB';result.checked_at=new Date().toISOString();
  fs.writeFileSync(path.join(__dirname,'wasm-result.json'),JSON.stringify(result,null,2)+'\n');
})().catch(error=>{console.error(error);process.exitCode=1;});
