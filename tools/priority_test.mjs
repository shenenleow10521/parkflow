// Deterministic invariant checks for the shared driver/operator demo ledger.
// Run with Node 24+: node tools/priority_test.mjs
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { stripTypeScriptTypes } from 'node:module';
const storage=new Map();let lock=Promise.resolve();
const context={console,Date,Intl,Math,Event,TextEncoder,assert,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},navigator:{locks:{request:(_name,fn)=>{const next=lock.then(fn);lock=next.catch(()=>{});return next;}}},window:{dispatchEvent(){},addEventListener(){},removeEventListener(){}}};
vm.createContext(context);
const source=stripTypeScriptTypes(fs.readFileSync('src/shared/priority.ts','utf8'),{mode:'transform'}).replace(/^export /gm,'');
vm.runInContext(source,context);
await vm.runInContext(`(async()=>{
 await priorityEnsure();let d=priorityRead(),c=priorityCounts(priorityPool(d,'klgcc'));
 assert.equal(c.total,100);assert.equal(c.occupied,72);assert.equal(c.reserved,6);assert.equal(c.atp,20);
 const date=priorityDemoDate();const results=await Promise.all(Array.from({length:25},(_,i)=>priorityReserve('klgcc',date,'18:45','WXY '+(1000+i))));
 assert.equal(results.filter(r=>r.ok).length,20,'concurrent submissions must respect safety capacity');
 d=priorityRead();c=priorityCounts(priorityPool(d,'klgcc'));assert.equal(c.atp,0);assert.equal(c.reserved,26);assert.equal(c.occupied,72);
 assert.equal((await priorityAdmit('klgcc','WALK 1','walkin')).ok,false,'walk-in cannot consume commitments');
 const b=results[0].booking;const duplicate=await priorityReserve('klgcc',date,'18:45',b.plate);assert.equal(duplicate.booking.id,b.id);
 assert.equal((await priorityAdmit('klgcc','WRONG','booking',b.id)).ok,false,'plate mismatch');
 await priorityClock('klgcc',b.id);const entry=await priorityAdmit('klgcc',b.plate,'booking',b.id);assert.equal(entry.ok,true);
 c=priorityCounts(priorityPool(priorityRead(),'klgcc'));assert.equal(c.occupied,73);assert.equal(c.reserved,25);assert.equal(c.atp,0,'arrival transfers a claim, not another deduction');
 assert.equal((await priorityAdmit('klgcc',b.plate,'booking',b.id)).ok,false,'duplicate booking entry');
 await priorityCancel(results[1].booking.id);c=priorityCounts(priorityPool(priorityRead(),'klgcc'));assert.equal(c.atp,1);
 assert.equal((await priorityAdmit('klgcc','WALK 2','walkin')).ok,true);assert.equal((await priorityAdmit('klgcc','WALK 2','walkin')).ok,false,'duplicate plate entry');
 console.log('PASS concurrent capacity guard, duplicate reservation, plate/window checks, booked-entry transfer and walk-ins');
 await priorityFault('klgcc','exit');const before=priorityCounts(priorityPool(priorityRead(),'klgcc')).occupied;await priorityExit('klgcc');assert.equal(priorityCounts(priorityPool(priorityRead(),'klgcc')).occupied,before,'egress fault cannot create an unverified vacancy');
 assert.equal((await priorityReserve('klgcc',date,'19:00','FAULT 1')).ok,false);await priorityFault('klgcc','reconnect');assert.equal(priorityReady(priorityRead().ops.klgcc),false);
 assert.equal((await priorityReconcile('klgcc',before-1,'Count checked')).ok,false);assert.equal(priorityRead().ops.klgcc.paused,true);
 assert.equal((await priorityReconcile('klgcc',before,'Physical demo count checked')).ok,true);assert.equal(priorityReady(priorityRead().ops.klgcc),true);
 console.log('PASS fault pause, preserved egress, reconnection lock and verified reconciliation');
 await priorityClock('klgcc');assert.equal(priorityRead().bookings.find(x=>x.id===results[2].booking.id).status,'expired');
 await priorityExit('klgcc');assert.equal(priorityCounts(priorityPool(priorityRead(),'klgcc')).occupied,before-1);
 const mallOther=priorityCounts(priorityPool(priorityRead(),'kleast'));assert.equal(mallOther.occupied,72);assert.equal(mallOther.reserved,6,'mall isolation');
 await priorityDeckScenario('klgcc');c=priorityCounts(priorityPool(priorityRead(),'klgcc'));assert.equal(c.occupied,82);assert.equal(c.reserved,12);assert.equal(c.atp,4);assert.equal(priorityRead().bookings.find(x=>x.id===b.id).status,'checked-in','scenario preserves driver visits');
 const x=await priorityReserve('klgcc',date,'20:00','PRESERVE');await priorityDeckScenario('klgcc');assert.equal(priorityRead().bookings.find(v=>v.id===x.booking.id).status,'confirmed');
 const prev=JSON.stringify(priorityRead().pools.klgcc);await priorityPlan('klgcc','accepted','Reviewed assumptions');assert.equal(JSON.stringify(priorityRead().pools.klgcc),prev,'shadow plan cannot alter capacity');
 d=priorityRead();for(const mall of Object.keys(PRIORITY_MALLS)){const pool=priorityPool(d,mall),c=priorityCounts(pool,d.ops[mall].safety);assert.equal(c.occupied+c.reserved+c.available,100);assert.equal(c.reserved,d.bookings.filter(x=>x.mall===mall&&x.status==='confirmed').length,'one ledger claim per protected slot');}
 assert.ok(d.ops.klgcc.logs.some(x=>x.action==='Booked entry approved'&&x.bookingId===b.id));assert.ok(d.ops.klgcc.logs.some(x=>x.action==='Counts reconciled; service resumed'));
 console.log('PASS expiry, verified exit, mall isolation, 82/12/2/4 pitch scenario, protected user records, shadow review and traceable audit');
})()`,context);
// Rendering regression: user-facing screens must retain clear state labels and no navigation/tier flow.
context.esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
context.document={getElementById:()=>({innerHTML:'',classList:{toggle(){}},scrollTop:0}),querySelectorAll:()=>[]};
let driver=stripTypeScriptTypes(fs.readFileSync('src/mobile/app.ts','utf8'),{mode:'transform'}).replace(/^import[^\n]*\n/gm,'');driver=driver.slice(0,driver.lastIndexOf('if (document.readyState'));
vm.runInContext(driver,context);
await vm.runInContext(`(async()=>{const html=driverForm()+driverZone()+driverProfile();assert.ok(html.includes('Reserved')&&html.includes('Occupied')&&html.includes('100 total priority bays'));assert.ok(!/Gold|navigation|tier/i.test(html));DRV_APP.selected=DRV_APP.data.bookings.find(b=>b.source==='driver'&&b.status==='checked-in').id;assert.ok(driverConfirmation().includes('Entry Verified'));await priorityFault('klgcc','count');DRV_APP.data=priorityRead();assert.ok(driverForm().includes('disabled')&&driverForm().includes('paused'));console.log('PASS driver state rendering, clear status labels, checked-in confirmation and fault pause');})()`,context);
