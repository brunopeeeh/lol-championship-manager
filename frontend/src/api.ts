export const attributes = {mec:'Mecânica',lan:'Laning',agr:'Agressividade',sob:'Sobrevivência',mac:'Macro',vis:'Visão',obj:'Objetivos',tf:'Teamfight',con:'Consistência',ver:'Versatilidade',ada:'Adaptação',dec:'Decisão'} as const;
export type Attribute = keyof typeof attributes;
export interface Portrait {image_url:string;source_url:string;provider:string;retrieved_at:string;note:string;rights_status:string;photo_season:number|null}
export interface RosterSource {url:string;provider:string;published_at:string;retrieved_at:string;type:string}
export interface RosterEvent {name:string;team:string;kind:string;reported_date:string;effective_date:string|null;source_ids:string[];note:string;confidence:string}
export interface RosterContext {current_team:null;current_status:string;snapshots:{team:string;competition:string;reference_date:string;source_ids:string[]}[];events:RosterEvent[];sources:Record<string,RosterSource>}
export interface RosterCatalog {warning:string;reviewed_at:string;current_rosters_verified:boolean;sources:Record<string,RosterSource>;snapshots:{id:string;competition:string;reference_date:string;note:string;teams:{name:string;players:{name:string;position:string;player_id:string|null;identity_status:string;portrait?:Portrait|null;later_events:RosterEvent[]}[]}[]}[]}
export interface Player {portrait?:Portrait|null;roster_context?:RosterContext;id:string;player_id:string;name:string;team:string;team_id:string;region:string;season:number;split?:string;position:string;overall:number|null;potential:number|null;confidence:number;games:number;date_to:string}
export interface Evidence {status:string;games:number;metrics:string[];coverage?:number}
export interface Champion {champion:string;games:number;wins:number|null;win_rate?:number|null;score?:number|null;status?:string}
export interface Profile extends Player {attributes:Record<Attribute,number|null>;attribute_details:Record<Attribute,Evidence>;historical_games:number;split_games?:number;opponent_games?:number;partial_games:number;form:number|null;method:string;champion_pool:Champion[];rating_history:{season:number;position:string;overall:number|null;confidence:number;evaluated_at?:string;method?:string}[];stints:{team:string;from:string;to:string}[];career?:{team:string;from:string;to:string|null}[];measured_metrics:Record<string,{mean:number;games:number}>;sources:{url:string;filename?:string;sha256?:string;retrieved_at:string;license:string}[];calibration:{status:string;games?:number;confidence?:number};date_from:string}
export interface Page {items:Player[];total:number;page:number;page_size:number;storage:string}
export interface Team {id:string;name:string;region:string;players?:Player[];as_of?:string}
export interface Filters {regions:string[];seasons:number[];teams:Team[];storage:string}
export interface Dashboard {storage:string;players:number;teams:number;matches:number;ratings:number;global_overalls:number;regions:string[];distribution:{from:number;to:number;count:number}[];attribute_status:Record<string,number>;data_through?:string;last_import?:string;calibration_status:string;model?:string}
export async function api<T>(path:string,signal?:AbortSignal):Promise<T> {const r=await fetch('/api/v3'+path,{signal});if(!r.ok){const error=await r.json().catch(()=>({}));throw new Error(error.detail||`Falha de conexão (${r.status})`)}return r.json() as Promise<T>}
export const rating=(value:number|null|undefined)=>value==null?'N/D':String(value);
export const percent=(value:number)=>Math.round(value*100)+'%';
