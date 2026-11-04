// Test-only module boundaries. No production runtime switch or authentication bypass.
import {registerHooks} from 'node:module';
import {AsyncLocalStorage} from 'node:async_hooks';
globalThis.__epaletteRequestContext=new AsyncLocalStorage();
registerHooks({resolve(specifier,context,next){const modules={
 'cloudflare:workers':'export const env={get DB(){return globalThis.__epaletteTestDB}};',
 'next/headers':'export async function headers(){return globalThis.__epaletteRequestContext.getStore()??new Headers()}',
 'next/navigation':'export function redirect(path){throw new Error("redirect:"+path)}',
 };if(modules[specifier])return {url:'data:text/javascript,'+encodeURIComponent(modules[specifier]),shortCircuit:true};return next(specifier,context)}});
