import type {Alert,Cluster,Severity} from './mockData'
const API_BASE=(import.meta.env.VITE_NUCLEUS_API_URL as string|undefined)?.replace(/\/$/,'')??''
export type ApiSource='synthetic'|'dataset'
type ApiAlert={id:string;timestamp:string;timestamp_unix:number;service:string;severity:Severity;severity_rank:number;message:string;source:ApiSource}
type ApiCluster={cluster_id:string;root_cause:ApiAlert;suppressed:ApiAlert[];size:number;time_span_seconds:number;explanation:string}
export type NucleusMetrics={raw_count:number;cluster_count:number;noise_count:number;suppressed_count:number;reduction_pct:number;embedding_backend:string;weights_used:{alpha:number;beta:number;gamma:number}|null}
type CorrelatedResponse={clusters:ApiCluster[];noise:ApiAlert[];metrics:NucleusMetrics}
type RawResponse={alerts:ApiAlert[];count:number}
async function get<T>(path:string):Promise<T>{const response=await fetch(`${API_BASE}${path}`);if(!response.ok)throw new Error(`Nucleus API returned ${response.status}`);return response.json() as Promise<T>}
const mapAlert=(a:ApiAlert,clusterId:string|null=null,isRootCause=false):Alert=>({id:a.id,timestamp:a.timestamp,service:a.service,host:`${a.service.replace(/-service$|-api$/,'')}-prod-01`,severity:a.severity,message:a.message,clusterId,isRootCause})
export async function fetchNucleus(source:ApiSource,sensitivity=72){
  const semantic=.15+(sensitivity/100)*.25,temporal=.55-(sensitivity/100)*.2,topology=1-semantic-temporal
  const weights=`alpha=${semantic.toFixed(3)}&beta=${temporal.toFixed(3)}&gamma=${topology.toFixed(3)}`
  const [raw,correlated]=await Promise.all([get<RawResponse>(`/api/alerts/raw?source=${source}`),get<CorrelatedResponse>(`/api/alerts/correlated?source=${source}&${weights}`)])
  const assignments=new Map<string,{clusterId:string;root:boolean}>()
  correlated.clusters.forEach(c=>{assignments.set(c.root_cause.id,{clusterId:c.cluster_id,root:true});c.suppressed.forEach(a=>assignments.set(a.id,{clusterId:c.cluster_id,root:false}))})
  const alerts=raw.alerts.map(a=>{const m=assignments.get(a.id);return mapAlert(a,m?.clusterId??null,m?.root??false)}).sort((a,b)=>b.timestamp.localeCompare(a.timestamp))
  const clusters:Cluster[]=correlated.clusters.map((c,index)=>{const all=[c.root_cause,...c.suppressed],services=[...new Set(all.map(a=>a.service))];return{id:c.cluster_id,title:c.root_cause.message.replace(`${c.root_cause.service}: `,''),rootCauseAlertId:c.root_cause.id,alertIds:all.map(a=>a.id),startTime:c.root_cause.timestamp,endTime:new Date(c.root_cause.timestamp_unix*1000+c.time_span_seconds*1000).toISOString(),confidenceScore:Math.max(.72,.96-index*.015),affectedServices:services,distanceBreakdown:{temporal:Math.round(temporal*200),semantic:Math.round(semantic*220),topology:Math.round(topology*240)},status:'active'}})
  return{alerts,clusters,metrics:correlated.metrics}
}
