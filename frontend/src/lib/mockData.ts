export type Severity = 'critical' | 'warning' | 'info'
export type Alert = { id:string; timestamp:string; service:string; host:string; severity:Severity; message:string; clusterId:string|null; isRootCause:boolean }
export type Cluster = { id:string; title:string; rootCauseAlertId:string; alertIds:string[]; startTime:string; endTime:string; confidenceScore:number; affectedServices:string[]; distanceBreakdown:{temporal:number;semantic:number;topology:number}; status:'active'|'acknowledged'|'resolved' }

const now = Date.now()
const services = ['postgres-primary','checkout-api','payments-api','inventory','orders-worker','edge-gateway','auth-service','search-api']
const hosts = ['db-prod-01','k8s-use1-042','k8s-use1-018','edge-us-03','worker-07','redis-prod-02']
const storms = [
  {id:'INC-2481',title:'Database connection pool exhaustion',msg:'Connection pool exhausted; requests waiting > 30s',root:'postgres-primary',severity:'critical' as Severity,count:47},
  {id:'INC-2479',title:'Load balancer node degradation',msg:'Upstream connect timeout from edge node',root:'edge-gateway',severity:'critical' as Severity,count:31},
  {id:'INC-2476',title:'Worker disk pressure cascade',msg:'Disk usage above 94%; job execution degraded',root:'orders-worker',severity:'warning' as Severity,count:18},
]
let seq=6200
export const clusters: Cluster[] = storms.map((s,ci)=>{
  const ids = Array.from({length:s.count},()=>`ALT-${++seq}`)
  return {id:s.id,title:s.title,rootCauseAlertId:ids[0],alertIds:ids,startTime:new Date(now-(ci+1)*26*60000).toISOString(),endTime:new Date(now-ci*11*60000).toISOString(),confidenceScore:[.96,.91,.87][ci],affectedServices:services.slice(0,[6,4,3][ci]),distanceBreakdown:[{temporal:94,semantic:89,topology:97},{temporal:88,semantic:84,topology:93},{temporal:91,semantic:76,topology:82}][ci],status:ci===1?'acknowledged':'active'}
})
const stormAlerts: Alert[] = clusters.flatMap((c,ci)=>c.alertIds.map((id,i)=>({id,timestamp:new Date(new Date(c.startTime).getTime()+i*23000).toISOString(),service:i===0?storms[ci].root:services[(i+ci)%services.length],host:hosts[(i+ci)%hosts.length],severity:i===0?storms[ci].severity:(i%5===0?'critical':i%3===0?'info':'warning'),message:i===0?storms[ci].msg:i%3===0?'Latency SLO burn rate exceeded (14.2x)':'Dependency health check failed after 3 retries',clusterId:c.id,isRootCause:i===0})))
const noiseAlerts: Alert[] = Array.from({length:22},(_,i)=>({id:`ALT-${++seq}`,timestamp:new Date(now-i*78000).toISOString(),service:services[i%services.length],host:hosts[i%hosts.length],severity:i%7===0?'warning':'info',message:i%2?'CPU throttling detected on container':'Replica sync lag above baseline',clusterId:null,isRootCause:false} as Alert))
export const alerts: Alert[] = [...stormAlerts,...noiseAlerts].sort((a,b)=>b.timestamp.localeCompare(a.timestamp))

export const fmtTime=(iso:string)=>new Date(iso).toLocaleTimeString([], {hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'})
export const liveMessages=['Elevated p99 latency detected','Pod restart count exceeded threshold','Health check timed out','Queue consumer lag increasing']
