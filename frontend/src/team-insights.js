const WEEK=7*86400;
function median(values){if(!values.length)return null;const sorted=[...values].sort((a,b)=>a-b);const mid=Math.floor(sorted.length/2);return sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2}
export function responseTrends(conversations,now,targetSeconds){
 function period(from,to){
  const rows=conversations.filter(c=>c.started_at>=from&&c.started_at<to);
  const answered=rows.filter(c=>c.first_response_at!=null&&c.first_response_at<=now);
  const closed=rows.filter(c=>c.closed_at!=null&&c.closed_at<=now);
  const within=answered.filter(c=>c.first_response_at-c.started_at<=targetSeconds).length;
  return {from,to,total:rows.length,answered:answered.length,closed:closed.length,within,
   frt:median(answered.map(c=>c.first_response_at-c.started_at)),
   resolution:median(closed.map(c=>c.closed_at-c.started_at)),
   rate:answered.length?100*within/answered.length:null};
 }
 return {current:period(now-WEEK,now),previous:period(now-2*WEEK,now-WEEK)};
}
export function followUpPressure(conversations,messages,now){
 const result=[];
 for(const c of conversations){
  if(c.closed_at!=null)continue;
  const history=messages.filter(m=>m.conversation_id===c.id&&m.at<=now&&!m.purpose?.startsWith('csat_'));
  const lastHuman=Math.max(-Infinity,...history.filter(m=>m.direction==='outgoing'&&m.sender_kind==='human').map(m=>m.at));
  const incoming=[...new Map(history.filter(m=>m.direction==='incoming'&&m.at>lastHuman).map(m=>[m.id,m])).values()].sort((a,b)=>a.at-b.at);
  if(incoming.length>=2)result.push({conversation:c,messages:incoming,seconds:Math.max(0,now-incoming[0].at)});
 }
 return result.sort((a,b)=>b.messages.length-a.messages.length||b.seconds-a.seconds);
}
