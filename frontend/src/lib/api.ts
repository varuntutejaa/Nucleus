const API_BASE=(import.meta.env.VITE_NUCLEUS_API_URL as string|undefined)?.replace(/\/$/,'')??''
async function get<T>(path:string):Promise<T>{const response=await fetch(`${API_BASE}${path}`);if(!response.ok)throw new Error(`Nucleus API returned ${response.status}`);return response.json() as Promise<T>}

export type AiopsSummary={raw_count:number;host_count:number}
export type EngineIncident={incident_id:number;host:string;root_metric:string;severity:string;root_alert_id:string;root_timestamp:string;root_value:number;root_score:number;alert_count:number;suppressed_count:number}
export type EngineMetrics={raw_count:number;incident_count:number;suppressed_count:number;reduction_pct:number;host_count:number}
export type EngineResult={incidents:EngineIncident[];metrics:EngineMetrics}
export type SampleAlert={alert_id:string;timestamp:string;host:string;metric:string;severity:string;message:string}

export async function fetchAiopsSummary(){return get<AiopsSummary>('/api/aiops/summary')}

export async function fetchAiopsSample(limit=220){return get<{alerts:SampleAlert[];count:number}>(`/api/aiops/sample?limit=${limit}`)}

export async function runAiopsEngine(){
  const response=await fetch(`${API_BASE}/api/aiops/run`,{method:'POST'})
  if(!response.ok)throw new Error(`Engine run failed: ${response.status}`)
  return response.json() as Promise<EngineResult>
}
