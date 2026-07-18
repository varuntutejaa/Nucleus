export type Severity = 'critical' | 'warning' | 'info'
export type Alert = { id:string; timestamp:string; service:string; host:string; severity:Severity; message:string; clusterId:string|null; isRootCause:boolean }

export const fmtTime=(iso:string)=>new Date(iso).toLocaleTimeString([], {hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'})
