import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createAPI } from '../src/api.js';

const json = value => new Response(JSON.stringify(value), {headers:{'Content-Type':'application/json'}});
test('unrelated scientific requests start independently', async () => {
  const original=globalThis.fetch;let release;const pending=new Promise(resolve=>release=resolve);const calls=[];
  globalThis.fetch=async path=>{calls.push(path);if(path.includes('/search')){await pending;return json({direct:[],related:[],documentary:[],discovery:[]});}return json({items:[],total:0});};
  try {const api=createAPI();const slow=api.search('invented fixture');await api.catalog();assert.equal(calls.length,2);release();await slow;}finally{globalThis.fetch=original;}
});
test('cancel during operation creation cancels the eventual server identifier',async()=>{
  const original=globalThis.fetch;let release;const pending=new Promise(resolve=>release=resolve);let canceled=0;
  globalThis.fetch=async path=>{if(path.endsWith('/cancel')){canceled++;return json({status:'canceled'});}await pending;return json({operation_id:'fixture-operation'});};
  try{const controller=new AbortController();const answer=createAPI().chat({message:'fixture'},controller.signal);controller.abort();release();await assert.rejects(answer,{name:'AbortError'});assert.ok(canceled>=1);}finally{globalThis.fetch=original;}
});
test('scoped read cancellation forwards abort and never supplies a cached stale result',async()=>{
  const original=globalThis.fetch;let received;
  globalThis.fetch=async(path,{signal})=>{received=signal;return json({items:[],total:0});};
  try{const api=createAPI();const controller=new AbortController();const scoped=api.scoped(controller.signal);await scoped.catalog();assert.equal(received,controller.signal);controller.abort();await assert.rejects(scoped.catalog(),{name:'AbortError'});}finally{globalThis.fetch=original;}
});
