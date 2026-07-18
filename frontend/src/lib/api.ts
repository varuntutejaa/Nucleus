const API_BASE=(import.meta.env.VITE_NUCLEUS_API_URL as string|undefined)?.replace(/\/$/,'')??''
async function get<T>(path:string):Promise<T>{const response=await fetch(`${API_BASE}${path}`);if(!response.ok)throw new Error(`Nucleus API returned ${response.status}`);return response.json() as Promise<T>}

export type AiopsSummary={raw_count:number;host_count:number;hosts:string[]}
export type EngineIncidentMember={alert_id:string;timestamp:string;host:string;metric:string;severity:string;value:number;root_score:number;is_root:boolean}
export type EngineIncident={incident_id:number;host:string;root_metric:string;severity:string;root_alert_id:string;root_timestamp:string;root_value:number;root_score:number;alert_count:number;suppressed_count:number;members:EngineIncidentMember[]}
export type EngineMetrics={raw_count:number;incident_count:number;suppressed_count:number;reduction_pct:number;host_count:number}
export type EngineResult={incidents:EngineIncident[];metrics:EngineMetrics}
export type SampleAlert={alert_id:string;timestamp:string;host:string;metric:string;value:number;severity:string;message:string}

export async function fetchAiopsSummary(){return get<AiopsSummary>('/api/aiops/summary')}

export async function fetchAiopsSample(limit=220){return get<{alerts:SampleAlert[];count:number}>(`/api/aiops/sample?limit=${limit}`)}

async function postEngine(path:string){
  const response=await fetch(`${API_BASE}${path}`,{method:'POST'})
  if(!response.ok)throw new Error(`Engine run failed: ${response.status}`)
  return response.json() as Promise<EngineResult>
}
export const DEMO_SIZES=[100,1000,10000,100000] as const
export type DemoSize=typeof DEMO_SIZES[number]
export async function runAiopsSampleEngine(size:DemoSize=100,includeMembers=false){return postEngine(`/api/aiops/run-sample?size=${size}&include_members=${includeMembers}`)}
export async function runAiopsEngine(includeMembers=false){return postEngine(`/api/aiops/run?include_members=${includeMembers}`)}
