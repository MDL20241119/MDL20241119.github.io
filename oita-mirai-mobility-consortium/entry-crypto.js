(function (root) {
  'use strict';
  const spec = { version: 1, algorithm: 'PBKDF2-SHA256', iterations: 210000 };
  const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
  const unhex = value => new Uint8Array(value.match(/../g).map(x => parseInt(x, 16)));
  function valid(config) {
    return config && Object.keys(config).sort().join(',') === 'algorithm,id,iterations,salt,verifier,version'
      && config.version === spec.version && config.algorithm === spec.algorithm
      && config.iterations === spec.iterations && /^[a-f0-9]{32}$/.test(config.id)
      && /^[a-f0-9]{32}$/.test(config.salt) && /^[a-f0-9]{64}$/.test(config.verifier);
  }
  async function derive(password, salt) {
    const bytes = new TextEncoder().encode(password);
    try {
      const key = await crypto.subtle.importKey('raw', bytes, 'PBKDF2', false, ['deriveBits']);
      return hex(await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt:unhex(salt),iterations:spec.iterations},key,256));
    } finally { bytes.fill(0); }
  }
  async function create(password) {
    if (typeof password !== 'string' || !password.trim() || password.length < 4 || password.length > 128) throw new Error('length');
    const salt = hex(crypto.getRandomValues(new Uint8Array(16)));
    return {...spec,id:hex(crypto.getRandomValues(new Uint8Array(16))),salt,verifier:await derive(password,salt)};
  }
  async function verify(password, config) {
    if (!valid(config) || typeof password !== 'string' || !password.trim() || password.length === 0 || password.length > 128) return false;
    const value = await derive(password,config.salt);
    let difference = 0;
    for (let i=0;i<value.length;i++) difference |= value.charCodeAt(i)^config.verifier.charCodeAt(i);
    return difference === 0;
  }
  root.OitaEntryCrypto = Object.freeze({create,verify,valid});
})(globalThis);
