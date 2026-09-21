// No browser/dependencies required: exercise the page's actual JS with a small DOM stub.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const elements = new Map();
function element() { return {value:'',textContent:'',hidden:false,disabled:false,style:{},
  classList:{add(){},remove(){}},setAttribute(){},append(){},replaceChildren(){},focus(){}}; }
const context = vm.createContext({document:{getElementById(id){
  if(!elements.has(id)) elements.set(id,element()); return elements.get(id);
},createElement:element},TextDecoder,Uint8Array,Date,JSON,atob,
setTimeout(){},clearTimeout(){},setInterval(){},navigator:{}});
const source = fs.readFileSync(path.join(__dirname,'../static/index.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInContext(source,context);
const run = code => vm.runInContext(code,context);
async function test() {
  const scenario=process.argv[2];
  if(scenario==='stale') {
    let resolve, calls=0;
    context.fetch=()=>{calls++;return new Promise(r=>resolve=r);};
    run("session={token:'dummy',user:'Alice',exp:9999999999}; $('username').value='Bob'; $('password').value='test-password'; globalThis.pending=$('auth-form').onsubmit({preventDefault(){}});");
    await run("$('auth-form').onsubmit({preventDefault(){}})");
    assert.equal(calls,1);
    run("$('logout').onclick()");
    resolve({ok:true,status:200,json:async()=>({access_token:'stale-token-must-not-be-opened'})});
    await context.pending;
    assert.equal(run('session'),null);
    assert.equal(run("$('session-actions').hidden"),true);
  } else if(scenario==='unauthorized') {
    context.fetch=async()=>({ok:false,status:401,json:async()=>({detail:'Unauthorized'})});
    run("session={token:'dummy',user:'Alice',exp:9999999999}");
    await run("$('send').onclick()");
    assert.equal(run('session'),null);
    assert.equal(run("$('send').disabled"),true);
    assert.match(run("$('toast').textContent"),/Session expired/);
  } else if(scenario==='errors') {
    assert.equal(run("message({detail:'Safe detail'},400)"),'Safe detail');
    assert.equal(run("message({error:'Safe error'},400)"),'Safe error');
    assert.match(run("message({error:'Rate limit exceeded'},429)"),/Too many requests/);
    context.fetch=async()=>({ok:false,status:502,json:async()=>{throw Error('private server content');}});
    const result=await run("call('/login')");
    assert.equal(result.response.status,502);
    assert.match(result.data.detail,/unreadable response/);
    assert.ok(!JSON.stringify(result.data).includes('private server content'));
  } else { throw Error('Unknown scenario'); }
}
test().catch(()=>{console.error('Frontend regression failed');process.exitCode=1;});
