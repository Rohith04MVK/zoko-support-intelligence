import React,{useState} from 'react';
import TeamInsights from './TeamInsights.jsx';
import {supportSignals} from './support-signals.js';
const wait=n=>n>=86400?`${Math.floor(n/86400)}d ${Math.floor(n%86400/3600)}h`:n>=3600?`${Math.floor(n/3600)}h ${Math.floor(n%3600/60)}m`:`${Math.floor(n/60)}m ${Math.floor(n%60)}s`;
export default function SupportSignals({data,now,onOpen}){
 const [target,setTarget]=useState(()=>{const n=Number(localStorage.getItem('responseTargetMinutes'));return Number.isInteger(n)&&n>=1&&n<=1440?n:5});
 const [draft,setDraft]=useState(String(target));
 const s=supportSignals(data.conversations,data.messages,data.agents,now,target*60);
 const customer=c=>data.customers.find(u=>u.id===c.customer_id)?.name||'Unknown customer';
 function save(e){e.preventDefault();const n=Number(draft);if(Number.isInteger(n)&&n>=1&&n<=1440){setTarget(n);localStorage.setItem('responseTargetMinutes',String(n))}}
 return <><section className="panel support-signals"><div className="section-title"><div><h2>Workload and response target</h2><p>Current ownership and conversations that need a human reply.</p></div></div>
 <form className="target-control" onSubmit={save}><label htmlFor="response-target">First-response target (minutes)</label><input id="response-target" type="number" min="1" max="1440" step="1" required value={draft} onChange={e=>setDraft(e.target.value)}/><button className="secondary">Apply</button><small>Saved in this browser · Elapsed time, including nights and weekends</small></form>
 <div className="signal-totals"><div><strong>{s.rate==null?'—':`${s.rate}%`}</strong><span>First replies within {target} min</span><small>{s.within} of {s.answered} conversations with a human reply</small></div><div><strong>{s.overdue.length}</strong><span>Open chats overdue for a first reply</span><small>No human reply and waiting longer than {target} min</small></div></div>
 <p className="footnote">The percentage covers all captured answered conversations. Unanswered chats are excluded; {s.closedUnanswered} closed without an observed human reply. Changing the target recalculates this view.</p>
 {s.overdue.length>0&&<details className="signal-details"><summary>Review {s.overdue.length} overdue conversations</summary>{s.overdue.map(c=><button className="signal-link" key={c.id} onClick={()=>onOpen(c.id)}>{customer(c)}<span>{wait(Math.max(0,now-c.started_at))} since start →</span></button>)}</details>}
 <div className="workload-scroll"><table className="workload-table"><thead><tr><th>Current owner</th><th>Open chats</th><th>Awaiting human reply</th><th>Longest wait</th></tr></thead><tbody>{s.rows.map(r=><tr key={r.id||'unassigned'}><td>{r.name}</td><td>{r.open}</td><td>{r.waiting.length? <details><summary>{r.waiting.length} · View chats</summary>{r.waiting.map(w=><button className="signal-link" key={w.conversation.id} onClick={()=>onOpen(w.conversation.id)}>{customer(w.conversation)}<span>{wait(w.seconds)} →</span></button>)}</details>:0}</td><td>{r.waiting.length?wait(r.waiting[0].seconds):'—'}</td></tr>)}</tbody></table></div>
 <p className="footnote">Wait starts at the oldest customer message since the last human reply; automated and unidentified replies do not clear it. Closed chats are excluded. Timers update every 15 seconds; use Refresh to fetch new activity. Reassign chats in Zoko.</p>
 </section><TeamInsights data={data} now={now} target={target} onOpen={onOpen}/></>
}
